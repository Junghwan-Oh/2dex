"""
Nado BookDepth Handler

Processes BookDepth stream data from Nado WebSocket.
Maintains local order book state and provides slippage estimation.
"""

import asyncio
import logging
from decimal import Decimal
from sortedcontainers import SortedDict
from typing import Dict, Optional, Tuple, List

from .nado_websocket_client import NadoWebSocketClient


class BookDepthHandler:
    """
    Handle BookDepth stream data.

    Processes 50ms order book updates with incremental deltas.
    Maintains local order book state and provides:
    - Best bid/ask prices
    - Full depth by level
    - Slippage estimation
    - Liquidity analysis
    """

    def __init__(
        self,
        product_id: int,
        ws_client: NadoWebSocketClient,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize BookDepth handler.

        Args:
            product_id: Product ID (4 for ETH, 8 for SOL)
            ws_client: WebSocket client instance
            logger: Optional logger instance
        """
        self.product_id = product_id
        self.ws_client = ws_client
        self.logger = logger or logging.getLogger(__name__)

        # Local order book state
        # bids: sorted in descending order (highest first)
        self.bids: SortedDict = SortedDict(lambda x: -x)
        # asks: sorted in ascending order (lowest first)
        self.asks: SortedDict = SortedDict()

        # Timestamp tracking
        self.last_timestamp: int = 0

        # Callbacks
        self._callbacks: List = []

    async def start(self) -> None:
        """Start subscribing to BookDepth stream."""
        await self.ws_client.subscribe(
            "book_depth",
            self.product_id,
            self._on_bookdepth_message
        )
        self.logger.info(f"BookDepth handler started for product_id={self.product_id}")

    async def _on_bookdepth_message(self, message: Dict) -> None:
        """
        Process BookDepth message from WebSocket.

        Args:
            message: Raw message from WebSocket
        """
        try:
            # Update timestamp
            if "max_timestamp" in message:
                self.last_timestamp = int(message["max_timestamp"])

            # Process bids (incremental deltas)
            for price_str, qty_str in message.get("bids", []):
                price = Decimal(price_str) / Decimal(1e18)
                qty = Decimal(qty_str) / Decimal(1e18)

                if qty == 0:
                    # Delete level
                    self.bids.pop(price, None)
                else:
                    # Add/update level
                    self.bids[price] = qty

            # Process asks (incremental deltas)
            for price_str, qty_str in message.get("asks", []):
                price = Decimal(price_str) / Decimal(1e18)
                qty = Decimal(qty_str) / Decimal(1e18)

                if qty == 0:
                    # Delete level
                    self.asks.pop(price, None)
                else:
                    # Add/update level
                    self.asks[price] = qty

            # Call registered callbacks
            for callback in self._callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    self.logger.error(f"Error in BookDepth callback: {e}")

        except (KeyError, ValueError) as e:
            self.logger.error(f"Failed to parse BookDepth message: {e}")

    def get_best_bid(self) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """
        Get best bid price and quantity.

        Returns:
            Tuple of (price, quantity) or (None, None) if no bids
        """
        if not self.bids:
            return None, None
        best_price = next(iter(self.bids.keys()))
        return best_price, self.bids[best_price]

    def get_best_ask(self) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """
        Get best ask price and quantity.

        Returns:
            Tuple of (price, quantity) or (None, None) if no asks
        """
        if not self.asks:
            return None, None
        best_price = next(iter(self.asks.keys()))
        return best_price, self.asks[best_price]

    def get_depth_at_level(
        self,
        level: int,
        side: str
    ) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """
        Get price and quantity at specific depth level.

        Args:
            level: Depth level (0 = best, 1 = second best, etc.)
            side: "bid" or "ask"

        Returns:
            Tuple of (price, quantity) or (None, None) if level doesn't exist
        """
        if side == "bid":
            if level >= len(self.bids):
                return None, None
            price = list(self.bids.keys())[level]
            return price, self.bids[price]
        else:  # ask
            if level >= len(self.asks):
                return None, None
            price = list(self.asks.keys())[level]
            return price, self.asks[price]

    def estimate_slippage(
        self,
        side: str,
        quantity: Decimal
    ) -> Decimal:
        """
        Estimate slippage for a given order quantity.

        Args:
            side: "buy" or "sell"
            quantity: Order quantity

        Returns:
            Slippage in basis points, or 999999 if insufficient liquidity
        """
        # Handle zero quantity - no slippage
        if quantity == 0:
            return Decimal("0")

        if side == "buy":
            best_price, _ = self.get_best_ask()
            if best_price is None or best_price == 0:
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
                return Decimal(999999)  # Not enough liquidity

            vwap /= total_qty
            slippage = (vwap - best_price) / best_price * 10000
            return slippage

        else:  # sell
            best_price, _ = self.get_best_bid()
            if best_price is None or best_price == 0:
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

    def get_available_liquidity(
        self,
        side: str,
        max_depth: int = 20
    ) -> Decimal:
        """
        Get total available liquidity up to specified depth.

        Args:
            side: "bid" or "ask"
            max_depth: Maximum depth levels to consider

        Returns:
            Total liquidity quantity
        """
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

    def estimate_exit_capacity(
        self,
        current_position: Decimal,
        max_slippage_bps: int = 20
    ) -> Tuple[bool, Decimal]:
        """
        Check if we can exit position without excessive slippage.

        Args:
            current_position: Current position (positive = long, negative = short)
            max_slippage_bps: Maximum acceptable slippage in bps

        Returns:
            Tuple of (can_exit, exitable_quantity)
        """
        if current_position == 0:
            return True, Decimal(0)

        side = "sell" if current_position > 0 else "buy"
        abs_position = abs(current_position)

        slippage = self.estimate_slippage(side, abs_position)

        if slippage <= max_slippage_bps:
            return True, abs_position
        else:
            # Binary search for max exitable quantity
            low, high = Decimal(0), abs_position
            for _ in range(10):  # 10 iterations enough
                mid = (low + high) / 2
                slippage_mid = self.estimate_slippage(side, mid)

                if slippage_mid <= max_slippage_bps:
                    low = mid
                else:
                    high = mid

            return False, low

    def get_order_book_summary(self, max_levels: int = 5) -> Dict:
        """
        Get summary of current order book state.

        Args:
            max_levels: Number of levels to include

        Returns:
            Dictionary with order book summary
        """
        best_bid, bid_qty = self.get_best_bid()
        best_ask, ask_qty = self.get_best_ask()

        bid_levels = []
        for i in range(min(max_levels, len(self.bids))):
            price = list(self.bids.keys())[i]
            qty = self.bids[price]
            bid_levels.append({
                "level": i,
                "price": str(price),
                "quantity": str(qty)
            })

        ask_levels = []
        for i in range(min(max_levels, len(self.asks))):
            price = list(self.asks.keys())[i]
            qty = self.asks[price]
            ask_levels.append({
                "level": i,
                "price": str(price),
                "quantity": str(qty)
            })

        return {
            "product_id": self.product_id,
            "best_bid": str(best_bid) if best_bid else None,
            "bid_qty": str(bid_qty) if bid_qty else None,
            "best_ask": str(best_ask) if best_ask else None,
            "ask_qty": str(ask_qty) if ask_qty else None,
            "spread": str(best_ask - best_bid) if best_bid and best_ask else None,
            "bid_levels": bid_levels,
            "ask_levels": ask_levels,
            "total_bid_liquidity": str(sum(self.bids.values())),
            "total_ask_liquidity": str(sum(self.asks.values()))
        }

    def register_callback(self, callback) -> None:
        """
        Register callback for BookDepth updates.

        Args:
            callback: Function to call on each update
        """
        self._callbacks.append(callback)
