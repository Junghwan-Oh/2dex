from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from hedge.DN_pair_eth_sol_nado import DNPairBot


def make_client(*, connected: bool, ws_ready: bool, rest_position: Decimal):
    client = Mock()
    client._ws_connected = connected
    client.has_ws_market_data = Mock(return_value=ws_ready)
    client.get_account_positions = AsyncMock(return_value=rest_position)
    return client


def make_bot() -> DNPairBot:
    with patch.dict(
        "os.environ",
        {
            "NADO_PRIVATE_KEY": "0x" + "1" * 64,
            "NADO_MODE": "MAINNET",
            "NADO_SUBACCOUNT_NAME": "test",
        },
    ):
        return DNPairBot(
            target_notional=Decimal("100"),
            csv_path="/tmp/test_startup_positions.csv",
        )


class TestWebSocketStartupBootstrap:
    @pytest.mark.asyncio
    async def test_wait_for_ws_position_sync_seeds_positions_after_warmup(self):
        bot = make_bot()
        bot.eth_client = make_client(connected=True, ws_ready=True, rest_position=Decimal("0.15"))
        bot.sol_client = make_client(connected=True, ws_ready=True, rest_position=Decimal("-1.30"))

        synced = await bot._wait_for_ws_position_sync(timeout=0.1)

        assert synced is True
        assert bot._ws_initial_sync_complete is True
        assert bot._startup_data_source == "websocket_runtime + rest_seed"
        assert bot._ws_positions["ETH"] == Decimal("0.15")
        assert bot._ws_positions["SOL"] == Decimal("-1.30")

    @pytest.mark.asyncio
    async def test_wait_for_ws_position_sync_times_out_without_rest_spam(self):
        bot = make_bot()
        bot.eth_client = make_client(connected=True, ws_ready=False, rest_position=Decimal("9"))
        bot.sol_client = make_client(connected=True, ws_ready=False, rest_position=Decimal("9"))

        synced = await bot._wait_for_ws_position_sync(timeout=0.05)

        assert synced is False
        assert bot._ws_initial_sync_complete is False
        bot.eth_client.get_account_positions.assert_not_awaited()
        bot.sol_client.get_account_positions.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_startup_positions_prefers_ws_seeded_state(self):
        bot = make_bot()
        bot._ws_positions = {"ETH": Decimal("0.07"), "SOL": Decimal("-0.90")}
        bot._ws_initial_sync_complete = True
        bot._startup_data_source = "websocket_runtime + rest_seed"
        bot.eth_client = make_client(connected=True, ws_ready=True, rest_position=Decimal("99"))
        bot.sol_client = make_client(connected=True, ws_ready=True, rest_position=Decimal("99"))

        eth_pos, sol_pos = await bot._get_startup_positions()

        assert eth_pos == Decimal("0.07")
        assert sol_pos == Decimal("-0.90")
        bot.eth_client.get_account_positions.assert_not_awaited()
        bot.sol_client.get_account_positions.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_startup_positions_falls_back_to_rest_when_ws_not_ready(self):
        bot = make_bot()
        bot.eth_client = make_client(connected=True, ws_ready=False, rest_position=Decimal("0.01"))
        bot.sol_client = make_client(connected=True, ws_ready=False, rest_position=Decimal("0"))

        eth_pos, sol_pos = await bot._get_startup_positions()

        assert eth_pos == Decimal("0.01")
        assert sol_pos == Decimal("0")
        assert bot._startup_data_source == "rest_api"


class TestStartupResidualChecks:
    @pytest.mark.asyncio
    async def test_startup_check_exits_on_seeded_residual_positions(self):
        bot = make_bot()
        bot._ws_positions = {"ETH": Decimal("0.05"), "SOL": Decimal("0")}
        bot._ws_initial_sync_complete = True
        bot._startup_data_source = "websocket_runtime + rest_seed"

        with pytest.raises(SystemExit) as exc:
            await bot._check_residual_positions_at_startup()

        assert exc.value.code == 1

    @pytest.mark.asyncio
    async def test_startup_check_allows_flat_seeded_positions(self):
        bot = make_bot()
        bot._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}
        bot._ws_initial_sync_complete = True
        bot._startup_data_source = "websocket_runtime + rest_seed"

        assert await bot._check_residual_positions_at_startup() is True


class TestRuntimeVerificationFallback:
    @pytest.mark.asyncio
    async def test_verify_and_sync_positions_skips_rest_when_ws_runtime_ready(self):
        bot = make_bot()
        bot._ws_positions = {"ETH": Decimal("0.05"), "SOL": Decimal("-1.20")}
        bot.eth_client = make_client(connected=True, ws_ready=True, rest_position=Decimal("99"))
        bot.sol_client = make_client(connected=True, ws_ready=True, rest_position=Decimal("99"))

        await bot._verify_and_sync_positions_from_rest()

        assert bot._ws_positions["ETH"] == Decimal("0.05")
        assert bot._ws_positions["SOL"] == Decimal("-1.20")
        bot.eth_client.get_account_positions.assert_not_awaited()
        bot.sol_client.get_account_positions.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_and_sync_positions_uses_rest_only_when_ws_not_ready(self):
        bot = make_bot()
        bot._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}
        bot.eth_client = make_client(connected=True, ws_ready=False, rest_position=Decimal("0.07"))
        bot.sol_client = make_client(connected=True, ws_ready=False, rest_position=Decimal("-0.90"))

        await bot._verify_and_sync_positions_from_rest()

        assert bot._ws_positions["ETH"] == Decimal("0.07")
        assert bot._ws_positions["SOL"] == Decimal("-0.90")
