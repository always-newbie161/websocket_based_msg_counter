# WebSocket Message Counter

A WebSocket service built with Django Channels, featuring blue-green deployments, comprehensive observability, and graceful shutdown handling.

## Demo
[🎥 Watch Demo on how to deploy, run, test and check metrics](loom.com/share/084bbf45b7fa4eb1bc63e7ad916fe73f)

## 🚀 Quick Start

**One-liner to spin up the full stack:**

```bash
make dev-up
```

**Run load tests:**

```bash
make load-test
```

**Deploy blue→green:**

```bash
make promote
```


## 📋 Features

### Core Functionality
- ✅ WebSocket endpoint `/ws/chat/` with message counting
- ✅ Server-side heartbeat broadcast every 30 seconds
- ✅ Graceful shutdown with SIGTERM handling
- ✅ Session reconnection with UUID persistence

### Production Features
- ✅ **Blue-Green Deployment** with zero downtime
- ✅ **Observability Stack** (Prometheus + Grafana + structured logs)
- ✅ **Health Checks** (liveness + readiness probes)
- ✅ **ASGI Concurrency** tuning for 5000+ connections
- ✅ **Graceful Shutdown** within 10 seconds
- ✅ **Monitoring & Alerting** with real-time metrics

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │   Django App    │    │     Redis       │
│  (Load Balancer)│◄──►│  (Blue/Green)   │◄──►│  (Channel Layer)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
    ┌─────────┐            ┌─────────────┐         ┌─────────────┐
    │ Clients │            │ Prometheus  │         │  Grafana    │
    │         │            │ (Metrics)   │         │(Dashboards) │
    └─────────┘            └─────────────┘         └─────────────┘
                                   │                       │
                            ┌─────────────┐         ┌─────────────┐
                            │    Loki     │◄────────│    Logs     │
                            │(Log Aggr.)  │         │ (Structured)│
                            └─────────────┘         └─────────────┘
```

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **WebSocket Server** | Django Channels 4.x | ASGI WebSocket handling |
| **ASGI Server** | Uvicorn with uvloop | High-performance async server |
| **Message Broker** | Redis 7 | Channel layer backend |
| **Reverse Proxy** | Nginx Alpine | Load balancing & WebSocket proxy |
| **Metrics** | Prometheus + Grafana | Observability & monitoring |
| **Containerization** | Docker + Compose | Deployment & orchestration |
| **Load Testing** | Socket-based | Direct WebSocket testing |

## 📁 Project Structure

```
.
├── docker/
│   ├── Dockerfile              # Multi-stage production image
│   ├── compose.yml             # Full stack with blue/green
│   ├── nginx.conf              # WebSocket-optimized config
│   └── grafana/                # Pre-built dashboards
├── app/
│   ├── manage.py
│   ├── config/                 # Django settings & ASGI
│   ├── chat/                   # WebSocket consumers
│   └── core/                   # Health checks & metrics
├── scripts/
│   ├── promote.sh              # Blue-green deployment script
│   └── monitor.sh              # Real-time monitoring
├── tests/
│   ├── test_websocket.py       # Unit & integration tests
│   └── socket_load_test.py     # WebSocket load testing
├── docs/
│   ├── DESIGN.md               # Architecture & concurrency details
│   └── OBSERVABILITY.md        # Monitoring & alerting guide
└── README.md                   # This file
```

## 🔧 Configuration

### ASGI Concurrency Settings

The application is tuned for optimal WebSocket performance:

```yaml
# In docker-compose.yml
ASGI_WORKERS: 4      
```

**Rationale:**
- **ASGI Workers**: No.of ASGI workers are tuned through load testing and monitoring conneciton time and response time, As this is I/O heavy websocket server, we are going with 4 workers which gave us 5.6ms avg conneciton time and 0.1ms avg msg response time.

### WebSocket Configuration

```python
# Key settings in config/settings.py
WEBSOCKET_HEARTBEAT_INTERVAL = 30    # Heartbeat every 30 seconds
GRACEFUL_SHUTDOWN_TIMEOUT = 10       # Max shutdown time
```

## 🚀 Getting Started

### Prerequisites

- **Docker & Docker Compose** (required)
- **Python 3.11+** (for local development)
- **Make** (optional, for convenience commands)

### 1. Clone and Setup

```bash
git clone <repository>
cd websocket_based_msg_counter
make setup  # Install dependencies and verify requirements
```

### 2. Start Development Environment

```bash
make dev-up
```

This starts:
- **Application**: http://localhost (via nginx)
- **Blue deployment**: http://localhost:8001
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### 3. Test WebSocket Connection

Open http://localhost in your browser for an interactive WebSocket test interface, or use curl:

```bash
# Health checks
curl http://localhost/healthz/
curl http://localhost/readyz/

