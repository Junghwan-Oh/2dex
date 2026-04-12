import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from hedge.DN_pair_eth_sol_nado import DNPairBot


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
            csv_path="/tmp/test_ws_positions.csv",
        )
    bot.eth_client = Mock()
    bot.eth_client.config.contract_id = 4
    bot.sol_client = Mock()
    bot.sol_client.config.contract_id = 8
    bot.log_position_update = Mock()
    return bot


def make_fill(product_id: int, qty: str, *, is_bid: bool, order_digest: str) -> dict:
    return {
        "product_id": product_id,
        "filled_qty": qty,
        "remaining_qty": "0",
        "timestamp": 1234567890,
        "is_bid": is_bid,
        "order_digest": order_digest,
    }


class TestPositionChangeDiagnostics:
    def test_position_change_records_raw_signal_but_not_ws_positions(self):
        bot = make_bot()
        bot._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}

        bot._on_position_change(
            {
                "product_id": 4,
                "amount": "100000000000000000",
                "reason": "trade",
            }
        )

        assert bot._ws_positions["ETH"] == Decimal("0")
        assert bot._ws_position_change_raw["ETH"] == Decimal("0.1")
        assert "ETH" in bot._ws_initial_sync_received

    def test_position_change_prefers_position_size_when_present(self):
        bot = make_bot()

        bot._on_position_change(
            {
                "product_id": 8,
                "amount": "999999999999999999",
                "position_size": "1300000000000000000",
                "reason": "trade",
            }
        )

        assert bot._ws_positions["SOL"] == Decimal("0")
        assert bot._ws_position_change_raw["SOL"] == Decimal("1.3")


class TestFillBasedPositionTruth:
    def test_fill_message_updates_ws_positions_authoritatively(self):
        bot = make_bot()

        bot._on_fill_message(
            make_fill(
                4,
                "100000000000000000",
                is_bid=True,
                order_digest="eth-open",
            )
        )

        assert bot._ws_positions["ETH"] == Decimal("0.1")

    def test_fill_message_uses_signed_direction(self):
        bot = make_bot()

        bot._on_fill_message(
            make_fill(
                8,
                "1300000000000000000",
                is_bid=False,
                order_digest="sol-open",
            )
        )

        assert bot._ws_positions["SOL"] == Decimal("-1.3")

    def test_bridged_fill_is_ignored_once(self):
        bot = make_bot()
        bot._bridged_fill_order_ids.add("eth-bridge")

        bot._on_fill_message(
            make_fill(
                4,
                "100000000000000000",
                is_bid=True,
                order_digest="eth-bridge",
            )
        )

        assert bot._ws_positions["ETH"] == Decimal("0")
        assert "eth-bridge" not in bot._bridged_fill_order_ids


class TestPositionWaitMechanism:
    @pytest.mark.asyncio
    async def test_wait_for_position_zero_is_signaled_by_fill_flattening(self):
        bot = make_bot()
        bot._ws_positions["SOL"] = Decimal("-1.0")

        wait_task = asyncio.create_task(bot._wait_for_position_zero("SOL", timeout=0.5))
        await asyncio.sleep(0)

        bot._on_fill_message(
            make_fill(
                8,
                "1000000000000000000",
                is_bid=True,
                order_digest="sol-close",
            )
        )

        assert await wait_task is True
        assert bot._ws_positions["SOL"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_wait_for_position_zero_times_out_without_flat_fill(self):
        bot = make_bot()
        bot._ws_positions["SOL"] = Decimal("-1.0")

        assert await bot._wait_for_position_zero("SOL", timeout=0.05) is False
        assert bot._ws_positions["SOL"] == Decimal("-1.0")

    @pytest.mark.asyncio
    async def test_wait_respects_feature_flag(self):
        bot = make_bot()
        bot.USE_ASYNC_POSITION_WAIT = False
        bot._ws_positions["ETH"] = Decimal("0.1")

        assert await bot._wait_for_position_zero("ETH", timeout=0.05) is True
        assert bot._ws_positions["ETH"] == Decimal("0.1")


class TestPositionDriftDetection:
    @pytest.mark.asyncio
    async def test_detect_position_drift_uses_ws_positions_against_rest(self):
        bot = make_bot()
        bot._ws_positions["SOL"] = Decimal("-1.3")
        bot.sol_client.get_account_positions = AsyncMock(return_value=Decimal("-1.0"))
        bot.POSITION_DRIFT_THRESHOLD = Decimal("0.1")

        drift = await bot._detect_position_drift("SOL", bot.sol_client)

        assert drift == Decimal("0.3")

    @pytest.mark.asyncio
    async def test_detect_position_drift_returns_zero_when_positions_match(self):
        bot = make_bot()
        bot._ws_positions["ETH"] = Decimal("0.05")
        bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal("0.05"))

        drift = await bot._detect_position_drift("ETH", bot.eth_client)

        assert drift == Decimal("0")
