# Troubleshooting Guide

Common issues and solutions for Axon deployment and operation.

## Installation Issues

### Problem: "command not found: pywrangler"

**Solution:**

```bash
pip install pywrangler
# Or if you're using a virtual environment:
source venv/bin/activate
pip install pywrangler
```

### Problem: "command not found: wrangler"

**Solution:**

```bash
npm install -g wrangler@latest
# If permission error on Linux/Mac:
sudo npm install -g wrangler@latest
```

### Problem: "Module not found: cloudflare.workers"

**Solution:**

```bash
# Don't use regular wrangler dev, use:
uv run pywrangler dev
# Or:
wrangler dev --compatibility-flags python_workers
```

### Problem: "Python version not supported"

**Solution:**

```bash
# Check Python version (need 3.11+)
python --version

# Install Python 3.11 or later
# On Ubuntu:
sudo apt install python3.11
# On Mac:
brew install python@3.11
```

## Database Issues

### Problem: "Database not found" or "database_id is required"

**Solution:**

1. Create the database:
   ```bash
   wrangler d1 create axon-db
   ```

2. Copy the database_id from output

3. Update `wrangler.toml`:
   ```toml
   [[d1_databases]]
   binding = "DB"
   database_name = "axon-db"
   database_id = "paste-id-here"
   ```

4. Apply schema:
   ```bash
   wrangler d1 execute axon-db --file=schema.sql
   ```

### Problem: "table traffic already exists"

**Solution:**

```bash
# Drop and recreate (WARNING: deletes all data)
wrangler d1 execute axon-db --command="DROP TABLE IF EXISTS traffic;"
wrangler d1 execute axon-db --file=schema.sql

# Or skip if table exists:
# Edit schema.sql to use CREATE TABLE IF NOT EXISTS
```

### Problem: D1 queries timing out

**Solution:**

1. Check if database is over capacity
2. Add indexes if missing:
   ```sql
   CREATE INDEX idx_timestamp ON traffic(timestamp);
   CREATE INDEX idx_prediction ON traffic(prediction);
   ```
3. Optimize queries (use LIMIT)
4. Consider data retention/cleanup

### Problem: "Error executing SQL"

**Solution:**

```bash
# Test query locally first:
wrangler d1 execute axon-db --local --command="SELECT 1;"

# Check syntax in schema.sql
# Make sure no trailing semicolons in multi-line commands
```

## Deployment Issues

### Problem: "Worker exceeds size limit"

**Solution:**

1. Remove unnecessary dependencies
2. Use external packages via imports
3. Split into multiple Workers if needed
4. Check `wrangler.toml` for unused bindings

### Problem: "Deployment failed: authentication required"

**Solution:**

```bash
# Login to Cloudflare:
wrangler login

# Or use API token:
export CLOUDFLARE_API_TOKEN=your-token
wrangler deploy
```

### Problem: "Durable Object class not found"

**Solution:**

1. Check `wrangler.toml` has correct binding:
   ```toml
   [[durable_objects.bindings]]
   name = "TRAFFIC_MONITOR"
   class_name = "TrafficMonitor"
   script_name = "axon"
   ```

2. Check migrations section exists:
   ```toml
   [[migrations]]
   tag = "v1"
   new_classes = ["TrafficMonitor"]
   ```

3. Make sure class is exported in `traffic_monitor.py`

### Problem: "Cannot read property 'TRAFFIC_MONITOR' of undefined"

**Solution:**

```python
# In worker.py, access via env parameter:
async def on_fetch(request, env):
    do_id = env.TRAFFIC_MONITOR.idFromName("global")
    # NOT: TRAFFIC_MONITOR.idFromName("global")
```

## WebSocket Issues

### Problem: "WebSocket connection failed"

**Solution:**

1. Check URL uses `wss://` not `ws://` in production
2. Verify Worker is deployed and accessible
3. Check CORS settings if dashboard is on different domain
4. Test with wscat:
   ```bash
   wscat -c wss://axon.your-subdomain.workers.dev/ws
   ```

### Problem: "Connection established but no messages received"

**Solution:**

1. Check if honeypot is receiving traffic:
   ```bash
   curl https://axon.your-subdomain.workers.dev/test
   ```

2. Check Worker logs:
   ```bash
   wrangler tail
   ```

3. Verify `broadcast()` is being called in `honeypot.py`

