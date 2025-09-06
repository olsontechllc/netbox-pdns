# Reliability Features

Enterprise-grade reliability and resilience for mission-critical DNS operations.

## :shield: Overview

The Netbox PowerDNS Connector implements multiple reliability patterns:

- **:arrows_counterclockwise: Exponential Backoff Retries**: Automatic recovery from transient failures
- **:lock: Thread-Safe Operations**: Concurrent operation protection  
- **:zap: Non-Blocking Startup**: Fast application startup with background sync
- **:wrench: Graceful Error Handling**: Intelligent failure management

## :arrows_counterclockwise: Exponential Backoff Retries

### Automatic Retry Logic

All PowerDNS API operations include automatic retry logic with exponential backoff:

```python
# Retry configuration (built-in)
max_attempts = 3
base_delay = 1.0 seconds  
max_delay = 60.0 seconds
backoff_factor = 2.0
jitter = True  # Prevents thundering herd
```

### Retry Strategy

The retry mechanism follows this pattern:

1. **First attempt**: Immediate execution
2. **Second attempt**: Wait ~1 second (with jitter)
3. **Third attempt**: Wait ~2 seconds (with jitter)
4. **Failure**: Log error and propagate exception

### Jitter Implementation

Random jitter prevents thundering herd problems:

```python
# Without jitter (problematic)
delay = base_delay * (backoff_factor ** attempt)

# With jitter (implemented)
delay = base_delay * (backoff_factor ** attempt) * (0.5 + random() * 0.5)
```

This ensures multiple failed operations don't all retry simultaneously.

### Operations with Retry Logic

All PowerDNS API calls include retry logic:

| Operation | API Call | Failure Scenarios |
|-----------|----------|-------------------|
| **Zone Retrieval** | `list_zone()` | Network timeouts, API unavailable |
| **Zone Creation** | `create_zone()` | Temporary API errors, rate limits |
| **Zone Updates** | `patch_zone()` | Concurrent modifications, locks |
| **Zone Deletion** | `delete_zone()` | Resource conflicts, dependencies |

### Retry Logging

Detailed logging provides visibility into retry behavior:

```
INFO: Attempting zone sync for example.com
WARNING: Function _patch_pdns_zone failed (attempt 1/3): Connection timeout. Retrying in 1.2s
WARNING: Function _patch_pdns_zone failed (attempt 2/3): Connection timeout. Retrying in 2.4s
ERROR: Function _patch_pdns_zone failed after 3 attempts: Connection timeout
```

## :lock: Thread-Safe Operations

### Operation Locking

All critical operations are protected by threading locks to prevent:

- **Race conditions** between scheduled sync and webhook operations
- **Concurrent modifications** of the same zone
- **Resource conflicts** during bulk operations

### Lock Implementation

```python
# Thread-safe operation wrapper
with self._operation_lock_with_logging("zone_sync"):
    # Atomic zone synchronization
    sync_zone(nb_zone, pdns_zone)
```

### Lock Monitoring

Advanced lock monitoring provides operational visibility:

```python
# Lock acquisition timing
DEBUG: Attempting to acquire lock for operation: full_sync
DEBUG: Lock acquired for full_sync (waited 0.001s)
INFO: Synchronizing all zones from Netbox
DEBUG: Lock released for full_sync (total operation time: 45.234s)
```

### Lock Contention Detection

Automatic detection and logging of lock contention:

- **Warnings** for waits > 1 second
- **Errors** for lock timeouts > 30 seconds
- **Metrics** for lock hold times

Example log output:

```
WARNING: Lock acquired for mqtt_zone_update after 2.34s wait
ERROR: Failed to acquire lock for full_sync within 30 seconds
```

## :zap: Non-Blocking Startup

### Background Initial Sync

The application starts immediately with sync operations running in background:

```python
# Traditional blocking startup (problematic)
app = FastAPI()
api.full_sync()  # Blocks until complete
return app

# Non-blocking startup (implemented)  
app = FastAPI()
threading.Thread(target=api.full_sync, daemon=True).start()
return app  # Returns immediately
```

### Startup Status Tracking

Application state is tracked during initialization:

```python
app_state = {
    "initial_sync_complete": False,
    "initial_sync_started": False, 
    "initial_sync_error": None,
    "startup_time": time.time()
}
```

### Status Visibility

The `/status` endpoint provides startup progress visibility:

```json
{
  "status": "Healthy",
  "uptime_seconds": 15.3,
  "initial_sync": {
    "started": true,
    "completed": false,  
    "error": null
  }
}
```

### Health Status Logic

Smart health status determination:

- **Healthy**: Normal operation
- **Warning**: Sync incomplete after 5 minutes
- **Degraded**: Sync failed with errors

## :wrench: Graceful Error Handling

### Conflict Resolution

Intelligent handling of PowerDNS conflicts:

```python
# 409 Conflict handling (zone already exists)
if "409" in str(e) and "Conflict" in str(e):
    logger.warning("Zone already exists in PowerDNS, skipping creation")
    return  # Graceful handling, not an error
```

