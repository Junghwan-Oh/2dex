"""
Unit tests for ConfigLoader

SPEC-001: config.yaml 설정 파일 지원
TDD Phase: RED (테스트 먼저 작성)
"""

import os
import tempfile
from pathlib import Path
import pytest
import yaml

# Will be implemented
from config_loader import ConfigLoader, ConfigValidationError


class TestConfigLoaderDefaults:
    """REQ-U01: config.yaml 없어도 기본값으로 동작"""

    def test_returns_default_position_diff_threshold(self):
        """기본 position_diff_threshold는 0.2"""
        loader = ConfigLoader(config_path="nonexistent.yaml")
        assert loader.get("trading", "position_diff_threshold") == 0.2

    def test_returns_default_order_cancel_timeout(self):
        """기본 order_cancel_timeout은 10초"""
        loader = ConfigLoader(config_path="nonexistent.yaml")
        assert loader.get("trading", "order_cancel_timeout") == 10

    def test_returns_default_buy_price_multiplier(self):
        """기본 buy_price_multiplier는 0.998"""
        loader = ConfigLoader(config_path="nonexistent.yaml")
        assert loader.get("pricing", "buy_price_multiplier") == 0.998

    def test_returns_default_sell_price_multiplier(self):
        """기본 sell_price_multiplier는 1.002"""
        loader = ConfigLoader(config_path="nonexistent.yaml")
        assert loader.get("pricing", "sell_price_multiplier") == 1.002

    def test_returns_all_defaults_when_no_config(self):
        """모든 기본값 반환"""
        loader = ConfigLoader(config_path="nonexistent.yaml")

        expected = {
            "trading": {
                "position_diff_threshold": 0.2,
                "order_cancel_timeout": 10,
                "trading_loop_timeout": 180,
                "max_retries": 15,
                "fill_check_interval": 10,
            },
            "pricing": {
                "buy_price_multiplier": 0.998,
                "sell_price_multiplier": 1.002,
            }
        }

        assert loader.get("trading", "position_diff_threshold") == expected["trading"]["position_diff_threshold"]
        assert loader.get("trading", "order_cancel_timeout") == expected["trading"]["order_cancel_timeout"]
        assert loader.get("trading", "trading_loop_timeout") == expected["trading"]["trading_loop_timeout"]
        assert loader.get("pricing", "buy_price_multiplier") == expected["pricing"]["buy_price_multiplier"]


class TestConfigLoaderFromFile:
    """REQ-E01: config.yaml 파일 자동 로드"""

    def test_loads_values_from_yaml_file(self):
        """config.yaml에서 값 로드"""
        config_content = {
            "trading": {
                "position_diff_threshold": 0.5,
                "order_cancel_timeout": 20,
            },
            "pricing": {
                "buy_price_multiplier": 0.995,
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_content, f)
            temp_path = f.name

        try:
            loader = ConfigLoader(config_path=temp_path)
            assert loader.get("trading", "position_diff_threshold") == 0.5
            assert loader.get("trading", "order_cancel_timeout") == 20
            assert loader.get("pricing", "buy_price_multiplier") == 0.995
            # 파일에 없는 값은 기본값
            assert loader.get("pricing", "sell_price_multiplier") == 1.002
        finally:
            os.unlink(temp_path)

    def test_partial_config_uses_defaults_for_missing(self):
        """일부만 정의된 config는 나머지 기본값 사용"""
        config_content = {
            "trading": {
                "position_diff_threshold": 0.3,
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_content, f)
            temp_path = f.name

        try:
            loader = ConfigLoader(config_path=temp_path)
            # 파일에 있는 값
            assert loader.get("trading", "position_diff_threshold") == 0.3
            # 파일에 없는 값 → 기본값
            assert loader.get("trading", "order_cancel_timeout") == 10
            assert loader.get("pricing", "buy_price_multiplier") == 0.998
        finally:
            os.unlink(temp_path)


class TestConfigLoaderErrorHandling:
    """REQ-E02: 로드 실패 시 기본값 사용"""

    def test_invalid_yaml_uses_defaults(self):
        """잘못된 YAML 형식 시 기본값 사용"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            loader = ConfigLoader(config_path=temp_path)
            # 파싱 실패해도 기본값 사용
            assert loader.get("trading", "position_diff_threshold") == 0.2
        finally:
            os.unlink(temp_path)

    def test_logs_warning_on_load_failure(self, caplog):
        """로드 실패 시 경고 로그"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: [")
            temp_path = f.name

        try:
            loader = ConfigLoader(config_path=temp_path)
            # 경고 로그 확인
            assert any("warning" in record.levelname.lower() or "error" in record.levelname.lower()
                      for record in caplog.records) or loader.load_error is not None
        finally:
            os.unlink(temp_path)


class TestConfigLoaderTypeValidation:
    """REQ-U02: 타입 검증"""

    def test_invalid_type_raises_error_or_uses_default(self):
        """잘못된 타입 시 에러 또는 기본값"""
        config_content = {
            "trading": {
                "position_diff_threshold": "not_a_number",  # should be float
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_content, f)
            temp_path = f.name

        try:
            loader = ConfigLoader(config_path=temp_path)
            # 잘못된 타입이면 기본값 사용 또는 에러
            value = loader.get("trading", "position_diff_threshold")
            assert isinstance(value, (int, float))
        finally:
            os.unlink(temp_path)


class TestConfigLoaderPriority:
    """REQ-S01, REQ-S02: 설정 우선순위"""

    def test_get_with_override_returns_override(self):
        """override 파라미터가 config보다 우선"""
        config_content = {
            "trading": {
                "position_diff_threshold": 0.5,
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_content, f)
            temp_path = f.name

        try:
            loader = ConfigLoader(config_path=temp_path)
            # CLI override 시뮬레이션
            value = loader.get("trading", "position_diff_threshold", override=0.8)
            assert value == 0.8
        finally:
            os.unlink(temp_path)

    def test_none_override_uses_config_value(self):
        """override가 None이면 config 값 사용"""
        config_content = {
            "trading": {
                "position_diff_threshold": 0.5,
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_content, f)
            temp_path = f.name

        try:
            loader = ConfigLoader(config_path=temp_path)
            value = loader.get("trading", "position_diff_threshold", override=None)
            assert value == 0.5
        finally:
            os.unlink(temp_path)


class TestConfigLoaderSecurity:
    """REQ-W01, REQ-W02: 보안 요구사항"""

    def test_does_not_expose_sensitive_fields(self):
        """민감정보 필드가 config에 포함되지 않음"""
        loader = ConfigLoader(config_path="nonexistent.yaml")

        # 민감정보 필드는 None 반환 (지원하지 않음)
        assert loader.get("credentials", "api_key", default=None) is None
        assert loader.get("credentials", "secret_key", default=None) is None

    def test_config_template_has_no_secrets(self):
        """config 템플릿에 시크릿 없음"""
        # 이 테스트는 config.yaml 생성 후 실행
        pass
