"""
Trade Data Logger

Structured logging system for trade execution, strategic decisions, and performance analysis.

Purpose:
- Record all trades (entry/exit, prices, sizes, P&L)
- Log all strategic decisions (spread calculations, risk checks)
- Capture errors and exceptions
- Export to CSV/JSON for post-analysis
- Enable backtesting validation against live data

Design:
- Separate loggers for trades, decisions, and errors
- CSV format for time-series analysis (Excel, pandas)
- JSON format for machine-readable processing
- File rotation by date
- Atomic writes to prevent corruption

Integration:
- Complements structured logging (logging module = diagnostics, TradeLogger = data)
- Complements MonitoringDashboard (dashboard = real-time, logger = historical)
"""

import csv
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from threading import Lock


@dataclass
class TradeLogEntry:
    """Single trade execution record"""
    timestamp: float  # Unix timestamp
    datetime_utc: str  # ISO 8601 format for readability
    order_id: str
    client_order_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    order_type: str  # 'LIMIT', 'MARKET'
    price: float
    size: float
    fee: float
    fee_asset: str  # 'USDT' or base asset
    realized_pnl: float  # P&L from this trade
    spread_captured: float  # Spread % at entry (bid-ask)
    inventory_before: float  # Position before trade
    inventory_after: float  # Position after trade
    equity_before: float  # Account equity before
    equity_after: float  # Account equity after
    notes: str = ""  # Additional context


@dataclass
class DecisionLogEntry:
    """Strategic decision record"""
    timestamp: float
    datetime_utc: str
    decision_type: str  # 'spread_calculation', 'risk_check', 'rebalance', 'order_placement'
    symbol: str
    parameters: Dict[str, Any]  # Strategy parameters used
    result: Dict[str, Any]  # Decision outcome
    reason: str  # Human-readable explanation
    notes: str = ""


@dataclass
class ErrorLogEntry:
    """Error and exception record"""
    timestamp: float
    datetime_utc: str
    error_type: str  # 'order_failed', 'api_error', 'strategy_error', 'risk_breach'
    severity: str  # 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    symbol: str
    message: str
    exception_type: str = ""
    exception_message: str = ""
    stack_trace: str = ""
    recovery_action: str = ""
    notes: str = ""


