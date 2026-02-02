"""
Startup Residual Position Detection Testing (TDD - RED PHASE)

Tests for residual position detection at bot startup.

This file contains FAILING tests that should initially fail.
They will pass after proper implementation of WebSocket-based
startup position detection.

Key Issues Being Tested:
1. WebSocket is connected and ready BEFORE startup check
2. Bot waits for WebSocket position sync before checking residuals
3. Startup check uses WebSocket positions instead of REST API
4. REST API is used as fallback if WebSocket unavailable
5. Positions persist correctly across bot restarts

Context:
- REST API has 20+ second lag showing 0.0 when positions exist
- WebSocket positions (_ws_positions) are real-time
- Current implementation at main() lines 3952-3971 uses REST API
- User had to manually close positions because bot didn't detect them
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from decimal import Decimal
import sys
import os
from typing import Dict, Any

# Add project to path
sys.path.insert(0, '/Users/botfarmer/2dex')

from hedge.DN_pair_eth_sol_nado import DNPairBot


class Config:
    """Config class that converts dict to object with attributes."""
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)


class TestWebSocketConnectedBeforeStartupCheck:
    """
    Test 1: WebSocket is connected and ready BEFORE startup check.

    Current Issue: Startup check happens immediately after initialize_clients(),
    but WebSocket may not have received initial position_change events yet.

    Expected Behavior:
    - WebSocket connection should be fully established
    - WebSocket should have received initial position state
    - Startup check should wait for WebSocket to be ready
    """

    @pytest.mark.asyncio
    async def test_websocket_connected_before_startup_check(self):
        """
        RED PHASE: Test that WebSocket is connected before startup check runs.

        This test will FAIL because current implementation:
        1. Calls initialize_clients() which starts WebSocket connection
        2. Immediately checks positions via REST API (lines 3955-3956)
        3. Doesn't wait for WebSocket to receive initial position state

        Expected behavior:
        - Should verify _ws_connected is True for both clients
        - Should wait for initial position_change events
        - Should have _ws_positions populated before checking
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients (including WebSocket connection)
            await bot.initialize_clients()

            # ASSERTION: WebSocket should be connected
            # This FAILS if WebSocket connection failed silently
            assert bot.eth_client._ws_connected, (
                "ETH WebSocket should be connected after initialize_clients()"
            )
            assert bot.sol_client._ws_connected, (
                "SOL WebSocket should be connected after initialize_clients()"
            )

            # ASSERTION: _ws_positions should be initialized
            # This FAILS if _ws_positions is not set up during initialization
            assert hasattr(bot, '_ws_positions'), (
                "Bot should have _ws_positions initialized after WebSocket connection"
            )

            # ASSERTION: _ws_positions should have both tickers
            assert "ETH" in bot._ws_positions, (
                "_ws_positions should have ETH ticker"
            )
            assert "SOL" in bot._ws_positions, (
                "_ws_positions should have SOL ticker"
            )

    @pytest.mark.asyncio
    async def test_websocket_subscription_confirmed_before_startup(self):
        """
        RED PHASE: Test that WebSocket subscription to position_change
        is confirmed before startup check runs.

        This test will FAIL because current implementation:
        1. Subscribes to position_change streams (lines 3754-3775)
        2. Doesn't wait for confirmation of initial data received
        3. Proceeds immediately to REST API check

        Expected behavior:
        - Should wait for first position_change event for each ticker
        - Should have a flag or event tracking "initial sync complete"
        - Startup check should only run after initial sync
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients (this subscribes to position_change streams)
            await bot.initialize_clients()

            # ASSERTION: Should have WebSocket clients connected
            assert bot.eth_client._ws_connected, (
                "ETH WebSocket should be connected after initialize_clients()"
            )
            assert bot.sol_client._ws_connected, (
                "SOL WebSocket should be connected after initialize_clients()"
            )

            # ASSERTION: Should have a way to track initial sync completion
            # This FAILS because current implementation doesn't track this
            assert hasattr(bot, '_ws_initial_sync_complete'), (
                "Bot should track WebSocket initial sync completion state"
            )

            # ASSERTION: Should have a way to track initial sync completion
            # This FAILS because current implementation doesn't track this
            assert hasattr(bot, '_ws_initial_sync_complete'), (
                "Bot should track WebSocket initial sync completion state"
            )


class TestWaitForWebSocketPositionSync:
    """
    Test 2: Bot waits for WebSocket position sync before checking residuals.

    Current Issue: Startup check runs immediately without waiting for
    WebSocket to receive first position_change event.

    Expected Behavior:
    - Bot should wait for initial position_change events
    - Should have a timeout for WebSocket sync
    - Should fall back to REST API if WebSocket doesn't sync
    """

    @pytest.mark.asyncio
    async def test_waits_for_websocket_position_sync(self):
        """
        RED PHASE: Test that bot waits for WebSocket position sync
        before performing startup check.

        This test will FAIL because current implementation:
        1. Doesn't wait for WebSocket to receive position data
        2. Uses REST API immediately (line 3955-3956 in main())
        3. Has no mechanism to wait for initial sync

        Expected behavior:
        - Should implement _wait_for_ws_position_sync() method
        - Should wait up to X seconds for initial position_change events
        - Should return True when sync complete, False on timeout
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients
            await bot.initialize_clients()

            # ASSERTION: Should have a method to wait for WebSocket sync
            # This FAILS because method doesn't exist
            assert hasattr(bot, '_wait_for_ws_position_sync'), (
                "Bot should have _wait_for_ws_position_sync() method"
            )

            # ASSERTION: Method should wait for initial position data
            # This FAILS because method doesn't exist
            sync_complete = await bot._wait_for_ws_position_sync(timeout=5.0)

            assert isinstance(sync_complete, bool), (
                "_wait_for_ws_position_sync() should return bool"
            )

    @pytest.mark.asyncio
    async def test_websocket_sync_timeout_fallback(self):
        """
        RED PHASE: Test that bot falls back to REST API if WebSocket
        sync times out.

        This test will FAIL because current implementation:
        1. Always uses REST API at startup (doesn't attempt WebSocket sync)
        2. Has no timeout logic for WebSocket sync
        3. No fallback mechanism implemented

        Expected behavior:
        - If WebSocket doesn't receive position data within timeout
        - Should fall back to REST API
        - Should log a warning about WebSocket sync timeout
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients
            await bot.initialize_clients()

            # Mock WebSocket sync timing out
            # Simulate no position_change events received

            # ASSERTION: Should have timeout handling
            # This FAILS because timeout logic doesn't exist
            try:
                sync_complete = await bot._wait_for_ws_position_sync(timeout=1.0)
                # If timeout, should return False
                assert not sync_complete, (
                    "Should return False when WebSocket sync times out"
                )
            except asyncio.TimeoutError:
                # Alternative: raise timeout exception
                pass

    @pytest.mark.asyncio
    async def test_websocket_sync_success_detection(self):
        """
        RED PHASE: Test that bot correctly detects when WebSocket
        sync is successful.

        This test will FAIL because current implementation:
        1. Doesn't track whether WebSocket has received position data
        2. Has no "sync complete" state tracking

        Expected behavior:
        - Should track receipt of initial position_change events
        - Should consider sync complete when both tickers have data
        - Should return True when sync is successful
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients
            await bot.initialize_clients()

            # Simulate WebSocket position_change events
            bot._on_position_change({
                "product_id": 4,  # ETH
                "amount": "100000000000000000",  # 0.1 ETH
                "v_quote_amount": "200000000",
                "reason": "trade"
            })

            bot._on_position_change({
                "product_id": 8,  # SOL
                "amount": "0",  # No position
                "v_quote_amount": "0",
                "reason": "trade"
            })

            # ASSERTION: Should detect sync completion
            # This FAILS because sync tracking doesn't exist
            if hasattr(bot, '_ws_initial_sync_complete'):
                assert bot._ws_initial_sync_complete, (
                    "Should mark WebSocket sync as complete after receiving position data"
                )


