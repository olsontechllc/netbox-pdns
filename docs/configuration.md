# Configuration

Complete configuration reference for the Netbox PowerDNS Connector.

!!! info "Environment Variables"
    All configuration uses environment variables with the prefix `NETBOX_PDNS_`.

## :gear: Core Settings

### Required Configuration

| Setting | Type | Description | Environment Variable |
|---------|------|-------------|---------------------|
| `api_key` | `string` | Secret API key for webhook authentication | `NETBOX_PDNS_API_KEY` |
| `nb_url` | `string` | Netbox installation URL with DNS plugin | `NETBOX_PDNS_NB_URL` |
| `nb_token` | `string` | Netbox API token | `NETBOX_PDNS_NB_TOKEN` |
| `nb_ns_id` | `integer` | Netbox nameserver object ID | `NETBOX_PDNS_NB_NS_ID` |
| `pdns_url` | `string` | PowerDNS Authoritative Server API URL | `NETBOX_PDNS_PDNS_URL` |
| `pdns_token` | `string` | PowerDNS API token | `NETBOX_PDNS_PDNS_TOKEN` |

### Optional Core Settings

| Setting | Type | Default | Description | Environment Variable |
|---------|------|---------|-------------|---------------------|
| `webhook_secret` | `string` | `None` | HMAC webhook signature secret | `NETBOX_PDNS_WEBHOOK_SECRET` |
| `sync_crontab` | `string` | `*/15 * * * *` | Periodic sync schedule | `NETBOX_PDNS_SYNC_CRONTAB` |
| `log_level` | `string` | `INFO` | Logging level | `NETBOX_PDNS_LOG_LEVEL` |
| `pdns_server_id` | `string` | `localhost` | PowerDNS server identifier | `NETBOX_PDNS_PDNS_SERVER_ID` |

## :lock: Security Settings

### HMAC Signature Verification

Enable webhook signature verification for enhanced security:

```bash
export NETBOX_PDNS_WEBHOOK_SECRET="your-secret-key-here"
```

!!! tip "Security Recommendation"
    Always configure `webhook_secret` in production environments to prevent unauthorized webhook requests.

### Rate Limiting

Rate limiting is automatically enabled with the following defaults:

| Endpoint Type | Limit | Description |
|---------------|-------|-------------|
| Health checks | 100/minute | `/health` endpoint |
| Status checks | 30/minute | `/status`, `/mqtt/status` endpoints |
| Sync operations | 5/minute | `/sync` endpoint |
| Webhook operations | 20/minute | Zone creation/update/delete |

!!! note "Rate Limit Customization"
    Rate limits are currently hardcoded but will be configurable in future versions.

## :arrows_counterclockwise: MQTT Settings

### Basic MQTT Configuration

| Setting | Type | Default | Description | Environment Variable |
|---------|------|---------|-------------|---------------------|
| `mqtt_enabled` | `boolean` | `False` | Enable MQTT integration | `NETBOX_PDNS_MQTT_ENABLED` |
| `mqtt_broker_url` | `string` | `mqtt://localhost:1883` | MQTT broker connection URL | `NETBOX_PDNS_MQTT_BROKER_URL` |
| `mqtt_client_id` | `string` | `netbox-pdns` | Unique MQTT client identifier | `NETBOX_PDNS_MQTT_CLIENT_ID` |
| `mqtt_topic_prefix` | `string` | `dns/zones` | Topic prefix for zone messages | `NETBOX_PDNS_MQTT_TOPIC_PREFIX` |

### MQTT Advanced Settings

| Setting | Type | Default | Range | Description | Environment Variable |
|---------|------|---------|-------|-------------|---------------------|
| `mqtt_qos` | `integer` | `1` | 0-2 | Quality of Service level | `NETBOX_PDNS_MQTT_QOS` |
| `mqtt_keepalive` | `integer` | `60` | 10-3600 | Connection keepalive (seconds) | `NETBOX_PDNS_MQTT_KEEPALIVE` |
| `mqtt_reconnect_delay` | `integer` | `5` | 1-300 | Initial reconnection delay (seconds) | `NETBOX_PDNS_MQTT_RECONNECT_DELAY` |

### MQTT Authentication

| Setting | Type | Default | Description | Environment Variable |
|---------|------|---------|-------------|---------------------|
| `mqtt_username` | `string` | `None` | MQTT broker username | `NETBOX_PDNS_MQTT_USERNAME` |
| `mqtt_password` | `string` | `None` | MQTT broker password | `NETBOX_PDNS_MQTT_PASSWORD` |

!!! warning "MQTT Authentication"
    Both `mqtt_username` and `mqtt_password` must be provided together or both omitted.

## :wrench: Advanced Configuration

### Logging Configuration

Available log levels (case-insensitive):

- `DEBUG`: Detailed debugging information
- `INFO`: General operational information (default)
- `WARNING`: Warning messages for recoverable issues
- `ERROR`: Error messages for serious problems
- `CRITICAL`: Critical errors that may stop the application

