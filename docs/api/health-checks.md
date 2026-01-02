# Health Check API

This document describes the health check endpoints for monitoring FlexLink's operational status.

## Endpoints

### GET /health

Basic health check endpoint.

**Description:**
Simple endpoint to verify the service is running. Returns minimal information for quick health checks.

**Example:**
```bash
curl http://localhost:8000/health
```

**Response (HTTP 200):**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-23T12:00:00.000000"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Health status (`healthy` or `unhealthy`) |
| `timestamp` | string | ISO 8601 timestamp of the check |

**Use Cases:**
- Container health checks (Docker, Kubernetes)
- Load balancer health probes
- Uptime monitoring
- Quick service availability checks

**Docker Health Check Example:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

**Kubernetes Liveness Probe:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
  timeoutSeconds: 3
  failureThreshold: 3
```

### GET /health/detailed

Detailed system health and component information.

**Description:**
Comprehensive health check that returns detailed information about system components, dependencies, and configuration.

**Example:**
```bash
curl http://localhost:8000/health/detailed
```

**Response (HTTP 200):**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-23T12:00:00.000000",
  "system": {
    "platform": "Linux",
    "python_version": "3.12.12"
  },
  "components": {
    "api": "healthy",
    "file_processing": "healthy",
    "connectors": {
      "count": 4,
      "names": ["my_api", "jsonplaceholder", "postgres", "webhook"]
    },
    "routes": {
      "count": 12
    }
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Overall health status |
| `timestamp` | string | ISO 8601 timestamp |
| `system.platform` | string | Operating system platform |
| `system.python_version` | string | Python version |
| `components.api` | string | API component status |
| `components.file_processing` | string | File processing component status |
| `components.connectors` | object | Connector information |
| `components.connectors.count` | integer | Number of registered connectors |
| `components.connectors.names` | array[string] | List of connector names |
| `components.routes.count` | integer | Number of configured routes |

**Use Cases:**
- Operational dashboards
- Debugging deployment issues
- Configuration verification
- Dependency checking
- Performance monitoring

**Kubernetes Readiness Probe:**
```yaml
readinessProbe:
  httpGet:
    path: /health/detailed
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 10
  timeoutSeconds: 5
  successThreshold: 1
  failureThreshold: 3
```

## Health Status Values

| Status | Description | HTTP Code |
|--------|-------------|-----------|
| `healthy` | All components operational | 200 |
| `degraded` | Some non-critical components failing | 200 |
| `unhealthy` | Critical components failing | 503 |

**Note:** Currently FlexLink returns `healthy` when operational. Future versions will add dependency health checks (database, external APIs) with degraded/unhealthy states.

## Monitoring Integration

### Prometheus Metrics (Planned for v0.5.0)

```yaml
# Example prometheus.yml
scrape_configs:
  - job_name: 'flexlink'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Uptime Monitoring

Configure uptime monitors to check `/health` endpoint:

**UptimeRobot Example:**
- Monitor Type: HTTP(s)
- URL: `http://your-domain.com/health`
- Keyword: `healthy`
- Interval: 5 minutes

**Pingdom Example:**
- Check Type: HTTP Check
- URL: `https://your-domain.com/health`
- Response should contain: `"status":"healthy"`
- Check interval: 1 minute

### Log Aggregation

Health check requests are logged for monitoring:

```
INFO: Health check: status=healthy
INFO: Detailed health check: status=healthy, connectors=4, routes=12
```

Configure log aggregation (ELK, Splunk, etc.) to track health check patterns.

## Best Practices

### 1. Use Basic Health Check for Load Balancers

Use `/health` for frequent checks to minimize overhead:

```bash
# Simple and fast
curl http://localhost:8000/health
```

### 2. Use Detailed Health Check for Debugging

Use `/health/detailed` when investigating issues:

```bash
# Get component details
curl http://localhost:8000/health/detailed | jq .
```

### 3. Set Appropriate Timeouts

Configure health check timeouts based on endpoint:

**Basic health check:**
- Timeout: 3 seconds
- Interval: 30 seconds

**Detailed health check:**
- Timeout: 5 seconds
- Interval: 60 seconds

### 4. Monitor Health Check Failures

Set up alerts for repeated health check failures:

```yaml
# Example Prometheus alert
- alert: FlexLinkUnhealthy
  expr: probe_success{job="flexlink"} == 0
  for: 2m
  annotations:
    summary: "FlexLink is unhealthy"
    description: "Health check has been failing for 2 minutes"
```

### 5. Include Health Checks in CI/CD

Verify deployment health after deployments:

```bash
#!/bin/bash
# deploy.sh

# Deploy application
docker-compose up -d

# Wait for health check
for i in {1..30}; do
  if curl -f http://localhost:8000/health; then
    echo "Deployment successful!"
    exit 0
  fi
  sleep 2
done

echo "Deployment failed: Health check timeout"
exit 1
```

## Troubleshooting

### Health Check Returns 503

**Possible Causes:**
- Application starting up
- Critical dependency unavailable
- Configuration error

**Diagnosis:**
```bash
# Check application logs
docker logs flexlink

# Check detailed health status
curl http://localhost:8000/health/detailed
```

### Health Check Timeout

**Possible Causes:**
- Application not responding
- Network issues
- Resource exhaustion

**Diagnosis:**
```bash
# Check if container is running
docker ps | grep flexlink

# Check resource usage
docker stats flexlink

# Check application logs
docker logs flexlink --tail 100
```

### Intermittent Health Check Failures

**Possible Causes:**
- Resource contention
- Transient network issues
- Slow startup

**Solutions:**
1. Increase health check timeout
2. Add initial delay for startup
3. Increase retry count
4. Check resource limits

## Related Documentation

- [Troubleshooting Guide](../TROUBLESHOOTING.md)
- [Docker Deployment](../../README.md#docker-deployment)
- [REST Integration API](./rest-integration.md)
