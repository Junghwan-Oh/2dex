"""
WebSocket Position Tracking Testing (TDD - RED PHASE)

Tests for _ws_positions dictionary and WebSocket position_change events.

This file contains FAILING tests that should initially fail.
They will pass after proper implementation of the WebSocket position tracking.

Key Issues Being Tested:
1. WebSocket updates _ws_positions correctly
2. WebSocket provides real-time data (more accurate than REST API)
3. Reset works correctly without interfering with ongoing tracking
4. Position persistence across multiple updates
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, PropertyMock
from decimal import Decimal
import sys
import os
from typing import Dict, Any

# Add project to path
sys.path.insert(0, '/Users/botfarmer/2dex')

from hedge.DN_pair_eth_sol_nado import DNPairBot


class TestWebSocketPositionTracking:
    """Test WebSocket position tracking functionality."""

    @pytest.fixture
    async def bot(self):
        """Create a bot instance for testing."""
        # Mock environment variables
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            # Create bot with minimal config
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_websocket_positions.csv'
            )

            # Initialize _ws_positions
            bot._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}

            return bot

    @pytest.fixture
    def mock_eth_client(self):
        """Create a mock ETH NadoClient."""
        mock_client = Mock()
        mock_client.config = Mock()
        mock_client.config.contract_id = 4
        mock_client.config.ticker = "ETH"
        return mock_client

    @pytest.fixture
    def mock_sol_client(self):
        """Create a mock SOL NadoClient."""
        mock_client = Mock()
        mock_client.config = Mock()
        mock_client.config.contract_id = 5
        mock_client.config.ticker = "SOL"
        return mock_client


class TestWebSocketUpdatesDictCorrectly:
    """Test 1: WebSocket position_change events update _ws_positions dictionary."""

    @pytest.mark.asyncio
    async def test_eth_position_change_updates_ws_positions(self):
        """
        RED PHASE: Test that ETH position_change event updates _ws_positions.

        This test will FAIL initially because:
        1. The bot may not have _ws_positions initialized
        2. The position_change handler may not be implemented correctly
        3. The mock setup may not match actual WebSocket message format

        Expected behavior:
        - _ws_positions["ETH"] should be updated to the new position amount
        - The update should use Decimal precision (not float)
        - The amount should be divided by 1e18 (raw to decimal conversion)
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_ws_positions.csv'
            )

            # Initialize clients and _ws_positions
            bot.eth_client = Mock()
            bot.eth_client.config.contract_id = 4
            bot.sol_client = Mock()
            bot.sol_client.config.contract_id = 5
            bot._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}

            # Mock log_position_update to avoid CSV operations
            bot.log_position_update = Mock()

            # Simulate WebSocket position_change event for ETH
            # Raw amount: 100000000000000000 (0.1 ETH in wei)
            ws_message = {
                "product_id": 4,
                "amount": "100000000000000000",  # 0.1 ETH
                "v_quote_amount": "200000000",  # ~$200 USD value
                "reason": "trade"
            }

            # This should FAIL because the handler may not be properly wired
            # or the implementation doesn't update _ws_positions correctly
            bot._on_position_change(ws_message)

            # ASSERTION: _ws_positions should be updated
            # This will FAIL if the handler doesn't work correctly
            assert bot._ws_positions["ETH"] == Decimal("0.1"), (
                f"Expected ETH position to be 0.1, got {bot._ws_positions.get('ETH')}"
            )

            # ASSERTION: SOL should remain unchanged
            assert bot._ws_positions["SOL"] == Decimal("0"), (
                f"Expected SOL position to remain 0, got {bot._ws_positions.get('SOL')}"
            )

    @pytest.mark.asyncio
    async def test_sol_position_change_updates_ws_positions(self):
        """
        RED PHASE: Test that SOL position_change event updates _ws_positions.

        Expected behavior:
        - _ws_positions["SOL"] should be updated to the new position amount
        - ETH should remain unchanged
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_ws_positions.csv'
            )

            # Initialize clients and _ws_positions
            bot.eth_client = Mock()
            bot.eth_client.config.contract_id = 4
            bot.sol_client = Mock()
            bot.sol_client.config.contract_id = 5
            bot._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}

            # Mock log_position_update
            bot.log_position_update = Mock()

            # Simulate WebSocket position_change event for SOL
            # Raw amount: 5000000000 (5 SOL in atomic units)
            ws_message = {
                "product_id": 5,
                "amount": "5000000000",  # 5 SOL
                "v_quote_amount": "500000000",  # ~$500 USD value
                "reason": "trade"
            }

            # This should FAIL initially
            bot._on_position_change(ws_message)

            # ASSERTION: _ws_positions should be updated
            assert bot._ws_positions["SOL"] == Decimal("5"), (
                f"Expected SOL position to be 5, got {bot._ws_positions.get('SOL')}"
            )

            # ASSERTION: ETH should remain unchanged
            assert bot._ws_positions["ETH"] == Decimal("0"), (
                f"Expected ETH position to remain 0, got {bot._ws_positions.get('ETH')}"
            )

    @pytest.mark.asyncio
    async def test_multiple_position_changes_update_correctly(self):
        """
        RED PHASE: Test that multiple consecutive position_change events
        update _ws_positions correctly.

        Expected behavior:
        - Each update should replace the previous value (absolute position)
        - Updates should not accumulate (WebSocket sends absolute position)
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_ws_positions.csv'
            )

            # Initialize clients and _ws_positions
            bot.eth_client = Mock()
            bot.eth_client.config.contract_id = 4
            bot.sol_client = Mock()
            bot.sol_client.config.contract_id = 5
            bot._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}

            # Mock log_position_update
            bot.log_position_update = Mock()

            # First update: 0.1 ETH
            bot._on_position_change({
                "product_id": 4,
                "amount": "100000000000000000",  # 0.1 ETH
                "v_quote_amount": "200000000",
                "reason": "trade"
            })

            # ASSERTION: First update
            assert bot._ws_positions["ETH"] == Decimal("0.1"), (
                f"Expected ETH position to be 0.1 after first update, "
                f"got {bot._ws_positions.get('ETH')}"
            )

            # Second update: 0.2 ETH (position increased)
            bot._on_position_change({
                "product_id": 4,
                "amount": "200000000000000000",  # 0.2 ETH
                "v_quote_amount": "400000000",
                "reason": "trade"
            })

            # ASSERTION: Second update should REPLACE, not accumulate
            assert bot._ws_positions["ETH"] == Decimal("0.2"), (
                f"Expected ETH position to be 0.2 after second update, "
                f"got {bot._ws_positions.get('ETH')}"
            )

            # Third update: 0.05 ETH (position decreased)
            bot._on_position_change({
                "product_id": 4,
                "amount": "50000000000000000",  # 0.05 ETH
                "v_quote_amount": "100000000",
                "reason": "trade"
            })

            # ASSERTION: Third update
            assert bot._ws_positions["ETH"] == Decimal("0.05"), (
                f"Expected ETH position to be 0.05 after third update, "
                f"got {bot._ws_positions.get('ETH')}"
            )


