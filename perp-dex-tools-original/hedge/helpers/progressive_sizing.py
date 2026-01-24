"""
Progressive Sizing Manager for Hedge Bot
=========================================
Manages gradual position size increases with validation gates.

STORY-002 Implementation:
- Phase management ($10 → $20 → $50 → $100 → $200 → $500)
- Validation tracking (3 consecutive successes per phase)
- Automatic phase advancement
- Downgrade on failure (max 2 consecutive failures)
- Manual approval for phase transitions
- Telegram notification integration
- CSV logging support
"""

import logging
from decimal import Decimal
from typing import Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
import json


class ProgressiveSizingManager:
    """Manages progressive position sizing with validation gates."""

    def __init__(self, config: Dict, ticker: str, logger: Optional[logging.Logger] = None):
        """
        Initialize Progressive Sizing Manager.

        Args:
            config: Configuration dict from config.yaml
            ticker: Trading pair ticker (e.g., "ETH")
            logger: Optional logger instance
        """
        self.config = config
        self.ticker = ticker
        self.logger = logger or logging.getLogger(__name__)

        # Load progressive sizing config
        # Handle both dict and ConfigLoader instances
        if hasattr(config, 'get_all'):
            # ConfigLoader instance
            ps_config = config.get_all('progressive_sizing')
        else:
            # Plain dict (for tests)
            ps_config = config.get('progressive_sizing', {})
        self.enabled = ps_config.get('enabled', False)
        self.initial_size = Decimal(str(ps_config.get('initial_size', 0.1)))
        self.validation_count = ps_config.get('validation_count', 3)
        self.size_multiplier = Decimal(str(ps_config.get('size_multiplier', 2.0)))
        self.downgrade_on_failure = ps_config.get('downgrade_on_failure', True)
        self.max_consecutive_failures = ps_config.get('max_consecutive_failures', 2)
        self.manual_phase_approval = ps_config.get('manual_phase_approval', True)

        # Phase targets from config
        self.phase_targets = [
            Decimal(str(phase['max_position_value_usd']))
            for phase in ps_config.get('phase_targets', [])
        ]

        if not self.phase_targets:
            self.phase_targets = [
                Decimal('10.0'),
                Decimal('20.0'),
                Decimal('50.0'),
                Decimal('100.0'),
                Decimal('200.0'),
                Decimal('500.0')
            ]

        # State tracking
        self.current_phase = 0  # Phase index (0-5)
        self.consecutive_successes = 0
        self.consecutive_failures = 0
        self.phase_validated = False
        self.pending_approval = False
        self.approval_granted = False

        # Status file for persistence
        self.status_file = Path(__file__).parent.parent / f"progressive_sizing_{ticker}_status.json"

        # Load saved state if exists
        self._load_state()

        self.logger.info(f"Progressive Sizing Manager initialized - Enabled: {self.enabled}")
        if self.enabled:
            self.logger.info(f"Current Phase: {self.current_phase + 1}/6 (${self.phase_targets[self.current_phase]})")
            self.logger.info(f"Consecutive Successes: {self.consecutive_successes}/{self.validation_count}")

    def _load_state(self) -> None:
        """Load saved state from status file."""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r') as f:
                    state = json.load(f)

                self.current_phase = state.get('current_phase', 0)
                self.consecutive_successes = state.get('consecutive_successes', 0)
                self.consecutive_failures = state.get('consecutive_failures', 0)
                self.phase_validated = state.get('phase_validated', False)
                self.pending_approval = state.get('pending_approval', False)
                self.approval_granted = state.get('approval_granted', False)

                self.logger.info(f"Loaded progressive sizing state from {self.status_file}")
            except Exception as e:
                self.logger.warning(f"Failed to load progressive sizing state: {e}")

    def _save_state(self) -> None:
        """Save current state to status file."""
        state = {
            'current_phase': self.current_phase,
            'consecutive_successes': self.consecutive_successes,
            'consecutive_failures': self.consecutive_failures,
            'phase_validated': self.phase_validated,
            'pending_approval': self.pending_approval,
            'approval_granted': self.approval_granted,
            'last_updated': datetime.now().isoformat()
        }

        try:
            with open(self.status_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save progressive sizing state: {e}")

    def get_current_size(self, price: Decimal) -> Decimal:
        """
        Get current order size based on phase and price.

        Args:
            price: Current market price

        Returns:
            Order size in base currency (e.g., ETH)
        """
        if not self.enabled:
            return self.initial_size

        # Calculate size based on current phase target
        target_usd = self.phase_targets[self.current_phase]
        order_size = target_usd / price

        return order_size

    def record_success(self) -> Tuple[bool, Optional[str]]:
        """
        Record successful hedge iteration.

        Returns:
            Tuple of (phase_advanced, notification_message)
        """
        if not self.enabled:
            return False, None

        # Reset failure counter on success
        self.consecutive_failures = 0

        # Increment success counter
        self.consecutive_successes += 1

        self.logger.info(f"Success recorded: {self.consecutive_successes}/{self.validation_count} for Phase {self.current_phase + 1}")

        # Check if phase is validated
        if self.consecutive_successes >= self.validation_count:
            self.phase_validated = True

            # Check if we can advance to next phase
            if self.current_phase < len(self.phase_targets) - 1:
                if self.manual_phase_approval and not self.approval_granted:
                    self.pending_approval = True
                    self._save_state()

                    notification = (
                        f"Progressive Sizing Phase {self.current_phase + 1} Validated\n"
                        f"Current: ${self.phase_targets[self.current_phase]}\n"
                        f"Next: ${self.phase_targets[self.current_phase + 1]}\n"
                        f"Manual approval required to advance."
                    )

                    return False, notification
                else:
                    # Advance phase
                    old_phase = self.current_phase
                    self.current_phase += 1
                    self.consecutive_successes = 0
                    self.phase_validated = False
                    self.pending_approval = False
                    self.approval_granted = False
                    self._save_state()

                    notification = (
                        f"Progressive Sizing Advanced\n"
                        f"Phase {old_phase + 1} → Phase {self.current_phase + 1}\n"
                        f"${self.phase_targets[old_phase]} → ${self.phase_targets[self.current_phase]}"
                    )

                    self.logger.info(f"Phase advanced: {old_phase + 1} -> {self.current_phase + 1}")

                    return True, notification
            else:
                # Already at max phase
                self._save_state()
                notification = f"Progressive Sizing at maximum phase (${self.phase_targets[self.current_phase]})"
                return False, notification

        self._save_state()
        return False, None

    def record_failure(self) -> Tuple[bool, Optional[str]]:
        """
        Record failed hedge iteration.

        Returns:
            Tuple of (phase_downgraded, notification_message)
        """
        if not self.enabled:
            return False, None

        # Reset success counter on failure
        self.consecutive_successes = 0
        self.phase_validated = False

        # Increment failure counter
        self.consecutive_failures += 1

        self.logger.warning(f"Failure recorded: {self.consecutive_failures}/{self.max_consecutive_failures} for Phase {self.current_phase + 1}")

        # Check if we need to downgrade
        if self.downgrade_on_failure and self.consecutive_failures >= self.max_consecutive_failures:
            if self.current_phase > 0:
                old_phase = self.current_phase
                self.current_phase -= 1
                self.consecutive_failures = 0
                self.consecutive_successes = 0
                self.pending_approval = False
                self.approval_granted = False
                self._save_state()

                notification = (
                    f"Progressive Sizing Downgraded (failures)\n"
                    f"Phase {old_phase + 1} → Phase {self.current_phase + 1}\n"
                    f"${self.phase_targets[old_phase]} → ${self.phase_targets[self.current_phase]}"
                )

                self.logger.warning(f"Phase downgraded: {old_phase + 1} -> {self.current_phase + 1}")

                return True, notification
            else:
                # Already at minimum phase
                self.consecutive_failures = 0  # Reset to prevent infinite alerts
                self._save_state()
                notification = f"Progressive Sizing at minimum phase (${self.phase_targets[0]}) - failures reset"
                return False, notification

        self._save_state()
        return False, None

    def approve_phase_advance(self) -> Tuple[bool, Optional[str]]:
        """
        Manually approve phase advancement.

        Returns:
            Tuple of (advanced, notification_message)
        """
        if not self.pending_approval:
            return False, "No pending phase approval"

        if self.current_phase >= len(self.phase_targets) - 1:
            return False, "Already at maximum phase"

        # Advance phase
        old_phase = self.current_phase
        self.current_phase += 1
        self.consecutive_successes = 0
        self.phase_validated = False
        self.pending_approval = False
        self.approval_granted = True
        self._save_state()

        notification = (
            f"Progressive Sizing Advanced (manual approval)\n"
            f"Phase {old_phase + 1} → Phase {self.current_phase + 1}\n"
            f"${self.phase_targets[old_phase]} → ${self.phase_targets[self.current_phase]}"
        )

        self.logger.info(f"Phase manually advanced: {old_phase + 1} -> {self.current_phase + 1}")

        return True, notification

    def get_status_summary(self) -> str:
        """Get human-readable status summary."""
        if not self.enabled:
            return "Progressive Sizing: DISABLED"

        phase_num = self.current_phase + 1
        phase_target = self.phase_targets[self.current_phase]

        status_lines = [
            f"Progressive Sizing Status:",
            f"Phase: {phase_num}/6 (${phase_target})",
            f"Successes: {self.consecutive_successes}/{self.validation_count}",
            f"Failures: {self.consecutive_failures}/{self.max_consecutive_failures}",
            f"Validated: {'YES' if self.phase_validated else 'NO'}",
        ]

        if self.pending_approval:
            status_lines.append(f"PENDING APPROVAL for Phase {phase_num + 1}")

        return "\n".join(status_lines)

    def get_csv_log_data(self) -> Dict:
        """Get data for CSV logging."""
        return {
            'current_phase': self.current_phase + 1,
            'phase_target_usd': float(self.phase_targets[self.current_phase]),
            'consecutive_successes': self.consecutive_successes,
            'consecutive_failures': self.consecutive_failures,
            'phase_validated': self.phase_validated,
            'pending_approval': self.pending_approval
        }
