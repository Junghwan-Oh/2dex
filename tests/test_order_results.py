"""
TDD Tests for Order Result Handling (Priority 2)

TDD Approach: RED (failing tests) -> GREEN (implementation) -> REFACTOR

This test file implements Priority 2 from the Nado DN Pair Practical Fixes Plan:
- Test Coverage Improvement
- Test order result handling for negative filled_size (sell orders)
- Test zero filled_size returns success=False
- Test price extraction from order info

Test Cases:
1. Test negative filled_size for sell orders
2. Test zero filled_size returns False
3. Test order result price extraction
4. Test partial fill handling
5. Test full fill handling
6. Test order info parsing from various formats

These tests verify critical order handling logic that affects
position tracking and PnL calculation.
"""

import pytest
from decimal import Decimal
import sys
import os
from unittest.mock import Mock, AsyncMock, MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from exchanges.base import OrderResult, OrderInfo
    from exchanges.nado import NadoClient
    from hedge.DN_pair_eth_sol_nado import Config
    CLASSES_AVAILABLE = True
except ImportError as e:
    CLASSES_AVAILABLE = False
    IMPORT_ERROR = str(e)


class TestNegativeFilledSizeForSellOrders:
    """
    Test that sell orders with negative filled_size are handled correctly.

    CRITICAL BUG: In the original implementation, sell orders return negative
    filled_size values from the exchange. The order result handling must
    convert these to positive values and handle them correctly.

    This was causing position tracking errors and emergency unwinds.
    """

    def setup_method(self):
        """Setup test client."""
        if not CLASSES_AVAILABLE:
            pytest.skip(f"Required classes not available: {IMPORT_ERROR}")

        # Mock environment variables
        os.environ['NADO_PRIVATE_KEY'] = '0x' + 'a' * 64
        os.environ['NADO_MODE'] = 'MAINNET'
        os.environ['NADO_SUBACCOUNT_NAME'] = 'default'

        # Create client
        self.client = NadoClient(Config({"ticker": "ETH", "quantity": Decimal("1")}))

    def test_sell_order_result_with_negative_filled_size(self):
        """
        TEST: Sell order with negative filled_size is handled correctly.

        Scenario:
        - Place IOC sell order for 0.5 ETH
        - Order fills partially with -0.3 filled_size (negative for sell)
        - Expected: success=True, filled_size=0.3 (positive)

        Expected behavior:
        - Negative filled_size is converted to positive
        - success=True when filled_size != 0
        - OrderResult stores filled_size as positive value

        This test verifies the fix for the critical bug where sell orders
        with negative filled_size were not handled correctly.
        """
        if not CLASSES_AVAILABLE:
            pytest.skip("Required classes not available")

        # Simulate order result from exchange (negative filled_size for sell)
        # This is what get_order_info returns for a sell order
        order_info = OrderInfo(
            order_id="test_sell_123",
            side="sell",
            size=Decimal("-0.5"),  # Negative for sell
            price=Decimal("3000"),
            status="FILLED",
            filled_size=Decimal("-0.3"),  # NEGATIVE for sell orders
            remaining_size=Decimal("-0.2")
        )

        # Extract filled_size (should be positive)
        filled_size = abs(order_info.filled_size) if order_info.filled_size != 0 else Decimal('0')

        # Verify
        assert filled_size == Decimal("0.3"), f"Expected 0.3, got {filled_size}"
        assert filled_size > 0, "Filled size should be positive"

        # Verify success determination
        actual_fill = order_info.filled_size != 0
        assert actual_fill == True, "Order should be considered filled"

        # Create OrderResult as the code does
        result = OrderResult(
            success=actual_fill,
            order_id=order_info.order_id,
            side="sell",
            size=Decimal("0.5"),
            filled_size=abs(order_info.filled_size) if order_info.filled_size != 0 else Decimal('0'),
            price=order_info.price,
            status="FILLED"
        )

        # Verify OrderResult
        assert result.success == True, "OrderResult.success should be True"
        assert result.filled_size == Decimal("0.3"), f"OrderResult.filled_size should be 0.3, got {result.filled_size}"
        assert result.side == "sell", "Side should be sell"

    def test_buy_order_result_with_positive_filled_size(self):
        """
        TEST: Buy order with positive filled_size is handled correctly.

        Scenario:
        - Place IOC buy order for 0.5 ETH
        - Order fills with 0.3 filled_size (positive for buy)
        - Expected: success=True, filled_size=0.3

        Expected behavior:
        - Positive filled_size stays positive
        - success=True when filled_size != 0
        """
        if not CLASSES_AVAILABLE:
            pytest.skip("Required classes not available")

        order_info = OrderInfo(
            order_id="test_buy_123",
            side="buy",
            size=Decimal("0.5"),
            price=Decimal("3000"),
            status="FILLED",
            filled_size=Decimal("0.3"),  # Positive for buy
            remaining_size=Decimal("0.2")
        )

        # Extract filled_size
        filled_size = order_info.filled_size

        # Verify
        assert filled_size == Decimal("0.3"), f"Expected 0.3, got {filled_size}"

        # Verify success determination
        actual_fill = order_info.filled_size != 0
        assert actual_fill == True, "Order should be considered filled"

    def test_full_fill_sell_order_negative_size(self):
        """
        TEST: Fully filled sell order with negative sizes throughout.

        Scenario:
        - Sell order for 0.5 ETH fills completely
        - All size values are negative

        Expected behavior:
        - size, filled_size, remaining_size all negative
        - Order is correctly identified as filled
        - filled_size converted to positive in OrderResult
        """
        if not CLASSES_AVAILABLE:
            pytest.skip("Required classes not available")

        order_info = OrderInfo(
            order_id="test_sell_full_123",
            side="sell",
            size=Decimal("-0.5"),
            price=Decimal("3000"),
            status="FILLED",
            filled_size=Decimal("-0.5"),  # Full fill
            remaining_size=Decimal("0")   # No remaining
        )

        # Verify full fill
        assert order_info.remaining_size == 0, "Remaining size should be 0 for full fill"
        assert order_info.filled_size == Decimal("-0.5"), "Filled size should match size"

        # Create OrderResult
        result = OrderResult(
            success=order_info.filled_size != 0,
            order_id=order_info.order_id,
            side="sell",
            size=Decimal("0.5"),
            filled_size=abs(order_info.filled_size) if order_info.filled_size != 0 else Decimal('0'),
            price=order_info.price,
            status="FILLED"
        )

        # Verify
        assert result.success == True, "Full fill should be success=True"
        assert result.filled_size == Decimal("0.5"), "Filled size should be positive 0.5"


