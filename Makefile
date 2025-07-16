# WebSocket Message Counter - Production Ready

.PHONY: help dev-up dev-down build test load-test promote monitor clean

# Default target
help:
	@echo "WebSocket Message Counter - Production Commands"
	@echo ""
	@echo "Quick Start:"
	@echo "  make dev-up        Start the full development stack"
	@echo "  make test          Run all tests"
	@echo "  make load-test     Run load tests"
	@echo "  make promote       Run blue-green deployment"
	@echo ""
	@echo ""
	@echo "Testing Commands:"
	@echo "  make test          Run unit and integration tests"
	@echo "  make test-unit     Run unit tests only"
	@echo "  make test-integration  Run integration tests only"
	@echo "  make load-test     Run standard load tests (100 users)"
	@echo "  make load-test-quick   Quick load test (100 users, 1 min)"
	@echo "  make load-test-5k      High concurrency test (5000 users, 5 min)"
	@echo "  make load-test-10k     Stress test (10000 users, 10 min)"
	@echo "  make test-concurrency-5k   5K concurrency test with monitoring"
	@echo "  make test-concurrency-10k  10K concurrency test with monitoring"
	@echo "  make smoke-test    Run basic smoke tests"
	@echo ""
	@echo "Deployment Commands:"
	@echo "  make promote       Promote to next color (auto-detect)"
	@echo "  make promote-blue  Force promote to blue"
	@echo "  make promote-green Force promote to green"
	@echo ""
	@echo "Monitoring Commands:"
	@echo "  make monitor       Run monitoring script (60s)"
	@echo "  make monitor-30    Run monitoring script (30s)"
	@echo "  make logs          Show all container logs"
	@echo "  make metrics       Show current metrics"
	@echo ""
	@echo "Cleanup Commands:"
	@echo "  make clean         Clean up containers and volumes"
	@echo "  make clean-all     Clean everything including images"


# Development environment
dev-up:
	@echo "Starting WebSocket Message Counter development environment..."
	cd docker && docker-compose up -d redis
	cd docker && docker-compose up -d --build app_blue
	cd docker && docker-compose up -d nginx prometheus grafana
	@echo "Development environment started!"
	@echo ""
	@echo "Services available:"
	@echo "   Application:    http://localhost:8080"
	@echo "   Blue App:       http://localhost:8001"
	@echo "   Metrics:        http://localhost:8080/metrics/"
	@echo "   Prometheus:     http://localhost:9090"
	@echo "   Grafana:        http://localhost:3000 (admin/admin)"
	@echo ""
	@echo "Health checks:"
	@echo "   Health:         curl http://localhost:8080/healthz/"
	@echo "   Readiness:      curl http://localhost:8080/readyz/"
	@echo ""
	@sleep 3
	@echo "Waiting for services to be ready..."
	@timeout 60 sh -c 'until curl -sf http://localhost:8080/healthz/ >/dev/null 2>&1; do sleep 2; done' || echo "Health check timeout"
	@timeout 30 sh -c 'until curl -sf http://localhost:8080/readyz/ >/dev/null 2>&1; do sleep 2; done' || echo "Readiness check timeout"
	@echo "Services are ready!"

dev-down:
	@echo "Stopping development environment..."
	cd docker && docker-compose down
	@echo "Resetting nginx configuration to blue..."
	cp docker/nginx-blue.conf docker/nginx-active.conf
	@echo "Development environment stopped and reset to blue"

build:
	@echo "Building Docker images..."
	cd docker && docker-compose build
	@echo "Build completed"

# Testing commands
test: test-unit test-integration

test-unit:
	@echo "Running unit tests..."
	cd app && python -m pytest ../tests/test_websocket.py -v --tb=short -p no:warnings
	@echo "Unit tests completed"

test-integration:
	@echo "Running integration tests..."
	@timeout 60 sh -c 'until curl -sf http://localhost:8080/healthz/ >/dev/null 2>&1; do sleep 2; echo "Waiting for app..."; done'
	cd app && python -m pytest ../tests/test_websocket.py::test_websocket_integration -v -p no:warnings
	@echo "Integration tests completed"

smoke-test:
	@echo "Running smoke tests..."
	@curl -sf http://localhost:8080/healthz/ && echo "Health check passed" || echo "Health check failed"
	@curl -sf http://localhost:8080/readyz/ && echo "Readiness check passed" || echo "Readiness check failed"
	@curl -sf http://localhost:8080/metrics/ >/dev/null && echo "Metrics endpoint accessible" || echo "Metrics endpoint failed"
	@echo "Smoke tests completed"


load-test:
	@echo "Running load tests..."
	@timeout 60 sh -c 'until curl -sf http://localhost:8080/healthz/ >/dev/null 2>&1; do sleep 2; echo "Waiting for app..."; done'
	python tests/socket_load_test.py \
		--sockets 100 \
		--rate 10 \
		--duration 60 \
		--host ws://localhost:8080 \
		--send-rate 0.5
	@echo "Load test completed. Check console output for results."

# High concurrency testing
load-test-5k:
	@echo "Running 5K concurrent WebSocket connections test..."
	@timeout 60 sh -c 'until curl -sf http://localhost:8080/healthz/ >/dev/null 2>&1; do sleep 2; echo "Waiting for app..."; done'
	@mkdir -p reports
	python tests/socket_load_test.py \
		--sockets 5000 \
		--rate 100 \
		--duration 300 \
		--host ws://localhost:8080 \
		--send-rate 0.1
	@echo "5K load test completed. Check console output for results."

