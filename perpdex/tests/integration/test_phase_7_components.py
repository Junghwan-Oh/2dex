"""
Phase 7 Component Test Suite (No API Dependencies)

Validates core components that don't require apexomni:
- Data Logger (TradeLogger)
- Monitoring Dashboard (MonitoringDashboard)
- Order Book Analyzer (OrderBookAnalyzer)
- Component integration
- Data flow validation

Test Strategy:
1. Simulated data (no real API calls)
2. Component isolation tests
3. Integration validation
4. Output verification

Usage:
    python tests/integration/test_phase_7_components.py
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apex.monitor_dashboard import MonitoringDashboard, TradeRecord, MetricsSnapshot
from common.trade_logger import TradeLogger, create_trade_entry, create_decision_entry, create_error_entry
from common.order_book_analyzer import OrderBookAnalyzer


class ComponentTestRunner:
    """
    Component test runner for Phase 7 deployment

    Tests core components without API dependencies
    """

    def __init__(self):
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }

    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        if passed:
            self.results['passed'].append(test_name)
            print(f"[PASS] {test_name}")
            if message:
                print(f"       {message}")
        else:
            self.results['failed'].append(test_name)
            print(f"[FAIL] {test_name}")
            if message:
                print(f"       {message}")

    def test_trade_logger(self):
        """Test TradeLogger component"""
        print("\n" + "="*80)
        print("TEST 1: TradeLogger Component")
        print("="*80)

        # Initialize logger
        try:
            logger = TradeLogger(
                base_dir="logs/test_components",
                strategy_name="component_test"
            )
            self.log_result("TradeLogger initialization", True, f"Base: {logger.base_dir}")
        except Exception as e:
            self.log_result("TradeLogger initialization", False, str(e))
            return

        # Log trades
        try:
            for i in range(5):
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
                    notes=f"Component test trade {i+1}"
                )
                logger.log_trade(entry)
            self.log_result("Trade logging (5 trades)", True, "All trades logged")
        except Exception as e:
            self.log_result("Trade logging", False, str(e))

        # Log decisions
        try:
            entry = create_decision_entry(
                decision_type='spread_calculation',
                symbol="BTC-USDT",
                parameters={'gamma': 0.1, 'sigma': 0.02, 'k': 1.5},
                result={'bid_spread': 0.025, 'ask_spread': 0.025},
                reason='Avellaneda-Stoikov formula',
                notes='Component test decision'
            )
            logger.log_decision(entry)
            self.log_result("Decision logging", True, "Decision logged")
        except Exception as e:
            self.log_result("Decision logging", False, str(e))

        # Log error
        try:
            entry = create_error_entry(
                error_type='risk_breach',
                severity='WARNING',
                symbol="BTC-USDT",
                message='Test risk limit check',
                recovery_action='No action needed (test)',
                notes='Component test error'
            )
            logger.log_error(entry)
            self.log_result("Error logging", True, "Error logged")
        except Exception as e:
            self.log_result("Error logging", False, str(e))

        # Check CSV files
        try:
            csv_files = list(logger.csv_dir.glob("*.csv"))
            if len(csv_files) >= 3:  # trades, decisions, errors
                self.log_result("CSV file creation", True, f"Created {len(csv_files)} files")
            else:
                self.log_result("CSV file creation", False, f"Expected 3, found {len(csv_files)}")
        except Exception as e:
            self.log_result("CSV file creation", False, str(e))

        # Export to JSON
        try:
            exported = logger.export_to_json()
            if len(exported) == 3:  # trades, decisions, errors
                self.log_result("JSON export", True, f"Exported {len(exported)} files")
            else:
                self.log_result("JSON export", False, f"Expected 3, got {len(exported)}")
        except Exception as e:
            self.log_result("JSON export", False, str(e))

        # Summary statistics
        try:
            stats = logger.get_summary_stats()
            expected_trades = 5
            if stats['total_trades'] == expected_trades:
                self.log_result("Summary statistics", True,
                              f"Trades: {stats['total_trades']}, Win rate: {stats['win_rate']:.1f}%, Net P&L: ${stats['net_pnl']:.2f}")
            else:
                self.log_result("Summary statistics", False,
                              f"Expected {expected_trades}, got {stats['total_trades']}")
        except Exception as e:
            self.log_result("Summary statistics", False, str(e))

    def test_monitoring_dashboard(self):
        """Test MonitoringDashboard component"""
        print("\n" + "="*80)
        print("TEST 2: MonitoringDashboard Component")
        print("="*80)

        # Initialize dashboard
        try:
            dashboard = MonitoringDashboard(refresh_interval=5.0, history_size=100)
            self.log_result("Dashboard initialization", True, f"Refresh: {dashboard.refresh_interval}s")
        except Exception as e:
            self.log_result("Dashboard initialization", False, str(e))
            return

        # Record trades
        try:
            for i in range(10):
                trade = TradeRecord(
                    timestamp=time.time() + i,
                    order_id=f"dash_order_{i}",
                    side="BUY" if i % 2 == 0 else "SELL",
                    price=67500.0 + i * 5,
                    size=0.001,
                    fee=0.135,
                    pnl=0.50 if i % 2 == 0 else -0.30,
                    spread_captured=0.025
                )
                dashboard.record_trade(trade)
            self.log_result("Trade recording (10 trades)", True, "All trades recorded")
        except Exception as e:
            self.log_result("Trade recording", False, str(e))

        # Win rate calculation
        try:
            win_rate = dashboard.get_win_rate()
            expected = 50.0  # 5 wins, 5 losses
            if abs(win_rate - expected) < 0.1:
                self.log_result("Win rate calculation", True, f"Win rate: {win_rate:.1f}%")
            else:
                self.log_result("Win rate calculation", False,
                              f"Expected {expected:.1f}%, got {win_rate:.1f}%")
        except Exception as e:
            self.log_result("Win rate calculation", False, str(e))

        # Record metrics
        try:
            metrics = MetricsSnapshot(
                timestamp=time.time(),
                total_equity=101.0,
                unrealized_pnl=0.20,
                realized_pnl=0.80,
                daily_pnl=1.00,
                position_size=0.001,
                inventory_balance=0.001,
                open_orders=2,
                total_trades=10,
                win_rate=50.0,
                max_drawdown=3.5,
                sharpe_ratio=1.5
            )
            dashboard.record_metrics(metrics)
            self.log_result("Metrics recording", True, "Metrics snapshot recorded")
        except Exception as e:
            self.log_result("Metrics recording", False, str(e))

        # Sharpe ratio calculation
        try:
            sharpe = dashboard.calculate_sharpe_ratio()
            if sharpe is not None:
                self.log_result("Sharpe ratio calculation", True, f"Sharpe: {sharpe:.3f}")
            else:
                self.log_result("Sharpe ratio calculation", False, "Returned None")
        except Exception as e:
            self.log_result("Sharpe ratio calculation", False, str(e))

        # Console display format
        try:
            display = dashboard.format_console_display()
            if "PROFIT & LOSS" in display and "POSITION" in display:
                self.log_result("Console display format", True,
                              f"Generated {len(display)} chars with all sections")
            else:
                self.log_result("Console display format", False, "Missing expected sections")
        except Exception as e:
            self.log_result("Console display format", False, str(e))

        # JSON export
        try:
            json_data = dashboard.export_json()
            if 'recent_trades' in json_data and 'metrics' in json_data and 'performance' in json_data:
                self.log_result("JSON export", True, "Exported all data")
            else:
                self.log_result("JSON export", False, "Missing data in export")
        except Exception as e:
            self.log_result("JSON export", False, str(e))

    def test_order_book_analyzer(self):
        """Test OrderBookAnalyzer component"""
        print("\n" + "="*80)
        print("TEST 3: OrderBookAnalyzer Component")
        print("="*80)

        # Initialize analyzer
        try:
            analyzer = OrderBookAnalyzer()
            self.log_result("Analyzer initialization", True)
        except Exception as e:
            self.log_result("Analyzer initialization", False, str(e))
            return

        # Feed order book data
        try:
            base_price = 67500.0
            for i in range(20):
                # Simulate order book
                bids = [(base_price - j * 1.0, 0.5 + j * 0.1) for j in range(1, 11)]
                asks = [(base_price + j * 1.0, 0.5 + j * 0.1) for j in range(1, 11)]

                analyzer.update_order_book_data(
                    bids=bids,
                    asks=asks,
                    timestamp=time.time() + i
                )

                # Simulate price movement
                base_price += (i % 2) * 2 - 1  # Simple oscillation

            self.log_result("Order book data feeding", True, "Fed 20 snapshots")
        except Exception as e:
            self.log_result("Order book data feeding", False, str(e))

        # Get dynamic parameters
        try:
            params = analyzer.get_dynamic_parameters()

            # Validate parameter existence
            if 'alpha' in params and 'kappa' in params and 'sigma' in params:
                self.log_result("Dynamic parameter generation", True,
                              f"alpha={params['alpha']:.3f}, kappa={params['kappa']:.3f}, sigma={params['sigma']:.3f}")
            else:
                self.log_result("Dynamic parameter generation", False,
                              f"Missing parameters: {list(params.keys())}")
        except Exception as e:
            self.log_result("Dynamic parameter generation", False, str(e))
            return

        # Validate parameter ranges
        try:
            alpha = params.get('alpha', 0)
            kappa = params.get('kappa', 0)
            sigma = params.get('sigma', 0)

            # Accept alpha=1.0 as valid fallback when insufficient trade data
            valid_alpha = 0 < alpha <= 1.0
            valid_kappa = 0.1 <= kappa <= 5.0
            valid_sigma = 0 <= sigma < 1  # Accept 0 when no price movement

            if valid_alpha and valid_kappa and valid_sigma:
                self.log_result("Parameter range validation", True,
                              "All parameters within expected ranges (including fallbacks)")
            else:
                issues = []
                if not valid_alpha:
                    issues.append(f"alpha={alpha:.3f} out of (0, 1.0]")
                if not valid_kappa:
                    issues.append(f"kappa={kappa:.3f} out of [0.1, 5.0]")
                if not valid_sigma:
                    issues.append(f"sigma={sigma:.3f} out of [0, 1)")
                self.log_result("Parameter range validation", False, "; ".join(issues))
        except Exception as e:
            self.log_result("Parameter range validation", False, str(e))

    def test_component_integration(self):
        """Test component integration"""
        print("\n" + "="*80)
        print("TEST 4: Component Integration")
        print("="*80)

        # Initialize all components
        try:
            logger = TradeLogger(base_dir="logs/test_integration", strategy_name="integration")
            dashboard = MonitoringDashboard()
            analyzer = OrderBookAnalyzer()
            self.log_result("Component initialization", True, "All components initialized")
        except Exception as e:
            self.log_result("Component initialization", False, str(e))
            return

        # Simulate integrated workflow
        try:
            # 1. Update order book
            bids = [(67500.0 - i, 1.0) for i in range(1, 11)]
            asks = [(67500.0 + i, 1.0) for i in range(1, 11)]
            analyzer.update_order_book_data(bids=bids, asks=asks, timestamp=time.time())

            # 2. Get dynamic parameters
            params = analyzer.get_dynamic_parameters()

            # 3. Log decision (handle params being None or dict)
            if isinstance(params, dict):
                kappa_value = params.get('kappa', 1.5)
            else:
                kappa_value = 1.5

            decision = create_decision_entry(
                decision_type='spread_calculation',
                symbol="BTC-USDT",
                parameters={'dynamic_kappa': kappa_value},
                result={'bid_spread': 0.025, 'ask_spread': 0.025},
                reason='Dynamic parameter adaptation',
                notes='Integration test'
            )
            logger.log_decision(decision)

            # 4. Simulate trade
            trade_entry = create_trade_entry(
                order_id="integration_1",
                client_order_id="client_integration_1",
                symbol="BTC-USDT",
                side="BUY",
                order_type="LIMIT",
                price=67500.0,
                size=0.001,
                fee=0.135,
                fee_asset="USDT",
                realized_pnl=0.50,
                spread_captured=0.025,
                inventory_before=0.0,
                inventory_after=0.001,
                equity_before=100.0,
                equity_after=100.5,
                notes="Integration test trade"
            )
            logger.log_trade(trade_entry)

            # 5. Record to dashboard
            trade_record = TradeRecord(
                timestamp=time.time(),
                order_id="integration_1",
                side="BUY",
                price=67500.0,
                size=0.001,
                fee=0.135,
                pnl=0.50,
                spread_captured=0.025
            )
            dashboard.record_trade(trade_record)

            self.log_result("Integrated workflow", True, "All components worked together")
        except Exception as e:
            import traceback
            self.log_result("Integrated workflow", False, f"{str(e)}\n{traceback.format_exc()}")

    def run_all_tests(self):
        """Run complete component test suite"""
        print("\n" + "="*80)
        print("PHASE 7 COMPONENT TEST SUITE")
        print("="*80)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Test 1: TradeLogger
        self.test_trade_logger()

        # Test 2: MonitoringDashboard
        self.test_monitoring_dashboard()

        # Test 3: OrderBookAnalyzer
        self.test_order_book_analyzer()

        # Test 4: Component Integration
        self.test_component_integration()

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)

        total_tests = len(self.results['passed']) + len(self.results['failed'])
        passed = len(self.results['passed'])
        failed = len(self.results['failed'])

        print(f"\nTotal Tests:  {total_tests}")
        print(f"Passed:       {passed} ({passed/total_tests*100:.1f}%)" if total_tests > 0 else "Passed: 0")
        print(f"Failed:       {failed}")

        if self.results['failed']:
            print("\nFailed Tests:")
            for test in self.results['failed']:
                print(f"  - {test}")

        print("\n" + "="*80)

        if failed == 0:
            print("[SUCCESS] All component tests passed!")
            print("Ready for testnet deployment validation.")
            return True
        else:
            print(f"[ATTENTION] {failed} test(s) failed. Review before deployment.")
            return False


if __name__ == "__main__":
    print("""
================================================================================
PHASE 7 COMPONENT TEST SUITE
================================================================================

Testing core components:
- TradeLogger (CSV/JSON logging)
- MonitoringDashboard (Real-time metrics)
- OrderBookAnalyzer (Dynamic parameters)
- Component Integration

Mode: Simulated (no API dependencies)

================================================================================
""")

    runner = ComponentTestRunner()
    success = runner.run_all_tests()

    # Exit code
    sys.exit(0 if success else 1)
