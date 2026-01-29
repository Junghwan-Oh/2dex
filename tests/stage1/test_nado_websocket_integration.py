"""
Test Nado WebSocket Real Connection

Integration tests for Nado WebSocket public streams.
These tests connect to the real Nado testnet WebSocket endpoint.
"""

import pytest
import asyncio
import json
from decimal import Decimal

# Try importing websockets
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    pytest.skip("websockets library not installed", allow_module_level=True)


@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection to Nado."""
    ws_url = "wss://gateway.test.nado.xyz/v1/subscribe"

    async with websockets.connect(ws_url) as ws:
        # Just verify we can connect
        assert ws.open
        print("✓ Connected to Nado WebSocket")


@pytest.mark.asyncio
async def test_bbo_subscription():
    """Test BBO stream subscription."""
    ws_url = "wss://gateway.test.nado.xyz/v1/subscribe"

    async with websockets.connect(ws_url) as ws:
        # Subscribe to BBO for ETH
        subscribe_msg = {
            "method": "subscribe",
            "stream": {
                "type": "best_bid_offer",
                "product_id": 4
            },
            "id": 1
        }

        await ws.send(json.dumps(subscribe_msg))

        # Wait for subscription response
        response = await asyncio.wait_for(ws.recv(), timeout=2.0)
        data = json.loads(response)

        # Should have result: null (success)
        assert "result" in data
        assert data["id"] == 1
        print("✓ BBO subscription successful")

        # Wait for at least one BBO message
        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
        bbo_data = json.loads(msg)

        assert bbo_data["type"] == "best_bid_offer"
        assert "bid_price" in bbo_data
        assert "ask_price" in bbo_data

        # Parse prices
        bid_price = Decimal(bbo_data["bid_price"]) / Decimal(1e18)
        ask_price = Decimal(bbo_data["ask_price"]) / Decimal(1e18)

        print(f"✓ Received BBO: Bid=${bid_price:.2f}, Ask=${ask_price:.2f}")


@pytest.mark.asyncio
async def test_bookdepth_subscription():
    """Test BookDepth stream subscription."""
    ws_url = "wss://gateway.test.nado.xyz/v1/subscribe"

    async with websockets.connect(ws_url) as ws:
        # Subscribe to BookDepth for ETH
        subscribe_msg = {
            "method": "subscribe",
            "stream": {
                "type": "book_depth",
                "product_id": 4
            },
            "id": 2
        }

        await ws.send(json.dumps(subscribe_msg))

        # Wait for subscription response
        response = await asyncio.wait_for(ws.recv(), timeout=2.0)
        data = json.loads(response)

        assert "result" in data
        print("✓ BookDepth subscription successful")

        # Wait for BookDepth message
        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
        depth_data = json.loads(msg)

        assert depth_data["type"] == "book_depth"
        assert "bids" in depth_data
        assert "asks" in depth_data

        print(f"✓ Received BookDepth: {len(depth_data['bids'])} bids, {len(depth_data['asks'])} asks")


@pytest.mark.asyncio
async def test_multiple_subscriptions():
    """Test subscribing to multiple streams simultaneously."""
    ws_url = "wss://gateway.test.nado.xyz/v1/subscribe"

    async with websockets.connect(ws_url) as ws:
        # Subscribe to both BBO and BookDepth
        bbo_msg = {
            "method": "subscribe",
            "stream": {"type": "best_bid_offer", "product_id": 4},
            "id": 1
        }

        depth_msg = {
            "method": "subscribe",
            "stream": {"type": "book_depth", "product_id": 4},
            "id": 2
        }

        await ws.send(json.dumps(bbo_msg))
        await ws.send(json.dumps(depth_msg))

        # Get both subscription confirmations
        for i in range(2):
            response = await asyncio.wait_for(ws.recv(), timeout=2.0)
            data = json.loads(response)
            assert "result" in data

        print("✓ Multiple subscriptions successful")

        # Wait for messages from both streams
        messages_received = {}
        for _ in range(5):  # Get up to 5 messages
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(msg)

            msg_type = data.get("type")
            if msg_type:
                messages_received[msg_type] = messages_received.get(msg_type, 0) + 1

        print(f"✓ Received messages: {messages_received}")


@pytest.mark.asyncio
async def test_unsubscribe():
    """Test unsubscribing from a stream."""
    ws_url = "wss://gateway.test.nado.xyz/v1/subscribe"

    async with websockets.connect(ws_url) as ws:
        # Subscribe first
        subscribe_msg = {
            "method": "subscribe",
            "stream": {"type": "best_bid_offer", "product_id": 4},
            "id": 1
        }

        await ws.send(json.dumps(subscribe_msg))
        response = await asyncio.wait_for(ws.recv(), timeout=2.0)
        assert "result" in response

        # Now unsubscribe
        unsubscribe_msg = {
            "method": "unsubscribe",
            "stream": {"type": "best_bid_offer", "product_id": 4},
            "id": 2
        }

        await ws.send(json.dumps(unsubscribe_msg))
        response = await asyncio.wait_for(ws.recv(), timeout=2.0)
        data = json.loads(response)

        assert "result" in data
        assert data["id"] == 2

        print("✓ Unsubscribe successful")


@pytest.mark.asyncio
async def test_connection_with_ping():
    """Test that connection stays alive with ping frames."""
    ws_url = "wss://gateway.test.nado.xyz/v1/subscribe"

    # websockets library handles ping automatically
    async with websockets.connect(
        ws_url,
        ping_interval=25,  # Send ping every 25 seconds
        ping_timeout=10
    ) as ws:
        # Subscribe to BBO
        subscribe_msg = {
            "method": "subscribe",
            "stream": {"type": "best_bid_offer", "product_id": 4},
            "id": 1
        }

        await ws.send(json.dumps(subscribe_msg))
        response = await asyncio.wait_for(ws.recv(), timeout=2.0)
        assert "result" in response

        # Wait for a few messages to verify connection stays alive
        for i in range(3):
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(msg)
            assert data.get("type") == "best_bid_offer"
            print(f"✓ Message {i+1} received")

        print("✓ Connection stable with ping")


if __name__ == "__main__":
    # Run tests directly
    print("Running Nado WebSocket integration tests...")
    asyncio.run(test_websocket_connection())
    asyncio.run(test_bbo_subscription())
    asyncio.run(test_bookdepth_subscription())
    asyncio.run(test_multiple_subscriptions())
    asyncio.run(test_unsubscribe())
    asyncio.run(test_connection_with_ping())
    print("\n✅ All tests passed!")