### Error Classification

Errors are classified for appropriate handling:

| Error Type | Handling Strategy | Example |
|------------|-------------------|---------|
| **Transient** | Retry with backoff | Network timeouts, rate limits |
| **Conflict** | Skip with warning | Zone already exists |
| **Configuration** | Fail fast | Invalid credentials, missing settings |
| **Logic** | Log and continue | Zone not found (expected in some cases) |

### Exception Chaining

Proper exception chaining preserves error context:

```python
try:
    process_webhook(data)
except ValidationError as e:
    raise HTTPException(status_code=400, detail=f"Invalid data: {e}") from e
```

This maintains the full error trace for debugging while presenting clean user messages.

### Circuit Breaker Pattern (Future)

Planned circuit breaker implementation for external API protection:

- **Closed**: Normal operation
- **Open**: Temporary API bypass during outages  
- **Half-Open**: Gradual recovery testing

## :bar_chart: Reliability Monitoring

### Key Metrics

Monitor these reliability indicators:

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| **Retry Rate** | Percentage of operations requiring retries | > 10% |
| **Lock Wait Time** | Average time waiting for locks | > 1 second |
| **Sync Success Rate** | Percentage of successful sync operations | < 95% |
| **Error Rate** | Rate of unrecoverable errors | > 1% |

### Health Check Integration

Health checks reflect reliability status:

```bash
# Simple health check
curl http://localhost:8000/health
{"status": "Healthy"}

# Detailed reliability status  
curl http://localhost:8000/status | jq '.reliability'
{
  "last_sync": "2024-01-15T10:30:00Z",
  "sync_success_rate": 0.98,
  "average_retry_rate": 0.05,
  "lock_contention_events": 2
}
```

## :gear: Configuration for Reliability

### Sync Scheduling

Configure sync frequency based on reliability requirements:

```bash
# High availability (more frequent sync)
export NETBOX_PDNS_SYNC_CRONTAB="*/15 * * * *"  # Every 15 minutes

# Standard reliability (default)
export NETBOX_PDNS_SYNC_CRONTAB="0 */6 * * *"   # Every 6 hours

# Maintenance mode (daily sync)
export NETBOX_PDNS_SYNC_CRONTAB="0 2 * * *"     # Daily at 2 AM
```

### Logging Configuration

Enable detailed reliability logging:

```bash
# Debug level for troubleshooting
export NETBOX_PDNS_LOG_LEVEL=DEBUG

# Info level for production monitoring  
export NETBOX_PDNS_LOG_LEVEL=INFO
```

### Resource Limits

Configure appropriate resource limits:

```yaml
# Docker Compose resource limits
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
    reservations:
      cpus: '0.5'  
      memory: 256M
```

## :warning: Common Reliability Issues

### High Retry Rates

**Symptoms**: Many retry warnings in logs
**Causes**: Network instability, API rate limits, server overload
**Solutions**:
- Check network connectivity to APIs
- Verify API rate limits and quotas
- Monitor server resource usage

### Lock Contention

**Symptoms**: Lock wait warnings, delayed operations
**Causes**: Concurrent webhook floods, long-running sync operations
**Solutions**:
- Implement webhook rate limiting at source
- Optimize sync operations for speed
- Consider batch processing for bulk changes

### Sync Failures

**Symptoms**: Sync error messages, status endpoint shows errors
**Causes**: API credential issues, network problems, data inconsistencies
**Solutions**:
- Verify API credentials and permissions
- Check API connectivity and status
- Review zone data for consistency

### Memory Leaks

**Symptoms**: Gradual memory increase, eventual OOM kills
**Causes**: Unclosed connections, object retention, large zone sets
**Solutions**:
- Monitor memory usage trends
- Implement connection pooling
- Configure appropriate memory limits

## :rocket: Reliability Best Practices

### Deployment Practices

1. **Health Checks**: Configure container health checks
2. **Resource Limits**: Set appropriate CPU and memory limits  
3. **Restart Policies**: Use `unless-stopped` or `always`
4. **Rolling Updates**: Deploy with zero downtime

### Monitoring Practices

1. **Metrics Collection**: Gather reliability metrics
2. **Alerting**: Set up alerts for degraded performance
3. **Log Aggregation**: Centralize logs for analysis
4. **Dashboard**: Create reliability monitoring dashboard

### Operational Practices

1. **Regular Testing**: Test failure scenarios
2. **Backup Procedures**: Document recovery procedures
3. **Incident Response**: Prepare for reliability incidents
4. **Capacity Planning**: Monitor resource usage trends

## :arrow_right: Next Steps

To improve system reliability:

1. **Set up [Monitoring](monitoring.md)**: Implement comprehensive monitoring
2. **Configure [MQTT](mqtt.md)**: Add real-time sync for better reliability
3. **Review [Deployment](deployment/production.md)**: Production reliability patterns
4. **Plan [Disaster Recovery](deployment/production.md#disaster-recovery)**: Backup and recovery procedures