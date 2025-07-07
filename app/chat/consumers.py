"""
WebSocket consumers for the chat application.
"""
import asyncio
import json
import uuid
import time
from typing import Dict, Optional
from urllib.parse import parse_qs, unquote
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.conf import settings
import structlog

# Import metrics from core
from core.views import (
    message_counter, active_connections, error_counter, 
    connection_duration
)

logger = structlog.get_logger(__name__)

# In-memory storage for session data
# Format: {session_id: {'count': int, 'start_time': float}}
session_storage: Dict[str, Dict] = {}

class ChatConsumer(AsyncWebsocketConsumer):
    """
    Websocket consumer for message counter
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id: Optional[str] = None
        self.message_count: int = 0
        self.start_time: float = 0
        self.group_name = 'chat_all'
        self.is_shutting_down = False
        self.pending_count = 0  # tracker for inflight messages
    
    async def connect(self):
        """Handle WebSocket connection."""
        try:
            # Get session ID from query parameters (for reconnection)
            query_string = self.scope.get('query_string', b'').decode('utf-8')
            session_id = None
            
            if query_string:
                # Parse query parameters properly with URL decoding
                parsed_params = parse_qs(query_string)
                if 'session_id' in parsed_params and parsed_params['session_id']:
                    session_id = unquote(parsed_params['session_id'][0])
                    logger.info(
                        "Session ID from query params", 
                        session_id=session_id,
                        query_string=query_string
                    )
            
            # Use provided session_id or create new one
            if session_id:
                self.session_id = session_id
                if session_id in session_storage:
                    # Reconnecting to existing session
                    self.message_count = session_storage[session_id]['count']
                    logger.info(
                        "WebSocket reconnection",
                        session_id=self.session_id,
                        existing_count=self.message_count,
                        channel_name=self.channel_name
                    )
                else:
                    # New session with provided session_id
                    self.message_count = 0
                    logger.info(
                        "WebSocket new connection with provided session_id",
                        session_id=self.session_id,
                        channel_name=self.channel_name
                    )
            else:
                # No session_id provided, generate a new one
                self.session_id = str(uuid.uuid4())
                self.message_count = 0
                logger.info(
                    "WebSocket new connection with generated session_id",
                    session_id=self.session_id,
                    channel_name=self.channel_name
                )
            
            self.start_time = time.time()
            
            # Store session data
            if self.session_id is not None:
                session_storage[self.session_id] = {
                    'count': self.message_count,
                    'start_time': self.start_time
                }
            else:
                logger.error("Cannot store session: session_id is None")
            
            # Join the global group for heartbeat messages if channel_layer is available
            if self.channel_layer:
                await self.channel_layer.group_add(
                    self.group_name,
                    self.channel_name
                )
                logger.info(
                    "Added to group",
                    group_name=self.group_name,
                    channel_name=self.channel_name
                )
            else:
                logger.warning("Channel layer not available, skipping group_add")
            
            # Accept the connection
            await self.accept()
            
            # Update metrics
            active_connections.inc()
            
            logger.info(
                "WebSocket connected",
                session_id=self.session_id,
                channel_name=self.channel_name,
                group_name=self.group_name
            )
            
        except Exception as e:
            logger.error(
                "WebSocket connection error",
                error=str(e),
                exception_type=type(e).__name__
            )
            error_counter.labels(error_type='connection_error').inc()
            await self.close(code=1011)  # Internal error
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        try:
            # Calculate connection duration
            if self.start_time:
                duration = time.time() - self.start_time
                connection_duration.observe(duration)
            

            if self.pending_count > 0:
                logger.warning(
                    "Connection closed with pending messages",
                    session_id=self.session_id,
                    remaining_messages=self.pending_count
                )
            
            # Leave the group
            if self.channel_layer:
                await self.channel_layer.group_discard(
                    self.group_name,
                    self.channel_name
                )
            
            # Update metrics
            active_connections.dec()
            
            logger.info(
                "WebSocket disconnected",
                session_id=self.session_id,
                close_code=close_code,
                total_messages=self.message_count,
                duration=duration if self.start_time else 0,
                was_shutting_down=self.is_shutting_down
            )
            
        except Exception as e:
            logger.error(
                "WebSocket disconnect error",
                session_id=self.session_id,
                error=str(e),
                exception_type=type(e).__name__
            )
            error_counter.labels(error_type='disconnect_error').inc()
    
    async def receive(self, text_data):
        """Handle received WebSocket message."""
        try:
            #  reject new messages during shutdown
            if self.is_shutting_down:
                logger.info(
                    "Rejecting message during shutdown",
                    session_id=self.session_id
                )
                await self.send(text_data=json.dumps({
                    'error': 'Server is shutting down',
                    'session_id': self.session_id
                }))
                return
            
            self.pending_count += 1
            
            logger.debug(
                "Message processing started",
                session_id=self.session_id,
                inflight_count=self.pending_count
            )
            
            # Skip empty messages (just pressing enter)
            if not text_data or text_data.strip() == "":
                logger.debug(
                    "WebSocket empty message ignored",
                    session_id=self.session_id,
                    message_count=self.message_count
                )
                return
            
            # Check for special goodbye request
            if text_data.strip().lower() == "goodbye":
                # Send goodbye message and close
                goodbye_message = {
                    'bye': True,
                    'total': self.message_count
                }
                await self.send(text_data=json.dumps(goodbye_message))
                logger.info(
                    "Goodbye message sent in response to client request",
                    session_id=self.session_id,
                    total_messages=self.message_count
                )
                # Close the connection after sending goodbye
                await self.close(code=1000, reason="Normal closure")
                return
       
            # Increment message count for non-empty messages
            self.message_count += 1
            
            # Update session storage
            if self.session_id in session_storage:
                session_storage[self.session_id]['count'] = self.message_count
            
            # Update metrics
            message_counter.inc()
            
            # Prepare response
            response = {
                'count': self.message_count,
                'session_id': self.session_id,
                'message': text_data
            }
            
            # Send response
            await self.send(text_data=json.dumps(response))
            
            logger.debug(
                "WebSocket message processed",
                session_id=self.session_id,
                message_count=self.message_count,
                message_length=len(text_data)
            )
            
        except json.JSONDecodeError as e:
            logger.warning(
                "WebSocket invalid JSON received",
                session_id=self.session_id,
                error=str(e),
                raw_data=text_data
            )
            error_counter.labels(error_type='json_decode_error').inc()
            
            # Send error response
            error_response = {
                'error': 'Invalid JSON format',
                'session_id': self.session_id
            }
            await self.send(text_data=json.dumps(error_response))
            
        except Exception as e:
            logger.error(
                "WebSocket message processing error",
                session_id=self.session_id,
                error=str(e),
                exception_type=type(e).__name__
            )
            error_counter.labels(error_type='message_processing_error').inc()
            
            # Send error response
            error_response = {
                'error': 'Message processing failed',
                'session_id': self.session_id
            }
            await self.send(text_data=json.dumps(error_response))
            
        finally:
            # update inflight message count
            self.pending_count = max(0, self.pending_count - 1)
            
            logger.debug(
                "Message processing completed",
                session_id=self.session_id,
                remaining_inflight=self.pending_count
            )
    
    async def heartbeat_message(self, event):
        """Handle heartbeat messages from the heartbeat service."""
        try:
            message = event['message']
            await self.send(text_data=json.dumps(message))
            
            logger.debug(
                "Heartbeat sent to client",
                session_id=self.session_id,
                timestamp=message.get('ts')
            )
            
        except Exception as e:
            logger.error(
                "Heartbeat send error",
                session_id=self.session_id,
                error=str(e),
                exception_type=type(e).__name__
            )
            error_counter.labels(error_type='heartbeat_error').inc()
    
    async def shutdown_message(self, event):
        """Handle shutdown message for graceful connection closure."""
        try:
            self.is_shutting_down = True
            
            logger.info(
                "Server shutdown initiated - waiting for inflight messages",
                session_id=self.session_id,
                inflight_count=self.pending_count,
                total_messages=self.message_count
            )
            
            # Wait for inflight messages to complete (with timeout)
            shutdown_timeout = getattr(settings, 'GRACEFUL_SHUTDOWN_TIMEOUT', 10)
            drain_timeout = min(shutdown_timeout - 2, 5)  # have a buffer for the cleanup
            
            if self.pending_count > 0:
                logger.info(
                    "Waiting for inflight messages to be processed",
                    session_id=self.session_id,
                    inflight_count=self.pending_count,
                    timeout_seconds=drain_timeout
                )
                
                start_time = time.time()
                while self.pending_count > 0 and (time.time() - start_time) < drain_timeout:
                    await asyncio.sleep(0.1)  # Check every 100ms
                    
                if self.pending_count > 0:
                    logger.warning(
                        "Shutdown timeout - some messages may not have been processed successfully",
                        session_id=self.session_id,
                        remaining_inflight=self.pending_count,
                        elapsed_time=time.time() - start_time
                    )
                else:
                    logger.info(
                        "All inflight messages are processed successfully",
                        session_id=self.session_id,
                        elapsed_time=time.time() - start_time
                    )
            
            # Send goodbye message indicating server shutdown
            goodbye_message = {
                'bye': True,
                'total': self.message_count,
                'reason': 'server_shutdown',
                'inflight_completed': self.pending_count == 0
            }
            
            await self.send(text_data=json.dumps(goodbye_message))
            logger.info(
                "Server shutdown - goodbye message sent",
                session_id=self.session_id,
                total_messages=self.message_count,
                inflight_completed=self.pending_count == 0
            )
            
            # Give client a moment to receive the goodbye message
            await asyncio.sleep(0.5)
            
            # Close with code 1001 (Going away)
            await self.close(code=1001, reason="Going away")
            
        except Exception as e:
            logger.error(
                "Error closing WebSocket during shutdown",
                session_id=self.session_id,
                error=str(e)
            )
