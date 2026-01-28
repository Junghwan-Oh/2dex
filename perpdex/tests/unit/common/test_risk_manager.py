"""
RiskManager 유닛 테스트

TDD 방식: 테스트를 먼저 작성하고 구현은 나중에
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from common.lib.risk_manager import RiskManager, RiskConfig


class TestRiskManager:
    """리스크 관리 클래스 테스트"""

    @pytest.fixture
    def defaultConfig(self):
        """기본 리스크 설정"""
        return RiskConfig(
            maxDrawdown=0.15,        # 15% 최대 낙폭
            maxDailyLoss=500.0,      # $500 일일 최대 손실
            maxDailyTrades=200,      # 일일 최대 거래 200회
            maxExposure=50000.0      # $50,000 최대 노출
        )

    @pytest.fixture
    def riskManager(self, defaultConfig):
        """기본 RiskManager 인스턴스"""
        return RiskManager(defaultConfig)

    # ========== Drawdown Tests ==========

    def test_drawdown_within_limit(self, riskManager):
        """낙폭이 허용 범위 내"""
        currentEquity = 9000.0
        peakEquity = 10000.0
        # Drawdown: (10000 - 9000) / 10000 = 10% < 15%
        assert riskManager.checkDrawdown(currentEquity, peakEquity) == True

    def test_drawdown_at_limit(self, riskManager):
        """낙폭이 정확히 한계값"""
        currentEquity = 8500.0
        peakEquity = 10000.0
        # Drawdown: (10000 - 8500) / 10000 = 15% = 15%
        assert riskManager.checkDrawdown(currentEquity, peakEquity) == True

    def test_drawdown_exceeds_limit(self, riskManager):
        """낙폭이 한계값 초과"""
        currentEquity = 8400.0
        peakEquity = 10000.0
        # Drawdown: (10000 - 8400) / 10000 = 16% > 15%
        assert riskManager.checkDrawdown(currentEquity, peakEquity) == False

    def test_drawdown_no_loss(self, riskManager):
        """손실이 없는 경우"""
        currentEquity = 11000.0
        peakEquity = 10000.0
        # Profit, not drawdown
        assert riskManager.checkDrawdown(currentEquity, peakEquity) == True

    # ========== Daily Loss Tests ==========

    def test_daily_loss_within_limit(self, riskManager):
        """일일 손실이 허용 범위 내"""
        dailyPnl = -400.0
        # Loss: $400 < $500
        assert riskManager.checkDailyLoss(dailyPnl) == True

    def test_daily_loss_at_limit(self, riskManager):
        """일일 손실이 정확히 한계값"""
        dailyPnl = -500.0
        # Loss: $500 = $500
        assert riskManager.checkDailyLoss(dailyPnl) == True

    def test_daily_loss_exceeds_limit(self, riskManager):
        """일일 손실이 한계값 초과"""
        dailyPnl = -501.0
        # Loss: $501 > $500
        assert riskManager.checkDailyLoss(dailyPnl) == False

    def test_daily_profit(self, riskManager):
        """일일 수익이 있는 경우"""
        dailyPnl = 300.0
        # Profit, not loss
        assert riskManager.checkDailyLoss(dailyPnl) == True

    # ========== Trade Limit Tests ==========

    def test_trade_count_within_limit(self, riskManager):
        """거래 횟수가 허용 범위 내"""
        tradesCount = 150
        # 150 < 200
        assert riskManager.checkTradeLimit(tradesCount) == True

    def test_trade_count_at_limit(self, riskManager):
        """거래 횟수가 정확히 한계값"""
        tradesCount = 200
        # 200 = 200
        assert riskManager.checkTradeLimit(tradesCount) == True

    def test_trade_count_exceeds_limit(self, riskManager):
        """거래 횟수가 한계값 초과"""
        tradesCount = 201
        # 201 > 200
        assert riskManager.checkTradeLimit(tradesCount) == False

    def test_trade_count_zero(self, riskManager):
        """거래 횟수가 0인 경우"""
        tradesCount = 0
        assert riskManager.checkTradeLimit(tradesCount) == True

    # ========== Exposure Tests ==========

    def test_exposure_within_limit(self, riskManager):
        """노출이 허용 범위 내"""
        totalNotional = 40000.0
        # $40,000 < $50,000
        assert riskManager.checkExposure(totalNotional) == True

    def test_exposure_at_limit(self, riskManager):
        """노출이 정확히 한계값"""
        totalNotional = 50000.0
        # $50,000 = $50,000
        assert riskManager.checkExposure(totalNotional) == True

    def test_exposure_exceeds_limit(self, riskManager):
        """노출이 한계값 초과"""
        totalNotional = 50001.0
        # $50,001 > $50,000
        assert riskManager.checkExposure(totalNotional) == False

    def test_exposure_zero(self, riskManager):
        """노출이 0인 경우"""
        totalNotional = 0.0
        assert riskManager.checkExposure(totalNotional) == True

    # ========== Overall Halt Tests ==========

    def test_should_halt_all_safe(self, riskManager):
        """모든 조건이 안전한 경우"""
        # Safe conditions
        riskManager.checkDrawdown(9000.0, 10000.0)  # 10% drawdown
        riskManager.checkDailyLoss(-400.0)           # $400 loss
        riskManager.checkTradeLimit(150)             # 150 trades
        riskManager.checkExposure(40000.0)           # $40K exposure

        assert riskManager.shouldHalt() == False

    def test_should_halt_drawdown_breach(self, riskManager):
        """낙폭 위반 시 중단"""
        # Drawdown breach: 16% > 15%
        riskManager.checkDrawdown(8400.0, 10000.0)
        assert riskManager.shouldHalt() == True

    def test_should_halt_daily_loss_breach(self, riskManager):
        """일일 손실 위반 시 중단"""
        # Daily loss breach: $501 > $500
        riskManager.checkDailyLoss(-501.0)
        assert riskManager.shouldHalt() == True

    def test_should_halt_trade_limit_breach(self, riskManager):
        """거래 횟수 위반 시 중단"""
        # Trade limit breach: 201 > 200
        riskManager.checkTradeLimit(201)
        assert riskManager.shouldHalt() == True

    def test_should_halt_exposure_breach(self, riskManager):
        """노출 위반 시 중단"""
        # Exposure breach: $50,001 > $50,000
        riskManager.checkExposure(50001.0)
        assert riskManager.shouldHalt() == True

    def test_should_halt_multiple_breaches(self, riskManager):
        """여러 조건 위반 시 중단"""
        # Multiple breaches
        riskManager.checkDrawdown(8000.0, 10000.0)   # 20% drawdown
        riskManager.checkDailyLoss(-600.0)            # $600 loss
        riskManager.checkTradeLimit(250)              # 250 trades

        assert riskManager.shouldHalt() == True

    # ========== Reset Tests ==========

    def test_reset_violations(self, riskManager):
        """위반 상태 초기화"""
        # Set violations
        riskManager.checkDrawdown(8000.0, 10000.0)   # Breach
        riskManager.checkDailyLoss(-600.0)            # Breach
        assert riskManager.shouldHalt() == True

        # Reset
        riskManager.reset()

        # Should be clear now
        assert riskManager.shouldHalt() == False

    # ========== Custom Config Tests ==========

    def test_custom_config_stricter_limits(self):
        """더 엄격한 리스크 설정"""
        strictConfig = RiskConfig(
            maxDrawdown=0.10,        # 10% 최대 낙폭
            maxDailyLoss=300.0,      # $300 일일 최대 손실
            maxDailyTrades=100,      # 일일 최대 거래 100회
            maxExposure=30000.0      # $30,000 최대 노출
        )
        strictManager = RiskManager(strictConfig)

        # Test stricter drawdown
        assert strictManager.checkDrawdown(9100.0, 10000.0) == True   # 9% OK
        assert strictManager.checkDrawdown(8900.0, 10000.0) == False  # 11% BREACH

        # Test stricter daily loss
        assert strictManager.checkDailyLoss(-299.0) == True   # OK
        assert strictManager.checkDailyLoss(-301.0) == False  # BREACH

    def test_custom_config_relaxed_limits(self):
        """더 완화된 리스크 설정"""
        relaxedConfig = RiskConfig(
            maxDrawdown=0.25,        # 25% 최대 낙폭
            maxDailyLoss=1000.0,     # $1,000 일일 최대 손실
            maxDailyTrades=500,      # 일일 최대 거래 500회
            maxExposure=100000.0     # $100,000 최대 노출
        )
        relaxedManager = RiskManager(relaxedConfig)

        # Test relaxed drawdown
        assert relaxedManager.checkDrawdown(7600.0, 10000.0) == True   # 24% OK
        assert relaxedManager.checkDrawdown(7400.0, 10000.0) == False  # 26% BREACH

        # Test relaxed daily loss
        assert relaxedManager.checkDailyLoss(-999.0) == True   # OK
        assert relaxedManager.checkDailyLoss(-1001.0) == False  # BREACH

    # ========== Edge Cases ==========

    def test_zero_peak_equity(self, riskManager):
        """최고 자산이 0인 경우 (edge case)"""
        # Division by zero scenario - should handle gracefully
        with pytest.raises(ValueError):
            riskManager.checkDrawdown(5000.0, 0.0)

    def test_negative_equity(self, riskManager):
        """음수 자산 (edge case)"""
        # Negative equity should fail
        assert riskManager.checkDrawdown(-1000.0, 10000.0) == False

    def test_negative_trade_count(self, riskManager):
        """음수 거래 횟수 (invalid input)"""
        # Negative trades should fail
        with pytest.raises(ValueError):
            riskManager.checkTradeLimit(-5)

    def test_negative_exposure(self, riskManager):
        """음수 노출 (invalid input)"""
        # Negative exposure should fail
        with pytest.raises(ValueError):
            riskManager.checkExposure(-10000.0)
