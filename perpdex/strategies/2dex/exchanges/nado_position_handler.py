"""
Nado PositionChange Handler

Processes PositionChange stream data from Nado WebSocket.
Tracks position updates in real-time.
"""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, Optional, List, Callable


class PositionChangeHandler:
    """
    Handle PositionChange stream data for real-time position updates.

    Processes WebSocket PositionChange messages and tracks current positions.
    """

    def __init__(
        self,
        product_id: int,
        subaccount: str,
        ws_client,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize PositionChange handler.

        Args:
            product_id: Product ID (4 for ETH, 8 for SOL)
            subaccount: Subaccount hex string
            ws_client: WebSocket client instance
            logger: Optional logger instance
        """
        self.product_id = product_id
        self.subaccount = subaccount
        self.ws_client = ws_client
        self.logger = logger or logging.getLogger(__name__)

        # Current position
        self._current_position: Decimal = Decimal("0")

        # Position history
        self._position_history: List[tuple] = []  # (timestamp, old_position, new_position)

        # Callbacks for position changes
        self._position_callbacks: list = []

    async def start(self) -> None:
        """Start subscribing to PositionChange stream."""
        await self.ws_client.subscribe(
            "position_change",
            self.product_id,
            callback=self._on_position_message,
            subaccount=self.subaccount
        )
        self.logger.info(f"PositionChange handler started for product_id={self.product_id}")

    async def _on_position_message(self, message: Dict) -> None:
        """
        Process PositionChange message from WebSocket.

        Args:
            message: Raw message from WebSocket
        """
        try:
            # Check if message is for this product
            msg_product_id = message.get("product_id")
            if msg_product_id is not None and msg_product_id != self.product_id:
                return

            # Parse position size from x18 format
            position_size_x18 = message.get("position_size", "0")
            new_position = Decimal(position_size_x18) / Decimal(1e18) if int(position_size_x18) > 1000000 else Decimal(position_size_x18)

            old_position = self._current_position
            self._current_position = new_position

            # Add to history
            import time
            self._position_history.append((int(time.time()), old_position, new_position))

            # Keep history limited to last 100 entries
            if len(self._position_history) > 100:
                self._position_history = self._position_history[-100:]

            self.logger.info(f"Position changed: {old_position} → {new_position}")

            # Notify callbacks
            for callback in self._position_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(old_position, new_position)
                    else:
                        callback(old_position, new_position)
                except Exception as e:
                    self.logger.error(f"Error in position callback: {e}")

        except (KeyError, ValueError) as e:
            self.logger.error(f"Failed to parse PositionChange message: {e}")

    def get_current_position(self) -> Decimal:
        """Get current position."""
        return self._current_position

    def register_callback(self, callback: Callable) -> None:
        """
        Register callback for position changes.

        Args:
            callback: Function called with (old_position, new_position)
        """
        self._position_callbacks.append(callback)

    def get_position_history(self, limit: int = 10) -> List[tuple]:
        """
        Get recent position changes.

        Args:
            limit: Maximum number of history entries to return

        Returns:
            List of (timestamp, old_position, new_position) tuples
        """
        return self._position_history[-limit:]

    def clear_history(self) -> None:
        """Clear position history."""
        self._position_history = []