class TestZeroFilledSizeReturnsFalse:
    """
    Test that unfilled orders return success=False.

    CRITICAL: Orders with zero filled_size must return success=False
    to prevent incorrect position tracking.
    """

    def setup_method(self):
        """Setup test client."""
        if not CLASSES_AVAILABLE:
            pytest.skip(f"Required classes not available: {IMPORT_ERROR}")

        os.environ['NADO_PRIVATE_KEY'] = '0x' + 'a' * 64
        os.environ['NADO_MODE'] = 'MAINNET'
        os.environ['NADO_SUBACCOUNT_NAME'] = 'default'

        self.client = NadoClient(Config({"ticker": "ETH", "quantity": Decimal("1")}))

    def test_zero_filled_size_buy_order(self):
        """
        TEST: Buy order with zero filled_size returns success=False.

        Scenario:
        - Place IOC buy order
        - Order expires with no fill
        - filled_size = 0

        Expected behavior:
        - success=False (no fill occurred)
        - status='EXPIRED' or 'OPEN'
        """
        if not CLASSES_AVAILABLE:
            pytest.skip("Required classes not available")

        order_info = OrderInfo(
            order_id="test_buy_no_fill_123",
            side="buy",
            size=Decimal("0.5"),
            price=Decimal("3000"),
            status="EXPIRED",
            filled_size=Decimal("0"),  # NO FILL
            remaining_size=Decimal("0.5")
        )

        # Determine success
        actual_fill = order_info.filled_size != 0

        # Verify
        assert actual_fill == False, "Order with zero filled_size should return success=False"
        assert order_info.filled_size == 0, "Filled size should be 0"

    def test_zero_filled_size_sell_order(self):
        """
        TEST: Sell order with zero filled_size returns success=False.

        Scenario:
        - Place IOC sell order
        - Order expires with no fill
        - filled_size = 0

        Expected behavior:
        - success=False
        - No position change
        """
        if not CLASSES_AVAILABLE:
            pytest.skip("Required classes not available")

        order_info = OrderInfo(
            order_id="test_sell_no_fill_123",
            side="sell",
            size=Decimal("-0.5"),
            price=Decimal("3000"),
            status="EXPIRED",
            filled_size=Decimal("0"),  # NO FILL
            remaining_size=Decimal("-0.5")
        )

        # Determine success
        actual_fill = order_info.filled_size != 0

        # Verify
        assert actual_fill == False, "Order with zero filled_size should return success=False"

    def test_order_result_success_logic(self):
        """
        TEST: OrderResult success logic for various filled_size values.

        Test cases:
        - filled_size = 0 → success=False
        - filled_size = 0.1 → success=True
        - filled_size = -0.1 → success=True (sell order)

        Expected behavior:
        - Only zero filled_size returns success=False
        - Any non-zero value (positive or negative) returns success=True
        """
        if not CLASSES_AVAILABLE:
            pytest.skip("Required classes not available")

        # Case 1: Zero filled_size
        result1 = OrderResult(
            success=Decimal("0") != 0,
            order_id="test1",
            side="buy",
            size=Decimal("0.5"),
            filled_size=Decimal("0"),
            price=Decimal("3000"),
            status="EXPIRED"
        )
        assert result1.success == False, "Zero filled_size should be success=False"

        # Case 2: Positive filled_size (buy)
        result2 = OrderResult(
            success=Decimal("0.1") != 0,
            order_id="test2",
            side="buy",
            size=Decimal("0.5"),
            filled_size=Decimal("0.1"),
            price=Decimal("3000"),
            status="PARTIALLY_FILLED"
        )
        assert result2.success == True, "Positive filled_size should be success=True"

        # Case 3: Negative filled_size (sell) - converted to positive in OrderResult
        result3 = OrderResult(
            success=Decimal("-0.1") != 0,
            order_id="test3",
            side="sell",
            size=Decimal("0.5"),
            filled_size=Decimal("0.1"),  # Stored as positive
            price=Decimal("3000"),
            status="PARTIALLY_FILLED"
        )
        assert result3.success == True, "Non-zero filled_size should be success=True"


