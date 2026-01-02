# ⚡ Axon

AI-powered bot detection and traffic classification at the edge.

## Setup

### Prerequisites
- Node.js (for Wrangler)
- Python 3.11+
- uv (`pip install uv`)

### Installation

1. Install pywrangler:
```bash
pip install pywrangler
```

2. Initialize:
```bash
uv run pywrangler init
```

3. Create D1 database:
```bash
wrangler d1 create axon-db
```

Copy the database_id into wrangler.toml

4. Create the schema:
```bash
wrangler d1 execute axon-db --file=schema.sql
```

### Development

Run locally:
```bash
uv run pywrangler dev
```

### Deployment
```bash
uv run pywrangler deploy
```

## Architecture

- **Cloudflare Workers (Python)**: Honeypot handlers, API endpoints
- **Durable Objects**: WebSocket coordination for real-time dashboard
- **D1**: Traffic logging and storage
- **Workers AI**: ML inference (post-training)
- **Pages**: Static dashboard hosting

## Weekend Plan

**Friday Night:**
- Deploy honeypot
- Let it collect overnight

**Saturday:**
- Train model on collected data
- Feature engineering
- Export to ONNX

**Sunday:**
- Deploy to Workers AI
- Polish dashboard
- Demo prep