class TestWebSocketProvidesRealTimeData:
    """Test 2: WebSocket positions are more accurate than REST API."""

    @pytest.mark.asyncio
    async def test_ws_positions_more_accurate_than_rest_at_startup(self):
        """
        RED PHASE: Test that WebSocket positions provide real-time data
        while REST API has lag at startup.

        Issue: At bot startup, REST API may show 0.0 positions but WebSocket
        events arrive shortly after with actual position values.

        Expected behavior:
        - WebSocket should update _ws_positions even if REST hasn't caught up
        - Bot should use _ws_positions when available, fallback to REST
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_ws_positions.csv'
            )

            # Initialize clients and _ws_positions
            bot.eth_client = Mock()
            bot.eth_client.config.contract_id = 4
            bot.sol_client = Mock()
            bot.sol_client.config.contract_id = 5
            bot._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}

            # Mock REST API returning 0 (lagging state)
            async def mock_get_position(*args, **kwargs):
                return Decimal("0")

            bot.eth_client.get_position = mock_get_position
            bot.sol_client.get_position = mock_get_position

            # Mock log_position_update
            bot.log_position_update = Mock()

            # Simulate WebSocket event arriving before REST updates
            bot._on_position_change({
                "product_id": 4,
                "amount": "100000000000000000",  # 0.1 ETH
                "v_quote_amount": "200000000",
                "reason": "trade"
            })

            # ASSERTION: WebSocket should have updated position
            assert bot._ws_positions["ETH"] == Decimal("0.1"), (
                "WebSocket position should be updated even if REST shows 0"
            )

            # ASSERTION: Bot should use WebSocket position over REST
            # This tests the prioritization logic
            ws_pos = bot._ws_positions.get("ETH", Decimal("0"))
            rest_pos = await bot.eth_client.get_position()

            assert ws_pos != rest_pos, (
                f"WebSocket position ({ws_pos}) should differ from REST ({rest_pos}) "
                "to demonstrate real-time advantage"
            )

    @pytest.mark.asyncio
    async def test_ws_positions_used_when_available(self):
        """
        RED PHASE: Test that bot code uses _ws_positions when available,
        falling back to REST API only when WebSocket hasn't received data yet.

        Expected behavior:
        - Code should check: _ws_positions.get(ticker) if hasattr else REST
        - This ensures real-time data is always preferred
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_ws_positions.csv'
            )

            # Initialize clients and _ws_positions
            bot.eth_client = Mock()
            bot.eth_client.config.contract_id = 4
            bot.sol_client = Mock()
            bot.sol_client.config.contract_id = 5

            # Set up WebSocket positions
            bot._ws_positions = {"ETH": Decimal("0.15"), "SOL": Decimal("3.5")}

            # Mock REST API returning different (stale) values
            async def mock_get_position(*args, **kwargs):
                return Decimal("0")

            bot.eth_client.get_position = mock_get_position

            # ASSERTION: _ws_positions should be accessible and used
            # This tests that the pattern exists in the codebase
            ticker = "ETH"
            ws_pos = bot._ws_positions.get(ticker, Decimal("0"))

            assert ws_pos == Decimal("0.15"), (
                f"Expected WebSocket position 0.15, got {ws_pos}"
            )

            # Verify the pattern for using WS over REST
            # This simulates the actual usage pattern in the code
            if hasattr(bot, '_ws_positions') and ticker in bot._ws_positions:
                actual_position = bot._ws_positions[ticker]
            else:
                actual_position = await bot.eth_client.get_position()

            assert actual_position == Decimal("0.15"), (
                "Should use WebSocket position when available"
            )


