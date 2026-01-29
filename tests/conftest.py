"""
Shared pytest configuration and fixtures for DN Pair Bot tests.

This file contains mock fixtures for all Nado SDK interactions following
the TDD approach specified in the Nado DN Pair V4 Migration plan.
"""

import pytest
import os
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock
from pathlib import Path


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up required environment variables for testing."""
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")


@pytest.fixture
def mock_nado_client():
    """Mock NadoClient with REST API responses.

    This fixture provides a comprehensive mock for testing NadoClient
    interactions without requiring actual SDK connections.

    FROM_PHASE0: Update contract_id and tick_size values based on
    actual research findings from Phase 0.
    """
    client = Mock()
    client.context = Mock()
    client.context.engine_client = Mock()
    client.context.indexer_client = Mock()
    client.market = Mock()

    # Mock contract attributes (from Phase 0 research)
    # TODO: Update contract_id and tick_size after Phase 0 research
    client.get_contract_attributes = Mock(return_value={
        'contract_id': 4,  # FROM_PHASE0: Update with actual ETH product ID
        'tick_size': Decimal('0.01')  # FROM_PHASE0: Update with actual tick size
    })

    # Mock BBO prices
    client.fetch_bbo_prices = Mock(return_value=(Decimal('3000.00'), Decimal('3000.50')))

    # Mock positions
    client.get_account_positions = Mock(return_value=Decimal('0'))

    return client


@pytest.fixture
def mock_websocket_server():
    """Mock WebSocket server for testing (if WebSocket available).

    This fixture provides a mock WebSocket server for testing
    WebSocket-based order updates and message handling.

    CONDITIONAL: Only used if Phase 0 research confirms WebSocket
    availability in the Nado SDK.
    """
    import asyncio
    from unittest.mock import MagicMock

    ws = MagicMock()
    ws.connect = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock()
    ws.connected = True

    return ws


@pytest.fixture
def sample_eth_price():
    """Sample ETH price for testing."""
    return Decimal("3000.00")


@pytest.fixture
def sample_sol_price():
    """Sample SOL price for testing."""
    return Decimal("150.00")


@pytest.fixture
def tmp_csv_path(tmp_path):
    """Create a temporary CSV file path for testing."""
    return tmp_path / "test_trades.csv"


# Mock helpers for tests
def mock_order_result(order_id="test_order_123", side="buy", size=Decimal("0.01"), price=Decimal("3000")):
    """Create a mock OrderResult for testing."""
    from exchanges.base import OrderResult
    return OrderResult(
        success=True,
        order_id=order_id,
        side=side,
        size=size,
        price=price,  # Initial price
        status="OPEN"
    )


def mock_order_info(order_id="test_order_123", side="buy", size=Decimal("0.01"), price=Decimal("3000.5")):
    """Create a mock OrderInfo for testing."""
    from exchanges.base import OrderInfo
    return OrderInfo(
        order_id=order_id,
        side=side,
        size=size,
        price=price,  # Actual fill price (may differ from OrderResult.price)
        status="FILLED",
        filled_size=size
    )


@pytest.fixture
def mock_order_result_fixture():
    """Fixture for mock OrderResult."""
    return mock_order_result


@pytest.fixture
def mock_order_info_fixture():
    """Fixture for mock OrderInfo."""
    return mock_order_info
