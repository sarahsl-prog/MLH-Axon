# Axon Deployment Guide

Complete guide to deploying Axon to Cloudflare Workers.

## Prerequisites

- Cloudflare account (free tier works)
- Node.js 18+ (for Wrangler)
- Python 3.11+
- uv package manager
- Git

## Step 1: Install Dependencies

```bash
# Install pywrangler
pip install pywrangler

# Install uv if not already installed
pip install uv

# Install Wrangler globally
npm install -g wrangler@latest

# Login to Cloudflare
wrangler login
```

## Step 2: Configure the Project

### Create D1 Database

```bash
# Create the database
wrangler d1 create axon-db
```

This will output something like:

```
[[d1_databases]]
binding = "DB"
database_name = "axon-db"
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

Copy the `database_id` value.

### Update wrangler.toml

Edit `wrangler.toml` and update the `database_id`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "axon-db"
database_id = "your-actual-database-id-here"
```

### Update pyproject.toml

Similarly, update `pyproject.toml` with the database ID:

```toml
[tool.pywrangler.d1_databases]
bindings = [
    { binding = "DB", database_name = "axon-db", database_id = "your-actual-database-id-here" }
]
```

## Step 3: Initialize Database Schema

```bash
# Apply the schema to your D1 database
wrangler d1 execute axon-db --file=src/schema.sql
```

Verify the schema was created:

```bash
wrangler d1 execute axon-db --command="SELECT name FROM sqlite_master WHERE type='table';"
```

You should see the `traffic` table listed.

## Step 4: Test Locally

```bash
# Start local development server
uv run pywrangler dev

# Or with live reload
uv run pywrangler dev --live-reload
```

The server will start on `http://localhost:8787`

### Test the Endpoints

```bash
# Test health endpoint
curl http://localhost:8787/health

# Test dashboard (open in browser)
open http://localhost:8787/dashboard

# Send test traffic
curl http://localhost:8787/test
curl -A "curl/7.68.0" http://localhost:8787/.env
curl http://localhost:8787/admin
```

### Run Tests

```bash
# Install test dependencies
pip install -r tests/requirements_test.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

## Step 5: Deploy to Production

```bash
# Deploy the worker
uv run pywrangler deploy
```

This will deploy your worker and give you a URL like:
`https://axon.your-subdomain.workers.dev`

### Verify Deployment

```bash
# Test health endpoint
curl https://axon.your-subdomain.workers.dev/health

# Open dashboard in browser
open https://axon.your-subdomain.workers.dev/dashboard
```

## Step 6: Configure Custom Domain (Optional)

### Add Route in Cloudflare Dashboard

1. Go to your Cloudflare dashboard
2. Select your zone (domain)
3. Go to Workers & Pages
4. Click on your worker
5. Add a route: `axon.yourdomain.com/*`

### Update wrangler.toml

```toml
[[routes]]
pattern = "axon.yourdomain.com/*"
zone_name = "yourdomain.com"
```

Redeploy:

```bash
uv run pywrangler deploy
```

## Step 7: Monitor Your Deployment

### View Logs

```bash
# Stream real-time logs
wrangler tail

# Filter by status
wrangler tail --status error

# Filter by method
wrangler tail --method POST
```

### Check D1 Database

```bash
# View recent traffic
wrangler d1 execute axon-db --command="SELECT * FROM traffic ORDER BY timestamp DESC LIMIT 10;"

# Get stats
wrangler d1 execute axon-db --command="SELECT prediction, COUNT(*) as count FROM traffic GROUP BY prediction;"
```

### Use the Stats API

```bash
curl https://axon.your-subdomain.workers.dev/api/stats | jq
```

## Troubleshooting

### Database Errors

If you see database errors:

```bash
# Check database exists
wrangler d1 list

# Verify schema
wrangler d1 execute axon-db --command="PRAGMA table_info(traffic);"

# Re-apply schema if needed
wrangler d1 execute axon-db --file=src/schema.sql
```

### WebSocket Connection Failed

1. Check that your browser supports WebSockets
2. Verify the WebSocket URL is correct (wss:// for HTTPS)
3. Check browser console for errors
4. Ensure Durable Objects are properly configured

### Import Errors

If you see import errors during deployment:

```bash
# Clear cache and redeploy
rm -rf .wrangler
uv run pywrangler deploy
```

### Performance Issues

If experiencing slow response times:

1. Check the dashboard for request metrics
2. Review logs for slow queries
3. Consider adding indexes to D1
4. Monitor Durable Object usage

## Production Best Practices

### Security

1. **Add Authentication**: Protect the dashboard with Cloudflare Access
   ```toml
   [env.production]
   # Add Cloudflare Access policy
   ```

2. **Rate Limiting**: Configure rate limits for API endpoints

3. **CORS**: Configure CORS headers if needed
   ```python
   headers = {
       "Access-Control-Allow-Origin": "your-domain.com",
       "Access-Control-Allow-Methods": "GET, POST",
   }
   ```

### Monitoring

1. **Set up Alerts**: Use Cloudflare analytics to alert on errors
2. **Log Aggregation**: Send logs to external service (Datadog, etc.)
3. **Uptime Monitoring**: Use external monitoring (UptimeRobot, Pingdom)

### Scaling

1. **Database**: Monitor D1 storage limits (5GB free tier)
2. **Durable Objects**: Consider sharding if traffic is very high
3. **Workers**: Auto-scales, but monitor CPU time limits

### Backup

```bash
# Export database regularly
wrangler d1 export axon-db --output=backup-$(date +%Y%m%d).sql

# Or query and save as JSON
wrangler d1 execute axon-db --json \
  --command="SELECT * FROM traffic WHERE timestamp > $(date -d '7 days ago' +%s)000" \
  > backup.json
```

## Updating the Application

```bash
# Pull latest changes
git pull

# Run tests
pytest tests/ -v

# Deploy
uv run pywrangler deploy
```

## Rolling Back

If you need to rollback a deployment:

```bash
# View deployment history in Cloudflare dashboard
# Or use Wrangler versions

wrangler deployments list
wrangler rollback [deployment-id]
```

## Cost Estimation

### Free Tier Limits (as of 2024)

- **Workers**: 100,000 requests/day
- **D1**: 5GB storage, 5M reads/day
- **Durable Objects**: 1M requests/month
- **Workers AI**: 10,000 neurons/day (when using ML)

### Typical Usage

- Small site: ~1,000 requests/day = Free
- Medium site: ~100,000 requests/day = $5-10/month
- High traffic: 1M+ requests/day = $25-50/month

## Next Steps

1. **Train ML Model**: See `docs/model_training.md`
2. **Customize Features**: Add your own attack patterns
3. **Integrate with SIEM**: Forward logs to your security tools
4. **Set up Webhooks**: Get notified of high-confidence attacks

## Support

- Documentation: See `docs/` directory
- Issues: GitHub Issues
- Cloudflare: https://developers.cloudflare.com/workers/

## Additional Resources

- [Cloudflare Workers Docs](https://developers.cloudflare.com/workers/)
- [D1 Database Docs](https://developers.cloudflare.com/d1/)
- [Durable Objects Docs](https://developers.cloudflare.com/workers/runtime-apis/durable-objects/)
- [Workers AI Docs](https://developers.cloudflare.com/workers-ai/)
