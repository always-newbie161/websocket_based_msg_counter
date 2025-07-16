#!/usr/bin/env python3
"""
WebSocket load tester for concurrent socket testing.

Usage:
    python tests/socket_load_test.py --sockets 5000 --rate 100 --duration 300
    
Parameters:
    --sockets: Total number of concurrent WebSocket connections to maintain
    --rate: Number of new connections to create per second  
    --duration: How long to run the test (seconds)
    --host: WebSocket host (default: ws://localhost:8080)
    --send-rate: Messages per second per socket (default: 0.1)
"""
import asyncio
import websockets
import json
import time
import argparse
import signal
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
from collections import defaultdict, deque
import statistics

class SocketLoadTester:
    def __init__(self, target_sockets, connection_rate, duration, host, send_rate):
        self.target_sockets = target_sockets
        self.connection_rate = connection_rate  # connections/second
        self.duration = duration
        self.host = host
        self.send_rate = send_rate  # messages/second per socket
        
        # Connection tracking
        self.active_connections = set()
        self.connection_count = 0
        self.failed_connections = 0
        self.total_messages_sent = 0
        self.total_messages_received = 0
        self.total_errors = 0
        
        # Performance metrics
        self.connection_times = deque(maxlen=1000)
        self.message_times = deque(maxlen=1000)
        self.error_count_by_type = defaultdict(int)
        
        # Control flags
        self.running = True
        self.start_time = None
        self.tasks = []  # Store tasks for cleanup
        self.interrupted = False  # Flag for signal handling
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals by signaling run_test to end."""
        print(f"\nReceived signal {signum}, stopping test...")
        
        # Signal the test to stop
        self.interrupted = True
        self.running = False
        
    
    
    async def create_connection(self, connection_id):
        """Create a single WebSocket connection and handle its lifecycle."""
        ws = None
        session_id = None
        message_count = 0
        
        try:
            # Connect with timeout
            connect_start = time.time()
            ws = await asyncio.wait_for(
                websockets.connect(f"{self.host}/ws/chat/"),
                timeout=100.0
            )
            connect_time = time.time() - connect_start
            
            with self.lock:
                self.connection_count += 1
                self.active_connections.add(connection_id)
                self.connection_times.append(connect_time)
            
            print(f"[CONNECTED] Connection {connection_id} established in {connect_time:.3f}s")
            
            # Message sending loop
            last_message_time = time.time()
            message_interval = 1.0 / self.send_rate if self.send_rate > 0 else float('inf')
            
            while self.running:
                try:
                    current_time = time.time()
                    
                    # Check if we've been interrupted
                    if self.interrupted:
                        break
                    
                    # Send message based on send_rate
                    if current_time - last_message_time >= message_interval:
                        message = f"Load test message {message_count} from connection {connection_id}"
                        
                        send_start = time.time()
                        await ws.send(message)
                        
                        # Wait for response
                        response = await asyncio.wait_for(ws.recv(), timeout=100.0)
                        message_time = time.time() - send_start
                        
                        data = json.loads(response)
                        
                        # Extract session info
                        if not session_id and 'session_id' in data:
                            session_id = data['session_id']
                        
                        message_count += 1
                        last_message_time = current_time
                        
                        with self.lock:
                            self.total_messages_sent += 1
                            self.total_messages_received += 1
                            self.message_times.append(message_time)
                        
                        if message_count % 100 == 0:
                            print(f"[MESSAGE] Connection {connection_id}: {message_count} messages sent")
                    
                    else:
                        # Keep connection alive with small delay
                        await asyncio.sleep(0.1)
                        
                except asyncio.TimeoutError:
                    with self.lock:
                        self.error_count_by_type['timeout'] += 1
                        self.total_errors += 1
                    print(f"Connection {connection_id}: Timeout on message {message_count}")
                    
                except websockets.exceptions.ConnectionClosed:
                    print(f"Connection {connection_id}: Connection closed by server")
                    break
                    
                except Exception as e:
                    with self.lock:
                        self.error_count_by_type[type(e).__name__] += 1
                        self.total_errors += 1
                    print(f"[ERROR] Connection {connection_id}: Error - {e}")
                    await asyncio.sleep(1)  # Brief pause before retry
            
        except asyncio.TimeoutError:
            with self.lock:
                self.failed_connections += 1
                self.error_count_by_type['connection_timeout'] += 1
            print(f"Connection {connection_id}: Failed to connect (timeout)")
            
        except Exception as e:
            with self.lock:
                self.failed_connections += 1
                self.error_count_by_type[type(e).__name__] += 1
            print(f"[ERROR] Connection {connection_id}: Failed to connect - {e}")
            
        finally:
            # Cleanup
            if ws:
                try:
                    await ws.send("goodbye")
                    await asyncio.sleep(0.1)
                    await ws.close()
                except:
                    pass
            
            with self.lock:
                self.active_connections.discard(connection_id)
            
            print(f"Connection {connection_id} closed (sent {message_count} messages)")
    
    async def connection_spawner(self):
        """Spawn connections at the specified rate."""
        connection_id = 0
        interval = 1.0 / self.connection_rate
        
        print(f"[STARTING] Starting connection spawner: {self.connection_rate} connections/second")
        
        while self.running and len(self.active_connections) < self.target_sockets:
            # Create new connection
            connection_id += 1
            asyncio.create_task(self.create_connection(connection_id))
            
            # Wait for next spawn
            await asyncio.sleep(interval)
            
            if connection_id % 100 == 0:
                print(f"[SPAWNING] Spawned {connection_id} connections, {len(self.active_connections)} active")
        
        print(f"[COMPLETE] Connection spawning complete: {len(self.active_connections)} active connections")
    
    def print_stats(self):
        """Print current statistics."""
        with self.lock:
            active_count = len(self.active_connections)
            
            # Calculate averages
            avg_connect_time = statistics.mean(self.connection_times) if self.connection_times else 0
            avg_message_time = statistics.mean(self.message_times) if self.message_times else 0
            
            # Calculate rates
            elapsed = time.time() - self.start_time if self.start_time else 1
            connection_rate_actual = self.connection_count / elapsed
            message_rate = self.total_messages_sent / elapsed
            
            print(f"""
