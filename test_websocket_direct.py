#!/usr/bin/env python3
"""Direct WebSocket test for mobile camera streaming endpoint."""

import asyncio
import json

import websockets


async def test_websocket():
    uri = "ws://localhost:8005/api/v1/cameras/mobile/test_device/stream"
    print(f"Testing WebSocket connection to: {uri}")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connection established successfully!")

            # Try to receive initial message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5)
                print(f"📨 Received message: {message}")

                # Parse JSON if possible
                try:
                    data = json.loads(message)
                    print(f"📋 Parsed data: {data}")
                except json.JSONDecodeError:
                    print("📋 Message is not JSON")

            except asyncio.TimeoutError:
                print("⏰ No message received within 5 seconds")

            # Send a test message
            test_msg = {"type": "test", "message": "Hello from test client"}
            await websocket.send(json.dumps(test_msg))
            print(f"📤 Sent test message: {test_msg}")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ WebSocket connection closed: {e}")
    except websockets.exceptions.InvalidURI as e:
        print(f"❌ Invalid WebSocket URI: {e}")
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket())
