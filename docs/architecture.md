AXON ARCHITECTURE

This document describes the system architecture and design decisions behind Axon.

HIGH-LEVEL OVERVIEW

                     User's Browser
  +------------------+              +------------------+
  |  Dashboard       |<-------------|  WebSocket       |
  |  (HTML/JS)       |  Real-time   |  Connection      |
  +------------------+              +------------------+
            |
            | HTTPS/WSS
            |
+-----------------------------------------------------------+
|              Cloudflare Edge Network                      |
|                                                           |
|  +-------------------------------------------------------+|
|  |  Worker (Entry Point - worker.py)                    ||
|  |  • Routes WebSocket -> Durable Object                ||
|  |  • Routes API calls -> honeypot.py                   ||
|  |  • Serves dashboard HTML                             ||
|  +---------------+------------------+--------------------+|
|                  |                  |                     |
|    +-------------v-------------+  +-v-----------------+  |
|    |  Durable Object           |  |  Honeypot Handler|  |
|    |  (traffic_monitor.py)     |  |  (honeypot.py)   |  |
|    |                           |  |                  |  |
|    |  • WebSocket Server       |  |  • Extract       |  |
|    |  • Broadcast to clients   |  |    Features      |  |
|    |  • Session management     |  |  • Classify      |  |
|    +---------------------------+  |  • Log to D1     |  |
|                                   |  • Broadcast     |  |
|                                   +-----+------+------+  |
|                                         |      |         |
|              +--------------------------+      |         |
|              |                                 |         |
|    +---------v---------+      +---------v---------+     |
|    |   Workers AI      |      |   D1 Database     |     |
|    |   (ML Inference)  |      |   (SQLite)        |     |
|    |                   |      |                   |     |
|    |  • Model runs     |      |  • Traffic log    |     |
|    |    on GPU         |      |  • Analytics      |     |
|    |  • < 100ms        |      |  • History        |     |
|    +-------------------+      +-------------------+     |
|                                                          |
+----------------------------------------------------------+


COMPONENT DETAILS

1. Worker (worker.py)

Purpose: Entry point for all requests. Acts as a router.

Responsibilities:
- Route WebSocket upgrade requests to Durable Object
- Route API requests to honeypot handler
- Serve dashboard HTML (or redirect to Pages)
- Handle CORS if needed

Code Location: src/worker.py

Request Flow:

Request -> on_fetch() -> 
  /ws -> Durable Object
  /dashboard -> HTML response
  /* -> honeypot handler


2. Durable Object (traffic_monitor.py)

Purpose: Coordinate WebSocket connections and broadcast classifications in real-time.

Why Durable Objects?
- Single point of coordination (all dashboards connect to same instance)
- Stateful (maintains WebSocket connections)
- Low latency (runs close to users)
- Built-in WebSocket support

Responsibilities:
- Accept WebSocket connections from dashboards
- Maintain list of active sessions
- Broadcast classification events to all connected clients
- Clean up dead connections

Code Location: src/traffic_monitor.py

Key Methods:
- fetch() - Handles WebSocket upgrade
- webSocketMessage() - Receives messages from clients
- webSocketClose() - Cleanup on disconnect
- broadcast() - Send data to all clients

Performance Notes:
- Uses WebSocket Hibernation API to reduce costs
- Only charged for active processing time
- Can handle thousands of concurrent connections per instance


3. Honeypot Handler (honeypot.py)

Purpose: Process incoming traffic and classify it.

Responsibilities:
- Extract features from HTTP requests
- Classify traffic (ML model or heuristics)
- Log to D1 database
- Broadcast to connected dashboards
- Return innocuous response

Code Location: src/honeypot.py

Feature Extraction (features.py):
- Request path and method
- User-Agent parsing
- IP geolocation (from Cloudflare)
- Path entropy calculation
- Header anomaly detection
- Timing patterns

Classification Pipeline:

Request -> Extract Features -> Classify -> [Log to D1, Broadcast, Return]

Phase 1 (No ML yet): Uses Cloudflare's Bot Management score + simple heuristics
Phase 2 (After training): Uses trained model via Workers AI


4. D1 Database

Purpose: Store traffic logs for analysis and training.

Schema:

CREATE TABLE traffic (
    id INTEGER PRIMARY KEY,
    timestamp INTEGER,
    path TEXT,
    method TEXT,
    ip TEXT,
    country TEXT,
    user_agent TEXT,
    prediction TEXT,      -- 'attack' or 'legit'
    confidence REAL,      -- 0.0 to 1.0
    bot_score INTEGER,    -- Cloudflare bot score
    created_at DATETIME
);

Indexes:
- idx_timestamp - Fast time-based queries
- idx_prediction - Fast filtering by classification

Access Pattern:
- Writes: Every request (async, non-blocking)
- Reads: Analytics queries, model training data export


5. Workers AI (Post-Training)

Purpose: Run ML inference at the edge.

Model Format: ONNX (exported from your training pipeline)

Deployment:

prediction = await env.AI.run('@cf/user/axon-classifier', {
    'input': features
})

Benefits:
- Global deployment (runs everywhere)
- GPU acceleration
- Sub-100ms latency
- No separate inference server needed


6. Dashboard (dashboard.html)

Purpose: Real-time visualization of traffic classification.

Components:
- Stats Cards: Total requests, attacks, legit traffic, req/min
- Live Feed: Scrolling log of classified requests
- Connection Status: WebSocket health indicator

Technology:
- Vanilla JavaScript (no frameworks)
- WebSocket for real-time updates
- Chart.js (optional, for visualizations)

WebSocket Protocol:

// Client -> Server (optional commands)
{ "type": "ping" }
{ "type": "get_stats" }

// Server -> Client (classification events)
{
    "timestamp": 1704153600000,
    "path": "/admin",
    "method": "GET",
    "ip": "1.2.3.4",
    "country": "CN",
    "prediction": "attack",
    "confidence": 0.95
}


DATA FLOW

Incoming Request Flow:

1. Request hits Worker
   |
2. Extract features (path, headers, IP, etc.)
   |
3. Classify request
   |-> Phase 1: Cloudflare bot score + heuristics
   |-> Phase 2: Workers AI ML model
   |
4. Parallel operations:
   |-> Log to D1 (async)
   |-> Broadcast to dashboards (async)
   |
5. Return HTTP 200 OK (boring response)


Dashboard Update Flow:

1. Classification event occurs
   |
2. Honeypot calls TrafficMonitor.broadcast()
   |
3. Durable Object sends to all WebSocket sessions
   |
4. Dashboard receives event
   |
5. Update stats and feed in real-time


SCALING CONSIDERATIONS

Horizontal Scaling

Workers: Automatically scale to handle any request volume
- No configuration needed
- Pay per request
- Sub-millisecond cold starts

Durable Objects: One instance per unique ID
- idFromName("global") means single instance for all dashboards
- Can shard by region/user if needed
- Handles thousands of WebSocket connections

Cost Optimization

D1 Database:
- Free tier: 5GB storage, 5 million reads/day
- Batching writes if high volume

Workers AI:
- Free tier: 10,000 neurons/day
- Caching predictions for repeated patterns

Durable Objects:
- WebSocket Hibernation API reduces costs 10-100x
- Only charged when actively processing


SECURITY

Honeypot Safety
- Returns boring responses (no info disclosure)
- Logs everything but doesn't interact
- Rate limiting via Cloudflare (built-in)

Dashboard Access
- Consider adding authentication (Cloudflare Access)
- CORS configuration if needed
- WebSocket origin validation

Data Privacy
- IP addresses logged (consider anonymization for production)
- GDPR compliance considerations
- Data retention policy


PERFORMANCE BENCHMARKS

Request Latency (without ML):
- Feature extraction: ~5ms
- D1 write: ~10ms (async)
- WebSocket broadcast: ~5ms
- TOTAL: ~20ms (not blocking response)

Request Latency (with ML):
- Above + Workers AI inference: ~50-100ms
- Still non-blocking if async

WebSocket Latency:
- Classification -> Dashboard: ~50-200ms
- Depends on geographic distance


FUTURE ENHANCEMENTS

- Model versioning and A/B testing
- Attack pattern analysis
- Automatic retraining pipeline
- Multi-tenancy support
- Advanced visualization (charts, heatmaps)
- Integration with external threat intel
- Raspberry Pi edge deployment option