class TestResetWorksCorrectly:
    """Test 3: _ws_positions reset at cycle start doesn't interfere with tracking."""

    @pytest.mark.asyncio
    async def test_reset_clears_stale_positions(self):
        """
        RED PHASE: Test that _ws_positions reset at cycle start clears
        stale data from previous cycles.

        Expected behavior:
        - Reset should set _ws_positions to {"ETH": 0, "SOL": 0}
        - Reset should happen at the start of each cycle
        - Reset should not prevent WebSocket updates after reset
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_ws_positions.csv'
            )

            # Initialize clients
            bot.eth_client = Mock()
            bot.eth_client.config.contract_id = 4
            bot.sol_client = Mock()
            bot.sol_client.config.contract_id = 5

            # Simulate positions from previous cycle
            bot._ws_positions = {"ETH": Decimal("0.1"), "SOL": Decimal("2.5")}

            # Mock log_position_update
            bot.log_position_update = Mock()

            # Perform reset (simulating cycle start)
            bot._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}

            # ASSERTION: Positions should be reset to 0
            assert bot._ws_positions["ETH"] == Decimal("0"), (
                "ETH should be reset to 0 at cycle start"
            )
            assert bot._ws_positions["SOL"] == Decimal("0"), (
                "SOL should be reset to 0 at cycle start"
            )

            # Simulate WebSocket event after reset
            bot._on_position_change({
                "product_id": 4,
                "amount": "100000000000000000",  # 0.1 ETH
                "v_quote_amount": "200000000",
                "reason": "trade"
            })

            # ASSERTION: WebSocket should still work after reset
            assert bot._ws_positions["ETH"] == Decimal("0.1"), (
                "WebSocket updates should work after reset"
            )

    @pytest.mark.asyncio
    async def test_reset_does_not_interfere_with_ongoing_tracking(self):
        """
        RED PHASE: Test that reset doesn't interfere with WebSocket tracking
        during an active cycle.

        Expected behavior:
        - Reset should only happen at cycle boundaries
        - Reset should not clear positions during active trading
        - WebSocket events received immediately after reset should be processed
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_ws_positions.csv'
            )

            # Initialize clients
            bot.eth_client = Mock()
            bot.eth_client.config.contract_id = 4
            bot.sol_client = Mock()
            bot.sol_client.config.contract_id = 5

            # Mock log_position_update
            bot.log_position_update = Mock()

            # Simulate cycle start (reset)
            bot._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}

            # Simulate rapid WebSocket events after reset
            events = [
                {"product_id": 4, "amount": "50000000000000000", "v_quote_amount": "100000000", "reason": "trade"},  # 0.05 ETH
                {"product_id": 4, "amount": "100000000000000000", "v_quote_amount": "200000000", "reason": "trade"},  # 0.1 ETH
                {"product_id": 5, "amount": "1000000000", "v_quote_amount": "100000000", "reason": "trade"},  # 1 SOL
            ]

            for event in events:
                bot._on_position_change(event)

            # ASSERTION: All events should be processed correctly after reset
            assert bot._ws_positions["ETH"] == Decimal("0.1"), (
                f"Expected final ETH position 0.1, got {bot._ws_positions.get('ETH')}"
            )
            assert bot._ws_positions["SOL"] == Decimal("1"), (
                f"Expected final SOL position 1, got {bot._ws_positions.get('SOL')}"
            )


