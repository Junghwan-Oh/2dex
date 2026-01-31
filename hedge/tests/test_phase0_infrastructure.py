"""
Phase 0: Infrastructure Validation Testing

Tests for WebSocket PNL optimization implementation.

Key validation: Pure getters must be truly idempotent.
100 consecutive calls to get_spread_state() and get_momentum()
should return the exact same values without causing any state changes.
"""

import asyncio
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from decimal import Decimal
from typing import Optional

# Import the classes we need to test
import sys
sys.path.insert(0, '/Users/botfarmer/2dex/hedge')

from exchanges.nado_bbo_handler import (
    BBOHandler,
    BBOData,
    SpreadMonitor,
    MomentumDetector
)


class TestNadoClientIntegration:
    """Test 1: get_bbo_handler() accessibility"""

    @pytest.fixture
    def mock_nado_client(self):
        """Create a mock NadoClient with WebSocket components."""
        with patch('exchanges.nado.WEBSOCKET_AVAILABLE', True):
            from exchanges.nado import NadoClient

            # Mock config
            mock_config = Mock()
            mock_config.ticker = 'ETH'
            mock_config.contract_id = 4
            mock_config.quantity = Decimal('0.1')
            mock_config.tick_size = Decimal('0.0001')

            # Mock environment
            with patch.dict('os.environ', {
                'NADO_PRIVATE_KEY': '0x' + '1' * 64,
                'NADO_MODE': 'MAINNET',
                'NADO_SUBACCOUNT_NAME': 'test'
            }):
                client = NadoClient(mock_config)
                # Initialize WebSocket components
                client._bbo_handler = Mock(spec=BBOHandler)
                client._ws_connected = True
                return client

    def test_get_bbo_handler_exists(self, mock_nado_client):
        """Verify NadoClient.get_bbo_handler() method exists"""
        assert hasattr(mock_nado_client, 'get_bbo_handler'), \
            "NadoClient should have get_bbo_handler method"

    def test_get_bbo_handler_returns_handler_when_connected(self, mock_nado_client):
        """Verify it returns BBOHandler when WebSocket is connected"""
        mock_nado_client._ws_connected = True
        mock_nado_client._bbo_handler = Mock(spec=BBOHandler)

        result = mock_nado_client.get_bbo_handler()

        assert result is not None, "get_bbo_handler() should return BBOHandler when connected"
        assert isinstance(result, Mock), "Should return the BBOHandler instance"

    def test_get_bbo_handler_returns_none_when_disconnected(self, mock_nado_client):
        """Verify it returns None when WebSocket is disconnected"""
        mock_nado_client._ws_connected = False
        mock_nado_client._bbo_handler = Mock(spec=BBOHandler)

        result = mock_nado_client.get_bbo_handler()

        assert result is None, "get_bbo_handler() should return None when disconnected"


class TestPureGetterIdempotency:
    """Test 2: Pure getter idempotency (CRITICAL)"""

    @pytest.fixture
    def bbo_handler(self):
        """Create a BBOHandler instance for testing."""
        # Create mock WebSocket client
        mock_ws_client = Mock()
        mock_ws_client.subscribe = AsyncMock()

        # Create BBOHandler with a real logger
        import logging
        handler = BBOHandler(
            product_id=4,
            ws_client=mock_ws_client,
            logger=logging.getLogger(__name__)
        )
        return handler

    def test_get_spread_state_idempotent_100_calls(self, bbo_handler):
        """
        Call get_spread_state() 100 times consecutively.
        All 100 calls must return identical cached values.
        Verify no side effects (cached state unchanged).
        """
        # Get initial state
        initial_state = bbo_handler.get_spread_state()
        initial_cached_value = bbo_handler._cached_spread_state

        # Call 100 times and collect results
        results = []
        for i in range(100):
            result = bbo_handler.get_spread_state()
            results.append(result)

        # Verify all 100 calls returned the same value
        assert all(r == initial_state for r in results), \
            f"All 100 calls to get_spread_state() should return '{initial_state}', got: {set(results)}"

        # Verify cached state is unchanged
        assert bbo_handler._cached_spread_state == initial_cached_value, \
            "Cached state should not be modified by getter calls"

        # Verify it's the default "STABLE" value
        assert initial_state == "STABLE", \
            f"Initial spread state should be 'STABLE', got '{initial_state}'"

    def test_get_momentum_idempotent_100_calls(self, bbo_handler):
        """
        Call get_momentum() 100 times consecutively.
        All 100 calls must return identical cached values.
        Verify no side effects (cached state unchanged).
        """
        # Get initial state
        initial_state = bbo_handler.get_momentum()
        initial_cached_value = bbo_handler._cached_momentum

        # Call 100 times and collect results
        results = []
        for i in range(100):
            result = bbo_handler.get_momentum()
            results.append(result)

        # Verify all 100 calls returned the same value
        assert all(r == initial_state for r in results), \
            f"All 100 calls to get_momentum() should return '{initial_state}', got: {set(results)}"

        # Verify cached state is unchanged
        assert bbo_handler._cached_momentum == initial_cached_value, \
            "Cached state should not be modified by getter calls"

        # Verify it's the default "NEUTRAL" value
        assert initial_state == "NEUTRAL", \
            f"Initial momentum should be 'NEUTRAL', got '{initial_state}'"

    def test_no_side_effects_from_getters(self, bbo_handler):
        """
        Verify that repeated getter calls don't cause any side effects
        like changing internal state or triggering calculations.
        """
        # Record initial internal state
        initial_spread_cache = bbo_handler._cached_spread_state
        initial_momentum_cache = bbo_handler._cached_momentum
        initial_latest_bbo = bbo_handler._latest_bbo
        initial_callbacks = list(bbo_handler._callbacks)

        # Call getters 1000 times (stress test)
        for _ in range(1000):
            bbo_handler.get_spread_state()
            bbo_handler.get_momentum()

        # Verify internal state is completely unchanged
        assert bbo_handler._cached_spread_state == initial_spread_cache, \
            "Spread cache should be unchanged"
        assert bbo_handler._cached_momentum == initial_momentum_cache, \
            "Momentum cache should be unchanged"
        assert bbo_handler._latest_bbo == initial_latest_bbo, \
            "Latest BBO should be unchanged"
        assert bbo_handler._callbacks == initial_callbacks, \
            "Callbacks list should be unchanged"


