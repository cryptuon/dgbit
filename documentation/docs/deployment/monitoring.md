# Monitoring

Set up monitoring for your dgbit deployment.

## Logging

### Log Configuration

Configure logging via environment variables:

```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Log Format

dgbit uses structured JSON logging in production:

```json
{
    "timestamp": "2024-01-15T10:30:00Z",
    "level": "INFO",
    "logger": "dgbit_api.api.routes",
    "message": "Backtest job created",
    "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Log Aggregation

Ship logs to a central system:

#### Using Docker Logging Drivers

```yaml
# docker-compose.yml
services:
  api:
    logging:
      driver: fluentd
      options:
        fluentd-address: localhost:24224
        tag: dgbit.api
```

#### Using Filebeat

```yaml
# filebeat.yml
filebeat.inputs:
  - type: container
    paths:
      - /var/lib/docker/containers/*/*.log
    processors:
      - add_docker_metadata: ~

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
```

## Metrics

### Prometheus Integration

Add Prometheus metrics to dgbit:

```python
# metrics.py
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter(
    'dgbit_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'dgbit_request_duration_seconds',
    'Request latency',
    ['method', 'endpoint']
)

BACKTEST_DURATION = Histogram(
    'dgbit_backtest_duration_seconds',
    'Backtest execution time'
)

TRADES_TOTAL = Counter(
    'dgbit_trades_total',
    'Total trades executed',
    ['symbol', 'side', 'result']
)
```

### Metrics Endpoint

```python
from fastapi import FastAPI
from prometheus_client import generate_latest

@app.get("/metrics")
async def metrics():
    return Response(
        generate_latest(),
        media_type="text/plain"
    )
```

### Prometheus Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'dgbit'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
```

## Dashboards

### Grafana Dashboard

Key panels for a dgbit dashboard:

1. **Request Rate** - Requests per second
2. **Error Rate** - 4xx/5xx responses
3. **Latency** - P50, P95, P99 response times
4. **Active Jobs** - Pending/running jobs
5. **Trade Activity** - Trades per hour
6. **System Resources** - CPU, memory, disk

### Example Grafana Dashboard JSON

```json
{
  "title": "dgbit Overview",
  "panels": [
    {
      "title": "Request Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(dgbit_requests_total[5m])",
          "legendFormat": "{{method}} {{endpoint}}"
        }
      ]
    },
    {
      "title": "Error Rate",
      "type": "stat",
      "targets": [
        {
          "expr": "sum(rate(dgbit_requests_total{status=~\"5..\"}[5m])) / sum(rate(dgbit_requests_total[5m]))"
        }
      ]
    }
  ]
}
```

## Alerting

### Alert Rules

```yaml
# alerts.yml
groups:
  - name: dgbit
    rules:
      - alert: HighErrorRate
        expr: sum(rate(dgbit_requests_total{status=~"5.."}[5m])) / sum(rate(dgbit_requests_total[5m])) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate ({{ $value | humanizePercentage }})"
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(dgbit_request_duration_seconds_bucket[5m])) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency (P95: {{ $value | humanizeDuration }})"
      
      - alert: WorkerQueueBacklog
        expr: dgbit_jobs_pending > 100
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Job queue backlog ({{ $value }} pending)"
```

### Notification Channels

Configure Alertmanager for notifications:

```yaml
# alertmanager.yml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/...'
        channel: '#dgbit-alerts'
        send_resolved: true

  - name: 'email'
    email_configs:
      - to: 'alerts@example.com'
        from: 'dgbit@example.com'
        smarthost: 'smtp.example.com:587'

route:
  receiver: 'slack'
  routes:
    - match:
        severity: critical
      receiver: 'email'
```

## Health Checks

### Application Health

```bash
# Check API health
curl -s http://localhost:8000/api/health | jq

# Expected response
{
  "service": "dgbit",
  "status": "ok",
  "version": "0.2.0",
  "stats": {
    "total_jobs": 42,
    "pending": 0,
    "running": 1,
    "completed": 38,
    "failed": 3
  }
}
```

### Docker Health

```bash
# Check container health
docker-compose ps

# Check specific container
docker inspect --format='{{.State.Health.Status}}' dgbit-api
```

### Uptime Monitoring

Use external uptime monitoring:

```bash
# UptimeRobot, Pingdom, or similar
# Monitor: https://api.yourdomain.com/api/health
# Alert if: Response != 200 for 2 minutes
```

## Tracing

### OpenTelemetry Integration

```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# Use in code
@tracer.start_as_current_span("run_backtest")
def run_backtest(config):
    span = trace.get_current_span()
    span.set_attribute("symbol", config.symbol)
    # ...
```

## Debugging

### Debug Mode

Enable debug logging:

```env
LOG_LEVEL=DEBUG
```

### Request Tracing

Add request IDs for tracing:

```python
import uuid
from fastapi import Request

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

### Profiling

Profile slow endpoints:

```python
import cProfile
import pstats

def profile_endpoint():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Your code here
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)
```

## Best Practices

1. **Log at appropriate levels**
   - DEBUG: Detailed debugging
   - INFO: Normal operations
   - WARNING: Unexpected but handled
   - ERROR: Failures requiring attention

2. **Include context in logs**
   - Request ID
   - User ID (if applicable)
   - Job ID for async operations

3. **Set up alerts for**
   - Error rate > 1%
   - Latency P95 > 500ms
   - Job queue > 100
   - Memory > 80%
   - Disk > 90%

4. **Review dashboards daily**
   - Look for trends
   - Investigate anomalies
   - Plan capacity
