# Netbox PowerDNS Connector

A high-performance, enterprise-grade connector that synchronizes DNS zones between Netbox DNS and PowerDNS Authoritative servers with advanced security, reliability, and monitoring features.

## :rocket: Key Features

- **:arrows_counterclockwise: Real-time Sync**: Webhook and MQTT-based zone synchronization
- **:lock: Enterprise Security**: HMAC signature verification, timing-safe authentication, rate limiting
- **:shield: High Reliability**: Exponential backoff retries, graceful error handling, thread-safe operations  
- **:bar_chart: Comprehensive Monitoring**: Detailed status endpoints, structured logging, health checks
- **:zap: Performance**: Non-blocking startup, concurrent operations, optimized API calls
- **:wrench: Flexible Deployment**: Docker support, extensive configuration options

## :memo: Requirements

- **Netbox**: v4.2.2+ with [Netbox DNS plugin](https://github.com/peteeckel/netbox-plugin-dns) v1.2.7+
- **PowerDNS**: Authoritative server v4.9.x with API enabled
- **Authentication**: API tokens for both services
- **Optional**: MQTT broker for real-time updates

## :warning: Important Notes

!!! warning "Zone Management"
    - Designed for dedicated PowerDNS zones managed by Netbox
    - Will remove non-Netbox records from managed zones  
    - Supports co-existence with other domains not in Netbox

## :rocket: Quick Start

### 1. Install

```bash
# Using Docker (recommended)
docker pull ghcr.io/olsontechllc/netbox-pdns:latest

# Or from source
git clone https://github.com/olsontechllc/netbox-pdns
cd netbox-pdns
uv sync
```

### 2. Configure

```bash
# Minimum required configuration
export NETBOX_PDNS_API_KEY="your-webhook-api-key"
export NETBOX_PDNS_NB_URL="https://netbox.example.com"
export NETBOX_PDNS_NB_TOKEN="your-netbox-token"
export NETBOX_PDNS_NB_NS_ID="1"
export NETBOX_PDNS_PDNS_URL="https://pdns.example.com:8081"
export NETBOX_PDNS_PDNS_TOKEN="your-pdns-token"
```

### 3. Run

```bash
# Docker
docker run -p 8000:8000 --env-file .env ghcr.io/olsontechllc/netbox-pdns:latest

# From source
uv run netbox-pdns
```

### 4. Verify

```bash
# Check health
curl http://localhost:8000/health

# Check detailed status
curl http://localhost:8000/status
```

## :books: Documentation

| Section | Description |
|---------|-------------|
| [Quick Start](quickstart.md) | Get up and running in 5 minutes |
| [Installation](installation.md) | Detailed installation instructions |
| [Configuration](configuration.md) | Complete configuration reference |
| [Security](security.md) | Security features and best practices |
| [Reliability](reliability.md) | Reliability and error handling |

## :wrench: Development

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Testing**: pytest with 85% coverage
- **Code Quality**: ruff, mypy, pre-commit hooks
- **Documentation**: MkDocs with Material theme

## :handshake: Contributing

We welcome contributions! Please see the GitHub repository for development guidelines.

## :scroll: License

This project is licensed under the MIT License - see the LICENSE file for details.

## :question: Support

- **Documentation**: Full documentation available in this site
- **Issues**: Report bugs on [GitHub Issues](https://github.com/olsontechllc/netbox-pdns/issues)
- **Discussions**: Community support via [GitHub Discussions](https://github.com/olsontechllc/netbox-pdns/discussions)