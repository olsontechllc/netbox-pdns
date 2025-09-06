# Security Features

Comprehensive security features to protect your DNS infrastructure.

## :shield: Overview

The Netbox PowerDNS Connector implements multiple layers of security:

- **:lock: HMAC Signature Verification**: Cryptographic webhook authentication
- **:hourglass: Timing-Safe Authentication**: Protection against timing attacks
- **:traffic_light: Rate Limiting**: Built-in abuse protection
- **:closed_lock_with_key: Secure Configuration**: Best practices enforcement

## :lock: HMAC Signature Verification

### What is HMAC?

HMAC (Hash-based Message Authentication Code) provides cryptographic authentication for webhook requests, ensuring that:

- Requests originate from authorized sources
- Message content hasn't been tampered with
- Replay attacks are mitigated

### Configuration

Enable HMAC verification with a secret key:

```bash
export NETBOX_PDNS_WEBHOOK_SECRET="your-secure-secret-key"
```

!!! warning "Production Requirement"
    Always configure `WEBHOOK_SECRET` in production environments. Without it, only API key authentication is used.

### Generating Secure Secrets

Use cryptographically secure methods to generate secrets:

```bash
# Using OpenSSL (recommended)
openssl rand -hex 32

# Using Python
python -c "import secrets; print(secrets.token_hex(32))"

# Using /dev/urandom on Unix
head -c 32 /dev/urandom | base64
```

### Webhook Request Format

When HMAC is enabled, webhook requests must include both:

1. **API Key Header**: `x-netbox-pdns-api-key`
2. **HMAC Signature Header**: `x-hub-signature-256` or `x-signature-256`

Example request:

```bash
curl -X POST https://netbox-pdns.example.com/zones/create \
  -H "x-netbox-pdns-api-key: your-api-key" \
  -H "x-hub-signature-256: sha256=computed-hmac-signature" \
  -H "Content-Type: application/json" \
  -d '{"id": 123, "name": "example.com"}'
```

### HMAC Signature Calculation

The signature is calculated as:

```
HMAC-SHA256(webhook_secret, request_body)
```

Example in Python:

```python
import hmac
import hashlib
import json

def calculate_signature(secret, payload):
    """Calculate HMAC-SHA256 signature for webhook payload."""
    if isinstance(payload, dict):
        payload = json.dumps(payload, separators=(',', ':'))
    if isinstance(payload, str):
        payload = payload.encode('utf-8')
    
    signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return f"sha256={signature}"

# Example usage
secret = "your-webhook-secret"
payload = {"id": 123, "name": "example.com"}
signature = calculate_signature(secret, payload)
print(signature)  # sha256=abcdef123456...
```

### Netbox Webhook Configuration

Configure Netbox webhooks to send HMAC signatures:

1. **Navigate to**: Admin → Webhooks
2. **Create/Edit webhook** for DNS zone events
3. **Set URL**: `https://your-netbox-pdns.example.com/zones/{action}`
4. **Add Headers**:
   - `x-netbox-pdns-api-key`: `your-api-key`
   - `x-hub-signature-256`: Use Netbox's built-in HMAC feature
5. **Secret**: Set to your `NETBOX_PDNS_WEBHOOK_SECRET` value

## :hourglass: Timing-Safe Authentication

### Protection Against Timing Attacks

All authentication comparisons use `secrets.compare_digest()` to prevent timing attacks:

```python
# Vulnerable (DO NOT USE)
if user_api_key == configured_api_key:
    return True

# Secure (IMPLEMENTED)
if secrets.compare_digest(user_api_key, configured_api_key):
    return True
```

### Why This Matters

Timing attacks exploit microsecond differences in string comparison:

- **Vulnerable code** fails fast on first character mismatch
- **Secure code** always takes the same time regardless of input
- Prevents attackers from guessing secrets character by character

## :traffic_light: Rate Limiting

### Built-in Rate Limits

Automatic protection against abuse and DDoS attacks:

| Endpoint Category | Limit | Endpoints |
|------------------|-------|-----------|
| **Health Checks** | 100/minute | `/health` |
| **Status Monitoring** | 30/minute | `/status`, `/mqtt/status` |
| **Sync Operations** | 5/minute | `/sync` |
| **Webhook Operations** | 20/minute | `/zones/create`, `/zones/update`, `/zones/delete` |

### Rate Limit Headers

Responses include standard rate limit headers:

```
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 19  
X-RateLimit-Reset: 1640995200
```

### Rate Limit Exceeded Response

When limits are exceeded:

```json
{
  "error": "Rate limit exceeded",
  "detail": "20 per 1 minute"
}
```

HTTP Status: `429 Too Many Requests`

### Bypass Rate Limits

Rate limits are applied per client IP address. For legitimate high-volume use:

