# Design Document: WebSocket Message Counter

## Architecture Overview

This project implements a production-ready WebSocket message counter service using Django Channels with a focus on scalability, observability, and zero-downtime deployments.

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │   Django App    │    │     Redis       │
│  (Load Balancer)│◄──►│  (Blue/Green)   │◄──►│  (Channel Layer)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
    ┌─────────┐            ┌─────────────┐         ┌─────────────┐
    │ Clients │            │ Prometheus  │         │  Grafana    │
    │         │            │ (Metrics)   │         │(Dashboards) │
    └─────────┘            └─────────────┘         └─────────────┘
```

## ASGI Concurrency Model

### Worker Configuration

No.of ASGI workers are tuned through load testing and monitoring conneciton time and response time, As this is I/O heavy websocket server, we are going with 4 workers which gave us 5.6ms avg conneciton time and 0.1ms avg msg response time.

```yaml
# Concurrency Settings (in compose.yml)
ASGI_WORKERS: 4       
```

## Session Management


### In-Memory Session Storage
We are using in-memory session storage to restore state for users connecting with `session_id` in their query parameters
```python
# Format: {session_id: {'count': int, 'start_time': float}}
session_storage: Dict[str, Dict] = {}
```


### Reconnection Logic

1. Client includes `?session_id=uuid` in WebSocket URL
2. Server checks if session exists in memory
3. If found, resumes message count
4. If not found, creates new session

## Graceful Shutdown

### Signal Handling

```python
# SIGTERM handling for graceful shutdown
def handle_sigterm():
    1. Mark application as shutting down (readiness probe fails)
    2. Stop accepting new connections
    3. Send close code 1001 to existing connections
    4. Serve inflight messages
    5. Wait up to 10 seconds for connections to close
    6. Force shutdown if timeout exceeded
```

### WebSocket Close Codes

- `1000`: Normal closure
- `1001`: Going away (server shutdown)
- `1011`: Internal server error

## Blue-Green Deployment

### Deployment Flow

```bash
# Promotion script workflow
1. Build new deployment (blue/green)
2. Start new containers
3. Health checks (liveness + readiness)
4. Smoke tests (HTTP + WebSocket)
5. Switch nginx upstream
6. Verify traffic switch
7. Graceful shutdown of old deployment
```

### Zero-Downtime Strategy

1. **Nginx upstream switching**: No connection drops
2. **Health checks**: Ensure new deployment is ready
3. **Graceful shutdown**: Allow existing connections to complete
4. **Rollback capability**: Automatic rollback on failure



### Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `websocket_active_connections` | Gauge | Current active WebSocket connections |
| `websocket_messages_total` | Counter | Total messages processed |
| `websocket_errors_total` | Counter | Total errors by type |
| `websocket_connection_duration_seconds` | Histogram | Connection duration distribution |
| `websocket_shutdown_time_seconds` | Gauge | Graceful shutdown duration |

### Health Checks

1. **Liveness (`/healthz/`)**: Process is alive
2. **Readiness (`/readyz/`)**: Ready to accept traffic
   - Returns 503 during startup delay and shutdown

## Performance Targets

### Concurrency Targets

- **10,000+ concurrent WebSocket connections** per instance
- **Sub-10ms message processing latency**
- **<3 second startup time**
- **<10 second graceful shutdown**

## Security Considerations

### WebSocket Security

1. **Origin validation**: Check `Origin` header
2. **Authentication**: Use Django session auth
3. **Rate limiting**: Implement message rate limits
4. **Input validation**: Sanitize all WebSocket messages

## Error Handling

### Error Categories

1. **Connection Errors**: Network issues, invalid handshake
2. **Message Processing Errors**: Invalid JSON, processing failures
3. **System Errors**: Redis unavailable, memory issues


## Development Workflow

### Local Development

```bash
# Quick setup
make dev-up          # Start development environment
make test            # Run all tests
make load-test       # Run load tests
make promote blue    # Test blue-green deployment
```

### Testing Strategy

1. **Unit Tests**: Consumer logic, message handling
2. **Integration Tests**: Full WebSocket flow
3. **Load Tests**: Concurrent connection testing
4. **Smoke Tests**: Basic functionality validation
