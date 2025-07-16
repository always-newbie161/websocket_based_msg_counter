"""
Core application views for health checks and metrics.
"""
import time
import uuid
import json
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
import structlog
from datetime import timezone

logger = structlog.get_logger(__name__)

# Prometheus metrics
message_counter = Counter('websocket_messages_total', 'Total number of WebSocket messages processed')
active_connections = Gauge('websocket_active_connections', 'Number of active WebSocket connections')
error_counter = Counter('websocket_errors_total', 'Total number of WebSocket errors', ['error_type'])
connection_duration = Histogram('websocket_connection_duration_seconds', 'WebSocket connection duration')
shutdown_time = Gauge('websocket_shutdown_time_seconds', 'Time taken for graceful shutdown')

# Application state
app_state = {
    'startup_time': time.time(),
    'ready': False,
    'shutting_down': False,
}

def startup():
    """Mark the application as ready after startup delay."""
    time.sleep(settings.HEALTH_CHECK_STARTUP_DELAY)
    app_state['ready'] = True
    logger.info("Application ready", startup_time=app_state['startup_time'], ready=app_state['ready'], shutting_down=app_state['shutting_down'])

def shutdown():
    """Mark the application as shutting down."""
    app_state['shutting_down'] = True
    logger.info("Application shutting down")

@require_http_methods(["GET"])
def health_check(request):
    """
    Liveness probe endpoint.
    Returns 200 if the application is alive.
    """
    request_id = getattr(request, 'request_id', str(uuid.uuid4()))
    
    logger.info(
        "Health check requested",
        request_id=request_id,
        endpoint="healthz"
    )
    
    return JsonResponse({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'uptime': time.time() - app_state['startup_time']
    })

@require_http_methods(["GET"])
def readiness_check(request):
    """
    Readiness probe endpoint.
    Returns 200 if the application is ready to serve traffic.
    """
    request_id = getattr(request, 'request_id', str(uuid.uuid4()))
    
    is_ready = app_state['ready'] and not app_state['shutting_down']
    status_code = 200 if is_ready else 503
    
    logger.info(
        "Readiness check requested",
        request_id=request_id,
        endpoint="readyz",
        ready=is_ready,
        shutting_down=app_state['shutting_down'],
        state_ready=app_state['ready'],
    )
    
    response_data = {
        'status': 'ready' if is_ready else 'not_ready',
        'timestamp': datetime.utcnow().isoformat(),
        'ready': is_ready,
        'shutting_down': app_state['shutting_down']
    }
    
    return JsonResponse(response_data, status=status_code)

@csrf_exempt
@require_http_methods(["GET"])
def metrics(request):
    """
    Prometheus metrics endpoint.
    Returns metrics in Prometheus format.
    """
    request_id = getattr(request, 'request_id', str(uuid.uuid4()))
    
    logger.debug(
        "Metrics requested",
        request_id=request_id,
        endpoint="metrics",
        method=request.method,
        path=request.path
    )
    
    try:
        metrics_data = generate_latest()
        logger.debug(
            "Metrics generated successfully",
            request_id=request_id,
            data_length=len(metrics_data)
        )
        
        return HttpResponse(
            metrics_data,
            content_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(
            "Error generating metrics",
            request_id=request_id,
            error=str(e),
            exception_type=type(e).__name__
        )
        return HttpResponse(
            "Error generating metrics",
            status=500,
            content_type="text/plain"
        )
