# InfraIQ Demo Environment

Interactive browser-based demo environment for [InfraIQ](https://github.com/autonops/infraIQ) - try all tools without installation.

**Live Demo:** https://demo.autonops.io

## Overview

This repo contains the infrastructure for hosting an interactive InfraIQ demo where users can:

- Get a 15-minute browser terminal session
- Run real InfraIQ commands against sample data
- Explore Heroku→AWS migrations, security scanning, and more
- No installation or cloud credentials required

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  demo.autonops.io                                       │
│                                                         │
│  ┌──────────────┐     ┌────────────────────────────┐    │
│  │ Landing Page │────▶│ FastAPI Backend            │    │
│  │ Email Capture│     │ - Session management       │    │
│  └──────────────┘     │ - Container lifecycle      │    │
│                       │ - Lead capture             │    │
│                       └─────────────┬──────────────┘    │
│                                     │                   │
│                       ┌─────────────▼──────────────┐    │
│                       │ Docker Containers (ttyd)   │    │
│                       │ ┌────────┐ ┌────────┐      │    │
│                       │ │Session1│ │Session2│ ...  │    │
│                       │ └────────┘ └────────┘      │    │
│                       └────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Demo Scenarios

### 1. Heroku → AWS Migration
```bash
infraiq migrate scan heroku --app-name acme-prod
infraiq migrate map scan.json aws
infraiq migrate generate migration-plan.json --output ./terraform
```

### 2. Infrastructure Security Scan
```bash
infraiq verify scan --provider aws
infraiq verify analyze verify-report.json
```

### 3. Monolith Decomposition
```bash
cd ~/samples/acme-monolith
infraiq tessera analyze --source .
infraiq tessera design --analysis analysis.json --pattern domain
```

### 4. SOC2 Compliance
```bash
infraiq comply quickscan
infraiq comply scan --provider aws --framework soc2
```

## Sample Data

| File | Description |
|------|-------------|
| `heroku_scan.json` | Acme Corp production app (3 dynos, PostgreSQL, Redis) |
| `aws_resources.json` | AWS account with 5 security issues, 2 cost optimizations |
| `acme-monolith/` | Django e-commerce app for Tessera decomposition |

## Deployment

See [DEMO_DEPLOYMENT.md](DEMO_DEPLOYMENT.md) for full deployment instructions.

**Quick start:**

```bash
# Create GCP VM
gcloud compute instances create infraiq-demo \
    --zone=us-central1-a \
    --machine-type=e2-small \
    --boot-disk-size=20GB \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --tags=http-server,https-server

# SSH in and deploy
gcloud compute ssh infraiq-demo --zone=us-central1-a
# Follow DEMO_DEPLOYMENT.md
```

**Estimated cost:** ~$16/month

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_DURATION_MINUTES` | 15 | Session timeout |
| `MAX_CONCURRENT_SESSIONS` | 10 | Max simultaneous users |
| `ADMIN_SECRET` | (required) | Secret for `/api/leads` endpoint |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Landing page |
| `/api/session` | POST | Create new session (requires email) |
| `/api/session/{id}` | GET | Get session status |
| `/api/session/{id}` | DELETE | End session early |
| `/api/leads` | GET | Export captured leads (requires secret) |
| `/api/health` | GET | Health check |

## Repository Structure

```
infraiq-demo/
├── frontend/
│   └── index.html           # Landing page with email capture
├── api/
│   ├── Dockerfile
│   ├── main.py              # FastAPI session management
│   └── requirements.txt
├── container/
│   ├── Dockerfile           # Demo terminal image
│   ├── bashrc               # Shell config + welcome
│   ├── motd.txt             # ASCII banner
│   ├── data/                # Sample scan data
│   └── samples/             # Sample applications
├── docker-compose.yml
└── DEMO_DEPLOYMENT.md
```

## License

MIT - See [LICENSE](LICENSE)

## Related

- [InfraIQ](https://github.com/autonops/infraIQ) - Main product repo
- [Wraith](https://github.com/autonops/wraith) - Telemetry system
- [autonops.io](https://autonops.io) - Company website
