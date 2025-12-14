"""
Configuration Loader for Delta Neutral Volume Farming Bot

SPEC-001: config.yaml 설정 파일 지원
Priority: CLI > config.yaml > defaults

Usage:
    from config_loader import ConfigLoader

    config = ConfigLoader()
    threshold = config.get("trading", "position_diff_threshold")
    # With CLI override
    threshold = config.get("trading", "position_diff_threshold", override=args.threshold)
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when config validation fails"""
    pass


class ConfigLoader:
    """
    Load and manage configuration from config.yaml

    Priority: CLI override > config.yaml > DEFAULT_CONFIG

    Attributes:
        config_path: Path to config.yaml file
        config: Loaded configuration dictionary
        load_error: Error message if load failed, None otherwise
    """

    DEFAULT_CONFIG: Dict[str, Dict[str, Any]] = {
        "trading": {
            "position_diff_threshold": 0.2,
            "order_cancel_timeout": 10,
            "trading_loop_timeout": 180,
            "max_retries": 15,
            "fill_check_interval": 10,
            "default_size": 0.01,
            "default_iterations": 10,
        },
        "monitoring": {
            "funding_fee_logging": True,
            "funding_fee_log_interval": 5,
            "funding_fee_warning_threshold": -10.0,
            "balance_logging": True,
            "balance_log_interval": 5,
            "balance_warning_threshold": 0.3,
        },
        "pricing": {
            "buy_price_multiplier": 0.998,
            "sell_price_multiplier": 1.002,
        }
    }

    # Type definitions for validation
    TYPE_DEFINITIONS: Dict[str, Dict[str, type]] = {
        "trading": {
            "position_diff_threshold": (int, float),
            "order_cancel_timeout": (int, float),
            "trading_loop_timeout": (int, float),
            "max_retries": int,
            "fill_check_interval": (int, float),
            "default_size": (int, float),
            "default_iterations": int,
        },
        "monitoring": {
            "funding_fee_logging": bool,
            "funding_fee_log_interval": int,
            "funding_fee_warning_threshold": (int, float),
            "balance_logging": bool,
            "balance_log_interval": int,
            "balance_warning_threshold": (int, float),
        },
        "pricing": {
            "buy_price_multiplier": (int, float),
            "sell_price_multiplier": (int, float),
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize ConfigLoader

        Args:
            config_path: Path to config.yaml. Defaults to 'config.yaml' in current directory.
        """
        self.config_path = config_path or "config.yaml"
        self.load_error: Optional[str] = None
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Dict[str, Any]]:
        """
        Load configuration from YAML file

        Returns:
            Merged configuration with defaults for missing values
        """
        # Start with defaults
        config = self._deep_copy_dict(self.DEFAULT_CONFIG)

        # Try to load from file
        config_file = Path(self.config_path)
        if not config_file.exists():
            logger.debug(f"Config file not found: {self.config_path}, using defaults")
            return config

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f)

            if file_config is None:
                logger.warning(f"Config file is empty: {self.config_path}, using defaults")
                return config

            if not isinstance(file_config, dict):
                self.load_error = f"Config file root must be a dictionary"
                logger.warning(f"{self.load_error}, using defaults")
                return config

            # Merge file config with defaults
            config = self._merge_configs(config, file_config)
            logger.info(f"Loaded config from: {self.config_path}")

        except yaml.YAMLError as e:
            self.load_error = f"YAML parse error: {e}"
            logger.warning(f"Failed to parse config file: {e}, using defaults")

        except Exception as e:
            self.load_error = f"Config load error: {e}"
            logger.warning(f"Failed to load config file: {e}, using defaults")

        return config

    def _deep_copy_dict(self, d: Dict) -> Dict:
        """Deep copy a nested dictionary"""
        result = {}
        for key, value in d.items():
            if isinstance(value, dict):
                result[key] = self._deep_copy_dict(value)
            else:
                result[key] = value
        return result

    def _merge_configs(
        self,
        defaults: Dict[str, Dict[str, Any]],
        overrides: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Merge override config into defaults

        Args:
            defaults: Default configuration
            overrides: Override values from file

        Returns:
            Merged configuration
        """
        result = self._deep_copy_dict(defaults)

        for section, values in overrides.items():
            if section not in result:
                continue  # Ignore unknown sections

            if not isinstance(values, dict):
                continue

            for key, value in values.items():
                if key not in result[section]:
                    continue  # Ignore unknown keys

                # Validate type
                if self._validate_type(section, key, value):
                    result[section][key] = value
                else:
                    logger.warning(
                        f"Invalid type for {section}.{key}: expected "
                        f"{self.TYPE_DEFINITIONS.get(section, {}).get(key)}, "
                        f"got {type(value).__name__}, using default"
                    )

        return result

    def _validate_type(self, section: str, key: str, value: Any) -> bool:
        """
        Validate value type against expected type

        Args:
            section: Config section name
            key: Config key name
            value: Value to validate

        Returns:
            True if type is valid, False otherwise
        """
        expected_types = self.TYPE_DEFINITIONS.get(section, {}).get(key)

        if expected_types is None:
            return True  # No type definition, accept any

        if isinstance(expected_types, tuple):
            return isinstance(value, expected_types)

        return isinstance(value, expected_types)

    def get(
        self,
        section: str,
        key: str,
        default: Any = None,
        override: Any = None
    ) -> Any:
        """
        Get configuration value with priority: override > config > default

        Args:
            section: Config section (e.g., 'trading', 'pricing')
            key: Config key (e.g., 'position_diff_threshold')
            default: Fallback value if not found anywhere
            override: CLI override value (highest priority)

        Returns:
            Configuration value

        Examples:
            # Basic usage
            threshold = config.get("trading", "position_diff_threshold")

            # With CLI override
            threshold = config.get("trading", "position_diff_threshold", override=args.threshold)
        """
        # Priority 1: CLI override
        if override is not None:
            return override

        # Priority 2: Config file value
        if section in self.config and key in self.config[section]:
            return self.config[section][key]

        # Priority 3: Provided default
        if default is not None:
            return default

        # Priority 4: DEFAULT_CONFIG
        if section in self.DEFAULT_CONFIG and key in self.DEFAULT_CONFIG[section]:
            return self.DEFAULT_CONFIG[section][key]

        return None

    def get_all(self, section: str) -> Dict[str, Any]:
        """
        Get all values in a section

        Args:
            section: Config section name

        Returns:
            Dictionary of all values in section
        """
        return self.config.get(section, {}).copy()

    def __repr__(self) -> str:
        return f"ConfigLoader(config_path='{self.config_path}', loaded={self.load_error is None})"


# Convenience function for quick access
def load_config(config_path: Optional[str] = None) -> ConfigLoader:
    """
    Quick function to load configuration

    Args:
        config_path: Path to config.yaml

    Returns:
        ConfigLoader instance
    """
    return ConfigLoader(config_path)
