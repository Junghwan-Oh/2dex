"""
Nado Fill Handler

Processes Fill stream data from Nado WebSocket.
Tracks pending orders and detects fills in real-time.
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, Optional, Tuple, Callable


class FillHandler:
    """
    Handle Fill stream data for real-time fill detection.

    Processes WebSocket Fill messages and tracks pending orders.
    Replaces REST polling with sub-100ms fill detection.
    """

    def __init__(
        self,
        product_id: int,
        subaccount: str,
        ws_client,
        logger: Optional[logging.Logger] = None,
        timeout_seconds: int = 30
    ):
        """
        Initialize Fill handler.

        Args:
            product_id: Product ID (4 for ETH, 8 for SOL)
            subaccount: Subaccount hex string
            ws_client: WebSocket client instance
            logger: Optional logger instance
            timeout_seconds: Timeout for pending orders (default 30s)
        """
        self.product_id = product_id
        self.subaccount = subaccount
        self.ws_client = ws_client
        self.logger = logger or logging.getLogger(__name__)
        self.timeout_seconds = timeout_seconds

        # Track pending orders: order_id -> {quantity, timestamp, fill_info}
        self._pending_orders: Dict[str, Dict] = {}

        # Track completed orders: order_id -> fill_info
        self._completed_orders: Dict[str, Dict] = {}

        # Callbacks for fill events
        self._fill_callbacks: list = []

    async def start(self) -> None:
        """Start subscribing to Fill stream."""
        await self.ws_client.subscribe(
            "fill",
            self.product_id,
            callback=self._on_fill_message,
            subaccount=self.subaccount
        )
        self.logger.info(f"Fill handler started for product_id={self.product_id}, subaccount={self.subaccount[:10]}...")

    async def _on_fill_message(self, message: Dict) -> None:
        """
        Process Fill message from WebSocket.

        Args:
            message: Raw message from WebSocket
        """
        try:
            order_id = message.get("order_id")
            if not order_id:
                self.logger.warning(f"Fill message missing order_id: {message}")
                return

            # Parse filled size from x18 format
            filled_size_x18 = message.get("filled_size", "0")
            filled_quantity = Decimal(filled_size_x18) / Decimal(1e18) if int(filled_size_x18) > 1000000 else Decimal(filled_size_x18)

            # Parse price from x18 format
            price_x18 = message.get("price", "0")
            price = Decimal(price_x18) / Decimal(1e18) if int(price_x18) > 1000000 else Decimal(price_x18)

            fill_info = {
                "order_id": order_id,
                "filled_quantity": filled_quantity,
                "price": price,
                "timestamp": int(time.time())
            }

            # If this order was pending, move to completed
            if order_id in self._pending_orders:
                del self._pending_orders[order_id]
                self._completed_orders[order_id] = fill_info
                self.logger.info(f"Order {order_id[:10]}... filled: {filled_quantity} @ ${price}")

                # Notify callbacks
                for callback in self._fill_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(fill_info)
                        else:
                            callback(fill_info)
                    except Exception as e:
                        self.logger.error(f"Error in fill callback: {e}")

            # Store fill info even if not tracked
            else:
                self._completed_orders[order_id] = fill_info
                self.logger.debug(f"Fill received for untracked order {order_id[:10]}...")

        except (KeyError, ValueError) as e:
            self.logger.error(f"Failed to parse Fill message: {e}")

    def track_order(self, order_id: str, quantity: Decimal) -> None:
        """
        Start tracking a pending order.

        Args:
            order_id: Order ID to track
            quantity: Expected fill quantity
        """
        self._pending_orders[order_id] = {
            "quantity": quantity,
            "timestamp": int(time.time())
        }
        self.logger.debug(f"Tracking order {order_id[:10]}... (qty: {quantity})")

    def is_pending(self, order_id: str) -> bool:
        """Check if order is still pending."""
        return order_id in self._pending_orders

    def get_pending_quantity(self, order_id: str) -> Optional[Decimal]:
        """Get pending order quantity."""
        if order_id in self._pending_orders:
            return self._pending_orders[order_id]["quantity"]
        return None

    def is_timed_out(self, order_id: str) -> bool:
        """Check if pending order has timed out."""
        if order_id not in self._pending_orders:
            return False

        elapsed = int(time.time()) - self._pending_orders[order_id]["timestamp"]
        return elapsed > self.timeout_seconds

    def get_fill_info(self, order_id: str) -> Optional[Dict]:
        """
        Get fill information for an order.

        Args:
            order_id: Order ID

        Returns:
            Fill info dict or None if not filled
        """
        return self._completed_orders.get(order_id)

    def register_callback(self, callback: Callable) -> None:
        """Register callback for fill events."""
        self._fill_callbacks.append(callback)

    def cleanup_timeouts(self) -> list:
        """
        Remove timed-out orders from pending list.

        Returns:
            List of timed-out order IDs
        """
        timed_out = []
        for order_id in list(self._pending_orders.keys()):
            if self.is_timed_out(order_id):
                timed_out.append(order_id)
                del self._pending_orders[order_id]

        if timed_out:
            self.logger.warning(f"{len(timed_out)} orders timed out")

        return timed_out

    def get_pending_count(self) -> int:
        """Get number of pending orders."""
        return len(self._pending_orders)

    def clear_completed(self, older_than_seconds: int = 3600) -> int:
        """
        Clear old completed orders from memory.

        Args:
            older_than_seconds: Remove orders completed more than this long ago

        Returns:
            Number of orders cleared
        """
        cutoff = int(time.time()) - older_than_seconds
        cleared = 0

        for order_id in list(self._completed_orders.keys()):
            if self._completed_orders[order_id]["timestamp"] < cutoff:
                del self._completed_orders[order_id]
                cleared += 1

        if cleared > 0:
            self.logger.debug(f"Cleared {cleared} old completed orders")

        return cleared
