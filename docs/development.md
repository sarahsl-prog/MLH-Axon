DEVELOPMENT GUIDE

This guide covers local development, testing, and customization of Axon.

LOCAL DEVELOPMENT SETUP

Running Locally

# Start the development server
uv run pywrangler dev

# Or with hot reload
uv run pywrangler dev --live-reload

# With custom port
uv run pywrangler dev --port 3000


Development Workflow

1. Make changes to Python files in src/
2. Save - Changes are automatically detected
3. Test - Visit http://localhost:8787
4. Iterate - Repeat


Project Structure

axon/
├── src/
│   ├── worker.py           # Main entry point
│   ├── traffic_monitor.py  # Durable Object (WebSocket)
│   ├── honeypot.py         # Traffic classification
│   └── features.py         # Feature extraction
├── public/
│   └── dashboard.html      # Frontend
├── docs/
│   └── *.txt              # Documentation
├── tests/
│   └── test_*.py          # Unit tests
├── schema.sql             # Database schema
├── wrangler.toml          # Cloudflare configuration
├── pyproject.toml         # Python dependencies
└── README.md              # Project overview


TESTING

Unit Tests

Create tests in tests/ directory:

tests/test_features.py:

import pytest
from src.features import get_request_entropy, parse_user_agent


def test_request_entropy():
    # Low entropy (repeated characters)
    assert get_request_entropy("aaaaaaa") < 1.0

    # High entropy (random)
    assert get_request_entropy("/a1B2c3D4") > 2.0

    # Empty string
    assert get_request_entropy("") == 0


def test_parse_user_agent_bot():
    ua = "Mozilla/5.0 (compatible; Googlebot/2.1)"
    result = parse_user_agent(ua)
    assert result['is_bot'] == True


def test_parse_user_agent_browser():
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0"
    result = parse_user_agent(ua)
    assert result['is_bot'] == False
    assert result['client'] == 'chrome'


Run tests:

pytest tests/


Integration Testing

Test the full flow locally:

# Terminal 1: Start dev server
uv run pywrangler dev

# Terminal 2: Send test requests
curl http://localhost:8787/test
curl http://localhost:8787/.env
curl -A "curl/7.68.0" http://localhost:8787/admin

# Check D1 logs
wrangler d1 execute axon-db --local \
  --command="SELECT * FROM traffic ORDER BY timestamp DESC LIMIT 5;"


WebSocket Testing

tests/test_websocket.py:

import asyncio
import websockets


async def test_websocket_connection():
    uri = "ws://localhost:8787/ws"

    async with websockets.connect(uri) as websocket:
        # Should connect successfully
        print("Connected!")

        # Send a test message
        await websocket.send("ping")

        # Receive response
        response = await websocket.recv()
        print(f"Received: {response}")

        # Wait for some traffic events
        for i in range(5):
            event = await websocket.recv()
            print(f"Event {i}: {event}")


if __name__ == "__main__":
    asyncio.run(test_websocket_connection())


Run:

python tests/test_websocket.py


CUSTOMIZING AXON

Adding New Features

Step 1: Add feature extraction logic to features.py:

def detect_sql_injection(url, params):
    """Detect potential SQL injection attempts"""
    sql_patterns = ["'", "OR", "1=1", "UNION", "SELECT"]
    full_string = url + str(params)

    matches = sum(1 for pattern in sql_patterns
                  if pattern.lower() in full_string.lower())

    return {
        'has_sql_pattern': matches > 0,
        'sql_pattern_count': matches
    }


Step 2: Use it in honeypot.py:

def extract_features(request):
    # ... existing features ...

    features['sql_injection'] = detect_sql_injection(
        request.url,
        dict(request.query)
    )

    return features


Step 3: Update D1 schema if needed:

ALTER TABLE traffic ADD COLUMN sql_injection_detected INTEGER DEFAULT 0;


Customizing Classification Logic

Before ML training, you can improve heuristics:

async def classify_request(features):
    """Improved heuristic classification"""

    score = 0

    # Check user agent
    if features['ua_parsed']['is_bot']:
        score += 40

    # Check path entropy (high = suspicious)
    if features['path_entropy'] > 4.0:
        score += 30

    # Check for common attack paths
    attack_paths = ['admin', '.env', 'wp-login', 'phpmyadmin']
    if any(path in features['path'].lower() for path in attack_paths):
        score += 30

    # Check SQL injection
    if features.get('sql_injection', {}).get('has_sql_pattern'):
        score += 20

    return {
        'label': 'attack' if score > 50 else 'legit',
        'confidence': min(score / 100, 1.0),
        'score': score
    }