# Metrics
curl http://localhost:8080/metrics/ 
```

### 4. Run Tests

```bash
make test           # Unit & integration tests
make smoke-test     # Basic functionality
make load-test      # 100 concurrent users for 60s
```

## 🔄 Blue-Green Deployment

### Automatic Promotion

```bash
make promote        # Auto-detects current color and switches
```

### Manual Promotion

```bash
make promote-blue   # Force deploy to blue
make promote-green  # Force deploy to green
```

### Deployment Process

1. **Build & Start** new color deployment
2. **Health Checks** (liveness + readiness)
3. **Smoke Tests** (HTTP + WebSocket validation)
4. **Traffic Switch** via nginx upstream
5. **Graceful Shutdown** of old deployment

### Zero-Downtime Features

- ✅ Nginx upstream switching (no dropped connections)
- ✅ Health check validation before traffic switch
- ✅ Automatic rollback on failure
- ✅ Graceful WebSocket connection closure

## 📊 Monitoring & Observability

### Key Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `websocket_active_connections` | Current active connections | <10 (warning) |
| `websocket_messages_total` | Total messages processed | - |
| `websocket_errors_total` | Errors by type | >1% rate (critical) |
| `websocket_connection_duration_seconds` | Connection duration histogram | >300s (long connections) |

### Real-Time Monitoring

```bash
make monitor        # 60-second monitoring session
make monitor-30     # 30-second session
```

**Features:**
- Live error log detection
- Metrics snapshots every 10s
- System resource monitoring
- WebSocket connection tracking

### Dashboards

- **Grafana**: Pre-configured WebSocket dashboard at http://localhost:3000
  - Metrics Dashboard: WebSocket connections, message rates, error rates
  - Logs Dashboard: Structured log exploration and filtering
- **Prometheus**: Raw metrics and alerts at http://localhost:9090
- **Loki**: Log aggregation service at http://localhost:3100

### Structured Logging with Loki

All logs are JSON-formatted and automatically shipped to Loki:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "client-session-uuid",
  "event": "websocket_message_processed",
  "message_count": 5,
  "service": "websocket-message-counter"
}
```

**Log Queries in Grafana:**
```logql
# All application logs
{service="websocket-message-counter"}

# Error logs only
{service="websocket-message-counter"} |= "ERROR"

# WebSocket events
{service="websocket-message-counter"} |= "WebSocket"
```

**Test Loki Integration:**
```bash
./scripts/test_loki.sh
```

## 🧪 Testing Strategy

### Unit Tests

```bash
make test           # Run all tests
./scripts/test.sh   # Test script with proper environment setup
```

### Integration Tests

```bash
# Start the service first
make dev-up

# Run integration tests (requires running service)
make test-integration
```

### Load Testing

```bash
# Start the service
make dev-up

# Using socket_load_test.py directly
python tests/socket_load_test.py --sockets 100 --rate 10 --duration 60 --host ws://localhost:8001

# Using make commands
make load-test      # 100 concurrent connections, 60s duration
make load-test-5k   # 5000 concurrent connections
make load-test-10k  # 10000 concurrent connections
```

**Load Test Features:**
- WebSocket connection testing with session management
- Message counting validation
- Concurrent user simulation
- Response time and error rate monitoring
- HTML reports generated

### Performance Targets

- ✅ **5,000+ concurrent connections** per instance
- ✅ **<10ms message processing latency**
- ✅ **<3 second startup time**
- ✅ **<10 second graceful shutdown**



## 📈 Performance Optimization

### Connection Handling

- **Event loop optimization** with uvloop
- **Connection pooling** for Redis
- **Efficient JSON parsing** with built-in libraries
- **Memory-efficient session storage**

## 🔍 Troubleshooting

### Common Commands

```bash
# View logs
make logs

# Check current metrics
make metrics

# Resource usage
docker stats

# Container health
docker-compose ps
```

### Debug WebSocket Issues

```bash
# Test WebSocket directly
wscat -c ws://localhost/ws/chat/

# Monitor connection count
watch "curl -s http://localhost:8080/metrics/  | grep websocket_active_connections"

# Check nginx upstream
docker exec nginx_container nginx -T
```

## 📚 Documentation

- **[DESIGN.md](docs/DESIGN.md)**: Architecture, concurrency model, and design decisions
- **[OBSERVABILITY.md](docs/OBSERVABILITY.md)**: Monitoring, alerting, and troubleshooting guide


