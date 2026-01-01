# InfraIQ Demo Environment - Deployment Guide

## Overview

Interactive web-based demo at `demo.autonops.io` where users can try InfraIQ in a browser terminal without installation.

**Features:**
- Email capture before access
- 15-minute isolated sessions
- Pre-loaded demo data
- Max 10 concurrent sessions

**Estimated Cost:** ~$15-20/month (e2-small VM)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  demo.autonops.io                                       │
│  ┌─────────────────┐    ┌─────────────────────────────┐ │
│  │  Caddy (SSL)    │───▶│  Demo API (FastAPI)         │ │
│  │  Port 443       │    │  - Email capture            │ │
│  └─────────────────┘    │  - Session management       │ │
│                         │  - Container lifecycle      │ │
│                         └──────────┬──────────────────┘ │
│                                    │                    │
│                         ┌──────────▼──────────────────┐ │
│                         │  Docker Engine              │ │
│                         │  ┌────────┐ ┌────────┐      │ │
│                         │  │Session1│ │Session2│ ...  │ │
│                         │  │ ttyd   │ │ ttyd   │      │ │
│                         │  └────────┘ └────────┘      │ │
│                         └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Step 1: Create GCP VM

```bash
gcloud compute instances create infraiq-demo \
    --zone=us-central1-a \
    --machine-type=e2-small \
    --boot-disk-size=20GB \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --tags=http-server,https-server

# Get external IP
gcloud compute instances describe infraiq-demo \
    --zone=us-central1-a \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

## Step 2: Configure DNS

In Cloudflare, add A record:
- **Name:** `demo`
- **Content:** `<VM_IP>`
- **Proxy:** OFF (grey cloud)

## Step 3: SSH and Install Dependencies

```bash
gcloud compute ssh infraiq-demo --zone=us-central1-a
```

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
```

## Step 4: Clone and Setup

```bash
# Clone demo repo
git clone https://github.com/autonops/infraiq-demo.git
cd infraiq-demo

# Create .env file
cat > .env << 'EOF'
ADMIN_SECRET=your-secret-key-here
EOF

# Build demo container image
docker build -t autonops/infraiq-demo:latest -f container/Dockerfile container/

# Start the stack
docker compose up -d
```

## Step 5: Configure Caddy

```bash
sudo tee /etc/caddy/Caddyfile << 'EOF'
demo.autonops.io {
    reverse_proxy localhost:8080
    
    # WebSocket support for ttyd
    @websocket {
        header Connection *Upgrade*
        header Upgrade websocket
    }
    reverse_proxy @websocket localhost:7700-7710
}
EOF

sudo systemctl restart caddy
```

## Step 6: Test

1. Visit https://demo.autonops.io
2. Enter email
3. Terminal should launch

---

## Operations

### View Logs

```bash
# API logs
docker compose logs -f demo-api

# List running demo sessions
docker ps | grep demo-
```

### Export Leads

```bash
curl "https://demo.autonops.io/api/leads?secret=your-secret-key-here"
```

### Update Demo Image

```bash
cd ~/infraiq-demo
git pull
docker build -t autonops/infraiq-demo:latest -f container/Dockerfile container/
docker compose restart
```

### Clean Up Stuck Sessions

```bash
# Stop all demo containers
docker ps -q --filter "name=demo-" | xargs -r docker stop

# Restart API to reset state
docker compose restart demo-api
```

---

## Troubleshooting

### Terminal Not Loading

1. Check container started:
   ```bash
   docker ps | grep demo-
   ```

2. Check ttyd port is accessible:
   ```bash
   curl http://localhost:7700
   ```

3. Check Caddy WebSocket config

### Sessions Not Expiring

Check cleanup task in API logs:
```bash
docker compose logs demo-api | grep -i cleanup
```

### Out of Memory

Increase VM size or reduce MAX_CONCURRENT_SESSIONS in API config.

---

## Cost Breakdown

| Component | Monthly Cost |
|-----------|-------------|
| e2-small VM | ~$13 |
| 20GB disk | ~$2 |
| Egress (light) | ~$1 |
| **Total** | **~$16/month** |

---

## Quick Reference

| Task | Command |
|------|---------|
| Start demo | `docker compose up -d` |
| Stop demo | `docker compose down` |
| View logs | `docker compose logs -f` |
| Rebuild image | `docker build -t autonops/infraiq-demo:latest -f container/Dockerfile container/` |
| Export leads | `curl ".../api/leads?secret=..."` |
| Check health | `curl https://demo.autonops.io/api/health` |