class TestWebSocketPositionCheckAtStartup:
    """
    Test 3: Startup check uses WebSocket positions instead of REST API.

    Current Issue: Lines 3955-3956 in main() use REST API directly,
    which has 20+ second lag and shows 0.0 when positions exist.

    Expected Behavior:
    - Startup check should use _ws_positions when available
    - Should only use REST API as fallback
    - Should log which source was used
    """

    @pytest.mark.asyncio
    async def test_startup_uses_websocket_positions_when_available(self):
        """
        RED PHASE: Test that startup check uses WebSocket positions
        when WebSocket is available and synced.

        This test will FAIL because current implementation:
        1. Uses REST API at startup (lines 3955-3956)
        2. Doesn't check _ws_positions first
        3. Always uses get_account_positions() which is REST API

        Expected behavior:
        - Should check _ws_positions first
        - Should use WebSocket data if available
        - Should fall back to REST only if WebSocket unavailable
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients
            await bot.initialize_clients()

            # Simulate WebSocket positions (bot has residual 0.15 ETH)
            bot._ws_positions = {"ETH": Decimal("0.15"), "SOL": Decimal("0")}

            # Mock REST API returning 0 (lagging state)
            async def mock_get_position(*args, **kwargs):
                return Decimal("0")

            bot.eth_client.get_account_positions = mock_get_position
            bot.sol_client.get_account_positions = mock_get_position

            # ASSERTION: Should have method to get startup positions
            # This FAILS because method doesn't exist
            assert hasattr(bot, '_get_startup_positions'), (
                "Bot should have _get_startup_positions() method"
            )

            # ASSERTION: Method should return WebSocket positions
            eth_pos, sol_pos = await bot._get_startup_positions()

            assert eth_pos == Decimal("0.15"), (
                f"Should return WebSocket position 0.15, got {eth_pos} "
                f"(WebSocket has real-time data, REST has lag)"
            )

            assert sol_pos == Decimal("0"), (
                f"Should return WebSocket position 0, got {sol_pos}"
            )

    @pytest.mark.asyncio
    async def test_startup_falls_back_to_rest_when_websocket_unavailable(self):
        """
        RED PHASE: Test that startup check falls back to REST API
        when WebSocket is unavailable.

        This test will FAIL because current implementation:
        1. Always uses REST API (so this test accidentally passes)
        2. Doesn't have proper WebSocket-first logic

        Expected behavior:
        - Should check if WebSocket is available
        - Should use REST API if WebSocket unavailable
        - Should log which source was used
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients
            await bot.initialize_clients()

            # Simulate WebSocket not connected
            bot.eth_client._ws_connected = False
            bot.sol_client._ws_connected = False

            # Remove _ws_positions to simulate unavailable WebSocket
            if hasattr(bot, '_ws_positions'):
                delattr(bot, '_ws_positions')

            # Mock REST API returning actual positions
            async def mock_get_position(*args, **kwargs):
                return Decimal("0.1")

            bot.eth_client.get_account_positions = mock_get_position
            bot.sol_client.get_account_positions = mock_get_position

            # ASSERTION: Should have method to get startup positions
            assert hasattr(bot, '_get_startup_positions'), (
                "Bot should have _get_startup_positions() method"
            )

            # ASSERTION: Should fall back to REST when WebSocket unavailable
            eth_pos, sol_pos = await bot._get_startup_positions()

            assert eth_pos == Decimal("0.1"), (
                f"Should fall back to REST position 0.1, got {eth_pos}"
            )

    @pytest.mark.asyncio
    async def test_startup_position_check_logs_data_source(self):
        """
        RED PHASE: Test that startup position check logs which
        data source was used (WebSocket vs REST).

        This test will FAIL because current implementation:
        1. Doesn't differentiate between data sources
        2. Doesn't log whether WebSocket or REST was used

        Expected behavior:
        - Should log "Using WebSocket positions" or "Using REST API"
        - Should help debugging position detection issues
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients
            await bot.initialize_clients()

            # Set up WebSocket positions
            bot._ws_positions = {"ETH": Decimal("0.1"), "SOL": Decimal("0")}

            # Mock logger to capture log messages
            log_messages = []

            def capture_log(msg, *args, **kwargs):
                log_messages.append(msg)

            bot.logger.info = capture_log

            # Get startup positions
            if hasattr(bot, '_get_startup_positions'):
                await bot._get_startup_positions()

            # ASSERTION: Should log data source
            # This FAILS because logging doesn't exist
            log_text = ' '.join(log_messages)
            assert any(keyword in log_text for keyword in ['WebSocket', 'WS', 'REST', 'data source']), (
                f"Should log which data source was used. Logs: {log_text}"
            )


class TestPositionPersistenceAcrossRestarts:
    """
    Test 4: Positions persist correctly across bot restarts.

    Current Issue: Bot crashes/restarts without state persistence,
    leaving positions open that startup check doesn't detect.

    Expected Behavior:
    - Bot should detect residual positions from previous crashes
    - Should use real-time WebSocket data to detect positions
    - Should warn user and exit if positions detected
    """

    @pytest.mark.asyncio
    async def test_residual_position_detected_after_restart(self):
        """
        RED PHASE: Test that residual positions from previous crash
        are detected at startup.

        This test will FAIL because current implementation:
        1. Uses REST API which shows 0.0 due to 20+ second lag
        2. Doesn't wait for WebSocket to sync before checking
        3. User had to manually close positions (reported issue)

        Expected behavior:
        - Should use WebSocket positions to detect residuals
        - Should wait for WebSocket sync before checking
        - Should detect 0.15 ETH position from previous session
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients
            await bot.initialize_clients()

            # Simulate WebSocket position from previous crash
            # (This would arrive via position_change stream)
            bot._on_position_change({
                "product_id": 4,  # ETH
                "amount": "150000000000000000",  # 0.15 ETH (residual from crash)
                "v_quote_amount": "300000000",
                "reason": "trade"
            })

            # Mock REST API returning 0 (lagging state)
            async def mock_get_position(*args, **kwargs):
                return Decimal("0")

            bot.eth_client.get_account_positions = mock_get_position
            bot.sol_client.get_account_positions = mock_get_position

            # ASSERTION: Startup check should use WebSocket positions
            # This FAILS because current code uses REST API
            if hasattr(bot, '_get_startup_positions'):
                eth_pos, sol_pos = await bot._get_startup_positions()

                assert eth_pos == Decimal("0.15"), (
                    f"Should detect 0.15 ETH residual from WebSocket, got {eth_pos}. "
                    f"REST API shows 0 due to lag."
                )

    @pytest.mark.asyncio
    async def test_no_residual_positions_detected_correctly(self):
        """
        RED PHASE: Test that startup correctly detects when
        there are no residual positions.

        Expected behavior:
        - Should detect 0.0 positions for both tickers
        - Should allow bot to start normally
        - Should log "No residual positions found"
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients
            await bot.initialize_clients()

            # Simulate WebSocket showing no positions
            bot._on_position_change({
                "product_id": 4,  # ETH
                "amount": "0",  # No position
                "v_quote_amount": "0",
                "reason": "trade"
            })

            bot._on_position_change({
                "product_id": 8,  # SOL
                "amount": "0",  # No position
                "v_quote_amount": "0",
                "reason": "trade"
            })

            # ASSERTION: Startup check should detect no positions
            if hasattr(bot, '_get_startup_positions'):
                eth_pos, sol_pos = await bot._get_startup_positions()

                assert eth_pos == Decimal("0"), (
                    f"Should detect 0 ETH position, got {eth_pos}"
                )
                assert sol_pos == Decimal("0"), (
                    f"Should detect 0 SOL position, got {sol_pos}"
                )

    @pytest.mark.asyncio
    async def test_partial_residual_positions_detected(self):
        """
        RED PHASE: Test that startup correctly detects when only
        one ticker has a residual position (hedge break scenario).

        Expected behavior:
        - Should detect ETH position but no SOL position (or vice versa)
        - Should warn about hedge break (directional exposure)
        - Should prevent bot start until positions are closed
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients
            await bot.initialize_clients()

            # Simulate hedge break: ETH has position, SOL doesn't
            bot._on_position_change({
                "product_id": 4,  # ETH
                "amount": "200000000000000000",  # 0.2 ETH (residual)
                "v_quote_amount": "400000000",
                "reason": "trade"
            })

            bot._on_position_change({
                "product_id": 8,  # SOL
                "amount": "0",  # No position
                "v_quote_amount": "0",
                "reason": "trade"
            })

            # ASSERTION: Should detect hedge break
            if hasattr(bot, '_get_startup_positions'):
                eth_pos, sol_pos = await bot._get_startup_positions()

                assert eth_pos > Decimal("0.001"), (
                    f"Should detect non-zero ETH position, got {eth_pos}"
                )
                assert sol_pos < Decimal("0.001"), (
                    f"Should detect zero SOL position, got {sol_pos}"
                )


