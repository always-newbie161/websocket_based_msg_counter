# Observability Guide

## Overview

This document describes the observability stack for the WebSocket Message Counter application, including metrics, logging, monitoring, and alerting.

## Metrics Collection

### Prometheus Metrics

The application exposes metrics at `/metrics/` endpoint in Prometheus format.

#### Core WebSocket Metrics

```promql
# Active connections
websocket_active_connections

# Total messages processed
rate(websocket_messages_total[5m])

# Error rate by type
rate(websocket_errors_total[5m])

# Connection duration percentiles
histogram_quantile(0.95, websocket_connection_duration_seconds_bucket)

# Shutdown time
websocket_shutdown_time_seconds
```


## Structured Logging

### Log Format

All logs are emitted in JSON format for machine parsing:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "logger": "chat.consumers",
  "request_id": "xxxxxxxxxxxxx",
  "session_id": "client-session-uuid",
  "event": "websocket_message_received",
  "message_count": 5,
  "message_length": 128,
  "duration_ms": 12.3,
  "client_ip": "192.168.1.100",
}
```

### Log Levels

| Level | Usage | Examples |
|-------|-------|----------|
| DEBUG | Detailed flow information | Message content, internal state |
| INFO | Normal operations | Connection established, message processed |
| WARN | Unexpected but recoverable | Reconnection attempts, rate limiting |
| ERROR | Error conditions | Connection failures, processing errors |
| CRITICAL | System failures | Service unavailable, data corruption |

### Structured Logging Implementation

```python
import structlog

logger = structlog.get_logger(__name__)

# Log with context
logger.info(
    "WebSocket message processed",
    session_id=self.session_id,
    message_count=self.message_count,
    duration_ms=processing_time * 1000
)
```

## Log Aggregation with Loki

### Loki Integration

The application ships structured logs to Grafana Loki for centralized log management and searching.

#### Configuration

```yaml
# Environment variables
LOKI_URL=http://loki:3100
LOKI_ENABLED=true
```

#### Log Labels

Loki automatically adds these labels for filtering:

```promql
{service="websocket-message-counter", environment="production", level="INFO"}
```

#### Common LogQL Queries

```logql
# All application logs
{service="websocket-message-counter"}

# Error logs only
{service="websocket-message-counter"} |= "ERROR"

# WebSocket connection events
{service="websocket-message-counter"} |= "WebSocket" | json

# Logs from specific session
{service="websocket-message-counter"} | json | session_id="uuid-here"

# Rate of error logs per minute
rate({service="websocket-message-counter"} |= "ERROR" [1m])

# Top error messages
topk(10, 
  sum by (message) (
    count_over_time({service="websocket-message-counter"} |= "ERROR" [1h])
  )
)
```

#### Log Dashboard Features

- **Log Volume**: Real-time log ingestion rates
- **Error Analysis**: Error distribution and trends
- **Session Tracking**: Follow individual WebSocket sessions


## Health Checks

### Endpoint Specifications

#### Liveness Probe: `/healthz/`

```http
GET /healthz/ HTTP/1.1

HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime": 3600.5
}
```
#### Readiness Probe: `/readyz/`

```http
GET /readyz/ HTTP/1.1

HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "ready",
  "timestamp": "2024-01-15T10:30:00Z",
  "ready": true,
  "shutting_down": false
}
```

### Grafana Dashboards

#### WebSocket Overview Dashboard

**Key Panels**:
1. Active Connections (Gauge)
2. Message Rate (Graph)
3. Error Rate (Graph)
4. Connection Duration (Histogram)


### Custom Monitoring Script

The `monitor.sh` script provides real-time monitoring:

```bash
./scripts/monitor.sh 60  # Monitor for 60 seconds

# Features:
# - Real-time log error detection
# - Metrics snapshot every 10 seconds
# - Container health checks
```

### Load Testing Metrics

```bash
# Run load test with monitoring
python tests/socket_load_test.py \
  --sockets 1000 \
  --rate 10 \
  --duration 300 \
  --host ws://localhost:8080 \
  --send-rate 0.1
```