=== WebSocket Load Test Statistics ===
Runtime: {elapsed:.1f}s
Connections: {active_count} active, {self.connection_count} total, {self.failed_connections} failed
Messages: {self.total_messages_sent} sent, {self.total_messages_received} received
 Errors: {self.total_errors} total
Rates: {connection_rate_actual:.1f} conn/s, {message_rate:.2f} msg/s
Avg Times: {avg_connect_time*1000:.1f}ms connect, {avg_message_time*1000:.1f}ms message
""")
            
            if self.error_count_by_type:
                print("Error breakdown:")
                for error_type, count in self.error_count_by_type.items():
                    print(f"   {error_type}: {count}")
    
    async def monitor_loop(self):
        """Monitor and print statistics every 10 seconds."""
        while self.running:
            await asyncio.sleep(10)
            self.print_stats()
    
    async def run_test(self):
        """Run the complete load test."""
        print(f"""
Starting WebSocket Load Test
   Target Sockets: {self.target_sockets}
   Connection Rate: {self.connection_rate}/second  
   Duration: {self.duration} seconds
   Host: {self.host}
   Send Rate: {self.send_rate} messages/second/socket
""")
        
        self.start_time = time.time()
        
        # Start tasks and store references
        self.tasks = [
            asyncio.create_task(self.connection_spawner()),
            asyncio.create_task(self.monitor_loop())
        ]
        
        try:
            # Run for specified duration or until interrupted
            while not self.interrupted:
                await asyncio.sleep(0.1)
                # Check if duration has elapsed
                if time.time() - self.start_time >= self.duration:
                    break
            
        except KeyboardInterrupt:
            print("\n[INTERRUPTED] Test interrupted by user")
            self.interrupted = True
            
        finally:
            # Stop everything
            self.running = False
            
            # Wait a moment for tasks to stop gracefully
            await asyncio.sleep(1.0)
            
            # Cancel any remaining tasks
            for task in self.tasks:
                if not task.done():
                    task.cancel()
            
            # Print final stats
            print("\n" + "="*50)
            if self.interrupted:
                print("[STATS] FINAL RESULTS (INTERRUPTED)")
            else:
                print("[STATS] FINAL RESULTS")
            print("="*50)
            self.print_stats()
            
            # Test results
            success_rate = (self.connection_count / (self.connection_count + self.failed_connections)) * 100 if (self.connection_count + self.failed_connections) > 0 else 0
            
            print(f"""
Test Results:
   Success Rate: {success_rate:.1f}%
   Peak Concurrent Connections: {max(len(self.active_connections), self.connection_count)}
   Target Achievement: {'PASS' if self.connection_count >= self.target_sockets * 0.9 else 'FAIL'}
""")
            
            # Ensure output is flushed
            sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser(description='WebSocket Load Tester')
    parser.add_argument('--sockets', type=int, default=5000, help='Number of concurrent connections')
    parser.add_argument('--rate', type=int, default=100, help='Connections per second')
    parser.add_argument('--duration', type=int, default=300, help='Test duration in seconds')
    parser.add_argument('--host', default='ws://localhost:8080', help='WebSocket host')
    parser.add_argument('--send-rate', type=float, default=0.1, help='Messages per second per socket')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.sockets <= 0 or args.rate <= 0 or args.duration <= 0:
        print("[ERROR] sockets, rate, and duration must be positive numbers")
        sys.exit(1)
    
    # Create and run tester
    tester = SocketLoadTester(
        target_sockets=args.sockets,
        connection_rate=args.rate,
        duration=args.duration,
        host=args.host,
        send_rate=args.send_rate
    )
    
    try:
        asyncio.run(tester.run_test())
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
