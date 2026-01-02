# Deployment Guide

This guide covers deploying Axon to production and configuring it for optimal performance.

## Production Deployment Checklist

Before deploying to production:

- [ ] Database schema applied
- [ ] Environment variables configured
- [ ] Custom domain set up (optional)
- [ ] Monitoring configured
- [ ] Rate limiting configured
- [ ] Dashboard authentication (if needed)
- [ ] Backup strategy in place

## Deploying to Cloudflare

### Step 1: Configure Production Environment

**wrangler.toml:**

```toml
name = "axon-prod"
main = "src/worker.py"
compatibility_date = "2024-04-01"
compatibility_flags = ["python_workers"]

[env.production]
vars = { ENVIRONMENT = "production" }

[[env.production.d1_databases]]
binding = "DB"
database_name = "axon-prod-db"
database_id = "your-production-db-id"

[env.production.ai]
binding = "AI"

[[durable_objects.bindings]]
name = "TRAFFIC_MONITOR"
class_name = "TrafficMonitor"
script_name = "axon-prod"
```

### Step 2: Create Production Database

```bash
# Create production D1 database
wrangler d1 create axon-prod-db

# Apply schema
wrangler d1 execute axon-prod-db --file=schema.sql

# Verify
wrangler d1 execute axon-prod-db --command="SELECT name FROM sqlite_master WHERE type='table';"
```

### Step 3: Deploy Worker

```bash
# Deploy to production
uv run pywrangler deploy --env production

# Or deploy to default environment
uv run pywrangler deploy
```

Your Worker will be live at: `https://axon-prod.your-subdomain.workers.dev`

### Step 4: Deploy Dashboard to Pages

```bash
# Create Pages project
wrangler pages project create axon-dashboard

# Deploy
cd public/
wrangler pages deploy . --project-name=axon-dashboard --branch=main
```

Your dashboard will be live at: `https://axon-dashboard.pages.dev`

### Step 5: Update Dashboard WebSocket URL

**Edit `public/dashboard.html`:**

```javascript
const WS_URL = 'wss://axon-prod.your-subdomain.workers.dev/ws';
```

**Redeploy dashboard:**

```bash
wrangler pages deploy . --project-name=axon-dashboard
```

## Custom Domain Setup

### Option 1: Custom Domain for Worker

1. Add domain in Cloudflare dashboard:
   **Workers & Pages > axon-prod > Settings > Domains & Routes**

2. Add custom domain:
   - Domain: `axon.yourdomain.com`
   - Cloudflare will create DNS records automatically

3. Update WebSocket URL in dashboard to use custom domain

### Option 2: Custom Domain for Dashboard

1. In Pages project settings:
   **Pages > axon-dashboard > Custom domains**

2. Add domain:
   - Domain: `dashboard.yourdomain.com`
   - Configure DNS as instructed

3. SSL certificate is automatic

## Environment Variables

**Recommended production environment variables:**

```toml
[env.production.vars]
ENVIRONMENT = "production"
MAX_REQUESTS_PER_MIN = "1000"
ENABLE_DEBUG_LOGS = "false"
DASHBOARD_AUTH_ENABLED = "true"
```

**Access in code:**

```python
async def on_fetch(request, env):
    is_production = env.ENVIRONMENT == "production"
    max_rate = int(env.MAX_REQUESTS_PER_MIN)
```

## Monitoring and Observability

### Enable Cloudflare Analytics

1. Go to **Workers & Pages > axon-prod**
2. Navigate to **Metrics** tab
3. Monitor:
   - Request rate
   - Error rate
   - CPU time
   - Duration

### Set up Alerts

1. In Cloudflare dashboard:
   **Notifications > Add**

2. Create alerts for:
   - High error rate (> 5%)
   - High CPU usage
   - Failed deployments

3. Configure notification channels (email, Slack, PagerDuty)

### Log Aggregation

**Stream logs to external service:**

```bash
# Real-time logs
wrangler tail --env production --format json | your-log-aggregator
```

