"""
Test configuration for Django.
"""
import os
import sys
import django
import asyncio
import websockets
import json
from django.conf import settings
from django.test.utils import get_runner

# Add the app directory to Python path
app_dir = os.path.join(os.path.dirname(__file__), '..', 'app')
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

TestRunner = get_runner(settings)


class WebSocketTestClient:
    """Utility class for testing WebSocket functionality."""
    
    def __init__(self, uri="ws://localhost:8080/ws/chat/"):
        self.uri = uri
        self.websocket = None
        
    async def connect(self):
        """Connect to WebSocket."""
        self.websocket = await websockets.connect(self.uri)
        return self.websocket
        
    async def send_and_receive(self, message):
        """Send message and receive response."""
        if not self.websocket:
            raise ValueError("Not connected. Call connect() first.")
            
        await self.websocket.send(message)
        if message.strip():  # Only expect response for non-empty messages
            response = await self.websocket.recv()
            return json.loads(response)
        return None
        
    async def test_goodbye(self):
        """Send goodbye and receive goodbye response."""
        if not self.websocket:
            raise ValueError("Not connected. Call connect() first.")
            
        await self.websocket.send("goodbye")
        response = await self.websocket.recv()
        return json.loads(response)
        
    async def close(self, code=1000, reason="Normal closure"):
        """Close WebSocket connection."""
        if self.websocket:
            await self.websocket.close(code=code, reason=reason)
            
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
