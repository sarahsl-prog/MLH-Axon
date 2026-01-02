# Axon Documentation

Welcome to the Axon documentation! Axon is an AI-powered bot detection and traffic classification system running entirely on Cloudflare's edge network.

## Documentation Index

- **[Getting Started](getting-started.md)** - Installation, setup, and first deployment
- **[Architecture](architecture.md)** - System design and component overview
- **[Development Guide](development.md)** - Local development, testing, and iteration
- **[Deployment Guide](deployment.md)** - Production deployment and configuration
- **[API Reference](api-reference.md)** - Endpoints, WebSocket protocol, and data formats
- **[Training Guide](training.md)** - Model training and deployment workflow
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

## Quick Links

- [GitHub Repository](https://github.com/yourusername/axon)
- [Live Demo](https://axon.your-subdomain.workers.dev)
- [Cloudflare Workers Docs](https://developers.cloudflare.com/workers/)
- [Python Workers Docs](https://developers.cloudflare.com/workers/languages/python/)

## Project Overview

Axon uses machine learning to classify incoming web traffic in real-time, distinguishing between legitimate users and malicious bots. The system:

- **Collects** traffic data through honeypot endpoints
- **Extracts** meaningful features from HTTP requests
- **Classifies** traffic using ML models (or heuristics during initial phase)
- **Visualizes** results through a real-time dashboard
- **Runs** entirely on Cloudflare's edge network (no servers to manage)

## Technology Stack

- **Backend**: Python Workers (Cloudflare)
- **Real-time**: Durable Objects + WebSockets
- **Storage**: D1 (SQLite at the edge)
- **ML**: Workers AI (post-training)
- **Frontend**: Vanilla JavaScript + HTML/CSS
- **Deployment**: Cloudflare Pages + Workers

## Contributing

This is a hackathon project built during [Hack for Hackers]. Contributions welcome!

## License

MIT License - see LICENSE file for details