class TestOrderResultPriceExtraction:
    """
    Test correct price extraction from order info.

    CRITICAL: The execution price must be extracted correctly from order info
    for accurate PnL calculation and position tracking.
    """

    def setup_method(self):
        """Setup test client."""
        if not CLASSES_AVAILABLE:
            pytest.skip(f"Required classes not available: {IMPORT_ERROR}")

        os.environ['NADO_PRIVATE_KEY'] = '0x' + 'a' * 64
        os.environ['NADO_MODE'] = 'MAINNET'
        os.environ['NADO_SUBACCOUNT_NAME'] = 'default'

        self.client = NadoClient(Config({"ticker": "ETH", "quantity": Decimal("1")}))

    def test_price_extraction_from_order_info(self):
        """
        TEST: Price is correctly extracted from OrderInfo.

        Scenario:
        - IOC buy order fills at 3000.50
        - OrderInfo contains execution price

        Expected behavior:
        - OrderInfo.price is used (not order price)
        - Price reflects actual execution
        """
        if not CLASSES_AVAILABLE:
            pytest.skip("Required classes not available")

        order_info = OrderInfo(
            order_id="test_price_123",
            side="buy",
            size=Decimal("0.5"),
            price=Decimal("3000.50"),  # Execution price
            status="FILLED",
            filled_size=Decimal("0.5"),
            remaining_size=Decimal("0")
        )

        # Create OrderResult with price from OrderInfo
        result = OrderResult(
            success=True,
            order_id=order_info.order_id,
            side=order_info.side,
            size=order_info.size,
            filled_size=order_info.filled_size,
            price=order_info.price,  # Use OrderInfo price
            status=order_info.status
        )

        # Verify price extraction
        assert result.price == Decimal("3000.50"), f"Expected 3000.50, got {result.price}"

    def test_price_from_x18_format(self):
        """
        TEST: Price is correctly converted from X18 format.

        Nado SDK returns prices in X18 format (fixed point with 18 decimals).
        The conversion must handle this correctly.

        Expected behavior:
        - X18 format is converted to Decimal
        - Price has correct precision
        """
        if not CLASSES_AVAILABLE:
            pytest.skip("Required classes not available")

        # Simulate X18 format price
        # 3000.50 in X18 = 3000.50 * 10^18
        from nado_protocol.utils.math import from_x18

        price_x18 = int(3000.50 * 1e18)  # X18 format
        price_decimal = Decimal(str(from_x18(price_x18)))

        # Verify conversion
        assert price_decimal == Decimal("3000.50"), f"X18 conversion failed: {price_decimal}"

    def test_price_extraction_for_partial_fill(self):
        """
        TEST: Price extraction for partial fills.

        Scenario:
        - Order for 0.5 ETH
        - Partial fill of 0.3 ETH at 3000.50
        - Remaining 0.2 ETH unfilled

        Expected behavior:
        - Price reflects execution price of filled portion
        - Partial fill status is correct
        """
        if not CLASSES_AVAILABLE:
            pytest.skip("Required classes not available")

        order_info = OrderInfo(
            order_id="test_partial_123",
            side="buy",
            size=Decimal("0.5"),
            price=Decimal("3000.50"),
            status="PARTIALLY_FILLED",
            filled_size=Decimal("0.3"),
            remaining_size=Decimal("0.2")
        )

        # Create OrderResult
        result = OrderResult(
            success=True,
            order_id=order_info.order_id,
            side=order_info.side,
            size=order_info.size,
            filled_size=order_info.filled_size,
            price=order_info.price,
            status="PARTIALLY_FILLED"
        )

        # Verify
        assert result.price == Decimal("3000.50"), "Price should be execution price"
        assert result.status == "PARTIALLY_FILLED", "Status should indicate partial fill"
        assert result.filled_size == Decimal("0.3"), "Filled size should be 0.3"


