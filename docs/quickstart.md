# Quick Start

Get Netbox PowerDNS Connector running in under 5 minutes.

## :zap: Prerequisites

Before starting, ensure you have:

- [ ] **Netbox** installation with DNS plugin
- [ ] **PowerDNS** Authoritative server with API enabled
- [ ] **API tokens** for both services
- [ ] **Docker** (recommended) or Python 3.11+

## :rocket: 5-Minute Setup

### Step 1: Get Required Information

Collect these details from your environment:

```bash
# Netbox Information
NETBOX_URL="https://netbox.example.com"
NETBOX_TOKEN="your-netbox-api-token"
NAMESERVER_ID="1"  # ID of nameserver object in Netbox

# PowerDNS Information  
PDNS_URL="https://pdns.example.com:8081"
PDNS_TOKEN="your-powerdns-api-key"

# Webhook Authentication
API_KEY="your-webhook-api-key"  # Generate a secure random key
```

### Step 2: Run with Docker

```bash
docker run -d \
  --name netbox-pdns \
  -p 8000:8000 \
  -e NETBOX_PDNS_API_KEY="$API_KEY" \
  -e NETBOX_PDNS_NB_URL="$NETBOX_URL" \
  -e NETBOX_PDNS_NB_TOKEN="$NETBOX_TOKEN" \
  -e NETBOX_PDNS_NB_NS_ID="$NAMESERVER_ID" \
  -e NETBOX_PDNS_PDNS_URL="$PDNS_URL" \
  -e NETBOX_PDNS_PDNS_TOKEN="$PDNS_TOKEN" \
  --restart unless-stopped \
  netbox-pdns:latest
```

### Step 3: Verify Installation

```bash
# Check container is running
docker ps | grep netbox-pdns

# Test health endpoint
curl http://localhost:8000/health
# Expected: {"status": "Healthy"}

# Check detailed status
curl http://localhost:8000/status | jq
```

### Step 4: Trigger Initial Sync

```bash
# Manual sync (requires API key)
curl -H "x-netbox-pdns-api-key: $API_KEY" \
     http://localhost:8000/sync
```

## :gear: Docker Compose Setup

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  netbox-pdns:
    image: netbox-pdns:latest
    ports:
      - "8000:8000"
    environment:
      - NETBOX_PDNS_API_KEY=${API_KEY}
      - NETBOX_PDNS_NB_URL=${NETBOX_URL}
      - NETBOX_PDNS_NB_TOKEN=${NETBOX_TOKEN}
      - NETBOX_PDNS_NB_NS_ID=${NAMESERVER_ID}
      - NETBOX_PDNS_PDNS_URL=${PDNS_URL}
      - NETBOX_PDNS_PDNS_TOKEN=${PDNS_TOKEN}
      - NETBOX_PDNS_LOG_LEVEL=INFO
      - NETBOX_PDNS_SYNC_CRONTAB=0 */6 * * *
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

Create `.env` file:

```bash
API_KEY=your-webhook-api-key
NETBOX_URL=https://netbox.example.com
NETBOX_TOKEN=your-netbox-api-token
NAMESERVER_ID=1
PDNS_URL=https://pdns.example.com:8081
PDNS_TOKEN=your-powerdns-api-key
```

Start the service:

```bash
docker-compose up -d
```

## :warning: Common Issues

### "Connection refused" Errors

Check network connectivity:

```bash
# Test Netbox API
curl -H "Authorization: Token $NETBOX_TOKEN" \
     "$NETBOX_URL/api/plugins/netbox-dns/zones/" | jq

# Test PowerDNS API  
curl -H "X-API-Key: $PDNS_TOKEN" \
     "$PDNS_URL/api/v1/servers" | jq
```

### "Invalid nameserver ID" 

Find the correct nameserver ID:

```bash
# List nameservers in Netbox
curl -H "Authorization: Token $NETBOX_TOKEN" \
     "$NETBOX_URL/api/plugins/netbox-dns/nameservers/" | jq
```

### Container Won't Start

Check logs for specific errors:

```bash
# Docker logs
docker logs netbox-pdns

# Or with Docker Compose
docker-compose logs -f
```

## :arrow_forward: What's Next?

Now that you have a basic installation running:

### 1. **Configure Security** :lock:
Enable HMAC signature verification for production:

```bash
# Add to your environment
export NETBOX_PDNS_WEBHOOK_SECRET="your-secret-key"
```

See [Security Guide](security.md) for complete setup.

### 2. **Set up MQTT** :arrows_counterclockwise:
Enable real-time synchronization:

```bash
# Add MQTT configuration
export NETBOX_PDNS_MQTT_ENABLED=true
export NETBOX_PDNS_MQTT_BROKER_URL=mqtt://your-mqtt-broker:1883
```

See [MQTT Integration](mqtt.md) for details.

### 3. **Configure Monitoring** :bar_chart:
Set up health checks and alerting:

```bash
# Monitor with detailed status
curl http://localhost:8000/status
```

See [Monitoring Guide](monitoring.md) for comprehensive setup.

### 4. **Production Deployment** :rocket:
Review production best practices:

- [Docker Deployment](deployment/docker.md)
- [Kubernetes Deployment](deployment/kubernetes.md)  
- [Production Guide](deployment/production.md)

## :sos: Getting Help

If you encounter issues:

1. **Check Logs**: Always start with application logs
2. **Verify Configuration**: Use the status endpoint to check settings
3. **Test Connectivity**: Ensure both APIs are accessible
4. **GitHub Issues**: Report bugs with logs and configuration
5. **Documentation**: Full guides available for all features

!!! tip "Pro Tip"
    Start with the minimal configuration and add features incrementally. This makes troubleshooting much easier!