Customizing the Dashboard

Add new stat card to dashboard.html:

<div class="stat-card">
    <div class="stat-value" id="sql-injection-count">0</div>
    <div class="stat-label">SQL Injections</div>
</div>


Update JavaScript:

function handleTrafficUpdate(data) {
    // ... existing code ...

    // Track SQL injections
    if (data.sql_injection_detected) {
        stats.sqlInjections = (stats.sqlInjections || 0) + 1;
        document.getElementById('sql-injection-count').textContent =
            stats.sqlInjections;
    }
}


Adding Charts

Install Chart.js (already in template):

<canvas id="attackChart" width="400" height="200"></canvas>

<script>
const ctx = document.getElementById('attackChart').getContext('2d');
const chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Attacks per Minute',
            data: [],
            borderColor: '#ff4444',
            tension: 0.1
        }]
    },
    options: {
        responsive: true,
        scales: {
            y: { beginAtZero: true }
        }
    }
});

// Update chart when new data arrives
function updateChart(timestamp, attackCount) {
    chart.data.labels.push(new Date(timestamp).toLocaleTimeString());
    chart.data.datasets[0].data.push(attackCount);

    // Keep last 20 data points
    if (chart.data.labels.length > 20) {
        chart.data.labels.shift();
        chart.data.datasets[0].data.shift();
    }

    chart.update();
}
</script>


DEBUGGING

View Logs

# Stream logs in real-time
wrangler tail

# Filter by worker name
wrangler tail --name axon

# Filter by status
wrangler tail --status error


Debug Durable Objects

Add logging to traffic_monitor.py:

async def broadcast(self, data):
    print(f"Broadcasting to {len(self.sessions)} sessions")
    print(f"Data: {json.dumps(data)}")

    # ... rest of method


View in logs:

wrangler tail --name axon


Inspect D1 Database

# Query locally
wrangler d1 execute axon-db --local \
  --command="SELECT * FROM traffic LIMIT 10;"

# Query production
wrangler d1 execute axon-db \
  --command="SELECT COUNT(*) as total FROM traffic;"

# Export data for analysis
wrangler d1 export axon-db --output=data.sql


Test WebSocket Connection

Use wscat tool:

npm install -g wscat

# Connect to local
wscat -c ws://localhost:8787/ws

# Connect to production
wscat -c wss://axon.your-subdomain.workers.dev/ws


PERFORMANCE OPTIMIZATION

Reduce Cold Starts

Python Workers have memory snapshots to reduce cold starts. Optimize by:

1. Minimize imports: Only import what you need
2. Pre-compute values: Calculate at module level
3. Use compatibility dates: Newer dates = faster snapshots


Optimize D1 Queries

# BAD: Synchronous writes block response
await env.DB.prepare("INSERT ...").bind(...).run()
return Response("OK")

# GOOD: Async writes don't block
asyncio.create_task(
    env.DB.prepare("INSERT ...").bind(...).run()
)
return Response("OK")  # Returns immediately


Batch WebSocket Broadcasts

# Instead of broadcasting every single request
# Buffer and broadcast in batches every 100ms

async def buffered_broadcast(self):
    while True:
        await asyncio.sleep(0.1)  # 100ms

        if self.buffer:
            await self.broadcast(self.buffer)
            self.buffer = []


COMMON DEVELOPMENT TASKS

Add a New Endpoint

src/worker.py:

async def on_fetch(request, env):
    # ... existing routes ...

    if path == "api/stats":
        from stats import get_stats
        return await get_stats(env)


Add Authentication

async def verify_token(request):
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        return False

    # Verify token (use Workers KV for token storage)
    # ...
    return True

async def on_fetch(request, env):
    # Protect admin endpoints
    if request.url.startswith("/admin/"):
        if not await verify_token(request):
            return Response("Unauthorized", status=401)

    # ... rest of routing


Environment Variables

Add to wrangler.toml:

[vars]
ENVIRONMENT = "development"
MAX_REQUESTS_PER_MIN = "100"


Access in code:

async def on_fetch(request, env):
    environment = env.ENVIRONMENT
    max_rate = int(env.MAX_REQUESTS_PER_MIN)


NEXT STEPS

- Training Guide (training.txt) - Train your ML model
- Deployment Guide (deployment.txt) - Deploy to production
- API Reference (api-reference.txt) - API documentation
