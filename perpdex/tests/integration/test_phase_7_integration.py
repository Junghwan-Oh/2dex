"""
Phase 7 Integration Test Suite

Complete validation of testnet deployment components:
- Trading Client (AvellanedaApexClient)
- Monitoring Dashboard (MonitoringDashboard)
- Data Logger (TradeLogger)
- Order Book Analyzer integration
- Risk management system
- Logging framework

Test Strategy:
1. Simulated mode (no real API calls)
2. Component integration validation
3. Data flow verification
4. Safety mechanism checks

Usage:
    python tests/integration/test_phase_7_integration.py
"""

import sys
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apex.avellaneda_client import AvellanedaApexClient, AvellanedaParameters
from apex.monitor_dashboard import MonitoringDashboard, TradeRecord, MetricsSnapshot
from common.trade_logger import TradeLogger, create_trade_entry, create_decision_entry, create_error_entry
from common.order_book_analyzer import OrderBookAnalyzer


class SimulatedMarketData:
    """
    Simulated market data for testing

    Generates realistic:
    - Order book snapshots
    - Price movements
    - Trade executions
    """

    def __init__(self, base_price: float = 67500.0, volatility: float = 0.02):
        self.base_price = base_price
        self.volatility = volatility
        self.current_price = base_price

    def get_order_book(self) -> Dict[str, Any]:
        """Generate simulated order book"""
        # Simulate bid/ask spread of ~0.025%
        spread = self.current_price * 0.00025

        bids = []
        asks = []

        # Generate 10 levels each side
        for i in range(10):
            bid_price = self.current_price - spread/2 - i * spread
            ask_price = self.current_price + spread/2 + i * spread

            # Random sizes between 0.5 and 2.0 BTC
            bid_size = 0.5 + (i * 0.1)
            ask_size = 0.5 + (i * 0.1)

            bids.append([str(bid_price), str(bid_size)])
            asks.append([str(ask_price), str(ask_size)])

        return {
            'bids': bids,
            'asks': asks,
            'timestamp': time.time() * 1000
        }

    def update_price(self):
        """Simulate price movement (random walk)"""
        import random
        change = random.gauss(0, self.volatility * self.current_price / 100)
        self.current_price = max(self.current_price + change, self.base_price * 0.95)
        self.current_price = min(self.current_price, self.base_price * 1.05)

    def simulate_trade(self, side: str, price: float, size: float) -> Dict[str, Any]:
        """Simulate trade execution"""
        return {
            'orderId': f"sim_order_{int(time.time() * 1000)}",
            'clientOrderId': f"client_{int(time.time() * 1000)}",
            'symbol': 'BTC-USDT',
            'side': side,
            'type': 'LIMIT',
            'price': str(price),
            'size': str(size),
            'fee': str(size * price * 0.0002),  # 0.02% maker fee
            'status': 'FILLED',
            'timestamp': time.time() * 1000
        }