4. Check Durable Object is processing messages

### Problem: "WebSocket closes immediately"

**Solution:**

1. Check browser console for errors
2. Verify Durable Object `fetch()` returns 101 status
3. Check for exceptions in `webSocketMessage` handler
4. Verify WebSocketPair is created correctly

### Problem: "Too many WebSocket connections"

**Solution:**

```python
# Limit connections per IP in Durable Object:
class TrafficMonitor:
    def __init__(self, state, env):
        self.sessions = {}  # Use dict instead of list
        self.ip_count = defaultdict(int)

    async def fetch(self, request):
        ip = request.headers.get('CF-Connecting-IP')
        if self.ip_count[ip] >= 10:
            return Response("Too many connections", status=429)
        # ... rest of code
```

## Runtime Errors

### Problem: "TypeError: 'NoneType' object is not iterable"

**Solution:**

```python
# Check for None values before iterating
if my_list is not None:
    for item in my_list:
        # ...
```

### Problem: "AttributeError: 'module' object has no attribute"

**Solution:**

```python
# Check imports:
from features import get_request_entropy  # Correct
# NOT: from features import features.get_request_entropy
```

### Problem: "JSON decode error"

**Solution:**

```python
# Wrap JSON parsing in try/catch:
try:
    data = json.loads(message)
except json.JSONDecodeError as e:
    print(f"Invalid JSON: {e}")
    return
```

### Problem: "Event loop already running"

**Solution:**

```python
# Use await instead of asyncio.run() in Workers:
# WRONG:
asyncio.run(some_async_function())

# RIGHT:
await some_async_function()
```

## Performance Issues

### Problem: "Worker CPU time limit exceeded"

**Solution:**

1. Optimize expensive operations
2. Use async operations to avoid blocking
3. Cache frequently accessed data
4. Consider moving heavy work to separate Worker

### Problem: "Durable Object duration charges are high"

**Solution:**

1. Use WebSocket Hibernation API
2. Batch operations instead of processing individually
3. Clean up idle connections more aggressively
4. Consider sharding across multiple Durable Objects

### Problem: "Slow database queries"

**Solution:**

1. Add indexes:
   ```sql
   CREATE INDEX idx_your_column ON traffic(your_column);
   ```

2. Use LIMIT on queries:
   ```sql
   SELECT * FROM traffic LIMIT 100;
   ```

3. Avoid `SELECT *` (specify columns)

4. Use prepared statements (already doing this)

### Problem: "High latency from ML model"

**Solution:**

1. Cache predictions for identical requests
2. Use simpler model (fewer features)
3. Consider client-side prediction for some cases
4. Batch inference requests

## ML Model Issues

### Problem: "Model not found" when calling Workers AI

**Solution:**

1. Verify model is uploaded:
   ```bash
   wrangler ai models list
   ```

2. Check model name matches in code:
   ```python
   await env.AI.run('@cf/your-account/axon-classifier', ...)
   ```

3. Re-upload if necessary:
   ```bash
   wrangler ai models upload axon_model.onnx --name axon-classifier
   ```

### Problem: "Invalid input shape" error

**Solution:**

```python
# Ensure feature vector matches training:
# Check feature_names.txt for correct order
# Count should match model input size
```

### Problem: "Model inference taking too long"

**Solution:**

1. Reduce model complexity
2. Use fewer features (feature selection)
3. Consider caching predictions
4. Use heuristics for obvious cases, ML for ambiguous

### Problem: "Poor model accuracy"

**Solution:**

1. Collect more training data
2. Balance attack/legit samples
3. Add more relevant features
4. Try different model types (XGBoost vs Neural Net)
5. Tune hyperparameters
6. Check for data leakage

## Dashboard Issues

### Problem: "Dashboard shows 'Disconnected'"

**Solution:**

1. Check WebSocket URL in `dashboard.html`
2. Verify Worker is deployed
3. Check browser console for errors
4. Test WebSocket with wscat

### Problem: "Stats not updating"

**Solution:**

1. Check if traffic is being logged:
   ```bash
   wrangler d1 execute axon-db --command="SELECT COUNT(*) FROM traffic;"
   ```

2. Verify `broadcast()` is being called

3. Check browser console for JavaScript errors

4. Test WebSocket connection separately

### Problem: "Charts not rendering"

**Solution:**

1. Check if Chart.js is loaded:
   ```html
   <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
   ```

