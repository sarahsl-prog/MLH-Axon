<div align="center">
  <img src="../public/Axon_logo.jpg" alt="Axon Logo" width="300"/>
</div>

# Getting Started with Axon

This guide will help you set up Axon from scratch and deploy your first honeypot.

## Prerequisites

Before you begin, ensure you have:

- **Node.js** (v18 or later) - Required for Wrangler
- **Python** (3.11 or later) - For Python Workers
- **uv** - Python package installer (`pip install uv`)
- **Cloudflare Account** - Free tier works fine
- **Git** - For version control

## Installation

### 1. Install Required Tools

```bash
# Install pywrangler (Python Workers CLI)
pip install pywrangler

# Install uv if you haven't already
pip install uv

# Install/update Wrangler
npm install -g wrangler@latest

# Login to Cloudflare
wrangler login
```

### 2. Clone the Project

```bash
git clone https://github.com/yourusername/axon.git
cd axon
```

Or create from scratch:

```bash
mkdir axon && cd axon
```

### 3. Set Up the Project Structure

Create the directory structure:

```bash
mkdir -p src public docs
```

Copy all the source files from the template into their respective directories.

### 4. Initialize Python Environment

```bash
# Create pyproject.toml (see template)
uv run pywrangler init
```

### 5. Create D1 Database

```bash
# Create the database
wrangler d1 create axon-db

# Output will include your database_id, copy it!
# Example output:
# [[d1_databases]]
# binding = "DB"
# database_name = "axon-db"
# database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

Update `wrangler.toml` with your database_id.

### 6. Initialize Database Schema

```bash
# Create schema.sql file (see template)
# Then apply it:
wrangler d1 execute axon-db --file=schema.sql
```

Verify the schema:

```bash
wrangler d1 execute axon-db --command="SELECT name FROM sqlite_master WHERE type='table';"
```

You should see the `traffic` table.

### 7. Local Development

Run Axon locally:

```bash
uv run pywrangler dev
```

Your honeypot will be available at `http://localhost:8787`

Test it:

```bash
# Send some test traffic
curl http://localhost:8787/test
curl http://localhost:8787/admin
curl http://localhost:8787/.env
```

### 8. Deploy to Cloudflare

```bash
uv run pywrangler deploy
```

Your Worker will be live at: `https://axon.your-subdomain.workers.dev`

### 9. Deploy Dashboard

**Option A:** Serve from the Worker (simple, included by default)
- Visit `https://axon.your-subdomain.workers.dev/dashboard`

**Option B:** Deploy to Cloudflare Pages (recommended for production)

```bash
# In the project root
wrangler pages project create axon-dashboard

# Deploy the public/ directory
wrangler pages deploy public --project-name=axon-dashboard
```

Update the WebSocket URL in `dashboard.html` to point to your Worker.

## First Steps After Deployment

### 1. Verify the Honeypot is Working

```bash
# Send test traffic
curl https://axon.your-subdomain.workers.dev/test-endpoint

# Check if it logged to D1
wrangler d1 execute axon-db --command="SELECT * FROM traffic ORDER BY timestamp DESC LIMIT 5;"
```

### 2. Open the Dashboard

Visit `https://axon.your-subdomain.workers.dev/dashboard`

You should see:
- Connection status indicator
- Live stats (initially all zeros)
- Live feed waiting for traffic

### 3. Generate Some Traffic

```bash
# Legitimate-looking traffic
curl -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" \
  https://axon.your-subdomain.workers.dev/

# Bot-like traffic
curl -A "python-requests/2.28.0" \
  https://axon.your-subdomain.workers.dev/admin

curl -A "curl/7.68.0" \
  https://axon.your-subdomain.workers.dev/.env
```

Watch the dashboard update in real-time!

### 4. Expose to Real Traffic (Optional)

If you want real attack data:

```bash
# On your Linux cloud host
# Create a simple reverse proxy or port forward
# CAUTION: This will expose your honeypot to the internet
# Make sure you understand the security implications

# Example with nginx (on your cloud host)
# Forward traffic from port 80 to your Cloudflare Worker
```

Or submit your URL to Shodan or similar to attract bot traffic.

## What's Next?

- [Development Guide](development.md) - Learn how to customize Axon
- [Model Training Guide](model_training.md) - Train your ML model on collected data
- [Architecture](architecture.md) - Understand how Axon works

## Troubleshooting

If something isn't working, check the [Troubleshooting Guide](troubleshooting.md).

**Common issues:**
- **"Database not found"** - Make sure you copied the database_id to `wrangler.toml`
- **"WebSocket connection failed"** - Check that the URL in `dashboard.html` matches your Worker URL
- **"Module not found"** - Run `uv run pywrangler dev` instead of plain `wrangler dev`