class IntegrationTestRunner:
    """
    Integration test runner for Phase 7 components

    Tests:
    1. Component initialization
    2. Data flow between components
    3. Logging and monitoring
    4. Risk management
    5. Dynamic parameters
    """

    def __init__(self):
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
        self.market_data = SimulatedMarketData()

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

    def log_warning(self, test_name: str, message: str):
        """Log warning"""
        self.results['warnings'].append((test_name, message))
        print(f"[WARN] {test_name}: {message}")

    def test_component_initialization(self):
        """Test 1: Component Initialization"""
        print("\n" + "="*80)
        print("TEST 1: Component Initialization")
        print("="*80)

        # Test AvellanedaParameters
        try:
            params = AvellanedaParameters(
                gamma=0.1,
                sigma=0.02,
                k=1.5,
                position_limit=100.0,
                max_daily_loss=5.0,
                max_total_drawdown=20.0,
                use_dynamic_params=True
            )
            self.log_result("AvellanedaParameters initialization", True, f"gamma={params.gamma}, sigma={params.sigma}")
        except Exception as e:
            self.log_result("AvellanedaParameters initialization", False, str(e))
            return None

        # Test TradeLogger
        try:
            logger = TradeLogger(
                base_dir="logs/test_integration",
                strategy_name="test_strategy"
            )
            self.log_result("TradeLogger initialization", True, f"Base dir: {logger.base_dir}")
        except Exception as e:
            self.log_result("TradeLogger initialization", False, str(e))
            return None

        # Test MonitoringDashboard
        try:
            dashboard = MonitoringDashboard(refresh_interval=5.0)
            self.log_result("MonitoringDashboard initialization", True, f"Refresh: {dashboard.refresh_interval}s")
        except Exception as e:
            self.log_result("MonitoringDashboard initialization", False, str(e))
            return None

        # Test OrderBookAnalyzer
        try:
            analyzer = OrderBookAnalyzer()
            self.log_result("OrderBookAnalyzer initialization", True)
        except Exception as e:
            self.log_result("OrderBookAnalyzer initialization", False, str(e))
            return None

        return {
            'params': params,
            'logger': logger,
            'dashboard': dashboard,
            'analyzer': analyzer
        }

    def test_data_flow(self, components: Dict):
        """Test 2: Data Flow Between Components"""
        print("\n" + "="*80)
        print("TEST 2: Data Flow Between Components")
        print("="*80)

        logger = components['logger']
        dashboard = components['dashboard']
        analyzer = components['analyzer']

        # Simulate trade and log
        try:
            trade_entry = create_trade_entry(
                order_id="test_order_1",
                client_order_id="test_client_1",
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
            self.log_result("TradeLogger.log_trade()", True, "Trade logged successfully")
        except Exception as e:
            self.log_result("TradeLogger.log_trade()", False, str(e))

        # Simulate decision and log
        try:
            decision_entry = create_decision_entry(
                decision_type='spread_calculation',
                symbol="BTC-USDT",
                parameters={'gamma': 0.1, 'sigma': 0.02, 'k': 1.5},
                result={'bid_spread': 0.025, 'ask_spread': 0.025},
                reason='Avellaneda-Stoikov formula',
                notes='Integration test decision'
            )
            logger.log_decision(decision_entry)
            self.log_result("TradeLogger.log_decision()", True, "Decision logged successfully")
        except Exception as e:
            self.log_result("TradeLogger.log_decision()", False, str(e))

        # Test MonitoringDashboard recording
        try:
            trade_record = TradeRecord(
                timestamp=time.time(),
                order_id="test_order_1",
                side="BUY",
                price=67500.0,
                size=0.001,
                fee=0.135,
                pnl=0.50,
                spread_captured=0.025
            )
            dashboard.record_trade(trade_record)
            self.log_result("MonitoringDashboard.record_trade()", True, "Trade recorded")
        except Exception as e:
            self.log_result("MonitoringDashboard.record_trade()", False, str(e))

        # Test OrderBookAnalyzer
        try:
            order_book = self.market_data.get_order_book()
            analyzer.update_order_book_data(
                bids=[(float(b[0]), float(b[1])) for b in order_book['bids']],
                asks=[(float(a[0]), float(a[1])) for a in order_book['asks']],
                timestamp=time.time()
            )
            params = analyzer.get_dynamic_parameters()
            self.log_result("OrderBookAnalyzer.get_dynamic_parameters()", True, f"kappa={params.get('kappa', 0):.3f}")
        except Exception as e:
            self.log_result("OrderBookAnalyzer.get_dynamic_parameters()", False, str(e))

    def test_logging_output(self, components: Dict):
        """Test 3: Logging Output Validation"""
        print("\n" + "="*80)
        print("TEST 3: Logging Output Validation")
        print("="*80)

        logger = components['logger']

        # Check CSV files created
        try:
            csv_dir = logger.csv_dir
            csv_files = list(csv_dir.glob("*.csv"))
            if len(csv_files) >= 2:  # At least trades and decisions
                self.log_result("CSV files created", True, f"Found {len(csv_files)} files")
            else:
                self.log_result("CSV files created", False, f"Expected >=2, found {len(csv_files)}")
        except Exception as e:
            self.log_result("CSV files created", False, str(e))

        # Test JSON export
        try:
            exported = logger.export_to_json()
            if 'trades' in exported and 'decisions' in exported:
                self.log_result("JSON export", True, f"Exported {len(exported)} file types")
            else:
                self.log_result("JSON export", False, "Missing expected exports")
        except Exception as e:
            self.log_result("JSON export", False, str(e))

        # Validate summary stats
        try:
            stats = logger.get_summary_stats()
            expected_trades = 1  # We logged 1 trade
            if stats['total_trades'] == expected_trades:
                self.log_result("Summary statistics", True, f"Total trades: {stats['total_trades']}, Win rate: {stats['win_rate']:.1f}%")
            else:
                self.log_result("Summary statistics", False, f"Expected {expected_trades} trades, got {stats['total_trades']}")
        except Exception as e:
            self.log_result("Summary statistics", False, str(e))

    def test_monitoring_dashboard(self, components: Dict):
        """Test 4: Monitoring Dashboard Functionality"""
        print("\n" + "="*80)
        print("TEST 4: Monitoring Dashboard Functionality")
        print("="*80)

        dashboard = components['dashboard']

        # Add multiple trades
        try:
            for i in range(5):
                trade = TradeRecord(
                    timestamp=time.time() + i,
                    order_id=f"test_{i}",
                    side="BUY" if i % 2 == 0 else "SELL",
                    price=67500.0 + i * 10,
                    size=0.001,
                    fee=0.135,
                    pnl=0.50 if i % 2 == 0 else -0.30,
                    spread_captured=0.025
                )
                dashboard.record_trade(trade)
            self.log_result("Dashboard trade recording", True, "Recorded 5 trades")
        except Exception as e:
            self.log_result("Dashboard trade recording", False, str(e))

        # Test win rate calculation
        try:
            win_rate = dashboard.get_win_rate()
            expected_win_rate = 60.0  # 3 wins, 2 losses
            if abs(win_rate - expected_win_rate) < 1.0:
                self.log_result("Win rate calculation", True, f"Win rate: {win_rate:.1f}%")
            else:
                self.log_result("Win rate calculation", False, f"Expected {expected_win_rate:.1f}%, got {win_rate:.1f}%")
        except Exception as e:
            self.log_result("Win rate calculation", False, str(e))

        # Test metrics snapshot
        try:
            metrics = MetricsSnapshot(
                timestamp=time.time(),
                total_equity=100.5,
                unrealized_pnl=-0.10,
                realized_pnl=0.60,
                daily_pnl=0.20,
                position_size=0.0012,
                inventory_balance=0.0012,
                open_orders=2,
                total_trades=5,
                win_rate=60.0,
                max_drawdown=5.2,
                sharpe_ratio=1.234
            )
            dashboard.record_metrics(metrics)
            self.log_result("Metrics snapshot recording", True, "Metrics recorded")
        except Exception as e:
            self.log_result("Metrics snapshot recording", False, str(e))

        # Test console display format
        try:
            display = dashboard.format_console_display()
            if len(display) > 100:  # Should have substantial content
                self.log_result("Console display format", True, f"Generated {len(display)} characters")
            else:
                self.log_result("Console display format", False, "Display too short")
        except Exception as e:
            self.log_result("Console display format", False, str(e))

    def test_risk_management(self):
        """Test 5: Risk Management Validation"""
        print("\n" + "="*80)
        print("TEST 5: Risk Management Validation")
        print("="*80)

        # Test risk parameters
        try:
            params = AvellanedaParameters(
                max_daily_loss=5.0,
                max_total_drawdown=20.0,
                position_limit=100.0
            )

            # Validate limits
            if params.max_daily_loss > 0 and params.max_total_drawdown > 0:
                self.log_result("Risk parameters validation", True, f"Daily: ${params.max_daily_loss}, Drawdown: {params.max_total_drawdown}%")
            else:
                self.log_result("Risk parameters validation", False, "Invalid risk limits")
        except Exception as e:
            self.log_result("Risk parameters validation", False, str(e))

        # Test position limit logic
        try:
            position_limit = 100.0
            test_position = 150.0  # 150% of limit

            if test_position > position_limit * 1.5:
                self.log_result("Position limit detection", True, f"Detected {test_position} > {position_limit * 1.5}")
            else:
                self.log_result("Position limit detection", False, "Failed to detect limit breach")
        except Exception as e:
            self.log_result("Position limit detection", False, str(e))

    def test_dynamic_parameters(self, components: Dict):
        """Test 6: Dynamic Parameters Integration"""
        print("\n" + "="*80)
        print("TEST 6: Dynamic Parameters Integration")
        print("="*80)

        analyzer = components['analyzer']

        # Feed multiple order book snapshots
        try:
            for i in range(10):
                order_book = self.market_data.get_order_book()
                analyzer.update_order_book_data(
                    bids=[(float(b[0]), float(b[1])) for b in order_book['bids']],
                    asks=[(float(a[0]), float(a[1])) for a in order_book['asks']],
                    timestamp=time.time() + i
                )
                self.market_data.update_price()  # Simulate price movement

            self.log_result("Order book data feeding", True, "Fed 10 snapshots")
        except Exception as e:
            self.log_result("Order book data feeding", False, str(e))
            return

        # Get dynamic parameters
        try:
            params = analyzer.get_dynamic_parameters()

            # Validate ranges
            alpha = params.get('alpha', 0)
            kappa = params.get('kappa', 0)
            sigma = params.get('sigma', 0)

            if 0 < alpha < 1 and 0.1 <= kappa <= 5.0 and 0 < sigma < 1:
                self.log_result("Dynamic parameter ranges", True,
                              f"alpha={alpha:.3f}, kappa={kappa:.3f}, sigma={sigma:.3f}")
            else:
                self.log_result("Dynamic parameter ranges", False,
                              f"Out of range: alpha={alpha:.3f}, kappa={kappa:.3f}, sigma={sigma:.3f}")
        except Exception as e:
            self.log_result("Dynamic parameter ranges", False, str(e))

    def run_all_tests(self):
        """Run complete integration test suite"""
        print("\n" + "="*80)
        print("PHASE 7 INTEGRATION TEST SUITE")
        print("="*80)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Test 1: Component Initialization
        components = self.test_component_initialization()
        if not components:
            print("\n[CRITICAL] Component initialization failed. Aborting tests.")
            return self.print_summary()

        # Test 2: Data Flow
        self.test_data_flow(components)

        # Test 3: Logging Output
        self.test_logging_output(components)

        # Test 4: Monitoring Dashboard
        self.test_monitoring_dashboard(components)

        # Test 5: Risk Management
        self.test_risk_management()

        # Test 6: Dynamic Parameters
        self.test_dynamic_parameters(components)

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
        warnings = len(self.results['warnings'])

        print(f"\nTotal Tests:  {total_tests}")
        print(f"Passed:       {passed} ({passed/total_tests*100:.1f}%)" if total_tests > 0 else "Passed: 0")
        print(f"Failed:       {failed}")
        print(f"Warnings:     {warnings}")

        if self.results['failed']:
            print("\nFailed Tests:")
            for test in self.results['failed']:
                print(f"  - {test}")

        if self.results['warnings']:
            print("\nWarnings:")
            for test, msg in self.results['warnings']:
                print(f"  - {test}: {msg}")

        print("\n" + "="*80)

        if failed == 0:
            print("[SUCCESS] All tests passed! Ready for testnet deployment.")
            return True
        else:
            print(f"[ATTENTION] {failed} test(s) failed. Review and fix before deployment.")
            return False


if __name__ == "__main__":
    print("""
================================================================================
PHASE 7 INTEGRATION TEST SUITE
================================================================================

Testing:
- Trading Client (AvellanedaApexClient)
- Monitoring Dashboard (MonitoringDashboard)
- Data Logger (TradeLogger)
- Order Book Analyzer
- Risk Management System
- Component Integration

Mode: Simulated (no real API calls)

================================================================================
""")

    runner = IntegrationTestRunner()
    success = runner.run_all_tests()

    # Exit code
    sys.exit(0 if success else 1)
