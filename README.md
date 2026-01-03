# ⚡ Axon

AI-powered bot detection and traffic classification running entirely on Cloudflare's edge network.

## 🚀 Features

- **Real-time Classification**: Instantly detect and classify malicious traffic
- **Live Dashboard**: WebSocket-powered dashboard with real-time traffic feed
- **Advanced Detection**: Multiple attack pattern detectors:
  - SQL Injection
  - Path Traversal
  - Sensitive File Access
  - WordPress/PHP Exploits
  - XSS Patterns
  - Shell Access Attempts
- **Smart Heuristics**: Enhanced classification with confidence scoring
- **REST API**: Get aggregate statistics and analytics
- **Edge Computing**: Runs entirely on Cloudflare's global network
- **Zero Infrastructure**: No servers to manage

## 📊 Dashboard

The real-time dashboard shows:
- Total requests processed
- Attack vs. legitimate traffic breakdown
- Requests per minute
- Live feed of all classified traffic
- Connection status indicator

Access at: `https://your-worker.workers.dev/dashboard`

## 🏗️ Architecture

```
User Traffic → Worker → Feature Extraction → Classification
                 ↓                              ↓
            WebSocket ←──────────────────── Broadcast
                 ↓
            Dashboard (Real-time updates)

            D1 Database (Traffic logs)
```

### Components

- **Worker (worker.py)**: Main entry point, routes requests
- **Honeypot (honeypot.py)**: Extracts features and classifies traffic
- **Features (features.py)**: Attack pattern detection
- **Traffic Monitor (traffic_monitor.py)**: WebSocket coordination via Durable Objects
- **Stats (stats.py)**: Analytics and aggregate statistics
- **Dashboard (dashboard.html)**: Real-time visualization

## 🛠️ Setup

### Prerequisites
- Node.js 18+ (for Wrangler)
- Python 3.11+
- uv (`pip install uv`)
- Cloudflare account

### Quick Start

1. **Install dependencies**:
```bash
pip install pywrangler uv
npm install -g wrangler@latest
wrangler login
```

2. **Create D1 database**:
```bash
wrangler d1 create axon-db
# Copy the database_id from output
```

3. **Update configuration**:
Edit `wrangler.toml` and `pyproject.toml` with your `database_id`

4. **Initialize database**:
```bash
wrangler d1 execute axon-db --file=src/schema.sql
```

5. **Run locally**:
```bash
uv run pywrangler dev
```

6. **Deploy**:
```bash
uv run pywrangler deploy
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## 📡 API Endpoints

### Dashboard
```
GET /dashboard
```
Real-time traffic visualization with WebSocket connection.

### Health Check
```
GET /health
```
Returns system status and version.

### Statistics
```
GET /api/stats
```
Returns aggregate statistics:
- Total requests
- Attacks blocked
- Legitimate traffic
- Attack rate
- Top attack types

### WebSocket
```
GET /ws
```
WebSocket endpoint for real-time updates. Sends classification events to connected clients.

## 🧪 Testing

```bash
# Install test dependencies
pip install -r tests/requirements_test.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_features.py -v
```

See [tests/README.md](tests/README.md) for more testing information.

## 🔍 Attack Detection

Axon detects various attack patterns:

### SQL Injection
- UNION SELECT statements
- OR 1=1 patterns
- SQL comments (-- and /* */)
- Encoding attempts

### Path Traversal
- ../ patterns (including encoded)
- Access to /etc/, /bin/, etc.
- Windows path attempts (C:\)

### Sensitive Files
- .env, .git, .svn
- Configuration files
- Backup files
- SSH keys

### Common Exploits
- WordPress scanning (wp-admin, wp-login)
- PHP exploits (phpinfo, phpmyadmin)
- Admin panel access attempts
- Shell access attempts
- XSS injection patterns

## 📈 Classification

Each request is scored based on multiple factors:
- User-Agent analysis (bot detection)
- Attack pattern matching
- Path entropy calculation
- Cloudflare bot score
- Suspicious character detection

Requests scoring ≥40 are classified as attacks. Confidence is calculated from the total score.

## 🚦 Development

### Run locally with hot reload
```bash
uv run pywrangler dev --live-reload
```

### View logs
```bash
wrangler tail
```

### Query database
```bash
wrangler d1 execute axon-db --command="SELECT * FROM traffic LIMIT 10;"
```

### Generate test traffic
```bash
# Legitimate
curl http://localhost:8787/api/users

# Attack patterns
curl http://localhost:8787/.env
curl http://localhost:8787/admin
curl "http://localhost:8787/api?q=1' OR '1'='1"
```

## 📚 Documentation

- [Getting Started](docs/getting-started.md)
- [Architecture](docs/architecture.md)
- [Development Guide](docs/development.md)
- [Deployment Guide](DEPLOYMENT.md)
- [API Reference](docs/api-reference.md)
- [Model Training](docs/model_training.md)
- [Troubleshooting](docs/troubleshooting.md)

## 🗺️ Roadmap

**Phase 1: Heuristic Detection** ✅
- [x] Feature extraction
- [x] Attack pattern detection
- [x] Basic classification
- [x] Real-time dashboard
- [x] REST API

**Phase 2: ML Integration** (Coming Soon)
- [ ] Collect training data
- [ ] Train classifier model
- [ ] Export to ONNX
- [ ] Deploy to Workers AI
- [ ] A/B testing framework

**Phase 3: Advanced Features**
- [ ] Automatic retraining
- [ ] Custom rule engine
- [ ] Webhook notifications
- [ ] Multi-tenancy
- [ ] Advanced analytics

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built for Major League Hacking's "Hack for Hackers" hackathon.

- Cloudflare Workers & D1
- Python Workers support
- Durable Objects
- Workers AI (future integration)
