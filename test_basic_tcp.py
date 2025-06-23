#!/usr/bin/env python3
"""
Test basic TCP connectivity to the Archipelago server
This helps determine if it's a network issue or WebSocket issue
"""

import socket
import sys

def test_connection(host='localhost', port=38281):
    print(f"Testing TCP connection to {host}:{port}...")
    
    # Test 1: Basic socket connection
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        
        if result == 0:
            print(f"✓ TCP connection successful to {host}:{port}")
            
            # Test 2: Send a basic HTTP request to see if it responds
            try:
                # Send a minimal WebSocket upgrade request
                request = (
                    f"GET / HTTP/1.1\r\n"
                    f"Host: {host}:{port}\r\n"
                    f"Upgrade: websocket\r\n"
                    f"Connection: Upgrade\r\n"
                    f"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
                    f"Sec-WebSocket-Version: 13\r\n"
                    f"\r\n"
                )
                sock.send(request.encode())
                
                # Try to receive a response
                response = sock.recv(1024).decode('utf-8', errors='ignore')
                print(f"\nServer response:\n{response}")
                
                if "101 Switching Protocols" in response:
                    print("\n✓ WebSocket upgrade successful!")
                else:
                    print("\n✗ Server did not upgrade to WebSocket")
                    
            except Exception as e:
                print(f"\n✗ Error sending WebSocket upgrade: {e}")
            
        else:
            print(f"✗ TCP connection failed with error code: {result}")
            print("  The server might not be running or the port is blocked")
            
    except Exception as e:
        print(f"✗ Connection error: {e}")
    finally:
        sock.close()
    
    # Test 3: Check if it's actually an Archipelago server
    print("\n" + "="*50)
    print("Archipelago Server Check:")
    print("="*50)
    
    try:
        import websocket
        
        ws = websocket.WebSocket()
        ws.connect(f"ws://{host}:{port}")
        
        # Send a minimal Connect packet
        connect_packet = '[{"cmd": "Connect", "game": "Test", "name": "TestClient", "uuid": "test-123", "version": {"class": "Version", "major": 0, "minor": 4, "build": 0}, "items_handling": 7, "tags": ["AP"]}]'
        ws.send(connect_packet)
        
        # Try to receive response
        response = ws.recv()
        print(f"✓ WebSocket connection successful!")
        print(f"Server response: {response[:200]}...")
        
        ws.close()
        
    except ImportError:
        print("✗ websocket-client not installed. Run: pip install websocket-client")
    except Exception as e:
        print(f"✗ WebSocket test failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        host = sys.argv[1]
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 38281
        test_connection(host, port)
    else:
        test_connection()