#!/bin/bash

# Blue-Green Deployment Promotion Script
# This script handles zero-downtime deployment by:
# 1. Building and starting the next color
# 2. Running smoke tests
# 3. Flipping traffic via nginx
# 4. Retiring the old color

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(cd "$SCRIPT_DIR/../docker" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Docker compose command detection
DOCKER_COMPOSE_CMD=""\

detect_docker_compose() {
    if [ -n "$DOCKER_COMPOSE_CMD" ]; then
        return 0
    fi
    
    # Try docker-compose first (legacy)
    if command -v docker-compose >/dev/null 2>&1; then
        if docker-compose version >/dev/null 2>&1; then
            DOCKER_COMPOSE_CMD="docker-compose"
            log_debug "Using docker-compose command"
            return 0
        fi
    fi
    
    # Fallback to docker compose (new)
    if docker compose version >/dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker compose"
        log_debug "Using docker compose command"
        return 0
    fi
    
    log_error "Neither 'docker-compose' nor 'docker compose' is available"
    return 1
}

# Wrapper function for docker compose commands
docker_compose() {
    detect_docker_compose || return 1
    $DOCKER_COMPOSE_CMD "$@"
}

# Check if a service is healthy
check_health() {
    local service=$1
    local max_attempts=${2:-30}
    local attempt=1
    
    log_info "Checking health of $service..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker_compose -f "$DOCKER_DIR/compose.yml" exec -T "$service" curl -f http://localhost:8000/healthz/ >/dev/null 2>&1; then
            log_info "$service is healthy"
            return 0
        fi
        
        log_debug "Health check attempt $attempt/$max_attempts failed for $service"
        sleep 2
        ((attempt++))
    done
    
    log_error "$service health check failed after $max_attempts attempts"
    return 1
}

# Check readiness
check_readiness() {
    local service=$1
    local max_attempts=${2:-30}
    local attempt=1
    
    log_info "Checking readiness of $service..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker_compose -f "$DOCKER_DIR/compose.yml" exec -T "$service" curl -f http://localhost:8000/readyz/ >/dev/null 2>&1; then
            log_info "$service is ready"
            return 0
        fi
        
        log_debug "Readiness check attempt $attempt/$max_attempts failed for $service"
        sleep 2
        ((attempt++))
    done
    
    log_error "$service readiness check failed after $max_attempts attempts"
    return 1
}

# Run smoke tests
run_smoke_tests() {
    local target_url=$1
    
    log_info "Running smoke tests against $target_url..."
    
    # Basic HTTP health check
    if ! curl -f "$target_url/healthz/" >/dev/null 2>&1; then
        log_error "Health endpoint failed"
        return 1
    fi
    
    # Check readiness
    if ! curl -f "$target_url/readyz/" >/dev/null 2>&1; then
        log_error "Readiness endpoint failed"
        return 1
    fi
    
    # Check metrics endpoint
    if ! curl -f "$target_url/metrics/" >/dev/null 2>&1; then
        log_error "Metrics endpoint failed"
        return 1
    fi
    
    # Basic WebSocket test using a simple Python script
    python3 - <<EOF
import asyncio
import websockets
import json
import sys

async def test_websocket():
    try:
        uri = "$target_url".replace("http://", "ws://") + "/ws/chat/"
        async with websockets.connect(uri) as websocket:
            # Send a test message
            await websocket.send("test message")
            
            # Receive response
            response = await websocket.recv()
            data = json.loads(response)
            
            # Check if response contains expected fields
            if 'count' in data and data['count'] == 1:
                print("WebSocket test passed")
                return True
            else:
                print(f"WebSocket test failed: unexpected response {data}")
                return False
    except Exception as e:
        print(f"WebSocket test failed: {e}")
        return False

# Run the test
result = asyncio.run(test_websocket())
sys.exit(0 if result else 1)
EOF
    
    if [ $? -eq 0 ]; then
        log_info "All smoke tests passed"
        return 0
    else
        log_error "Smoke tests failed"
        return 1
    fi
}

# Get currently active deployment
get_active_deployment() {
    if docker_compose -f "$DOCKER_DIR/compose.yml" ps app_blue | grep -q "Up"; then
        echo "blue"
    elif docker_compose -f "$DOCKER_DIR/compose.yml" ps app_green | grep -q "Up"; then
        echo "green"
    else
        echo "none"
    fi
}

# Switch nginx configuration
switch_nginx_config() {
    local target_color=$1
    
    log_info "Switching nginx configuration to $target_color..."
    
    # Copy the appropriate nginx configuration
    cp "$DOCKER_DIR/nginx-$target_color.conf" "$DOCKER_DIR/nginx-active.conf"
    
    # Update the nginx container configuration
    docker_compose -f "$DOCKER_DIR/compose.yml" exec nginx nginx -s reload
    
    if [ $? -eq 0 ]; then
        log_info "Nginx configuration switched to $target_color"
        return 0
    else
        log_error "Failed to switch nginx configuration"
        return 1
    fi
}

# Main deployment function
deploy() {
    local target_color=${1:-""}
    
    # Determine current and target deployments
    local current_deployment=$(get_active_deployment)
    
    if [ "$current_deployment" = "none" ]; then
        target_color="blue"
        log_info "No active deployment detected, deploying to blue"
    elif [ -z "$target_color" ]; then
        if [ "$current_deployment" = "blue" ]; then
            target_color="green"
        else
            target_color="blue"
        fi
        log_info "Auto-detected target deployment: $target_color (current: $current_deployment)"
    fi
    
    log_info "Starting blue-green deployment: $current_deployment -> $target_color"
    
    cd "$DOCKER_DIR"
    
    # Step 1: Build and start the target deployment
    log_info "Step 1: Building and starting $target_color deployment..."
    
    if [ "$target_color" = "green" ]; then
        docker_compose --profile green up -d --build app_green
    else
        docker_compose up -d --build app_blue
    fi
    
    # Step 2: Wait for the new deployment to be healthy
    log_info "Step 2: Waiting for $target_color deployment to be healthy..."
    
    if ! check_health "app_$target_color" 60; then
        log_error "New deployment failed health check"
        return 1
    fi
    
    if ! check_readiness "app_$target_color" 30; then
        log_error "New deployment failed readiness check"
        return 1
    fi
    
    # Step 3: Run smoke tests
    log_info "Step 3: Running smoke tests..."
    
    local test_port
    if [ "$target_color" = "blue" ]; then
        test_port="8001"
    else
        test_port="8002"
    fi
    
    if ! run_smoke_tests "http://localhost:$test_port"; then
        log_error "Smoke tests failed"
        return 1
    fi
    
    # Step 4: Switch traffic
    log_info "Step 4: Switching traffic to $target_color..."
    
    if ! switch_nginx_config "$target_color"; then
        log_error "Failed to switch traffic"
        return 1
    fi
    
    # Give a moment for traffic to switch
    sleep 5
    
    # Verify the switch worked
    if ! run_smoke_tests "http://localhost:8080"; then
        log_error "Traffic switch verification failed"
        # Attempt to rollback
        if [ "$current_deployment" != "none" ]; then
            log_warn "Attempting rollback to $current_deployment..."
            switch_nginx_config "$current_deployment"
        fi
        return 1
    fi
    
    # Step 5: Retire the old deployment (if there was one)
    if [ "$current_deployment" != "none" ] && [ "$current_deployment" != "$target_color" ]; then
        log_info "Step 5: Retiring old $current_deployment deployment..."
        
        # Send graceful shutdown signal
        docker_compose -f "$DOCKER_DIR/compose.yml" kill -s SIGTERM "app_$current_deployment"
        
        # Wait a bit for graceful shutdown
        sleep 10
        
        # Stop the old deployment
        docker_compose -f "$DOCKER_DIR/compose.yml" stop "app_$current_deployment"
        
        log_info "Old $current_deployment deployment retired"
    fi
    
    log_info "Blue-green deployment completed successfully!"
    log_info "Active deployment: $target_color"
    log_info "Application available at: http://localhost:8080"
    
    return 0
}

# Show usage
usage() {
    echo "Usage: $0 [blue|green]"
    echo ""
    echo "Blue-Green Deployment Script"
    echo ""
    echo "Options:"
    echo "  blue    Deploy to blue environment"
    echo "  green   Deploy to green environment"
    echo "  (none)  Auto-detect and deploy to the inactive environment"
    echo ""
    echo "Examples:"
    echo "  $0        # Auto-deploy to inactive environment"
    echo "  $0 green  # Force deploy to green environment"
}

# Main script logic
case "${1:-auto}" in
    blue)
        deploy "blue"
        ;;
    green)
        deploy "green"
        ;;
    auto)
        deploy
        ;;
    -h|--help)
        usage
        exit 0
        ;;
    *)
        log_error "Invalid argument: $1"
        usage
        exit 1
        ;;
esac