Or use **Cloudflare Log Push:**
1. **Workers & Pages > axon-prod > Settings > Logpush**
2. Configure destination (S3, Google Cloud Storage, etc.)

### Custom Metrics

**Track custom metrics in your code:**

```python
async def handle_honeypot_request(request, env):
    start_time = time.time()

    # ... processing ...

    duration = time.time() - start_time

    # Log metrics
    print(json.dumps({
        "metric": "request_duration",
        "value": duration,
        "classification": prediction['label']
    }))
```

## Rate Limiting

### Built-in Cloudflare Rate Limiting

**Configure in `wrangler.toml`:**

```toml
[env.production]
routes = [
  { pattern = "axon.yourdomain.com/*", zone_name = "yourdomain.com" }
]

# Then configure rate limiting in Cloudflare Dashboard:
# Security > WAF > Rate limiting rules
```

### Custom Rate Limiting

**Implement in worker:**

```python
from collections import defaultdict
from datetime import datetime, timedelta

# Simple in-memory rate limiter
rate_limit_cache = defaultdict(list)

async def check_rate_limit(ip, limit=100, window=60):
    """Check if IP exceeds rate limit"""
    now = datetime.now()
    cutoff = now - timedelta(seconds=window)

    # Clean old entries
    rate_limit_cache[ip] = [
        ts for ts in rate_limit_cache[ip] if ts > cutoff
    ]

    # Check limit
    if len(rate_limit_cache[ip]) >= limit:
        return False

    # Add new request
    rate_limit_cache[ip].append(now)
    return True


async def on_fetch(request, env):
    ip = request.headers.get('CF-Connecting-IP')

    if not await check_rate_limit(ip):
        return Response("Rate limit exceeded", status=429)

    # ... rest of processing
```

## Security Hardening

### Dashboard Authentication

**Option 1: Cloudflare Access (Recommended)**

1. Go to **Zero Trust > Access > Applications**
2. Create new application:
   - Name: Axon Dashboard
   - Domain: `dashboard.yourdomain.com`
   - Path: `/*`
3. Add policy:
   - Name: Axon Admins
   - Include: Emails ending in `@yourdomain.com`

**Option 2: Custom Authentication**

**Add to `worker.py`:**

```python
async def verify_auth(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return False

    # Check against KV store or hardcoded value
    token = auth_header.replace("Bearer ", "")
    valid_token = "your-secure-token-here"  # Use KV in production

    return token == valid_token


async def on_fetch(request, env):
    if request.url.endswith("/dashboard"):
        if not await verify_auth(request):
            return Response("Unauthorized", {
                "status": 401,
                "headers": {
                    "WWW-Authenticate": "Bearer"
                }
            })

    # ... rest of routing
```

### CORS Configuration

**If dashboard is on different domain:**

```python
from js import Response

def add_cors_headers(response):
    response.headers.set("Access-Control-Allow-Origin", "https://dashboard.yourdomain.com")
    response.headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    response.headers.set("Access-Control-Allow-Headers", "Content-Type")
    return response

async def on_fetch(request, env):
    # Handle preflight
    if request.method == "OPTIONS":
        return add_cors_headers(Response("OK"))

    # ... normal processing ...

    response = # ... your response ...
    return add_cors_headers(response)
```

## Data Retention

**Configure automatic cleanup:**

```sql
# Add to D1 migrations
CREATE TRIGGER cleanup_old_traffic
AFTER INSERT ON traffic
BEGIN
    DELETE FROM traffic
    WHERE created_at < datetime('now', '-30 days');
END;
```

**Or run periodic cleanup with Cron Triggers:**

```toml
# wrangler.toml
[triggers]
crons = ["0 2 * * *"]  # Run daily at 2 AM
```

```python
# In worker
async def scheduled(event, env):
    # Cleanup old data
    await env.DB.prepare(
        "DELETE FROM traffic WHERE created_at < datetime('now', '-30 days')"
    ).run()
```

## Backup Strategy

### Automatic D1 Backups