class TradeLogger:
    """
    Structured data logger for trading activity

    Features:
    - Separate CSV files for trades, decisions, errors
    - JSON export for machine processing
    - Automatic file rotation by date
    - Thread-safe atomic writes
    - Integration with existing logging framework

    Usage:
        logger = TradeLogger(base_dir="logs/data", strategy_name="avellaneda_mm")

        # Log trade
        logger.log_trade(TradeLogEntry(...))

        # Log decision
        logger.log_decision(DecisionLogEntry(...))

        # Log error
        logger.log_error(ErrorLogEntry(...))

        # Export to JSON
        logger.export_to_json(start_time, end_time, output_file)
    """

    def __init__(
        self,
        base_dir: str = "logs/data",
        strategy_name: str = "trading_bot",
        enable_csv: bool = True,
        enable_json: bool = True
    ):
        """
        Initialize trade logger

        Args:
            base_dir: Base directory for log files
            strategy_name: Strategy identifier for file naming
            enable_csv: Enable CSV export
            enable_json: Enable JSON export
        """
        self.base_dir = Path(base_dir)
        self.strategy_name = strategy_name
        self.enable_csv = enable_csv
        self.enable_json = enable_json

        # Create directory structure
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.csv_dir = self.base_dir / "csv"
        self.json_dir = self.base_dir / "json"

        if self.enable_csv:
            self.csv_dir.mkdir(exist_ok=True)
        if self.enable_json:
            self.json_dir.mkdir(exist_ok=True)

        # Thread safety
        self._lock = Lock()

        # In-memory buffers for JSON export
        self.trade_buffer: List[TradeLogEntry] = []
        self.decision_buffer: List[DecisionLogEntry] = []
        self.error_buffer: List[ErrorLogEntry] = []

        # Current date for file rotation
        self._current_date = datetime.now().strftime("%Y%m%d")

    def _get_date_suffix(self) -> str:
        """Get current date suffix, trigger rotation if date changed"""
        current_date = datetime.now().strftime("%Y%m%d")
        if current_date != self._current_date:
            # Date changed, export yesterday's data to JSON
            self._export_daily_json(self._current_date)
            self._current_date = current_date
        return current_date

    def _get_csv_path(self, log_type: str) -> Path:
        """Get CSV file path with date rotation"""
        date_suffix = self._get_date_suffix()
        filename = f"{self.strategy_name}_{log_type}_{date_suffix}.csv"
        return self.csv_dir / filename

    def _write_csv_row(self, log_type: str, entry: Any):
        """Write single row to CSV file (thread-safe)"""
        if not self.enable_csv:
            return

        csv_path = self._get_csv_path(log_type)
        entry_dict = asdict(entry)

        with self._lock:
            # Check if file exists to determine if header needed
            file_exists = csv_path.exists()

            with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=entry_dict.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(entry_dict)

    def log_trade(self, entry: TradeLogEntry):
        """
        Log completed trade

        Args:
            entry: TradeLogEntry with all trade details
        """
        # Add to buffer for JSON export
        with self._lock:
            self.trade_buffer.append(entry)

        # Write to CSV
        self._write_csv_row("trades", entry)

    def log_decision(self, entry: DecisionLogEntry):
        """
        Log strategic decision

        Args:
            entry: DecisionLogEntry with decision context
        """
        with self._lock:
            self.decision_buffer.append(entry)

        self._write_csv_row("decisions", entry)

    def log_error(self, entry: ErrorLogEntry):
        """
        Log error or exception

        Args:
            entry: ErrorLogEntry with error details
        """
        with self._lock:
            self.error_buffer.append(entry)

        self._write_csv_row("errors", entry)

    def _export_daily_json(self, date_suffix: str):
        """Export buffered data to JSON file (internal, called on date change)"""
        if not self.enable_json:
            return

        with self._lock:
            # Export trades
            if self.trade_buffer:
                trades_file = self.json_dir / f"{self.strategy_name}_trades_{date_suffix}.json"
                with open(trades_file, 'w', encoding='utf-8') as f:
                    json.dump([asdict(t) for t in self.trade_buffer], f, indent=2)
                self.trade_buffer.clear()

            # Export decisions
            if self.decision_buffer:
                decisions_file = self.json_dir / f"{self.strategy_name}_decisions_{date_suffix}.json"
                with open(decisions_file, 'w', encoding='utf-8') as f:
                    json.dump([asdict(d) for d in self.decision_buffer], f, indent=2)
                self.decision_buffer.clear()

            # Export errors
            if self.error_buffer:
                errors_file = self.json_dir / f"{self.strategy_name}_errors_{date_suffix}.json"
                with open(errors_file, 'w', encoding='utf-8') as f:
                    json.dump([asdict(e) for e in self.error_buffer], f, indent=2)
                self.error_buffer.clear()

    def export_to_json(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        output_file: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Export data to JSON files (manual export)

        Args:
            start_time: Unix timestamp start filter (None = all)
            end_time: Unix timestamp end filter (None = all)
            output_file: Custom output filename (None = auto-generate)

        Returns:
            Dict with paths to exported files
        """
        if not self.enable_json:
            return {}

        exported = {}

        with self._lock:
            # Filter by time range if specified
            def in_range(entry) -> bool:
                ts = entry.timestamp
                if start_time and ts < start_time:
                    return False
                if end_time and ts > end_time:
                    return False
                return True

            # Trades
            trades_filtered = [t for t in self.trade_buffer if in_range(t)]
            if trades_filtered:
                filename = output_file or f"{self.strategy_name}_trades_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                path = self.json_dir / filename
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump([asdict(t) for t in trades_filtered], f, indent=2)
                exported['trades'] = str(path)

            # Decisions
            decisions_filtered = [d for d in self.decision_buffer if in_range(d)]
            if decisions_filtered:
                filename = output_file or f"{self.strategy_name}_decisions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                path = self.json_dir / filename
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump([asdict(d) for d in decisions_filtered], f, indent=2)
                exported['decisions'] = str(path)

            # Errors
            errors_filtered = [e for e in self.error_buffer if in_range(e)]
            if errors_filtered:
                filename = output_file or f"{self.strategy_name}_errors_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                path = self.json_dir / filename
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump([asdict(e) for e in errors_filtered], f, indent=2)
                exported['errors'] = str(path)

        return exported

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics from logged data

        Returns:
            Dict with trade count, win rate, total P&L, error count
        """
        with self._lock:
            total_trades = len(self.trade_buffer)
            winning_trades = sum(1 for t in self.trade_buffer if t.realized_pnl > 0)
            losing_trades = sum(1 for t in self.trade_buffer if t.realized_pnl < 0)
            total_pnl = sum(t.realized_pnl for t in self.trade_buffer)
            total_fees = sum(t.fee for t in self.trade_buffer)

            error_counts = {}
            for e in self.error_buffer:
                error_counts[e.error_type] = error_counts.get(e.error_type, 0) + 1

            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0.0,
                'total_pnl': total_pnl,
                'total_fees': total_fees,
                'net_pnl': total_pnl - total_fees,
                'total_decisions': len(self.decision_buffer),
                'total_errors': len(self.error_buffer),
                'error_breakdown': error_counts
            }

    def flush(self):
        """Flush all buffers to JSON files (manual flush)"""
        self._export_daily_json(self._current_date)