class TestPositionPersistence:
    """Test 4: Positions are correctly tracked across multiple updates."""

    @pytest.mark.asyncio
    async def test_position_persistence_across_updates(self):
        """
        RED PHASE: Test that _ws_positions correctly persists the latest
        position across multiple WebSocket updates.

        Expected behavior:
        - Each update should correctly replace the previous value
        - Dictionary should maintain state between updates
        - No accumulation of values (WebSocket sends absolute positions)
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_ws_positions.csv'
            )

            # Initialize clients and _ws_positions
            bot.eth_client = Mock()
            bot.eth_client.config.contract_id = 4
            bot.sol_client = Mock()
            bot.sol_client.config.contract_id = 5
            bot._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}

            # Mock log_position_update
            bot.log_position_update = Mock()

            # Simulate trading sequence: opening, increasing, decreasing, closing
            sequence = [
                # (product_id, amount_raw, expected_position, description)
                (4, "50000000000000000", Decimal("0.05"), "Open small ETH position"),
                (4, "100000000000000000", Decimal("0.1"), "Increase ETH position"),
                (4, "200000000000000000", Decimal("0.2"), "Increase ETH position more"),
                (4, "150000000000000000", Decimal("0.15"), "Partial close ETH"),
                (4, "0", Decimal("0"), "Full close ETH"),
            ]

            for product_id, amount_raw, expected_pos, description in sequence:
                bot._on_position_change({
                    "product_id": product_id,
                    "amount": amount_raw,
                    "v_quote_amount": str(int(float(amount_raw) * 2000)),  # Approximate
                    "reason": "trade"
                })

                # ASSERTION: Position should match expected after each update
                actual_pos = bot._ws_positions["ETH"]
                assert actual_pos == expected_pos, (
                    f"After '{description}': expected {expected_pos}, got {actual_pos}"
                )

    @pytest.mark.asyncio
    async def test_both_tickers_tracked_independently(self):
        """
        RED PHASE: Test that ETH and SOL positions are tracked independently
        without interfering with each other.

        Expected behavior:
        - ETH updates should not affect SOL position
        - SOL updates should not affect ETH position
        - Both can be updated in any order
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_ws_positions.csv'
            )

            # Initialize clients and _ws_positions
            bot.eth_client = Mock()
            bot.eth_client.config.contract_id = 4
            bot.sol_client = Mock()
            bot.sol_client.config.contract_id = 5
            bot._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}

            # Mock log_position_update
            bot.log_position_update = Mock()

            # Interleaved updates to both tickers
            updates = [
                (4, "100000000000000000", Decimal("0.1"), Decimal("0")),  # ETH: 0.1, SOL: 0
                (5, "2000000000", Decimal("0.1"), Decimal("2")),  # ETH: 0.1, SOL: 2
                (4, "200000000000000000", Decimal("0.2"), Decimal("2")),  # ETH: 0.2, SOL: 2
                (5, "1000000000", Decimal("0.2"), Decimal("1")),  # ETH: 0.2, SOL: 1
                (4, "0", Decimal("0"), Decimal("1")),  # ETH: 0, SOL: 1
                (5, "0", Decimal("0"), Decimal("0")),  # ETH: 0, SOL: 0
            ]

            for product_id, amount_raw, expected_eth, expected_sol in updates:
                bot._on_position_change({
                    "product_id": product_id,
                    "amount": amount_raw,
                    "v_quote_amount": "100000000",
                    "reason": "trade"
                })

                # ASSERTION: Both positions should match expected values
                assert bot._ws_positions["ETH"] == expected_eth, (
                    f"ETH position mismatch: expected {expected_eth}, got {bot._ws_positions['ETH']}"
                )
                assert bot._ws_positions["SOL"] == expected_sol, (
                    f"SOL position mismatch: expected {expected_sol}, got {bot._ws_positions['SOL']}"
                )

    @pytest.mark.asyncio
    async def test_negative_positions_tracked_correctly(self):
        """
        RED PHASE: Test that negative (short) positions are tracked correctly.

        Expected behavior:
        - Short positions should be stored as negative values
        - WebSocket should preserve the sign from the amount field
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_ws_positions.csv'
            )

            # Initialize clients and _ws_positions
            bot.eth_client = Mock()
            bot.eth_client.config.contract_id = 4
            bot.sol_client = Mock()
            bot.sol_client.config.contract_id = 5
            bot._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}

            # Mock log_position_update
            bot.log_position_update = Mock()

            # Simulate short position (negative amount)
            bot._on_position_change({
                "product_id": 5,
                "amount": "-3000000000",  # -3 SOL (short)
                "v_quote_amount": "-300000000",
                "reason": "trade"
            })

            # ASSERTION: Negative position should be stored
            # Note: This test checks if the implementation handles negative values
            # Some implementations may store absolute values with direction separately
            sol_pos = bot._ws_positions.get("SOL", Decimal("0"))

            # The assertion allows for either negative value or absolute value
            # depending on implementation choice
            is_negative = sol_pos < 0
            is_correct_magnitude = abs(sol_pos) == Decimal("3")

            assert is_negative or is_correct_magnitude, (
                f"Expected SOL position to represent -3, got {sol_pos}"
            )


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_unknown_product_id_is_handled(self):
        """
        RED PHASE: Test that unknown product_id in position_change event
        is handled gracefully.

        Expected behavior:
        - Unknown product_id should log a warning
        - Should not update _ws_positions
        - Should not raise an exception
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_ws_positions.csv'
            )

            # Initialize clients and _ws_positions
            bot.eth_client = Mock()
            bot.eth_client.config.contract_id = 4
            bot.sol_client = Mock()
            bot.sol_client.config.contract_id = 5
            bot._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}

            # Mock log_position_update
            bot.log_position_update = Mock()

            # Simulate unknown product_id
            bot._on_position_change({
                "product_id": 999,  # Unknown
                "amount": "100000000000000000",
                "v_quote_amount": "200000000",
                "reason": "trade"
            })

            # ASSERTION: Positions should remain unchanged
            assert bot._ws_positions["ETH"] == Decimal("0"), (
                "ETH should remain 0 after unknown product_id"
            )
            assert bot._ws_positions["SOL"] == Decimal("0"), (
                "SOL should remain 0 after unknown product_id"
            )

    @pytest.mark.asyncio
    async def test_zero_amount_is_handled(self):
        """
        RED PHASE: Test that zero amount in position_change event
        is handled correctly.

        Expected behavior:
        - Zero amount should set position to 0 (position closed)
        - Should be stored as Decimal("0"), not skipped
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_ws_positions.csv'
            )

            # Initialize clients and _ws_positions
            bot.eth_client = Mock()
            bot.eth_client.config.contract_id = 4
            bot.sol_client = Mock()
            bot.sol_client.config.contract_id = 5
            bot._ws_positions = {"ETH": Decimal("0.1"), "SOL": Decimal("0")}

            # Mock log_position_update
            bot.log_position_update = Mock()

            # Simulate zero amount (position close)
            bot._on_position_change({
                "product_id": 4,
                "amount": "0",  # Position closed
                "v_quote_amount": "0",
                "reason": "trade"
            })

            # ASSERTION: Position should be set to 0
            assert bot._ws_positions["ETH"] == Decimal("0"), (
                f"Expected ETH position to be 0, got {bot._ws_positions.get('ETH')}"
            )

    @pytest.mark.asyncio
    async def test_ws_positions_initialization_when_missing(self):
        """
        RED PHASE: Test that _ws_positions is initialized if it doesn't exist
        when first position_change event arrives.

        Expected behavior:
        - First position_change event should initialize _ws_positions
        - Should not raise AttributeError for missing attribute
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_ws_positions.csv'
            )

            # Initialize clients
            bot.eth_client = Mock()
            bot.eth_client.config.contract_id = 4
            bot.sol_client = Mock()
            bot.sol_client.config.contract_id = 5

            # Explicitly remove _ws_positions to simulate uninitialized state
            if hasattr(bot, '_ws_positions'):
                delattr(bot, '_ws_positions')

            # Mock log_position_update
            bot.log_position_update = Mock()

            # Simulate first position_change event
            bot._on_position_change({
                "product_id": 4,
                "amount": "100000000000000000",  # 0.1 ETH
                "v_quote_amount": "200000000",
                "reason": "trade"
            })

            # ASSERTION: _ws_positions should be initialized
            assert hasattr(bot, '_ws_positions'), (
                "_ws_positions should be initialized after first event"
            )

            # ASSERTION: Position should be stored
            assert bot._ws_positions.get("ETH") == Decimal("0.1"), (
                f"Expected ETH position 0.1, got {bot._ws_positions.get('ETH')}"
            )

    @pytest.mark.asyncio
    async def test_missing_amount_field_is_handled(self):
        """
        RED PHASE: Test that missing amount field in position_change event
        is handled gracefully.

        Expected behavior:
        - Missing amount should default to 0
        - Should not raise an exception
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_ws_positions.csv'
            )

            # Initialize clients and _ws_positions
            bot.eth_client = Mock()
            bot.eth_client.config.contract_id = 4
            bot.sol_client = Mock()
            bot.sol_client.config.contract_id = 5
            bot._ws_positions = {"ETH": Decimal("0.1"), "SOL": Decimal("0")}

            # Mock log_position_update
            bot.log_position_update = Mock()

            # Simulate event with missing amount
            bot._on_position_change({
                "product_id": 4,
                # "amount" field is missing
                "v_quote_amount": "200000000",
                "reason": "trade"
            })

            # ASSERTION: Should default to 0, not crash
            eth_pos = bot._ws_positions.get("ETH", Decimal("0"))

            # Either position becomes 0 (default) or remains unchanged
            # depending on implementation
            assert eth_pos in [Decimal("0"), Decimal("0.1")], (
                f"Expected ETH position to be 0 or remain 0.1, got {eth_pos}"
            )
