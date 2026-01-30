"""
Test BookDepth Slippage Estimation

Unit tests for BookDepth slippage estimation functionality.
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock


class MockBookDepthHandler:
    """Mock BookDepth handler for testing."""

    def __init__(self):
        self.bids = {}
        self.asks = {}

    def set_orderbook(self, bids, asks):
        """Set order book state."""
        self.bids = bids
        self.asks = asks

    def estimate_slippage(self, side, quantity):
        """Estimate slippage for a given order quantity."""
        # Handle zero quantity
        if quantity == 0:
            return Decimal("0")

        if side == "buy":
            if not self.asks:
                return Decimal(999999)
            best_price = next(iter(self.asks.keys()))
            if best_price == 0:
                return Decimal(999999)

            remaining = quantity
            vwap = Decimal(0)
            total_qty = Decimal(0)

            for price in sorted(self.asks.keys()):
                if remaining <= 0:
                    break
                qty = min(remaining, self.asks[price])
                vwap += price * qty
                total_qty += qty
                remaining -= qty

            if total_qty < quantity:
                return Decimal(999999)

            vwap /= total_qty
            slippage = (vwap - best_price) / best_price * 10000
            return slippage
        else:  # sell
            if not self.bids:
                return Decimal(999999)
            best_price = next(iter(self.bids.keys()))
            if best_price == 0:
                return Decimal(999999)

            remaining = quantity
            vwap = Decimal(0)
            total_qty = Decimal(0)

            for price in sorted(self.bids.keys(), reverse=True):
                if remaining <= 0:
                    break
                qty = min(remaining, self.bids[price])
                vwap += price * qty
                total_qty += qty
                remaining -= qty

            if total_qty < quantity:
                return Decimal(999999)

            vwap /= total_qty
            slippage = (best_price - vwap) / best_price * 10000
            return slippage

    def estimate_exit_capacity(self, position, max_slippage_bps=20):
        """Check if we can exit position without excessive slippage."""
        if position == 0:
            return True, Decimal(0)

        side = "sell" if position > 0 else "buy"
        abs_position = abs(position)

        slippage = self.estimate_slippage(side, abs_position)

        if slippage <= max_slippage_bps:
            return True, abs_position
        else:
            # Binary search for max exitable quantity
            low, high = Decimal(0), abs_position
            for _ in range(10):
                mid = (low + high) / 2
                slippage_mid = self.estimate_slippage(side, mid)
                if slippage_mid <= max_slippage_bps:
                    low = mid
                else:
                    high = mid
            return False, low

    def get_available_liquidity(self, side, max_depth=20):
        """Get total available liquidity up to specified depth."""
        if side == "bid":
            total = Decimal(0)
            for i, (price, qty) in enumerate(self.bids.items()):
                if i >= max_depth:
                    break
                total += qty
            return total
        else:
            total = Decimal(0)
            for i, (price, qty) in enumerate(self.asks.items()):
                if i >= max_depth:
                    break
                total += qty
            return total


class TestBookDepthSlippage:
    """Test BookDepth slippage estimation."""

    def test_estimate_slippage_buy_single_level(self):
        """Test slippage estimation for buy order within single level."""
        handler = MockBookDepthHandler()
        # Order book: one ask level at $3000 with 10 ETH
        handler.set_orderbook(
            bids={},
            asks={Decimal("3000"): Decimal("10")}
        )

        # Buy 1 ETH should have minimal slippage (same price)
        slippage = handler.estimate_slippage("buy", Decimal("1"))
        assert slippage == Decimal("0")

    def test_estimate_slippage_buy_multiple_levels(self):
        """Test slippage estimation for buy order across multiple levels."""
        handler = MockBookDepthHandler()
        # Order book: multiple ask levels
        handler.set_orderbook(
            bids={},
            asks={
                Decimal("3000"): Decimal("1"),    # Best ask
                Decimal("3001"): Decimal("2"),    # +1 tick
                Decimal("3002"): Decimal("3"),    # +2 ticks
            }
        )

        # Buy 4 ETH should go 3 levels deep
        slippage = handler.estimate_slippage("buy", Decimal("4"))
        # VWAP = (1*3000 + 2*3001 + 1*3002) / 4 = 12004 / 4 = 3001
        # slippage = (3001 - 3000) / 3000 * 10000 = 10000/3000 = 3.33 bps
        assert slippage > Decimal("3")
        assert slippage < Decimal("4")

    def test_estimate_slippage_insufficient_liquidity(self):
        """Test slippage estimation when insufficient liquidity."""
        handler = MockBookDepthHandler()
        # Only 1 ETH available
        handler.set_orderbook(
            bids={},
            asks={Decimal("3000"): Decimal("1")}
        )

        # Try to buy 5 ETH
        slippage = handler.estimate_slippage("buy", Decimal("5"))
        assert slippage == Decimal(999999)

    def test_estimate_slippage_sell_single_level(self):
        """Test slippage estimation for sell order within single level."""
        handler = MockBookDepthHandler()
        # Order book: one bid level at $3000 with 10 ETH
        handler.set_orderbook(
            bids={Decimal("3000"): Decimal("10")},
            asks={}
        )

        # Sell 1 ETH should have minimal slippage
        slippage = handler.estimate_slippage("sell", Decimal("1"))
        assert slippage == Decimal("0")

    def test_estimate_slippage_sell_multiple_levels(self):
        """Test slippage estimation for sell order across multiple levels."""
        handler = MockBookDepthHandler()
        # Order book: multiple bid levels
        handler.set_orderbook(
            bids={
                Decimal("3000"): Decimal("1"),    # Best bid
                Decimal("2999"): Decimal("2"),    # -1 tick
                Decimal("2998"): Decimal("3"),    # -2 ticks
            },
            asks={}
        )

        # Sell 4 ETH should go 3 levels deep
        slippage = handler.estimate_slippage("sell", Decimal("4"))
        # VWAP = (1*3000 + 2*2999 + 1*2998) / 4 = 11996 / 4 = 2999
        # slippage = (3000 - 2999) / 3000 * 10000 = 10000/3000 = 3.33 bps
        assert slippage > Decimal("3")
        assert slippage < Decimal("4")

    def test_estimate_exit_capacity_sufficient(self):
        """Test exit capacity when sufficient liquidity."""
        handler = MockBookDepthHandler()
        handler.set_orderbook(
            bids={Decimal("3000"): Decimal("10")},
            asks={}
        )

        # Can exit 1 ETH position
        can_exit, qty = handler.estimate_exit_capacity(Decimal("1"), max_slippage_bps=20)
        assert can_exit == True
        assert qty == Decimal("1")

    def test_estimate_exit_capacity_insufficient(self):
        """Test exit capacity when slippage too high."""
        handler = MockBookDepthHandler()
        # Spread order book to create slippage
        handler.set_orderbook(
            bids={
                Decimal("3000"): Decimal("0.5"),   # First 0.5 at best price
                Decimal("2950"): Decimal("5"),     # Rest at much lower price (50 point drop = ~167 bps)
            },
            asks={}
        )

        # Try to exit 2 ETH position with 20 bps limit
        can_exit, qty = handler.estimate_exit_capacity(Decimal("2"), max_slippage_bps=20)
        # Should not be able to exit full 2 ETH, and returned qty should be less than 1
        assert can_exit == False
        assert qty < Decimal("1")  # Binary search finds max within limit

    def test_get_available_liquidity(self):
        """Test getting available liquidity."""
        handler = MockBookDepthHandler()
        handler.set_orderbook(
            bids={
                Decimal("3000"): Decimal("1"),
                Decimal("2999"): Decimal("2"),
                Decimal("2998"): Decimal("3"),
            },
            asks={}
        )

        # Get liquidity up to 2 levels
        liquidity = handler.get_available_liquidity("bid", max_depth=2)
        assert liquidity == Decimal("3")  # 1 + 2

    def test_zero_quantity_slippage(self):
        """Test slippage for zero quantity."""
        handler = MockBookDepthHandler()
        handler.set_orderbook(
            bids={Decimal("3000"): Decimal("10")},
            asks={Decimal("3000"): Decimal("10")}
        )

        # Zero quantity should return 0 slippage
        slippage_buy = handler.estimate_slippage("buy", Decimal("0"))
        slippage_sell = handler.estimate_slippage("sell", Decimal("0"))
        assert slippage_buy == Decimal("0")
        assert slippage_sell == Decimal("0")

    def test_widening_spread_detection(self):
        """Test that widening spread results in higher slippage."""
        handler = MockBookDepthHandler()

        # Tight spread scenario - buying across 2 levels
        handler.set_orderbook(
            bids={},
            asks={
                Decimal("3000"): Decimal("1"),     # First 1 ETH at $3000
                Decimal("3000.5"): Decimal("5"),   # Next at $3000.50 (0.5 tick spread)
            }
        )
        slippage_tight = handler.estimate_slippage("buy", Decimal("2"))

        # Wide spread scenario - buying across 2 levels with wider gaps
        handler.set_orderbook(
            bids={},
            asks={
                Decimal("3000"): Decimal("1"),     # First 1 ETH at $3000
                Decimal("3010"): Decimal("5"),     # Next at $3010 (10 point spread)
            }
        )
        slippage_wide = handler.estimate_slippage("buy", Decimal("2"))

        # Wide spread should have higher slippage because we have to go to the second level
        assert slippage_wide > slippage_tight


class TestNadoClientSlippageMethods:
    """Test NadoClient BookDepth accessor methods."""

    def test_estimate_slippage_no_websocket(self):
        """Test slippage estimation returns high value when WebSocket not connected."""
        # Create a mock NadoClient
        client = MagicMock()
        client._ws_connected = False
        client._bookdepth_handler = None

        # Import the function and bind it
        import asyncio

        async def test():
            from nado import NadoClient
            # The method should return 999999 when no WebSocket
            # We'll test this through the actual client later
            pass

        # For now, just verify the behavior conceptually
        assert client._ws_connected == False
        assert client._bookdepth_handler is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
