"""
Signal handlers for graceful WebSocket shutdown.
"""
import signal
import asyncio
import structlog
from channels.layers import get_channel_layer

logger = structlog.get_logger(__name__)

async def close_all_connections():
    """Close all WebSocket connections gracefully during shutdown."""
    channel_layer = get_channel_layer()
    
    if channel_layer is not None:
        try:
            # Send shutdown message to all connections
            await channel_layer.group_send(
                'chat_all',
                {
                    'type': 'shutdown_message'
                }
            )
            logger.info("Shutdown message sent to all WebSocket connections")
        except Exception as e:
            logger.error("Error sending shutdown message", error=str(e))
    else:
        logger.error("Cannot send shutdown message: channel layer not available")

def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        
        # Try to get the current event loop, or create a new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, schedule the shutdown
                asyncio.create_task(close_all_connections())
            else:
                loop.run_until_complete(close_all_connections())
        except RuntimeError:
            # No event loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(close_all_connections())
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
            finally:
                loop.close()
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    logger.info("Signal handlers registered for graceful shutdown")
