# Netbox PowerDNS Connector

[![Build Status](https://github.com/olsontechllc/netbox-pdns/workflows/CI/badge.svg)](https://github.com/olsontechllc/netbox-pdns/actions)
[![Coverage Status](https://codecov.io/gh/olsontechllc/netbox-pdns/branch/main/graph/badge.svg)](https://codecov.io/gh/olsontechllc/netbox-pdns)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue)](https://netbox-pdns.olsontech.io)

A high-performance, enterprise-grade connector that synchronizes DNS zones between [Netbox DNS](https://github.com/peteeckel/netbox-plugin-dns) and [PowerDNS Authoritative](https://www.powerdns.com/) servers.

## ✨ Features

- **🔄 Real-time Sync**: Webhook and MQTT-based zone synchronization
- **🔒 Enterprise Security**: HMAC signature verification, timing-safe authentication, rate limiting
- **🛡️ High Reliability**: Exponential backoff retries, graceful error handling, thread-safe operations  
- **📊 Comprehensive Monitoring**: Health checks, detailed status endpoints, structured logging
- **⚡ Performance**: Non-blocking startup, concurrent operations, 85% test coverage
- **🐳 Production Ready**: Docker support, Kubernetes manifests, extensive documentation

## 🚀 Quick Start

### Docker (Recommended)

```bash
docker run -d \
  --name netbox-pdns \
  -p 8000:8000 \
  -e NETBOX_PDNS_API_KEY="your-webhook-api-key" \
  -e NETBOX_PDNS_NB_URL="https://netbox.example.com" \
  -e NETBOX_PDNS_NB_TOKEN="your-netbox-token" \
  -e NETBOX_PDNS_NB_NS_ID="1" \
  -e NETBOX_PDNS_PDNS_URL="https://pdns.example.com:8081" \
  -e NETBOX_PDNS_PDNS_TOKEN="your-pdns-token" \
  netbox-pdns:latest

# Verify installation
curl http://localhost:8000/health
```

### From Source

```bash
git clone https://github.com/olsontechllc/netbox-pdns.git
cd netbox-pdns
uv sync
uv run netbox-pdns
```

## 📚 Documentation

| Section | Description |
|---------|-------------|
| [**Quick Start**](https://netbox-pdns.olsontech.io/quickstart/) | Get running in 5 minutes |
| [**Installation**](https://netbox-pdns.olsontech.io/installation/) | Detailed setup instructions |
| [**Configuration**](https://netbox-pdns.olsontech.io/configuration/) | Complete configuration reference |
| [**Security**](https://netbox-pdns.olsontech.io/security/) | HMAC signatures, rate limiting, best practices |
| [**MQTT Integration**](https://netbox-pdns.olsontech.io/mqtt/) | Real-time synchronization setup |
| [**Deployment**](https://netbox-pdns.olsontech.io/deployment/docker/) | Docker, Kubernetes, production guides |
| [**API Reference**](https://netbox-pdns.olsontech.io/api/endpoints/) | REST API and webhook documentation |

## 🔧 Configuration

Minimum required configuration:

```bash
export NETBOX_PDNS_API_KEY="your-webhook-api-key"
export NETBOX_PDNS_NB_URL="https://netbox.example.com"
export NETBOX_PDNS_NB_TOKEN="your-netbox-token" 
export NETBOX_PDNS_NB_NS_ID="1"
export NETBOX_PDNS_PDNS_URL="https://pdns.example.com:8081"
export NETBOX_PDNS_PDNS_TOKEN="your-pdns-token"
```

Production security (recommended):

```bash
export NETBOX_PDNS_WEBHOOK_SECRET="your-hmac-secret"  # Enable signature verification
export NETBOX_PDNS_MQTT_ENABLED=true                  # Enable real-time updates
export NETBOX_PDNS_MQTT_BROKER_URL="mqtts://mqtt.example.com:8883"
```

See [Configuration Guide](https://netbox-pdns.olsontech.io/configuration/) for complete options.

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/health
# {"status": "Healthy"}
```

### Detailed Status

```bash
curl http://localhost:8000/status | jq
```

```json
{
  "status": "Healthy",
  "uptime_seconds": 3600.42,
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
    "enabled": true,
    "connected": true
  }
}
```

## 🛡️ Production Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  netbox-pdns:
    image: netbox-pdns:latest
    ports:
      - "8000:8000"
    environment:
      - NETBOX_PDNS_WEBHOOK_SECRET=your-hmac-secret
      - NETBOX_PDNS_MQTT_ENABLED=true
      # ... other config
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Kubernetes

```bash
helm repo add netbox-pdns https://charts.netbox-pdns.olsontech.io
helm install netbox-pdns netbox-pdns/netbox-pdns
```

See [Deployment Guides](https://netbox-pdns.olsontech.io/deployment/docker/) for complete examples.

## 🔒 Security

Enterprise security features included:

- **HMAC Signature Verification**: Cryptographic webhook authentication
- **Timing-Safe Comparisons**: Protection against timing attacks  
- **Rate Limiting**: Built-in abuse protection
- **TLS Support**: Encrypted communications (HTTPS/MQTTS)

See [Security Guide](https://netbox-pdns.olsontech.io/security/) for configuration details.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](https://netbox-pdns.olsontech.io/development/contributing/) for details.

### Development Setup

```bash
git clone https://github.com/olsontechllc/netbox-pdns.git
cd netbox-pdns
uv sync --group dev
uv run pytest
```

## 📋 Requirements

- **Python**: 3.11+
- **Netbox**: 4.0+ with DNS plugin
- **PowerDNS**: 4.0+ Authoritative server
- **Optional**: MQTT broker for real-time updates

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🚨 Support

- **📖 Documentation**: [https://netbox-pdns.olsontech.io](https://netbox-pdns.olsontech.io)
- **🐛 Bug Reports**: [GitHub Issues](https://github.com/olsontechllc/netbox-pdns/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/olsontechllc/netbox-pdns/discussions)
- **🔒 Security**: Report security issues via email to security@olsontech.io

---

<div align="center">

**[📚 Full Documentation](https://netbox-pdns.olsontech.io)** • 
**[🚀 Quick Start](https://netbox-pdns.olsontech.io/quickstart/)** • 
**[🐳 Docker Hub](https://hub.docker.com/r/olsontech/netbox-pdns)**

</div>