def create_trade_entry(
    order_id: str,
    client_order_id: str,
    symbol: str,
    side: str,
    order_type: str,
    price: float,
    size: float,
    fee: float,
    fee_asset: str,
    realized_pnl: float,
    spread_captured: float,
    inventory_before: float,
    inventory_after: float,
    equity_before: float,
    equity_after: float,
    notes: str = ""
) -> TradeLogEntry:
    """
    Helper to create TradeLogEntry with automatic timestamp

    Args:
        All trade parameters

    Returns:
        TradeLogEntry ready to log
    """
    now = datetime.now()
    return TradeLogEntry(
        timestamp=now.timestamp(),
        datetime_utc=now.isoformat(),
        order_id=order_id,
        client_order_id=client_order_id,
        symbol=symbol,
        side=side,
        order_type=order_type,
        price=price,
        size=size,
        fee=fee,
        fee_asset=fee_asset,
        realized_pnl=realized_pnl,
        spread_captured=spread_captured,
        inventory_before=inventory_before,
        inventory_after=inventory_after,
        equity_before=equity_before,
        equity_after=equity_after,
        notes=notes
    )


def create_decision_entry(
    decision_type: str,
    symbol: str,
    parameters: Dict[str, Any],
    result: Dict[str, Any],
    reason: str,
    notes: str = ""
) -> DecisionLogEntry:
    """
    Helper to create DecisionLogEntry with automatic timestamp

    Args:
        All decision parameters

    Returns:
        DecisionLogEntry ready to log
    """
    now = datetime.now()
    return DecisionLogEntry(
        timestamp=now.timestamp(),
        datetime_utc=now.isoformat(),
        decision_type=decision_type,
        symbol=symbol,
        parameters=parameters,
        result=result,
        reason=reason,
        notes=notes
    )


def create_error_entry(
    error_type: str,
    severity: str,
    symbol: str,
    message: str,
    exception_type: str = "",
    exception_message: str = "",
    stack_trace: str = "",
    recovery_action: str = "",
    notes: str = ""
) -> ErrorLogEntry:
    """
    Helper to create ErrorLogEntry with automatic timestamp

    Args:
        All error parameters

    Returns:
        ErrorLogEntry ready to log
    """
    now = datetime.now()
    return ErrorLogEntry(
        timestamp=now.timestamp(),
        datetime_utc=now.isoformat(),
        error_type=error_type,
        severity=severity,
        symbol=symbol,
        message=message,
        exception_type=exception_type,
        exception_message=exception_message,
        stack_trace=stack_trace,
        recovery_action=recovery_action,
        notes=notes
    )