load-test-10k:
	@echo "Running 10K concurrent WebSocket connections test..."
	@timeout 60 sh -c 'until curl -sf http://localhost:8080/healthz/ >/dev/null 2>&1; do sleep 2; echo "Waiting for app..."; done'
	@mkdir -p reports
	python tests/socket_load_test.py \
		--sockets 10000 \
		--rate 200 \
		--duration 600 \
		--host ws://localhost:8080 \
		--send-rate 0.05
	@echo " 10K load test completed. Check console output for results."


load-test-20k:
	@echo "Running 20K concurrent WebSocket connections test..."
	@timeout 60 sh -c 'until curl -sf http://localhost:8080/healthz/ >/dev/null 2>&1; do sleep 2; echo "Waiting for app..."; done'
	@mkdir -p reports
	python tests/socket_load_test.py \
		--sockets 20000 \
		--rate 400 \
		--duration 1200 \
		--host ws://localhost:8080 \
		--send-rate 0.05
	@echo " 20K load test completed. Check console output for results."

load-test-quick:
	@echo " Running quick load test (100 users, 1 minute)..."
	@timeout 60 sh -c 'until curl -sf http://localhost:8080/healthz/ >/dev/null 2>&1; do sleep 2; echo "Waiting for app..."; done'
	@mkdir -p reports
	python tests/socket_load_test.py \
		--sockets 100 \
		--rate 20 \
		--duration 60 \
		--host ws://localhost:8080 \
		--send-rate 0.2
	@echo " Quick load test completed. Check console output for results."


# Deployment commands
promote:
	@echo " Running blue-green deployment (auto-detect)..."
	chmod +x scripts/promote.sh
	./scripts/promote.sh
	@echo " Deployment completed"

promote-blue:
	@echo " Promoting to blue deployment..."
	chmod +x scripts/promote.sh
	./scripts/promote.sh blue
	@echo " Blue deployment completed"

promote-green:
	@echo " Promoting to green deployment..."
	chmod +x scripts/promote.sh
	./scripts/promote.sh green
	@echo " Green deployment completed"

# Monitoring commands
monitor:
	@echo " Starting 60-second monitoring session..."
	chmod +x scripts/monitor.sh
	./scripts/monitor.sh 60

monitor-30:
	@echo " Starting 30-second monitoring session..."
	chmod +x scripts/monitor.sh
	./scripts/monitor.sh 30

logs:
	@echo " Showing container logs..."
	cd docker && docker-compose logs --tail=50 -f

metrics:
	@echo " Current metrics:"
	@curl -s http://localhost:8080/metrics/ | grep websocket_ | head -10

# Cleanup commands
clean:
	@echo " Cleaning up containers and volumes..."
	cd docker && docker-compose down -v
	docker system prune -f
	@echo " Cleanup completed"

clean-all: clean
	@echo "  Removing all images..."
	docker-compose -f docker/compose.yml down --rmi all
	docker system prune -af
	@echo " Full cleanup completed"

# Setup commands for first-time users
setup:
	@echo "  Setting up WebSocket Message Counter..."
	@echo "Checking dependencies..."
	@command -v docker >/dev/null 2>&1 || (echo " Docker is required" && exit 1)
	@command -v docker-compose >/dev/null 2>&1 || (echo " Docker Compose is required" && exit 1)
	@command -v python3 >/dev/null 2>&1 || (echo " Python 3 is required" && exit 1)
	@echo " Dependencies check passed"
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt
	@echo " Setup completed"
	@echo ""
	@echo " Ready to go! Run 'make dev-up' to start the development environment"

# Development utilities
install-deps:
	@echo " Installing Python dependencies..."
	pip install -r requirements.txt
	pip install black flake8 isort pytest-cov
	@echo " Dependencies installed"

format:
	@echo " Formatting code..."
	black app/
	isort app/
	@echo " Code formatted"

lint:
	@echo " Linting code..."
	flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
	black --check app/
	isort --check-only app/
	@echo " Linting completed"

# Performance testing
stress-test:
	@echo " Running stress test..."
	chmod +x scripts/monitor.sh
	./scripts/monitor.sh 30 stress
	@echo " Stress test completed"

# Documentation
docs:
	@echo " Documentation available:"
	@echo "   Design:         docs/DESIGN.md"
	@echo "   Observability:  docs/OBSERVABILITY.md"
	@echo "   README:         README.md"

# Create reports directory
reports:
	@mkdir -p reports

# All-in-one test suite
test-all: build dev-up test smoke-test load-test monitor-30
	@echo " Full test suite completed!"

# Combined load testing with monitoring
test-concurrency-5k:
	@echo " Testing 5K concurrent connections with monitoring..."
	@chmod +x scripts/monitor_load_test.sh
	@echo "Starting monitoring in background..."
	@scripts/monitor_load_test.sh 300 5k &
	@MONITOR_PID=$$!
	@sleep 5
	@echo "Starting load test..."
	@$(MAKE) load-test-5k
	@echo "Waiting for monitoring to complete..."
	@wait $$MONITOR_PID 2>/dev/null || true
	@echo " 5K concurrency test completed with monitoring"

test-concurrency-10k:
	@echo " Testing 10K concurrent connections with monitoring..."
	@chmod +x scripts/monitor_load_test.sh
	@echo "Starting monitoring in background..."
	@scripts/monitor_load_test.sh 600 10k &
	@MONITOR_PID=$$!
	@sleep 5
	@echo "Starting load test..."
	@$(MAKE) load-test-10k
	@echo "Waiting for monitoring to complete..."
	@wait $$MONITOR_PID 2>/dev/null || true
	@echo " 10K concurrency test completed with monitoring"