2. Verify canvas element exists:
   ```html
   <canvas id="myChart"></canvas>
   ```

3. Check browser console for errors

### Problem: "Feed showing old data"

**Solution:**

```javascript
// Clear feed periodically in JavaScript:
setInterval(() => {
    const feed = document.getElementById('feed');
    while (feed.children.length > 50) {
        feed.removeChild(feed.lastChild);
    }
}, 10000);  // Every 10 seconds
```

## Cloudflare-Specific Issues

### Problem: "Rate limit exceeded" during deployment

**Solution:**

```bash
# Wait a few minutes and try again
# Or upgrade to paid plan for higher limits
```

### Problem: "Worker not updating after deployment"

**Solution:**

1. Clear Cloudflare cache
2. Wait a few seconds for propagation
3. Hard refresh browser (Ctrl+Shift+R)
4. Check deployment succeeded:
   ```bash
   wrangler deployments list
   ```

### Problem: "Domain not resolving"

**Solution:**

1. Check DNS settings in Cloudflare dashboard
2. Wait for DNS propagation (can take up to 24 hours)
3. Test with dig or nslookup:
   ```bash
   dig axon.yourdomain.com
   ```

### Problem: "SSL certificate error"

**Solution:**

Usually auto-resolved, but if persistent:

1. Check SSL/TLS settings (should be "Full" or "Full (strict)")
2. Wait for certificate provisioning
3. Contact Cloudflare support if issue persists

## Debugging Tips

### Enable Verbose Logging

```python
# In your Python code:
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use print statements:
print(f"Debug: {variable_name}")
```

### View Real-time Logs

```bash
# Stream logs:
wrangler tail

# Filter by text:
wrangler tail | grep "ERROR"

# Save to file:
wrangler tail > logs.txt
```

### Test Locally First

```bash
# Always test locally before deploying:
uv run pywrangler dev

# This catches most issues before production
```

### Use Browser DevTools

1. Open DevTools (F12)
2. Check Console tab for errors
3. Check Network tab for failed requests
4. Check WebSocket frame for messages

### Check Cloudflare Dashboard

1. Go to Workers & Pages
2. Check metrics for errors
3. View real-time analytics
4. Check resource usage

## Common Error Messages

**"Error 1101: Worker threw JavaScript exception"**
- Check Worker logs with: `wrangler tail`
- Look for syntax errors or unhandled exceptions

**"Error 1102: Worker exceeded CPU time limit"**
- Optimize your code
- Move heavy operations to async
- Consider using a separate Worker

**"Error 1015: You are being rate limited"**
- Implement rate limiting in your Worker
- Contact Cloudflare if legitimate traffic

**"Error 1020: Access denied"**
- Check Cloudflare security settings
- Verify IP is not blocked

**"Error 520: Unknown error"**
- Check Worker is deployed correctly
- Verify no runtime errors
- Check logs for details

## Getting Help

If you're still stuck:

1. **Check documentation:**
   - [Cloudflare Workers docs](https://developers.cloudflare.com/workers/)
   - [Python Workers docs](https://developers.cloudflare.com/workers/languages/python/)

2. **Check logs:**
   ```bash
   wrangler tail --name axon
   ```

3. **Search Cloudflare Community:**
   [https://community.cloudflare.com/](https://community.cloudflare.com/)

4. **Ask in Discord:**
   [https://discord.gg/cloudflaredev](https://discord.gg/cloudflaredev)

5. **File an issue:**
   [https://github.com/yourusername/axon/issues](https://github.com/yourusername/axon/issues)

## Preventive Measures

To avoid common issues:

1. Test locally before deploying
2. Use version control (git)
3. Enable monitoring and alerts
4. Document your changes
5. Keep dependencies updated
6. Regular backups of D1 database
7. Load testing before scaling
8. Security reviews periodically

## Emergency Procedures

If Axon goes down in production:

1. Check Cloudflare status: [https://www.cloudflarestatus.com/](https://www.cloudflarestatus.com/)

2. Roll back to previous version:
   ```bash
   wrangler rollback
   ```

3. Check logs for errors:
   ```bash
   wrangler tail --status error
   ```

4. Disable Worker temporarily if needed:
   ```bash
   # Remove routes in wrangler.toml
   # Deploy with no routes
   ```

5. Contact Cloudflare support if infrastructure issue