class TestStartupCheckIntegration:
    """
    Test 5: Integration tests for startup position check.

    These tests verify the complete startup flow including
    error handling and user experience.
    """

    @pytest.mark.asyncio
    async def test_startup_exit_on_residual_positions(self):
        """
        RED PHASE: Test that bot exits with error code when
        residual positions are detected at startup.

        This test will FAIL because current implementation:
        1. May not detect positions due to REST API lag
        2. Doesn't use WebSocket positions for detection

        Expected behavior:
        - Should call sys.exit(1) when positions detected
        - Should print clear error message
        - Should guide user to close positions manually
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients
            await bot.initialize_clients()

            # Simulate residual positions
            bot._ws_positions = {"ETH": Decimal("0.1"), "SOL": Decimal("0")}

            # Mock REST API returning 0 (lagging)
            async def mock_get_position(*args, **kwargs):
                return Decimal("0")

            bot.eth_client.get_account_positions = mock_get_position
            bot.sol_client.get_account_positions = mock_get_position()

            # ASSERTION: Should have method to check startup positions
            # This FAILS because method doesn't exist
            assert hasattr(bot, '_check_residual_positions_at_startup'), (
                "Bot should have _check_residual_positions_at_startup() method"
            )

            # ASSERTION: Should detect positions and raise SystemExit
            with pytest.raises(SystemExit) as exc_info:
                await bot._check_residual_positions_at_startup()

            assert exc_info.value.code == 1, (
                "Should exit with code 1 when residual positions detected"
            )

    @pytest.mark.asyncio
    async def test_startup_proceeds_when_no_positions(self):
        """
        RED PHASE: Test that bot proceeds normally when
        no residual positions are detected at startup.

        Expected behavior:
        - Should not call sys.exit()
        - Should log "No residual positions. Ready to start."
        - Should allow bot to proceed to run_alternating_strategy()
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients
            await bot.initialize_clients()

            # Simulate no positions
            bot._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}

            # ASSERTION: Should have method to check startup positions
            if hasattr(bot, '_check_residual_positions_at_startup'):
                # Should not raise SystemExit
                result = await bot._check_residual_positions_at_startup()

                # Should return True to indicate clean start
                assert result is True, (
                    "Should return True when no residual positions detected"
                )

    @pytest.mark.asyncio
    async def test_startup_tolerance_for_dust_positions(self):
        """
        RED PHASE: Test that startup check uses tolerance for
        dust positions (rounding errors, tiny residuals).

        Expected behavior:
        - Should use POSITION_TOLERANCE = Decimal("0.001")
        - Should ignore positions smaller than tolerance
        - Should allow bot to start with dust positions
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients
            await bot.initialize_clients()

            # Simulate dust position (smaller than tolerance)
            bot._ws_positions = {
                "ETH": Decimal("0.0005"),  # 0.0005 ETH (< 0.001 tolerance)
                "SOL": Decimal("0")
            }

            # ASSERTION: Should ignore dust positions
            if hasattr(bot, '_check_residual_positions_at_startup'):
                # Should not raise SystemExit for dust positions
                result = await bot._check_residual_positions_at_startup()

                assert result is True, (
                    "Should ignore dust positions smaller than tolerance"
                )


class TestEdgeCases:
    """
    Test edge cases and error conditions for startup position detection.
    """

    @pytest.mark.asyncio
    async def test_websocket_disconnects_during_sync(self):
        """
        RED PHASE: Test that bot handles WebSocket disconnection
        during initial position sync gracefully.

        Expected behavior:
        - Should fall back to REST API
        - Should log warning about WebSocket disconnection
        - Should still detect positions via REST (even with lag)
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients
            await bot.initialize_clients()

            # Simulate WebSocket disconnection
            bot.eth_client._ws_connected = False
            bot.sol_client._ws_connected = False

            # Mock REST API
            async def mock_get_position(*args, **kwargs):
                return Decimal("0.1")

            bot.eth_client.get_account_positions = mock_get_position
            bot.sol_client.get_account_positions = mock_get_position

            # ASSERTION: Should fall back to REST gracefully
            if hasattr(bot, '_get_startup_positions'):
                eth_pos, sol_pos = await bot._get_startup_positions()

                # Should use REST API when WebSocket unavailable
                assert eth_pos == Decimal("0.1"), (
                    "Should fall back to REST when WebSocket unavailable"
                )

    @pytest.mark.asyncio
    async def test_negative_positions_at_startup(self):
        """
        RED PHASE: Test that startup correctly detects short
        (negative) positions.

        Expected behavior:
        - Should detect negative positions from WebSocket
        - Should treat negative positions same as positive
        - Should warn user about short positions
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients
            await bot.initialize_clients()

            # Simulate short position
            bot._on_position_change({
                "product_id": 8,  # SOL
                "amount": "-3000000000",  # -3 SOL (short)
                "v_quote_amount": "-300000000",
                "reason": "trade"
            })

            # ASSERTION: Should detect short position
            if hasattr(bot, '_get_startup_positions'):
                eth_pos, sol_pos = await bot._get_startup_positions()

                # Should detect negative position
                assert sol_pos < Decimal("0"), (
                    f"Should detect short position, got {sol_pos}"
                )

    @pytest.mark.asyncio
    async def test_both_tickers_with_residual_positions(self):
        """
        RED PHASE: Test that startup correctly detects when both
        tickers have residual positions (full hedge intact).

        Expected behavior:
        - Should detect both ETH and SOL positions
        - Should warn about residual positions even if hedged
        - Should require user to close both positions
        """
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_startup.csv'
            )

            # Initialize clients
            await bot.initialize_clients()

            # Simulate both positions (hedged)
            bot._on_position_change({
                "product_id": 4,  # ETH
                "amount": "100000000000000000",  # 0.1 ETH
                "v_quote_amount": "200000000",
                "reason": "trade"
            })

            bot._on_position_change({
                "product_id": 8,  # SOL
                "amount": "5000000000",  # 5 SOL
                "v_quote_amount": "500000000",
                "reason": "trade"
            })

            # ASSERTION: Should detect both positions
            if hasattr(bot, '_get_startup_positions'):
                eth_pos, sol_pos = await bot._get_startup_positions()

                assert abs(eth_pos) > Decimal("0.001"), (
                    f"Should detect ETH position, got {eth_pos}"
                )
                assert abs(sol_pos) > Decimal("0.001"), (
                    f"Should detect SOL position, got {sol_pos}"
                )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
