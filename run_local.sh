#!/bin/bash

# Local Development Server Script
# Runs the Django Channels app locally with Docker-like environment variables

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting WebSocket server locally..."

# Set environment variables (same as Docker compose)
export DJANGO_SETTINGS_MODULE=config.settings
export DEBUG=true
export REDIS_HOST=${REDIS_HOST:-localhost}
export SECRET_KEY=local-dev-secret-key
export ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
export LOG_LEVEL=DEBUG
export ASGI_WORKERS=4
export THREAD_POOL_SIZE=8
export WEBSOCKET_HEARTBEAT_INTERVAL=30
export GRACEFUL_SHUTDOWN_TIMEOUT=10
export LOKI_URL=http://localhost:3100
export LOKI_ENABLED=false
export WEB_CONCURRENCY=35
export WORKER_CONNECTIONS=1000
export HEALTH_CHECK_STARTUP_DELAY=0

# Change to app directory
cd "$SCRIPT_DIR/app"

echo "Environment variables set:"
echo "DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"
echo "DEBUG: $DEBUG"
echo "REDIS_HOST: $REDIS_HOST"
echo "WEB_CONCURRENCY: $WEB_CONCURRENCY"
echo "WORKER_CONNECTIONS: $WORKER_CONNECTIONS"
echo ""

# Check if Redis is running
echo "Checking Redis connection..."
if ! python -c "import redis; r = redis.Redis(host='$REDIS_HOST', port=6379); r.ping()" 2>/dev/null; then
    echo "Redis is not running on $REDIS_HOST:6379"
    echo ""
    echo "Please start Redis first:"
    echo "  Option 1: Install and run Redis locally"
    echo "    brew install redis  # macOS"
    echo "    redis-server"
    echo ""
    echo "  Option 2: Run Redis in Docker"
    echo "    docker run -d -p 6379:6379 --name redis redis:7-alpine"
    echo ""
    echo "  Option 3: Use existing Redis container"
    echo "    docker start redis"
    echo ""
    read -p "Press Enter to continue anyway or Ctrl+C to exit..."
    echo ""
else
    echo "Redis is running and accessible"
    echo ""
fi

# Run the server
echo "Starting gunicorn server..."
echo "Server will be available at: http://localhost:8000"
echo "WebSocket endpoint: ws://localhost:8000/ws/chat/"
echo "Health check: http://localhost:8000/healthz/"
echo "Readiness check: http://localhost:8000/readyz/"
echo "Press Ctrl+C to stop"
echo ""

exec gunicorn config.asgi:application \
    -k uvicorn.workers.UvicornWorker \
    --workers $WEB_CONCURRENCY \
    --worker-connections $WORKER_CONNECTIONS \
    --bind 0.0.0.0:8000 \
    --timeout 0 \
    --keep-alive 2 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level info



Connection 16503 closed (sent 0 messages)
[ERROR] Connection 16504: Failed to connect - Multiple exceptions: [Errno 61] Connect call failed ('::1', 8000, 0, 0), [Errno 49] Can't assign requested address
Connection 16504 closed (sent 0 messages)
[ERROR] Connection 16506: Failed to connect - Multiple exceptions: [Errno 61] Connect call failed ('::1', 8000, 0, 0), [Errno 49] Can't assign requested address
C

on 16547 closed (sent 0 messages)
[ERROR] Connection 16549: Failed to connect - Multiple exceptions: [Errno 61] Connect call failed ('::1', 8000, 0, 0), [Errno 49] Can't assign requested address
Connection 16549 closed (sent 0 messages)
[ERROR] Connection 16550: Failed to connect - Multiple exceptions: [Errno 61] Connect call failed ('::1', 8000, 0, 0), [Errno 49] Can't assign requested address
Connection 16550 closed (sent 0 messages)
[ERROR] Connection 16551: Failed to connect - Multiple exceptions: [Errno 61] Connect call failed ('::1', 8000, 0, 0), [Errno 49] Can't assign requested address
Connection 16551 closed (sent 0 messages)
[ERROR] Connection 16552: Failed to connect - Multiple exceptions: [Errno 61] Connect call failed ('::1', 8000, 0, 0), [Errno 49] Can't assign requested addr