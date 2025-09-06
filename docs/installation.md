# Installation

This guide covers different installation methods for the Netbox PowerDNS Connector.

## :whale: Docker Installation (Recommended)

### Pre-built Images

```bash
# Pull the latest stable release
docker pull ghcr.io/olsontechllc/netbox-pdns:latest

# Or pull a specific version
docker pull ghcr.io/olsontechllc/netbox-pdns:v1.0.0
```

### Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'
services:
  netbox-pdns:
    image: ghcr.io/olsontechllc/netbox-pdns:latest
    ports:
      - "8000:8000"
    environment:
      - NETBOX_PDNS_API_KEY=your-webhook-api-key
      - NETBOX_PDNS_NB_URL=https://netbox.example.com
      - NETBOX_PDNS_NB_TOKEN=your-netbox-token
      - NETBOX_PDNS_NB_NS_ID=1
      - NETBOX_PDNS_PDNS_URL=https://pdns.example.com:8081
      - NETBOX_PDNS_PDNS_TOKEN=your-pdns-token
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Start the service:

```bash
docker-compose up -d
```

## :package: Package Installation

### From PyPI (Coming Soon)

```bash
pip install netbox-pdns
```

### From Source

#### Prerequisites

- Python 3.11 or later
- [uv](https://github.com/astral-sh/uv) package manager

#### Clone and Install

```bash
# Clone the repository
git clone https://github.com/olsontechllc/netbox-pdns.git
cd netbox-pdns

# Install dependencies
uv sync

# Install in development mode
uv sync --group dev
```

#### Run from Source

```bash
# Run directly
uv run netbox-pdns

# Or with custom options
uv run netbox-pdns --host 0.0.0.0 --port 8080
```

## :whale2: Kubernetes Installation

### Using Helm (Recommended)

```bash
# Add the Helm repository
helm repo add netbox-pdns https://charts.netbox-pdns.olsontech.io
helm repo update

# Install with custom values
helm install netbox-pdns netbox-pdns/netbox-pdns \
  --set config.api_key="your-webhook-api-key" \
  --set config.netbox.url="https://netbox.example.com" \
  --set config.netbox.token="your-netbox-token" \
  --set config.netbox.nameserver_id=1 \
  --set config.powerdns.url="https://pdns.example.com:8081" \
  --set config.powerdns.token="your-pdns-token"
```

### Manual Kubernetes Deployment

See the [Kubernetes Deployment Guide](deployment/kubernetes.md) for detailed manifests.

## :gear: System Requirements

### Minimum Requirements

- **CPU**: 1 core
- **Memory**: 256MB RAM
- **Storage**: 50MB for application
- **Network**: HTTPS access to Netbox and PowerDNS APIs

### Recommended Requirements

- **CPU**: 2 cores
- **Memory**: 512MB RAM
- **Storage**: 100MB for logs and temporary files
- **Network**: Low-latency connection to both APIs

### Dependencies

#### Required Services

| Service | Version | Purpose |
|---------|---------|---------|
| Netbox | 3.0+ | DNS zone and record management |
| Netbox DNS Plugin | 1.0+ | DNS-specific functionality |
| PowerDNS Authoritative | 4.0+ | DNS server with API |

#### Optional Services

| Service | Version | Purpose |
|---------|---------|---------|
| MQTT Broker | 3.1.1+ | Real-time zone updates |
| Redis | 6.0+ | Future: caching and rate limiting |

## :heavy_check_mark: Verification

After installation, verify the setup:

### Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status": "Healthy"}
```

### Detailed Status

```bash
curl http://localhost:8000/status
```

Expected response:
```json
{
  "status": "Healthy",
  "uptime_seconds": 120.5,
  "initial_sync": {
    "started": true,
    "completed": true,
    "error": null
  },
  "scheduler": {
    "running": true,
    "jobs_count": 1
  },
  "mqtt": {
    "enabled": false
  }
}
```

### Test Sync

```bash
# Trigger manual sync (requires API key)
curl -H "x-netbox-pdns-api-key: your-api-key" \
     http://localhost:8000/sync
```

## :warning: Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000

# Use different port
uv run netbox-pdns --port 8080
```

#### Permission Denied

```bash
# For Docker on Linux
sudo usermod -aG docker $USER
# Log out and back in

# For source installation
chmod +x scripts/netbox-pdns
```

#### Connection Refused

Check that required services are accessible:

```bash
# Test Netbox connectivity
curl -H "Authorization: Token your-netbox-token" \
     https://netbox.example.com/api/

# Test PowerDNS connectivity
curl -H "X-API-Key: your-pdns-token" \
     https://pdns.example.com:8081/api/v1/servers
```

### Logs

View application logs:

```bash
# Docker
docker logs netbox-pdns

# Docker Compose
docker-compose logs -f netbox-pdns

# Source installation
uv run netbox-pdns --log-level DEBUG
```

## :arrow_right: Next Steps

After successful installation:

1. [Configure](configuration.md) the application for your environment
2. Set up [Security](security.md) features for production
3. Configure [MQTT](mqtt.md) for real-time updates
4. Review [Deployment](deployment/production.md) best practices