# Example integration with trading client
def integrate_with_trading_client(client, logger: TradeLogger):
    """
    Integration example: Connect TradeLogger with trading client

    Args:
        client: AvellanedaApexClient instance
        logger: TradeLogger instance

    Usage:
        from common.trade_logger import TradeLogger, integrate_with_trading_client

        logger = TradeLogger(strategy_name="avellaneda_testnet")
        integrate_with_trading_client(client, logger)
    """

    # Hook: Log every order fill
    original_on_fill = getattr(client, 'on_order_filled', None)

    def on_order_filled_with_logging(order_data):
        # Extract trade details
        order_id = order_data.get('orderId', '')
        client_order_id = order_data.get('clientOrderId', '')
        side = order_data.get('side', '')
        price = float(order_data.get('price', 0))
        size = float(order_data.get('size', 0))
        fee = float(order_data.get('fee', 0))

        # Calculate P&L (simplified - real version needs more context)
        realized_pnl = 0.0  # Client should provide this

        # Create and log trade entry
        entry = create_trade_entry(
            order_id=order_id,
            client_order_id=client_order_id,
            symbol=client.symbol,
            side=side,
            order_type='LIMIT',
            price=price,
            size=size,
            fee=fee,
            fee_asset='USDT',
            realized_pnl=realized_pnl,
            spread_captured=0.0,  # Client should provide
            inventory_before=client.inventory_balance,
            inventory_after=client.inventory_balance + (size if side == 'BUY' else -size),
            equity_before=0.0,  # Client should provide
            equity_after=0.0,  # Client should provide
            notes=f"Order filled successfully"
        )
        logger.log_trade(entry)

        # Call original handler if exists
        if original_on_fill:
            original_on_fill(order_data)

    client.on_order_filled = on_order_filled_with_logging

    # Hook: Log spread calculations
    original_calculate_spread = client.calculate_optimal_spread

    def calculate_spread_with_logging(*args, **kwargs):
        result = original_calculate_spread(*args, **kwargs)

        # Log decision
        entry = create_decision_entry(
            decision_type='spread_calculation',
            symbol=client.symbol,
            parameters={
                'gamma': client.params.gamma,
                'sigma': client.params.sigma,
                'k': client.params.k,
                'dynamic_kappa': kwargs.get('dynamic_kappa')
            },
            result={
                'bid_spread': result[0],
                'ask_spread': result[1]
            },
            reason='Avellaneda-Stoikov optimal spread calculation',
            notes=f"Current price: {client.current_price}"
        )
        logger.log_decision(entry)

        return result

    client.calculate_optimal_spread = calculate_spread_with_logging

    # Hook: Log risk limit checks
    original_check_risk = client.check_risk_limits

    def check_risk_with_logging():
        is_safe, reason = original_check_risk()

        if not is_safe:
            # Log as error
            entry = create_error_entry(
                error_type='risk_breach',
                severity='CRITICAL',
                symbol=client.symbol,
                message=f"Risk limit breached: {reason}",
                recovery_action="Emergency shutdown, all orders cancelled",
                notes=f"Daily P&L: {client.daily_pnl}, Drawdown: calculated from peak"
            )
            logger.log_error(entry)

        return is_safe, reason

    client.check_risk_limits = check_risk_with_logging


if __name__ == "__main__":
    """Demo: TradeLogger usage"""

    # Initialize logger
    logger = TradeLogger(
        base_dir="logs/data",
        strategy_name="demo_strategy"
    )

    print("=== TradeLogger Demo ===\n")

    # Simulate some trades
    print("Logging trades...")
    for i in range(3):
        entry = create_trade_entry(
            order_id=f"order_{i+1}",
            client_order_id=f"client_{i+1}",
            symbol="BTC-USDT",
            side="BUY" if i % 2 == 0 else "SELL",
            order_type="LIMIT",
            price=67500.0 + i * 10,
            size=0.001,
            fee=0.135,
            fee_asset="USDT",
            realized_pnl=0.50 if i % 2 == 0 else -0.30,
            spread_captured=0.025,
            inventory_before=0.0,
            inventory_after=0.001 if i % 2 == 0 else -0.001,
            equity_before=100.0,
            equity_after=100.5 if i % 2 == 0 else 99.7,
            notes=f"Demo trade {i+1}"
        )
        logger.log_trade(entry)

    # Simulate decisions
    print("Logging decisions...")
    entry = create_decision_entry(
        decision_type='spread_calculation',
        symbol="BTC-USDT",
        parameters={'gamma': 0.1, 'sigma': 0.02, 'k': 1.5},
        result={'bid_spread': 0.025, 'ask_spread': 0.025},
        reason='Avellaneda-Stoikov formula',
        notes='Using static parameters'
    )
    logger.log_decision(entry)

    # Simulate error
    print("Logging error...")
    entry = create_error_entry(
        error_type='api_error',
        severity='WARNING',
        symbol="BTC-USDT",
        message='Order placement failed',
        exception_type='APIError',
        exception_message='Rate limit exceeded',
        recovery_action='Retry after 1 second',
        notes='Temporary API issue'
    )
    logger.log_error(entry)

    # Get summary
    print("\n=== Summary Stats ===")
    stats = logger.get_summary_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")

    # Export to JSON
    print("\n=== Exporting to JSON ===")
    exported = logger.export_to_json()
    for log_type, path in exported.items():
        print(f"{log_type}: {path}")

    print("\n[OK] Demo complete. Check logs/data/ directory for output files.")
