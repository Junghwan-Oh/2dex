"""
Test V4 Helper Functions Ported to Nado

Unit tests for calculate_timeout, extract_filled_quantity, and calculate_slippage_bps.
"""

import os
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock


# We'll import these from nado once they're added
from exchanges.nado import NadoClient


class Config:
    """Simple config class for testing."""
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)


class TestCalculateTimeout:
    """Test calculate_timeout function."""

    def setup_method(self):
        """Setup test client."""
        # Mock environment variables
        with patch.dict(os.environ, {'NADO_PRIVATE_KEY': '0x' + '1' * 64}):
            # Mock config - doesn't need to be valid for testing helper functions
            config = Config({"ticker": "ETH", "quantity": Decimal("1")})
            self.client = NadoClient(config)

    def test_calculate_timeout_small(self):
        """Test timeout for small orders (<=0.1)."""
        assert self.client.calculate_timeout(Decimal('0.05')) == 5
        assert self.client.calculate_timeout(Decimal('0.1')) == 5
        assert self.client.calculate_timeout(Decimal('0.001')) == 5

    def test_calculate_timeout_medium(self):
        """Test timeout for medium orders (0.1-0.5)."""
        assert self.client.calculate_timeout(Decimal('0.2')) == 10
        assert self.client.calculate_timeout(Decimal('0.5')) == 10
        assert self.client.calculate_timeout(Decimal('0.35')) == 10

    def test_calculate_timeout_large(self):
        """Test timeout for large orders (>0.5)."""
        assert self.client.calculate_timeout(Decimal('1.0')) == 20
        assert self.client.calculate_timeout(Decimal('2.0')) == 20
        assert self.client.calculate_timeout(Decimal('10.0')) == 20

    def test_calculate_timeout_boundary(self):
        """Test timeout at boundary values."""
        # Exactly 0.1 should be 5s
        assert self.client.calculate_timeout(Decimal('0.1')) == 5
        # Just above 0.1 should be 10s
        assert self.client.calculate_timeout(Decimal('0.11')) == 10
        # Exactly 0.5 should be 10s
        assert self.client.calculate_timeout(Decimal('0.5')) == 10
        # Just above 0.5 should be 20s
        assert self.client.calculate_timeout(Decimal('0.51')) == 20


class TestExtractFilledQuantity:
    """Test extract_filled_quantity function."""

    def setup_method(self):
        """Setup test client."""
        with patch.dict(os.environ, {'NADO_PRIVATE_KEY': '0x' + '1' * 64}):
            config = Config({"ticker": "ETH", "quantity": Decimal("1")})
            self.client = NadoClient(config)

    def test_extract_filled_quantity_state_format(self):
        """Test extraction from state/traded_size format (Nado REST)."""
        # Full fill (1 ETH = 1000000000000000000 in x18 format)
        result = {'state': {'traded_size': '1000000000000000000'}}
        assert self.client.extract_filled_quantity(result) == Decimal('1.0')

        # Partial fill (0.5 ETH)
        result = {'state': {'traded_size': '500000000000000000'}}
        assert self.client.extract_filled_quantity(result) == Decimal('0.5')

    def test_extract_filled_quantity_list_format(self):
        """Test extraction from list format [price, size]."""
        result = [Decimal('3000'), Decimal('1.0')]
        assert self.client.extract_filled_quantity(result) == Decimal('1.0')

        result = ['3000', '0.5']
        assert self.client.extract_filled_quantity(result) == Decimal('0.5')

    def test_extract_filled_quantity_dict_size(self):
        """Test extraction from dict with 'size' key."""
        result = {'price': '3000', 'size': '1.0'}
        assert self.client.extract_filled_quantity(result) == Decimal('1.0')

    def test_extract_filled_quantity_dict_traded_size(self):
        """Test extraction from dict with 'traded_size' key."""
        result = {'traded_size': '0.5'}
        assert self.client.extract_filled_quantity(result) == Decimal('0.5')

    def test_extract_filled_quantity_metadata(self):
        """Test extraction from metadata format (WebSocket market orders)."""
        result = {'metadata': {}}
        assert self.client.extract_filled_quantity(result) == Decimal('0')

    def test_extract_filled_quantity_empty(self):
        """Test extraction from empty dict."""
        result = {}
        assert self.client.extract_filled_quantity(result) == Decimal('0')

    def test_extract_filled_quantity_invalid(self):
        """Test extraction with invalid data."""
        # Missing keys
        result = {'price': '3000'}
        assert self.client.extract_filled_quantity(result) == Decimal('0')

        # Invalid values
        result = {'state': {'traded_size': 'invalid'}}
        assert self.client.extract_filled_quantity(result) == Decimal('0')


class TestCalculateSlippageBps:
    """Test calculate_slippage_bps function."""

    def setup_method(self):
        """Setup test client."""
        with patch.dict(os.environ, {'NADO_PRIVATE_KEY': '0x' + '1' * 64}):
            config = Config({"ticker": "ETH", "quantity": Decimal("1")})
            self.client = NadoClient(config)

    def test_calculate_slippage_no_slippage(self):
        """Test slippage calculation when execution equals reference."""
        slippage = self.client.calculate_slippage_bps(Decimal('3000'), Decimal('3000'))
        assert slippage == Decimal('0')

    def test_calculate_slippage_positive(self):
        """Test positive slippage (worse execution)."""
        # 1% worse = 100 bps
        slippage = self.client.calculate_slippage_bps(Decimal('3030'), Decimal('3000'))
        assert abs(slippage - Decimal('100')) < Decimal('1')  # Allow rounding

    def test_calculate_slippage_negative(self):
        """Test negative slippage (better execution - uses abs)."""
        # 1% better = 100 bps (abs value)
        slippage = self.client.calculate_slippage_bps(Decimal('2970'), Decimal('3000'))
        assert abs(slippage - Decimal('100')) < Decimal('1')  # Allow rounding

    def test_calculate_slippage_small(self):
        """Test small slippage (0.01% = 1 bps)."""
        slippage = self.client.calculate_slippage_bps(Decimal('3000.3'), Decimal('3000'))
        assert abs(slippage - Decimal('1')) < Decimal('1')  # Allow rounding

    def test_calculate_slippage_zero_reference(self):
        """Test slippage with zero reference price (should return 0)."""
        slippage = self.client.calculate_slippage_bps(Decimal('3000'), Decimal('0'))
        assert slippage == Decimal('0')

    def test_calculate_slippage_negative_reference(self):
        """Test slippage with negative reference price (should return 0)."""
        slippage = self.client.calculate_slippage_bps(Decimal('3000'), Decimal('-100'))
        assert slippage == Decimal('0')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