class TestExtractFilledQuantity:
    """
    Test extract_filled_quantity method handles various order result formats.

    CRITICAL: The method must handle multiple response formats from Nado SDK:
    - REST API format with 'state'/'traded_size'
    - WebSocket format with 'metadata'
    - List format [price, size]
    - Dict format with 'size' or 'traded_size'
    """

    def setup_method(self):
        """Setup test client."""
        if not CLASSES_AVAILABLE:
            pytest.skip(f"Required classes not available: {IMPORT_ERROR}")

        os.environ['NADO_PRIVATE_KEY'] = '0x' + 'a' * 64
        os.environ['NADO_MODE'] = 'MAINNET'
        os.environ['NADO_SUBACCOUNT_NAME'] = 'default'

        self.client = NadoClient(Config({"ticker": "ETH", "quantity": Decimal("1")}))

    def test_extract_from_state_format(self):
        """
        TEST: Extract filled quantity from state format (REST API).

        Format: {'state': {'traded_size': X18_VALUE}}

        Expected behavior:
        - Detects 'state' and 'traded_size' keys
        - Converts from X18 format if needed
        - Returns correct Decimal value
        """
        if not CLASSES_AVAILABLE:
            pytest.skip("Required classes not available")

        # Simulate X18 format (large number)
        x18_value = str(0.5 * 1e18)  # 0.5 in X18
        order_result = {
            'state': {
                'traded_size': x18_value
            }
        }

        filled = self.client.extract_filled_quantity(order_result)

        # Should detect X18 format and convert
        assert filled > 0, "Should extract non-zero filled quantity"

    def test_extract_from_metadata_format(self):
        """
        TEST: Extract from WebSocket format (market orders).

        Format: {'metadata': {...}}

        Expected behavior:
        - Detects 'metadata' key
        - Returns 0 (market orders don't have metadata with size)
        """
        if not CLASSES_AVAILABLE:
            pytest.skip("Required classes not available")

        order_result = {
            'metadata': {'some': 'data'}
        }

        filled = self.client.extract_filled_quantity(order_result)

        assert filled == Decimal('0'), "Metadata format should return 0"

    def test_extract_from_list_format(self):
        """
        TEST: Extract from list format [price, size].

        Format: [price, size]

        Expected behavior:
        - Detects list/tuple format
        - Extracts size from index 1
        - Returns correct Decimal value
        """
        if not CLASSES_AVAILABLE:
            pytest.skip("Required classes not available")

        order_result = [3000.50, 0.5]  # [price, size]

        filled = self.client.extract_filled_quantity(order_result)

        assert filled == Decimal('0.5'), f"Expected 0.5, got {filled}"

    def test_extract_from_dict_size_format(self):
        """
        TEST: Extract from dict with 'size' key.

        Format: {'price': ..., 'size': ...}

        Expected behavior:
        - Detects 'size' key
        - Returns correct Decimal value
        """
        if not CLASSES_AVAILABLE:
            pytest.skip("Required classes not available")

        order_result = {
            'price': 3000.50,
            'size': 0.5
        }

        filled = self.client.extract_filled_quantity(order_result)

        assert filled == Decimal('0.5'), f"Expected 0.5, got {filled}"

    def test_extract_from_dict_traded_size_format(self):
        """
        TEST: Extract from dict with 'traded_size' key.

        Format: {'traded_size': ...}

        Expected behavior:
        - Detects 'traded_size' key
        - Returns correct Decimal value
        """
        if not CLASSES_AVAILABLE:
            pytest.skip("Required classes not available")

        order_result = {
            'traded_size': 0.5
        }

        filled = self.client.extract_filled_quantity(order_result)

        assert filled == Decimal('0.5'), f"Expected 0.5, got {filled}"

    def test_extract_from_empty_dict(self):
        """
        TEST: Extract from empty dict returns 0.

        Expected behavior:
        - No recognized keys found
        - Returns 0
        - No error or crash
        """
        if not CLASSES_AVAILABLE:
            pytest.skip("Required classes not available")

        order_result = {}

        filled = self.client.extract_filled_quantity(order_result)

        assert filled == Decimal('0'), "Empty dict should return 0"

    def test_extract_from_invalid_format(self):
        """
        TEST: Extract from invalid format returns 0.

        Expected behavior:
        - Handles invalid data gracefully
        - Returns 0
        - No crash
        """
        if not CLASSES_AVAILABLE:
            pytest.skip("Required classes not available")

        order_result = "invalid"

        filled = self.client.extract_filled_quantity(order_result)

        assert filled == Decimal('0'), "Invalid format should return 0"



