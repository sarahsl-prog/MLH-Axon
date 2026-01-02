API REFERENCE

This document describes all API endpoints, WebSocket protocol, and data formats used by Axon.

REST API ENDPOINTS

Base URL: https://axon.your-subdomain.workers.dev

1. Honeypot Endpoint

GET|POST|PUT|DELETE /*
Description: Catch-all endpoint that logs and classifies all traffic
Authentication: None (it's a honeypot)
Rate Limit: None (we want to see all attacks)

Request:
- Any HTTP method
- Any path
- Any headers
- Any body

Response:
- Status: 200 OK
- Body: "OK"
- Purpose: Boring response to not tip off attackers

Example:

curl -X GET https://axon.your-subdomain.workers.dev/admin
Response: OK


2. Dashboard Endpoint

GET /dashboard
Description: Serves the dashboard HTML
Authentication: Optional (configure in production)
Rate Limit: None

Response:
- Status: 200 OK
- Content-Type: text/html
- Body: Dashboard HTML

Example:

curl https://axon.your-subdomain.workers.dev/dashboard


3. WebSocket Endpoint

GET /ws
Description: Upgrades to WebSocket for real-time updates
Protocol: WebSocket
Authentication: Optional

Connection:

const ws = new WebSocket('wss://axon.your-subdomain.workers.dev/ws');

Connection Headers:
- Upgrade: websocket
- Connection: Upgrade
- Sec-WebSocket-Version: 13
- Sec-WebSocket-Key: <random>


4. Health Check (Optional)

GET /health
Description: Simple health check endpoint
Authentication: None
Rate Limit: None

Response:
{
    "status": "ok",
    "timestamp": 1704153600000,
    "version": "1.0.0"
}


5. Stats API (Optional)

GET /api/stats
Description: Get aggregate statistics
Authentication: Required
Rate Limit: 100 requests/hour

Response:
{
    "total_requests": 150000,
    "attacks_blocked": 45000,
    "legit_traffic": 105000,
    "attack_rate": 0.30,
    "requests_last_hour": 5000,
    "top_attack_types": [
        {"type": "path_traversal", "count": 12000},
        {"type": "sql_injection", "count": 8000},
        {"type": "wp_login", "count": 6000}
    ]
}


WEBSOCKET PROTOCOL

Connection Lifecycle

1. Client initiates WebSocket connection
2. Server accepts and adds to session list
3. Server broadcasts classification events to all clients
4. Client can send commands (optional)
5. Connection closed -> cleanup


Message Format

All messages are JSON strings.

Server -> Client Messages

Classification Event:

{
    "type": "classification",
    "timestamp": 1704153600000,
    "path": "/admin",
    "method": "GET",
    "ip": "1.2.3.4",
    "country": "CN",
    "user_agent": "curl/7.68.0",
    "prediction": "attack",
    "confidence": 0.95,
    "bot_score": 10
}

Connection Confirmation:

{
    "type": "connected",
    "timestamp": 1704153600000,
    "session_id": "abc123"
}

Error Message:

{
    "type": "error",
    "message": "Internal server error",
    "code": 500
}


Client -> Server Messages (Optional)

Ping:

{
    "type": "ping"
}

Response:
{
    "type": "pong",
    "timestamp": 1704153600000
}


Get Statistics:

{
    "type": "get_stats"
}

Response:
{
    "type": "stats",
    "total_requests": 150000,
    "attacks_blocked": 45000,
    "requests_per_min": 42
}


Filter Events:

{
    "type": "filter",
    "prediction": "attack"  // or "legit" or "all"
}


WebSocket Error Codes

1000 - Normal closure
1001 - Going away (e.g., browser tab closed)
1002 - Protocol error
1003 - Unsupported data
1008 - Policy violation (e.g., rate limit)
1011 - Internal server error


DATA FORMATS

Classification Object

{
    "timestamp": 1704153600000,           // Unix timestamp (ms)
    "path": "/admin/login",              // Request path
    "method": "POST",                    // HTTP method
    "ip": "1.2.3.4",                     // Client IP
    "country": "CN",                     // ISO country code
    "user_agent": "curl/7.68.0",        // User-Agent header
    "prediction": "attack",              // "attack" or "legit"
    "confidence": 0.95,                  // 0.0 to 1.0
    "bot_score": 10,                     // 0 to 100 (Cloudflare)
    "features": {                        // Optional: extracted features
        "path_entropy": 3.2,
        "ua_is_bot": true,
        "has_sql_pattern": false
    }
}


Feature Vector

When calling the ML model:

{
    "path_length": 25,
    "path_entropy": 3.2,
    "has_query_params": 1,
    "num_slashes": 3,
    "num_dots": 1,
    "has_admin": 1,
    "has_wp": 0,
    "has_php": 0,
    "has_env": 0,
    "has_sql": 0,
    "has_etc": 0,
    "method_get": 1,
    "method_post": 0,
    "ua_length": 100,
    "ua_is_bot": 1,
    "ua_is_browser": 0,
    "bot_score": 10,
    "high_risk_country": 1
}


Database Schema

traffic table:

Column          Type        Description
--------------  ----------  ---------------------------
id              INTEGER     Primary key (auto-increment)
timestamp       INTEGER     Unix timestamp (ms)
path            TEXT        Request path
method          TEXT        HTTP method
ip              TEXT        Client IP address
country         TEXT        ISO country code
user_agent      TEXT        User-Agent header
prediction      TEXT        "attack" or "legit"
confidence      REAL        0.0 to 1.0
bot_score       INTEGER     Cloudflare bot score (0-100)
created_at      DATETIME    ISO timestamp


RESPONSE CODES

Standard HTTP Status Codes

200 OK - Request successful
400 Bad Request - Invalid request format
401 Unauthorized - Authentication required
403 Forbidden - Access denied
404 Not Found - Endpoint doesn't exist
429 Too Many Requests - Rate limit exceeded
500 Internal Server Error - Server error
503 Service Unavailable - Temporary outage


Custom Error Responses

{
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Too many requests",
        "retry_after": 60
    }
}


AUTHENTICATION

Bearer Token (if enabled)

Request:

GET /api/stats
Authorization: Bearer your-token-here

Response if invalid:

401 Unauthorized
{
    "error": {
        "code": "INVALID_TOKEN",
        "message": "Invalid or expired token"
    }
}


API VERSIONING

Current Version: v1

Base URL includes version:
https://axon.your-subdomain.workers.dev/api/v1/

Future versions will use:
https://axon.your-subdomain.workers.dev/api/v2/


RATE LIMITS

Default Limits:

- Honeypot endpoints: None (unlimited)
- WebSocket connections: 100 per IP
- API endpoints: 100 requests/hour per IP
- Dashboard: 1000 requests/hour per IP

Rate Limit Headers:

X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704153600


When rate limited:

429 Too Many Requests
Retry-After: 60
{
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Rate limit exceeded. Try again in 60 seconds."
    }
}


PAGINATION

For endpoints that return lists:

Request:

GET /api/traffic?page=1&limit=100

Response:

{
    "data": [...],
    "pagination": {
        "page": 1,
        "limit": 100,
        "total": 15000,
        "pages": 150
    }
}


FILTERING

Filter query parameters:

GET /api/traffic?prediction=attack&country=CN&from=2024-01-01&to=2024-01-31

Supported filters:
- prediction: "attack" or "legit"
- country: ISO country code
- method: HTTP method
- from: Start date (YYYY-MM-DD)
- to: End date (YYYY-MM-DD)
- ip: Client IP address


SORTING

Sort query parameters:

GET /api/traffic?sort=timestamp&order=desc

Supported sort fields:
- timestamp (default)
- confidence
- bot_score

Supported orders:
- desc (default)
- asc


WEBHOOKS (Future)

Register webhook for events:

POST /api/webhooks
{
    "url": "https://your-server.com/webhook",
    "events": ["attack_detected", "high_confidence"],
    "filters": {
        "confidence": ">0.9"
    }
}

Webhook payload:

POST https://your-server.com/webhook
{
    "event": "attack_detected",
    "timestamp": 1704153600000,
    "data": {
        // Classification object
    }
}


CLIENT LIBRARIES

JavaScript/Node.js

// WebSocket client
const ws = new WebSocket('wss://axon.your-subdomain.workers.dev/ws');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Classification:', data);
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};


Python

import asyncio
import websockets
import json

async def connect():
    uri = "wss://axon.your-subdomain.workers.dev/ws"
    
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Classification: {data}")

asyncio.run(connect())


cURL

# Send test traffic
curl -X GET https://axon.your-subdomain.workers.dev/admin

# Get stats
curl -H "Authorization: Bearer token" \
  https://axon.your-subdomain.workers.dev/api/stats


EXAMPLES

Example 1: Monitor live traffic

const ws = new WebSocket('wss://axon.your-subdomain.workers.dev/ws');
const attacks = [];

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.prediction === 'attack') {
        attacks.push(data);
        console.log(`Attack detected from ${data.ip}: ${data.path}`);
    }
};


Example 2: Query historical data

async function getAttacks(startDate, endDate) {
    const response = await fet
