from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

from hedge.DN_pair_eth_sol_nado import DNPairBot
from hedge.exchanges.nado import OrderResult


def make_bot() -> DNPairBot:
    with patch.dict(
        "os.environ",
        {
            "NADO_PRIVATE_KEY": "0x" + "1" * 64,
            "NADO_MODE": "MAINNET",
            "NADO_SUBACCOUNT_NAME": "test",
        },
    ):
        bot = DNPairBot(
            target_notional=Decimal("100"),
            csv_path="/tmp/test_build_retry_handoff.csv",
        )

    bot._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}
    bot._wait_for_optimal_entry = AsyncMock(
        return_value={
            "waited_seconds": 0.1,
            "entry_spread_bps": Decimal("30"),
            "threshold_bps": Decimal("25"),
            "reason": "signal",
        }
    )
    bot._check_spread_profitability = Mock(
        return_value=(
            True,
            {
                "eth_spread_bps": Decimal("1"),
                "sol_spread_bps": Decimal("1"),
                "reason": "ok",
            },
        )
    )
    bot._check_momentum_filter = Mock(return_value=(True, "ok"))
    bot._maybe_place_tp_orders = AsyncMock()
    bot._log_spread_analysis = Mock()
    bot._log_skipped_cycle = Mock()
    bot.handle_emergency_unwind = AsyncMock(return_value=False)

    bot.eth_client = Mock()
    bot.eth_client.config = Mock(contract_id=4)
    bot.eth_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal("2000"), Decimal("2001")))
    bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal("0"))

    bot.sol_client = Mock()
    bot.sol_client.config = Mock(contract_id=8)
    bot.sol_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal("100"), Decimal("101")))
    bot.sol_client.get_account_positions = AsyncMock(return_value=Decimal("0"))

    return bot


def make_result(
    *,
    success: bool,
    filled_size: str,
    price: Optional[str],
    status: str,
    order_id: str,
    error_message: Optional[str] = None,
):
    return OrderResult(
        success=success,
        filled_size=Decimal(filled_size),
        price=Decimal(price) if price is not None else None,
        status=status,
        order_id=order_id,
        error_message=error_message,
    )


@pytest.mark.asyncio
async def test_build_succeeds_when_last_retry_reaches_targets_without_rest_ratio_fallback():
    bot = make_bot()
    bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal("0.05"))
    bot.sol_client.get_account_positions = AsyncMock(return_value=Decimal("-1.0"))

    async def place_orders(eth_direction, sol_direction):
        bot._last_order_target_quantities = {
            "ETH": Decimal("0.05"),
            "SOL": Decimal("1.0"),
        }
        bot.entry_quantities["SOL"] += Decimal("1.0")
        bot.entry_prices["SOL"] = Decimal("100")
        return (
            make_result(
                success=False,
                filled_size="0",
                price=None,
                status="TIMEOUT",
                order_id="eth-open",
                error_message="timeout",
            ),
            make_result(
                success=True,
                filled_size="1.0",
                price="100",
                status="FILLED",
                order_id="sol-open",
            ),
        )

    retry_results = [
        make_result(
            success=False,
            filled_size="0",
            price=None,
            status="TIMEOUT",
            order_id="eth-r1",
            error_message="timeout",
        ),
        make_result(
            success=False,
            filled_size="0",
            price=None,
            status="TIMEOUT",
            order_id="eth-r2",
            error_message="timeout",
        ),
        make_result(
            success=True,
            filled_size="0.05",
            price="2000",
            status="FILLED",
            order_id="eth-r3",
        ),
    ]

    bot.place_simultaneous_orders = AsyncMock(side_effect=place_orders)
    bot._retry_side_order = AsyncMock(side_effect=retry_results)

    with patch("hedge.DN_pair_eth_sol_nado.asyncio.sleep", new=AsyncMock()):
        result = await bot.execute_build_cycle(eth_direction="buy", sol_direction="sell")

    assert result is True
    assert bot.handle_emergency_unwind.await_count == 0
    bot._maybe_place_tp_orders.assert_awaited_once()
    assert bot.entry_quantities["ETH"] == Decimal("0.05")
    assert bot.entry_quantities["SOL"] == Decimal("1.0")


@pytest.mark.asyncio
async def test_build_does_not_use_rest_raw_qty_ratio_as_success_signal():
    bot = make_bot()
    bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal("1"))
    bot.sol_client.get_account_positions = AsyncMock(return_value=Decimal("1"))

    async def place_orders(eth_direction, sol_direction):
        bot._last_order_target_quantities = {
            "ETH": Decimal("0.05"),
            "SOL": Decimal("1.0"),
        }
        bot.entry_quantities["ETH"] += Decimal("0.01")
        bot.entry_quantities["SOL"] += Decimal("0.01")
        bot.entry_prices["ETH"] = Decimal("2000")
        bot.entry_prices["SOL"] = Decimal("100")
        return (
            make_result(
                success=True,
                filled_size="0.01",
                price="2000",
                status="PARTIALLY_FILLED",
                order_id="eth-open",
            ),
            make_result(
                success=True,
                filled_size="0.01",
                price="100",
                status="PARTIALLY_FILLED",
                order_id="sol-open",
            ),
        )

    no_fill_retry = make_result(
        success=False,
        filled_size="0",
        price=None,
        status="TIMEOUT",
        order_id="retry-none",
        error_message="timeout",
    )

    bot.place_simultaneous_orders = AsyncMock(side_effect=place_orders)
    bot._retry_side_order = AsyncMock(side_effect=[no_fill_retry] * 6)

    with patch("hedge.DN_pair_eth_sol_nado.asyncio.sleep", new=AsyncMock()):
        result = await bot.execute_build_cycle(eth_direction="buy", sol_direction="sell")

    assert result is False
    bot.handle_emergency_unwind.assert_awaited_once()
