"""
WebSocket heartbeat service for broadcasting periodic messages.
"""
import threading
import time
from datetime import datetime, timezone
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import structlog

logger = structlog.get_logger(__name__)

class SimpleHeartbeatService:
    """Heartbeat service that sends periodic messages to all WebSocket connections."""
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the heartbeat service in a separate thread."""
        if self.running:
            logger.info("Heartbeat service already running in this worker")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_heartbeat_loop, daemon=True)
        self.thread.start()
        logger.info(
            "Heartbeat service started",
            interval=settings.WEBSOCKET_HEARTBEAT_INTERVAL
        )
    
    def stop(self):
        """Stop the heartbeat service."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Heartbeat service stopped")
    
    def _run_heartbeat_loop(self):
        """Run the heartbeat loop."""
        while self.running:
            try:
                # Send heartbeat message
                heartbeat_data = {
                    'type': 'heartbeat',
                    'ts': datetime.now(timezone.utc).isoformat()
                }
                
                # Use async_to_sync to send to all connections if channel_layer exists
                if self.channel_layer:
                    async_to_sync(self.channel_layer.group_send)(
                        'chat_all',
                        {
                            'type': 'heartbeat_message',
                            'message': heartbeat_data
                        }
                    )
                    
                    logger.debug(
                        "Heartbeat sent", 
                        timestamp=heartbeat_data['ts']
                    )
                else:
                    logger.error("Channel layer is None, cannot send heartbeat")
                
                # Wait for next heartbeat
                time.sleep(settings.WEBSOCKET_HEARTBEAT_INTERVAL)
                
            except Exception as e:
                logger.error(
                    "Heartbeat error", 
                    error=str(e), 
                    exception_type=type(e).__name__
                )
                # Continue running even if there's an error
                time.sleep(1)

# Global heartbeat service instance
_heartbeat_service = None

def start_heartbeat_service():
    """Start the global heartbeat service."""
    global _heartbeat_service
    if _heartbeat_service is None:
        _heartbeat_service = SimpleHeartbeatService()
    _heartbeat_service.start()

def stop_heartbeat_service():
    """Stop the global heartbeat service."""
    global _heartbeat_service
    if _heartbeat_service:
        _heartbeat_service.stop()
        _heartbeat_service = None