1. **Multiple IPs**: Distribute requests across different source IPs
2. **Batch Operations**: Use MQTT for high-frequency updates
3. **Caching**: Cache responses when possible

!!! note "Future Enhancement"
    Configurable rate limits and whitelisting will be added in future versions.

## :closed_lock_with_key: Configuration Security

### Secure Configuration Management

#### Environment Variables

Never hardcode secrets in configuration files:

```bash
# ✅ Good: Environment variables
export NETBOX_PDNS_API_KEY="$(cat /etc/secrets/api-key)"
export NETBOX_PDNS_WEBHOOK_SECRET="$(cat /etc/secrets/webhook-secret)"

# ❌ Bad: Hardcoded in files
NETBOX_PDNS_API_KEY=hardcoded-key-here
```

#### Docker Secrets

Use Docker secrets for secure credential management:

```yaml
# docker-compose.yml
version: '3.8'
services:
  netbox-pdns:
    image: netbox-pdns:latest
    environment:
      - NETBOX_PDNS_API_KEY_FILE=/run/secrets/api_key
      - NETBOX_PDNS_WEBHOOK_SECRET_FILE=/run/secrets/webhook_secret
    secrets:
      - api_key
      - webhook_secret

secrets:
  api_key:
    file: ./secrets/api_key.txt
  webhook_secret:
    file: ./secrets/webhook_secret.txt
```

#### Kubernetes Secrets

Store sensitive data in Kubernetes secrets:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: netbox-pdns-secrets
type: Opaque
stringData:
  api-key: your-api-key-here
  webhook-secret: your-webhook-secret-here
  netbox-token: your-netbox-token-here
  pdns-token: your-pdns-token-here
```

### File Permissions

Restrict access to configuration files:

```bash
# Set restrictive permissions
chmod 600 .env
chmod 600 config/*.conf

# Verify permissions
ls -la .env
# Should show: -rw------- (600)
```

## :rocket: Production Security Checklist

### Required Security Measures

- [ ] **HMAC Webhook Signatures**: `WEBHOOK_SECRET` configured
- [ ] **API Key Rotation**: Regular rotation schedule established
- [ ] **TLS/SSL**: All communications encrypted (HTTPS/MQTTS)
- [ ] **Firewall Rules**: Restrict access to management ports
- [ ] **Network Segmentation**: Isolate DNS infrastructure
- [ ] **Log Monitoring**: Security events monitored and alerted

### Recommended Security Measures

- [ ] **Intrusion Detection**: Monitor for attack patterns
- [ ] **Backup Authentication**: Secondary authentication method
- [ ] **Audit Logging**: Comprehensive security audit trail
- [ ] **Penetration Testing**: Regular security assessments
- [ ] **Incident Response**: Security incident procedures documented

### Security Monitoring

#### Key Security Metrics

Monitor these security-related events:

- **Authentication Failures**: Failed API key validations
- **HMAC Failures**: Invalid webhook signatures
- **Rate Limit Violations**: Potential abuse attempts
- **Unusual Traffic Patterns**: Possible reconnaissance
- **Error Spikes**: Potential attack indicators

#### Log Analysis

Security-relevant log patterns:

```bash
# Failed authentications
grep "Could not validate API key" /var/log/netbox-pdns.log

# HMAC signature failures  
grep "Invalid webhook signature" /var/log/netbox-pdns.log

# Rate limit violations
grep "Rate limit exceeded" /var/log/netbox-pdns.log
```

## :warning: Security Considerations

### Network Security

- **Firewall Configuration**: Only allow necessary ports (8000, MQTT)
- **VPN Access**: Consider VPN for administrative access
- **Network Monitoring**: Monitor for unusual traffic patterns

### API Token Security

- **Scope Limitation**: Use least-privilege principle for API tokens
- **Regular Rotation**: Rotate tokens on a schedule
- **Monitoring**: Log and monitor token usage

### MQTT Security

When using MQTT integration:

- **TLS Encryption**: Always use `mqtts://` URLs in production
- **Authentication**: Configure MQTT broker authentication
- **Topic ACLs**: Restrict topic access to specific clients

### Incident Response

Prepare for security incidents:

1. **Detection**: Automated monitoring and alerting
2. **Containment**: Procedures to isolate compromised systems  
3. **Investigation**: Log analysis and forensics
4. **Recovery**: Restoration and hardening procedures
5. **Lessons Learned**: Post-incident analysis and improvements

## :arrow_right: Next Steps

After implementing security features:

1. **Configure [Monitoring](monitoring.md)**: Set up security event monitoring
2. **Review [Deployment](deployment/production.md)**: Production security guidelines
3. **Plan [MQTT Security](mqtt.md#security)**: Secure real-time updates
4. **Document Procedures**: Create security runbooks and procedures