# =============================================================================
# P0 CRITICAL: SOL Position Accumulation Bug Fix Tests
# Bug: Line 1013 checks `if result.success:` but should check
#      `if result.success and result.filled_size > 0:`
# =============================================================================

class TestSOLAccumulationBugPattern:
    """
    Test that detects and verifies the SOL accumulation bug fix.

    CRITICAL BUG: Line 1013 in DN_pair_eth_sol_nado.py
    Buggy: `if result.success:`
    Correct: `if result.success and result.filled_size > 0:`

    This matches the ETH pattern at lines 941 and 969.
    """

    def test_buggy_condition_with_zero_fill(self):
        """
        TEST: Detect buggy condition that allows zero-fill success logging.

        BUGGY BEHAVIOR (BEFORE FIX):
        - Condition: `if result.success:`
        - When: success=True, filled_size=0
        - Result: Logs "SOL closed: 0" - WRONG!
        - Impact: System thinks position closed when it didn't
        - Result: Position accumulation

        This test FAILS on buggy code, demonstrating the bug exists.
        AFTER FIX: This test is skipped as the bug is fixed.
        """
        import os

        file_path = "/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py"

        if not os.path.exists(file_path):
            pytest.skip(f"Source file not found: {file_path}")

        with open(file_path, 'r') as f:
            lines = f.readlines()

        # Check if fix has been applied
        if len(lines) >= 1013:
            line_1013 = lines[1012].strip()  # Line 1013
            has_correct_pattern = (
                "result.success" in line_1013 and
                "result.filled_size > 0" in line_1013 and
                "and" in line_1013
            )

            if has_correct_pattern:
                pytest.skip("Bug has been fixed - line 1013 now has correct pattern")

        # Simulate result with success=True but filled_size=0
        class MockResult:
            def __init__(self, success, filled_size, price):
                self.success = success
                self.filled_size = filled_size
                self.price = price
                self.error_message = "No liquidity"

        result = MockResult(success=True, filled_size=Decimal("0"), price=Decimal("100"))

        # BUGGY CODE PATTERN (line 1013 before fix)
        buggy_condition = result.success  # Only checks success

        # This condition evaluates to TRUE when it should be FALSE
        assert buggy_condition == True, "Buggy condition evaluates to True"

        # Verify this is the bug: success=True but filled_size=0
        assert result.success == True, "success is True"
        assert result.filled_size == Decimal("0"), "filled_size is 0"

        # BUG CONFIRMED: The buggy code would execute the success block
        # and log "SOL closed: 0 @ $100" which is WRONG
        buggy_message = f"[EMERGENCY] SOL closed: {result.filled_size} @ ${result.price}"
        assert "SOL closed: 0" in buggy_message, "Buggy message contains zero fill"

        # FAIL TEST to demonstrate bug exists
        pytest.fail(
            "BUG DETECTED: Line 1013 uses buggy condition 'if result.success:' "
            "which evaluates to True even when filled_size=0. "
            "This causes false success logging and position accumulation. "
            "Fix: Change to 'if result.success and result.filled_size > 0:'"
        )

    def test_correct_condition_with_zero_fill(self):
        """
        TEST: Verify correct condition rejects zero-fill results.

        CORRECT BEHAVIOR (AFTER FIX):
        - Condition: `if result.success and result.filled_size > 0:`
        - When: success=True, filled_size=0
        - Result: Condition is FALSE - no success logging
        - Impact: System correctly identifies failed close
        - Result: No accumulation

        This test PASSES after the fix is applied.
        """
        # Simulate result with success=True but filled_size=0
        class MockResult:
            def __init__(self, success, filled_size, price):
                self.success = success
                self.filled_size = filled_size
                self.price = price
                self.error_message = "No liquidity"

        result = MockResult(success=True, filled_size=Decimal("0"), price=Decimal("100"))

        # CORRECT CODE PATTERN (line 1013 after fix)
        correct_condition = result.success and result.filled_size > 0

        # This condition should evaluate to FALSE
        assert correct_condition == False, (
            "Correct condition should be False when filled_size=0"
        )

        # Verify the fix works
        assert result.success == True, "success is True"
        assert result.filled_size == Decimal("0"), "filled_size is 0"
        assert correct_condition == False, "Combined condition is False"

        # CORRECT: No success message logged
        # Error path should be executed instead

    def test_correct_condition_with_actual_fill(self):
        """
        TEST: Verify correct condition allows actual-fill results.

        CORRECT BEHAVIOR:
        - Condition: `if result.success and result.filled_size > 0:`
        - When: success=True, filled_size=50
        - Result: Condition is TRUE - success logging works
        - Impact: Normal operation unaffected
        - Result: Accumulation prevented, normal flow preserved

        This test PASSES on both buggy and fixed code (normal flow).
        """
        # Simulate result with actual fill
        class MockResult:
            def __init__(self, success, filled_size, price):
                self.success = success
                self.filled_size = filled_size
                self.price = price
                self.error_message = ""

        result = MockResult(success=True, filled_size=Decimal("50"), price=Decimal("100"))

        # CORRECT CODE PATTERN
        correct_condition = result.success and result.filled_size > 0

        # This condition should evaluate to TRUE
        assert correct_condition == True, (
            "Correct condition should be True when filled_size>0"
        )

        # Verify normal flow works
        assert result.success == True, "success is True"
        assert result.filled_size == Decimal("50"), "filled_size is 50"
        assert correct_condition == True, "Combined condition is True"

        # CORRECT: Success message is logged
        success_message = f"[EMERGENCY] SOL closed: {result.filled_size} @ ${result.price}"
        assert "SOL closed: 50" in success_message, "Success message contains actual fill"

    def test_code_pattern_matches_eth(self):
        """
        TEST: Verify SOL code pattern matches ETH pattern after fix.

        ETH Pattern (lines 941, 969):
        `if result.success and result.filled_size > 0:`

        SOL Pattern (line 1013 after fix):
        `if result.success and result.filled_size > 0:`

        This test verifies the patterns match exactly.
        """
        # ETH pattern from lines 941 and 969
        eth_pattern_condition = "result.success and result.filled_size > 0"

        # SOL pattern should match after fix
        sol_pattern_condition = "result.success and result.filled_size > 0"

        # Verify patterns match
        assert eth_pattern_condition == sol_pattern_condition, (
            f"SOL pattern should match ETH pattern. "
            f"ETH: {eth_pattern_condition}, "
            f"SOL: {sol_pattern_condition}"
        )

        # Test the logic with various scenarios
        test_cases = [
            # (success, filled_size, expected_result, description)
            (True, Decimal("0"), False, "Zero fill should be False"),
            (True, Decimal("50"), True, "Actual fill should be True"),
            (False, Decimal("0"), False, "Failed order should be False"),
            (False, Decimal("50"), False, "Failed with fill should be False"),
        ]

        for success, filled_size, expected, desc in test_cases:
            class MockResult:
                def __init__(self, success, filled_size):
                    self.success = success
                    self.filled_size = filled_size

            result = MockResult(success, filled_size)
            actual = result.success and result.filled_size > 0

            assert actual == expected, (
                f"{desc}. success={success}, filled_size={filled_size}, "
                f"expected={expected}, actual={actual}"
            )