```bash
export NETBOX_PDNS_LOG_LEVEL=DEBUG
```

### Cron Schedule Format

The sync schedule uses standard cron format:

```
# ┌───────────── minute (0 - 59)
# │ ┌───────────── hour (0 - 23)
# │ │ ┌───────────── day of the month (1 - 31)
# │ │ │ ┌───────────── month (1 - 12)
# │ │ │ │ ┌───────────── day of the week (0 - 6)
# │ │ │ │ │
# */15 * * * *
```

Examples:

| Schedule | Cron Expression | Description |
|----------|----------------|-------------|
| Every minute | `*/15 * * * *` | Default - testing only |
| Every hour | `0 * * * *` | Hourly sync |
| Every 6 hours | `0 */6 * * *` | Production recommended |
| Daily at 2 AM | `0 2 * * *` | Low-traffic sync |
| Twice daily | `0 2,14 * * *` | 2 AM and 2 PM |

## :file_folder: Configuration File

### .env File Example

Create a `.env` file for local development:

```bash
# Core Configuration
NETBOX_PDNS_API_KEY=your-webhook-api-key
NETBOX_PDNS_WEBHOOK_SECRET=your-hmac-secret-key

# Netbox Configuration
NETBOX_PDNS_NB_URL=https://netbox.example.com
NETBOX_PDNS_NB_TOKEN=your-netbox-api-token
NETBOX_PDNS_NB_NS_ID=1

# PowerDNS Configuration
NETBOX_PDNS_PDNS_URL=https://pdns.example.com:8081
NETBOX_PDNS_PDNS_TOKEN=your-powerdns-api-key
NETBOX_PDNS_PDNS_SERVER_ID=localhost

# Operational Settings
NETBOX_PDNS_LOG_LEVEL=INFO
NETBOX_PDNS_SYNC_CRONTAB=0 */6 * * *

# MQTT Configuration (Optional)
NETBOX_PDNS_MQTT_ENABLED=true
NETBOX_PDNS_MQTT_BROKER_URL=mqtts://mqtt.example.com:8883
NETBOX_PDNS_MQTT_USERNAME=netbox-pdns-user
NETBOX_PDNS_MQTT_PASSWORD=secure-mqtt-password
NETBOX_PDNS_MQTT_CLIENT_ID=netbox-pdns-primary
NETBOX_PDNS_MQTT_QOS=1
```

### Docker Environment File

For Docker deployments, use the same `.env` file:

```bash
docker run --env-file .env -p 8000:8000 ghcr.io/olsontechllc/netbox-pdns:latest
```

## :heavy_check_mark: Configuration Validation

The application validates configuration on startup and will report specific errors:

### URL Validation

- Netbox URL must use `http` or `https` scheme
- PowerDNS URL must use `http` or `https` scheme
- MQTT broker URL must use `mqtt` or `mqtts` scheme

### Value Validation

- `nb_ns_id` must be a positive integer
- Log level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL
- MQTT QoS must be 0, 1, or 2
- Cron expression must have exactly 5 fields

### Example Validation Errors

```
ValidationError: Invalid log level 'TRACE'. Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL
ValidationError: MQTT broker URL must use mqtt or mqtts scheme, got: http
ValidationError: Both mqtt_username and mqtt_password must be provided together, or both omitted
```

## :rocket: Environment-Specific Configurations

### Development

```bash
# Minimal configuration for development
export NETBOX_PDNS_LOG_LEVEL=DEBUG
export NETBOX_PDNS_SYNC_CRONTAB="*/5 * * * *"  # Every 5 minutes
```

### Staging

```bash
# Staging environment with MQTT
export NETBOX_PDNS_LOG_LEVEL=INFO
export NETBOX_PDNS_SYNC_CRONTAB="0 */2 * * *"  # Every 2 hours
export NETBOX_PDNS_MQTT_ENABLED=true
export NETBOX_PDNS_WEBHOOK_SECRET=staging-secret
```

### Production

```bash
# Production with all security features
export NETBOX_PDNS_LOG_LEVEL=WARNING
export NETBOX_PDNS_SYNC_CRONTAB="0 */6 * * *"  # Every 6 hours
export NETBOX_PDNS_MQTT_ENABLED=true
export NETBOX_PDNS_WEBHOOK_SECRET=production-hmac-secret
export NETBOX_PDNS_MQTT_BROKER_URL=mqtts://secure-mqtt:8883
export NETBOX_PDNS_MQTT_QOS=2  # Exactly once delivery
```

## :arrow_right: Next Steps

After configuration:

1. Review [Security](security.md) settings for production
2. Set up [MQTT Integration](mqtt.md) for real-time updates
3. Configure [Monitoring](monitoring.md) and alerting
4. Plan your [Deployment](deployment/production.md) strategy