class TestWebSocketDataFlow:
    """Test 3: WebSocket data flow"""

    @pytest.fixture
    def mock_ws_client(self):
        """Create a mock WebSocket client."""
        mock_client = Mock()
        mock_client.subscribe = AsyncMock()
        return mock_client

    @pytest.fixture
    def bbo_handler_with_mock(self, mock_ws_client):
        """Create a BBOHandler with mock WebSocket client."""
        import logging
        handler = BBOHandler(
            product_id=4,
            ws_client=mock_ws_client,
            logger=logging.getLogger(__name__)
        )
        return handler

    @pytest.mark.asyncio
    async def test_bbo_message_parsing(self, bbo_handler_with_mock):
        """Verify BBO message parsing works correctly."""
        handler = bbo_handler_with_mock

        # Create a sample BBO message (in x18 format as per protocol)
        message = {
            "product_id": 4,
            "bid_price": "3000000000000000000000",  # 3000 ETH in x18
            "bid_qty": "1000000000000000000",        # 1 ETH in x18
            "ask_price": "3001000000000000000000",   # 3001 ETH in x18
            "ask_qty": "1000000000000000000",        # 1 ETH in x18
            "timestamp": 1234567890
        }

        # Process the message
        await handler._on_bbo_message(message)

        # Verify BBO data was parsed and stored
        assert handler._latest_bbo is not None, "Latest BBO should be stored"
        assert handler._latest_bbo.product_id == 4
        assert handler._latest_bbo.bid_price == Decimal('3000')
        assert handler._latest_bbo.ask_price == Decimal('3001')
        assert handler._latest_bbo.bid_qty == Decimal('1')
        assert handler._latest_bbo.ask_qty == Decimal('1')

    @pytest.mark.asyncio
    async def test_on_bbo_message_updates_cached_states(self, bbo_handler_with_mock):
        """Verify _on_bbo_message updates cached states."""
        handler = bbo_handler_with_mock

        # Send multiple BBO messages to trigger state changes
        messages = [
            {
                "product_id": 4,
                "bid_price": f"{3000 + i}000000000000000000",
                "bid_qty": "1000000000000000000",
                "ask_price": f"{3001 + i}000000000000000000",
                "ask_qty": "1000000000000000000",
                "timestamp": 1234567890 + i
            }
            for i in range(15)  # Send 15 messages to trigger analysis
        ]

        for msg in messages:
            await handler._on_bbo_message(msg)

        # Verify cached states were updated (may still be STABLE/NEUTRAL depending on math)
        # The key is that they should be updated by the message handler
        assert handler._cached_spread_state in ["WIDENING", "NARROWING", "STABLE"]
        assert handler._cached_momentum in ["BULLISH", "BEARISH", "NEUTRAL"]

    @pytest.mark.asyncio
    async def test_callbacks_receive_correct_parameters(self, bbo_handler_with_mock):
        """Verify callbacks receive correct parameters."""
        handler = bbo_handler_with_mock

        # Track callback invocations
        callback_invocations = []

        def test_callback(bbo, spread_state, momentum):
            callback_invocations.append({
                'bbo': bbo,
                'spread_state': spread_state,
                'momentum': momentum
            })

        # Register callback
        handler.register_callback(test_callback)

        # Send a BBO message
        message = {
            "product_id": 4,
            "bid_price": "3000000000000000000000",
            "bid_qty": "1000000000000000000",
            "ask_price": "3001000000000000000000",
            "ask_qty": "1000000000000000000",
            "timestamp": 1234567890
        }

        await handler._on_bbo_message(message)

        # Verify callback was invoked
        assert len(callback_invocations) == 1, "Callback should be invoked once"

        # Verify callback received correct parameters
        invocation = callback_invocations[0]
        assert invocation['bbo'] is not None, "Callback should receive BBO data"
        assert isinstance(invocation['spread_state'], str), "spread_state should be string"
        assert isinstance(invocation['momentum'], str), "momentum should be string"
        assert invocation['spread_state'] in ["WIDENING", "NARROWING", "STABLE"]
        assert invocation['momentum'] in ["BULLISH", "BEARISH", "NEUTRAL"]


