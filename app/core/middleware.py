"""
Middleware for request tracking and structured logging.
"""
import uuid
import time
import structlog
from django.utils.deprecation import MiddlewareMixin

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(MiddlewareMixin):
    """
    Middleware to add a unique request ID to each request.
    """
    
    def process_request(self, request):
        request.request_id = str(uuid.uuid4())
        return None


class StructuredLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log requests with structured data.
    """
    
    def process_request(self, request):
        request.start_time = time.time()
        
        logger.info(
            "Request started",
            request_id=getattr(request, 'request_id', 'unknown'),
            method=request.method,
            path=request.path,
            remote_addr=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        return None
    
    def process_response(self, request, response):
        duration = time.time() - getattr(request, 'start_time', time.time())
        
        logger.info(
            "Request completed",
            request_id=getattr(request, 'request_id', 'unknown'),
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )
        return response
    
    def process_exception(self, request, exception):
        duration = time.time() - getattr(request, 'start_time', time.time())
        
        logger.error(
            "Request error",
            request_id=getattr(request, 'request_id', 'unknown'),
            method=request.method,
            path=request.path,
            exception=str(exception),
            exception_type=type(exception).__name__,
            duration_ms=round(duration * 1000, 2),
        )
        return None
    
    @staticmethod
    def get_client_ip(request):
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
