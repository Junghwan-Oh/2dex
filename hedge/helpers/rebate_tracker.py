"""
GRVT Rebate Tracker - STORY-004

Tracks cumulative rebate earnings from GRVT trades and provides:
- Milestone detection ($1, $5, $10, $25, $50, $100)
- Telegram notifications on milestone achievement
- CSV logging integration
- Daily summary reports
- State persistence across sessions
"""

import json
import logging
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict


class RebateTracker:
    """
    Tracks GRVT trading rebates with milestone notifications.

    Features:
    - Cumulative rebate tracking
    - Configurable milestone detection
    - State persistence via JSON
    - CSV logging integration
    - Telegram notification support
    """

    def __init__(self, config: dict, ticker: str, logger: Optional[logging.Logger] = None):
        """
        Initialize RebateTracker.

        Args:
            config: Configuration dictionary with rebate_tracking section
            ticker: Trading pair ticker (e.g., 'ETH', 'BTC')
            logger: Optional logger instance
        """
        self.ticker = ticker
        self.logger = logger or logging.getLogger(__name__)

        # Load configuration
        rebate_config = config.get('rebate_tracking', {})
        self.enabled = rebate_config.get('enabled', False)

        # Default milestones: $1, $5, $10, $25, $50, $100
        self.milestones = [Decimal(str(m)) for m in rebate_config.get('milestones', [1, 5, 10, 25, 50, 100])]
        self.milestones.sort()  # Ensure sorted order

        self.telegram_notifications = rebate_config.get('telegram_notifications', True)
        self.csv_logging = rebate_config.get('csv_logging', True)

        # State tracking
        self.cumulative_rebate = Decimal('0')
        self.last_milestone_hit = Decimal('0')
        self.milestones_hit = []
        self.start_date = datetime.now()

        # State file path
        self.state_file = Path(f'logs/rebate_state_{ticker}.json')
        self.state_file.parent.mkdir(exist_ok=True)

        # Load existing state if available
        self._load_state()

        # Save initial state (creates file if doesn't exist)
        self._save_state()

        if self.enabled:
            self.logger.info(f"RebateTracker initialized for {ticker}")
            self.logger.info(f"Milestones: {[float(m) for m in self.milestones]}")
        else:
            self.logger.info(f"RebateTracker disabled for {ticker}")

    def _load_state(self):
        """Load state from JSON file if it exists."""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)

            self.cumulative_rebate = Decimal(state.get('cumulative_rebate', '0'))
            self.last_milestone_hit = Decimal(state.get('last_milestone_hit', '0'))
            self.milestones_hit = [Decimal(str(m)) for m in state.get('milestones_hit', [])]

            # Parse start date
            start_date_str = state.get('start_date')
            if start_date_str:
                self.start_date = datetime.fromisoformat(start_date_str)

            self.logger.info(f"Loaded rebate state: ${self.cumulative_rebate} cumulative")

        except Exception as e:
            self.logger.warning(f"Failed to load rebate state: {e}")

    def _save_state(self):
        """Save current state to JSON file."""
        try:
            state = {
                'cumulative_rebate': str(self.cumulative_rebate),
                'last_milestone_hit': str(self.last_milestone_hit),
                'milestones_hit': [str(m) for m in self.milestones_hit],
                'start_date': self.start_date.isoformat(),
                'ticker': self.ticker
            }

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save rebate state: {e}")

    def record_rebate(self, rebate_amount: Decimal) -> Tuple[bool, Optional[str]]:
        """
        Record a rebate and check for milestone crossing.

        Args:
            rebate_amount: Rebate amount in USD (must be >= 0)

        Returns:
            Tuple of (milestone_hit: bool, notification_message: Optional[str])

        Raises:
            ValueError: If rebate_amount is negative
        """
        if not self.enabled:
            return False, None

        # Validate rebate amount
        if rebate_amount < 0:
            raise ValueError(f"Rebate amount must be non-negative, got {rebate_amount}")

        # Allow zero rebate (no-op)
        if rebate_amount == 0:
            return False, None

        # Store previous cumulative for milestone checking
        previous_cumulative = self.cumulative_rebate

        # Add to cumulative
        self.cumulative_rebate += rebate_amount

        self.logger.debug(f"Rebate recorded: +${rebate_amount} → Total: ${self.cumulative_rebate}")

        # Check for milestone crossing
        milestone_hit = False
        notification_message = None
        highest_milestone_crossed = None

        for milestone in self.milestones:
            # Check if we crossed this milestone
            if previous_cumulative < milestone <= self.cumulative_rebate:
                # Only notify if we haven't hit this milestone before
                if milestone not in self.milestones_hit:
                    milestone_hit = True
                    highest_milestone_crossed = milestone
                    self.milestones_hit.append(milestone)
                    self.last_milestone_hit = milestone

        # Generate notification message for highest milestone crossed
        if milestone_hit and highest_milestone_crossed:
            notification_message = self._generate_milestone_message(highest_milestone_crossed)
            self.logger.info(f"🎉 Milestone achieved: ${highest_milestone_crossed}")

        # Save state
        self._save_state()

        return milestone_hit, notification_message

    def _generate_milestone_message(self, milestone: Decimal) -> str:
        """
        Generate milestone achievement notification message.

        Args:
            milestone: Milestone amount achieved

        Returns:
            Formatted notification message
        """
        # Calculate next milestone
        next_milestone = None
        for m in self.milestones:
            if m > milestone:
                next_milestone = m
                break

        message = (
            f"🎉 <b>Rebate Milestone Achieved!</b>\n\n"
            f"Ticker: <code>{self.ticker}</code>\n"
            f"Milestone: <b>${milestone}</b>\n"
            f"Total Rebates: <b>${self.cumulative_rebate:.2f}</b>\n"
        )

        if next_milestone:
            remaining = next_milestone - self.cumulative_rebate
            message += f"Next Milestone: ${next_milestone} (${remaining:.2f} away)"
        else:
            message += "🏆 All milestones achieved!"

        return message

    def get_csv_log_data(self) -> Dict[str, str]:
        """
        Get rebate data for CSV logging.

        Returns:
            Dictionary with CSV column data
        """
        # Calculate next milestone
        next_milestone = 'N/A'
        for m in self.milestones:
            if m > self.cumulative_rebate:
                next_milestone = str(m)
                break

        return {
            'cumulative_rebate': str(self.cumulative_rebate),
            'last_milestone_hit': str(self.last_milestone_hit),
            'next_milestone': next_milestone
        }

    def get_daily_summary(self) -> str:
        """
        Get human-readable daily summary.

        Returns:
            Formatted summary string
        """
        # Calculate days since start
        days_elapsed = (datetime.now() - self.start_date).days
        if days_elapsed == 0:
            days_elapsed = 1  # Avoid division by zero

        daily_average = self.cumulative_rebate / days_elapsed

        # Find next milestone
        next_milestone = None
        for m in self.milestones:
            if m > self.cumulative_rebate:
                next_milestone = m
                break

        summary = (
            f"📊 <b>Rebate Summary ({self.ticker})</b>\n\n"
            f"Cumulative Rebates: <b>${self.cumulative_rebate:.2f}</b>\n"
            f"Days Active: {days_elapsed}\n"
            f"Daily Average: ${daily_average:.2f}\n"
            f"Milestones Hit: {len(self.milestones_hit)}/{len(self.milestones)}\n"
        )

        if next_milestone:
            remaining = next_milestone - self.cumulative_rebate
            progress_pct = (self.cumulative_rebate / next_milestone) * 100
            summary += (
                f"\n<b>Next Milestone: ${next_milestone}</b>\n"
                f"Remaining: ${remaining:.2f} ({progress_pct:.1f}% complete)"
            )
        else:
            summary += "\n🏆 <b>All milestones achieved!</b>"

        return summary

    def reset(self):
        """Reset tracker state (useful for testing or new tracking period)."""
        self.cumulative_rebate = Decimal('0')
        self.last_milestone_hit = Decimal('0')
        self.milestones_hit = []
        self.start_date = datetime.now()
        self._save_state()
        self.logger.info(f"RebateTracker reset for {self.ticker}")