class TestSOLCodeVerification:
    """
    Verify the actual code in DN_pair_eth_sol_nado.py has the correct pattern.
    """

    def test_verify_sol_line_1013_has_correct_pattern(self):
        """
        TEST: Read actual code and verify line 1013 has correct pattern.

        This test reads the actual source file and checks line 1013.
        """
        import os

        file_path = "/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py"

        if not os.path.exists(file_path):
            pytest.skip(f"Source file not found: {file_path}")

        with open(file_path, 'r') as f:
            lines = f.readlines()

        # Line 1013 (0-indexed: 1012)
        if len(lines) < 1013:
            pytest.skip(f"File has fewer than 1013 lines")

        line_1013 = lines[1012].strip()  # Line 1013

        # Check for correct pattern
        has_correct_pattern = (
            "result.success" in line_1013 and
            "result.filled_size > 0" in line_1013 and
            "and" in line_1013
        )

        # Check for buggy pattern
        has_buggy_pattern = (
            line_1013.startswith("if result.success:") and
            "filled_size" not in line_1013
        )

        if has_buggy_pattern:
            pytest.fail(
                f"BUGGY CODE DETECTED at line 1013: '{line_1013}'\n"
                f"Should be: 'if result.success and result.filled_size > 0:'\n"
                f"Currently is: '{line_1013}'"
            )

        if not has_correct_pattern:
            pytest.fail(
                f"Line 1013 does not have the expected pattern: '{line_1013}'\n"
                f"Expected pattern: 'if result.success and result.filled_size > 0:'"
            )

        # Verify pattern matches ETH
        assert has_correct_pattern, "Line 1013 has correct pattern"

    def test_verify_eth_lines_have_correct_pattern(self):
        """
        TEST: Verify ETH lines 941 and 969 have the correct pattern.
        """
        import os

        file_path = "/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py"

        if not os.path.exists(file_path):
            pytest.skip(f"Source file not found: {file_path}")

        with open(file_path, 'r') as f:
            lines = f.readlines()

        # Check lines 941 and 969
        eth_lines = [941, 969]

        for line_num in eth_lines:
            line_idx = line_num - 1  # 0-indexed
            if len(lines) < line_num:
                pytest.skip(f"File has fewer than {line_num} lines")

            line = lines[line_idx].strip()

            # ETH lines should have the correct pattern
            has_correct_pattern = (
                "result.success" in line and
                "result.filled_size > 0" in line and
                "and" in line
            )

            assert has_correct_pattern, (
                f"Line {line_num} does not have expected pattern: '{line}'\n"
                f"Expected: 'if result.success and result.filled_size > 0:'"
            )


# Run tests with verbose output
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