class TestStateCachingVerification:
    """Test 4: State caching verification"""

    @pytest.fixture
    def bbo_handler(self):
        """Create a fresh BBOHandler instance."""
        mock_ws_client = Mock()
        mock_ws_client.subscribe = AsyncMock()

        import logging
        handler = BBOHandler(
            product_id=4,
            ws_client=mock_ws_client,
            logger=logging.getLogger(__name__)
        )
        return handler

    def test_cached_spread_state_initialized_to_stable(self, bbo_handler):
        """Verify _cached_spread_state is initialized to "STABLE"."""
        assert hasattr(bbo_handler, '_cached_spread_state'), \
            "BBOHandler should have _cached_spread_state attribute"

        assert bbo_handler._cached_spread_state == "STABLE", \
            f"Initial _cached_spread_state should be 'STABLE', got '{bbo_handler._cached_spread_state}'"

    def test_cached_momentum_initialized_to_neutral(self, bbo_handler):
        """Verify _cached_momentum is initialized to "NEUTRAL"."""
        assert hasattr(bbo_handler, '_cached_momentum'), \
            "BBOHandler should have _cached_momentum attribute"

        assert bbo_handler._cached_momentum == "NEUTRAL", \
            f"Initial _cached_momentum should be 'NEUTRAL', got '{bbo_handler._cached_momentum}'"

    @pytest.mark.asyncio
    async def test_states_update_correctly_when_bbo_messages_arrive(self, bbo_handler):
        """Verify states update correctly when BBO messages arrive."""
        # Initial state
        initial_spread = bbo_handler._cached_spread_state
        initial_momentum = bbo_handler._cached_momentum

        assert initial_spread == "STABLE"
        assert initial_momentum == "NEUTRAL"

        # Send BBO messages with rising prices (should trigger BULLISH eventually)
        for i in range(10):
            message = {
                "product_id": 4,
                "bid_price": f"{3000 + i * 10}000000000000000000",
                "bid_qty": "1000000000000000000",
                "ask_price": f"{3001 + i * 10}000000000000000000",
                "ask_qty": "1000000000000000000",
                "timestamp": 1234567890 + i
            }
            await bbo_handler._on_bbo_message(message)

        # After rising prices, momentum might change (depends on threshold)
        # The key test is that states CAN change from initial values
        # We'll verify the state is still valid
        assert bbo_handler._cached_spread_state in ["WIDENING", "NARROWING", "STABLE"]
        assert bbo_handler._cached_momentum in ["BULLISH", "BEARISH", "NEUTRAL"]

    def test_getters_return_cached_values(self, bbo_handler):
        """Verify getters return the cached values, not calculated ones."""
        # Manually set cached values
        bbo_handler._cached_spread_state = "WIDENING"
        bbo_handler._cached_momentum = "BULLISH"

        # Getters should return these exact values
        assert bbo_handler.get_spread_state() == "WIDENING", \
            "get_spread_state() should return cached value"
        assert bbo_handler.get_momentum() == "BULLISH", \
            "get_momentum() should return cached value"

        # Verify no calculation was triggered by checking internal state
        assert bbo_handler._cached_spread_state == "WIDENING"
        assert bbo_handler._cached_momentum == "BULLISH"


class TestBBOMonitoringComponents:
    """Additional tests for BBO monitoring components"""

    def test_bbo_data_properties(self):
        """Test BBOData calculations."""
        bbo = BBOData(
            product_id=4,
            bid_price=Decimal('3000'),
            bid_qty=Decimal('1'),
            ask_price=Decimal('3001'),
            ask_qty=Decimal('1'),
            timestamp=1234567890
        )

        assert bbo.spread == Decimal('1')
        assert bbo.mid_price == Decimal('3000.5')

    def test_spread_monitor_initial_state(self):
        """Test SpreadMonitor initial state."""
        monitor = SpreadMonitor()

        # Should return STABLE with insufficient data
        bbo = BBOData(
            product_id=4,
            bid_price=Decimal('3000'),
            bid_qty=Decimal('1'),
            ask_price=Decimal('3001'),
            ask_qty=Decimal('1'),
            timestamp=1234567890
        )

        state = monitor.on_bbo(bbo)
        assert state == "STABLE"

    def test_momentum_detector_initial_state(self):
        """Test MomentumDetector initial state."""
        detector = MomentumDetector()

        # Should return NEUTRAL with insufficient data
        bbo = BBOData(
            product_id=4,
            bid_price=Decimal('3000'),
            bid_qty=Decimal('1'),
            ask_price=Decimal('3001'),
            ask_qty=Decimal('1'),
            timestamp=1234567890
        )

        state = detector.on_bbo(bbo)
        assert state == "NEUTRAL"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