Cloudflare provides automatic backups for D1:
- Point-in-time recovery (7 days)
- Accessed via dashboard or API

### Manual Backups

```bash
# Export data periodically
wrangler d1 export axon-prod-db --output=backup-$(date +%Y%m%d).sql

# Store in S3 or similar
aws s3 cp backup-$(date +%Y%m%d).sql s3://your-backup-bucket/
```

**Set up cron job for daily backups:**

```bash
0 3 * * * cd /path/to/axon && ./scripts/backup.sh
```

## Scaling Considerations

### Durable Object Scaling

**Single instance (current):**
- Good for: Single dashboard, moderate traffic
- Handles: ~10k concurrent WebSocket connections

**Multiple instances (if needed):**
- Shard by region: `idFromName(f"{region}-monitor")`
- Shard by user: `idFromName(f"user-{user_id}")`

**Example:**

```python
# In worker.py
async def on_fetch(request, env):
    if path == "ws":
        # Shard by Cloudflare region
        region = request.cf.colo  # e.g., "SFO"
        do_id = env.TRAFFIC_MONITOR.idFromName(f"{region}-monitor")
        stub = env.TRAFFIC_MONITOR.get(do_id)
        return await stub.fetch(request)
```

### D1 Database Scaling

**Monitor these metrics:**
- Storage: Free tier = 5GB, Paid = 10GB+
- Reads: Free tier = 5M/day
- Writes: Free tier = 100k/day

**If you exceed limits:**
- Implement write batching
- Use separate analytics database
- Archive old data to R2

### Workers AI Scaling

**Free tier:** 10,000 neurons/day
**Paid tier:** Unlimited (billed per neuron)

**Optimize:**
- Cache predictions for identical requests
- Batch inference if possible
- Use simpler model if under performance constraints

## Multi-Region Deployment

**For global low-latency:**

1. Deploy to multiple regions:

```bash
wrangler deploy --env us-west
wrangler deploy --env eu-central
wrangler deploy --env asia-pacific
```

2. Use Cloudflare Load Balancer to route traffic

3. Each region has its own Durable Object instance

## Rollback Strategy

**If deployment goes wrong:**

```bash
# List recent deployments
wrangler deployments list

# Rollback to previous version
wrangler rollback [DEPLOYMENT_ID]
```

**Or use staged rollout:**

```bash
# Deploy to 10% of traffic first
wrangler deploy --percentage 10

# Monitor for issues
# If good, scale to 100%
wrangler deploy --percentage 100
```

## Cost Estimation

**Estimate monthly costs:**

**Workers:**
- Free tier: 100k requests/day
- Paid: $0.50 per million requests

**Durable Objects:**
- Free tier: None (always paid)
- Paid: $0.15 per million requests + $12.50/GB-month duration

**D1:**
- Free tier: 5GB storage, 5M reads/day
- Paid: $0.75/GB storage, $0.001/1000 reads

**Workers AI:**
- Free tier: 10k neurons/day
- Paid: Variable by model

**Example for 1M requests/day with ML:**
- Workers: $15/month
- Durable Objects: ~$20/month (with WebSocket hibernation)
- D1: ~$5/month
- Workers AI: ~$30/month
- **Total: ~$70/month**

## Production Checklist

Before going live:

- [ ] SSL/TLS configured (automatic with Cloudflare)
- [ ] Custom domain configured
- [ ] Environment variables set
- [ ] Rate limiting enabled
- [ ] Monitoring configured
- [ ] Alerts set up
- [ ] Backup strategy implemented
- [ ] Documentation updated
- [ ] Load testing completed
- [ ] Security review completed
- [ ] Incident response plan in place

## Maintenance

**Regular maintenance tasks:**

**Daily:**
- Check error logs
- Monitor request rates
- Review attack patterns

**Weekly:**
- Review analytics
- Check storage usage
- Validate model performance

**Monthly:**
- Retrain ML model with new data
- Review and optimize costs
- Update dependencies
- Security audit

## Next Steps

- [API Reference](api-reference.md) - Understand the API
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
