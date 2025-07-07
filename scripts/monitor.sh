#!/bin/bash

# Simple Monitoring Script
# 1. Tails container logs for ERROR messages
# 2. Prints top-5 metrics from /metrics every 10 seconds

set -euo pipefail

DOCKER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../docker" && pwd)"

# Function to get active deployment from nginx config
get_active_deployment() {
    if grep -q "app_blue:8000" "$DOCKER_DIR/nginx-active.conf" 2>/dev/null; then
        echo "app_blue"
    elif grep -q "app_green:8000" "$DOCKER_DIR/nginx-active.conf" 2>/dev/null; then
        echo "app_green"
    else
        echo "app_blue"  # Default fallback
    fi
}

# Start error monitoring for active container only
echo "Starting error monitoring..."
ACTIVE_CONTAINER=$(get_active_deployment)
echo "Monitoring active container: $ACTIVE_CONTAINER"

docker-compose -f "$DOCKER_DIR/compose.yml" logs -f "$ACTIVE_CONTAINER" 2>&1 | \
    grep --line-buffered -i "error\|exception\|traceback\|critical" | \
    while IFS= read -r line; do
        echo "[$(date '+%H:%M:%S')] ERROR: $line"
    done &

LOG_PID=$!

# Cleanup on exit
trap 'echo "Stopping..."; kill $LOG_PID 2>/dev/null || true; exit 0' SIGINT SIGTERM

# Print metrics every 10 seconds
echo "Starting metrics monitoring (every 10s)..."
while true; do
    sleep 10
    echo ""
    echo "[$(date '+%H:%M:%S')] Top-5 Metrics:"
    curl -s http://localhost:8080/metrics/ 2>/dev/null | \
        grep -E '^[a-zA-Z_]+ [0-9.]+$' | \
        sort -k2 -nr | head -5 | \
        sed 's/^/  /' || echo "  Failed to fetch metrics"
done
