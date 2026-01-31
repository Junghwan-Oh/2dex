"""Rollback monitoring for DN pair trading bot."""

from typing import Tuple


class RollbackMonitor:
    """Monitor for rollback trigger conditions."""

    SAFETY_STOP_THRESHOLD = 0.30  # 30% safety stop rate
    NEGATIVE_PNL_THRESHOLD = -10  # -10 bps avg PNL per cycle
    MIN_FILLS_FOR_ROLLBACK = 5  # Need at least 5 cycles

    def __init__(self):
        self.cycle_count = 0
        self.safety_stop_count = 0
        self.pnl_history = []

    def record_cycle(self, had_safety_stop: bool, pnl_bps: float):
        """Record cycle results."""
        self.cycle_count += 1
        if had_safety_stop:
            self.safety_stop_count += 1
        self.pnl_history.append(pnl_bps)

    def should_rollback(self) -> Tuple[bool, str]:
        """Check if rollback should be triggered."""
        if self.cycle_count < self.MIN_FILLS_FOR_ROLLBACK:
            return False, "Insufficient data"

        # Check safety stop rate
        safety_stop_rate = self.safety_stop_count / self.cycle_count
        if safety_stop_rate > self.SAFETY_STOP_THRESHOLD:
            return True, (
                f"Rollback: Safety stop rate {safety_stop_rate:.1%} > "
                f"{self.SAFETY_STOP_THRESHOLD:.1%} threshold"
            )

        # Check average PNL
        avg_pnl = sum(self.pnl_history) / len(self.pnl_history)
        if avg_pnl < self.NEGATIVE_PNL_THRESHOLD:
            return True, (
                f"Rollback: Avg PNL {avg_pnl:.1f} bps < "
                f"{self.NEGATIVE_PNL_THRESHOLD} bps threshold"
            )

        return False, "Metrics healthy"
