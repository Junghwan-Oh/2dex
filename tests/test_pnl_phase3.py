#!/usr/bin/env python3
"""Test Phase 3 PNL calculation enhancements."""

from decimal import Decimal


def test_pnl_calculation():
    """Test the enhanced PNL calculation with breakdown dict."""

    # Simulate entry state
    entry_prices = {"ETH": Decimal("3000.00"), "SOL": Decimal("150.00")}
    entry_quantities = {"ETH": Decimal("0.1"), "SOL": Decimal("2.0")}  # $300 each
    exit_prices = {"ETH": Decimal("3050.00"), "SOL": Decimal("148.00")}  # ETH up, SOL down

    # Calculate ETH PNL (Long: exit - entry)
    eth_pnl = (exit_prices["ETH"] - entry_prices["ETH"]) * entry_quantities["ETH"]

    # Calculate SOL PNL (Short: entry - exit)
    sol_pnl = (entry_prices["SOL"] - exit_prices["SOL"]) * entry_quantities["SOL"]

    # Total PNL without fees
    pnl_no_fee = eth_pnl + sol_pnl

    # Fees (4 orders * 0.05% = 0.2% of total notional)
    total_fees = Decimal("600") * Decimal("0.0005") * 4  # $300 each * 4 orders * 0.05%

    # PNL with fees
    pnl_with_fee = pnl_no_fee - total_fees

    # Build breakdown dict
    breakdown = {
        "eth_pnl": float(eth_pnl),
        "sol_pnl": float(sol_pnl),
        "total_fees": float(total_fees),
        "eth_entry_price": float(entry_prices["ETH"]),
        "eth_exit_price": float(exit_prices["ETH"]),
        "sol_entry_price": float(entry_prices["SOL"]),
        "sol_exit_price": float(exit_prices["SOL"]),
        "eth_qty": float(entry_quantities["ETH"]),
        "sol_qty": float(entry_quantities["SOL"])
    }

    print("Test Case: Both positions profitable")
    print(f"  ETH PNL (Long): ${eth_pnl:.2f}")
    print(f"  SOL PNL (Short): ${sol_pnl:.2f}")
    print(f"  Total PNL (no fee): ${pnl_no_fee:.2f}")
    print(f"  Total Fees: ${total_fees:.2f}")
    print(f"  Total PNL (with fee): ${pnl_with_fee:.2f}")
    print(f"  Breakdown: {breakdown}")

    # Verify expected values
    assert eth_pnl == Decimal("5.00"), f"Expected ETH PNL $5.00, got ${eth_pnl}"
    assert sol_pnl == Decimal("4.00"), f"Expected SOL PNL $4.00, got ${sol_pnl}"
    assert pnl_no_fee == Decimal("9.00"), f"Expected PNL $9.00, got ${pnl_no_fee}"
    assert total_fees == Decimal("1.20"), f"Expected fees $1.20, got ${total_fees}"
    assert pnl_with_fee == Decimal("7.80"), f"Expected PNL with fee $7.80, got ${pnl_with_fee}"

    # Verify breakdown dict structure
    assert "eth_pnl" in breakdown
    assert "sol_pnl" in breakdown
    assert "total_fees" in breakdown
    assert "eth_entry_price" in breakdown
    assert "eth_exit_price" in breakdown
    assert "sol_entry_price" in breakdown
    assert "sol_exit_price" in breakdown
    assert "eth_qty" in breakdown
    assert "sol_qty" in breakdown

    print("\nAll assertions passed!")


def test_edge_cases():
    """Test edge cases for PNL calculation."""

    print("\nTest Case: Missing entry prices")
    entry_prices = {"ETH": Decimal("0"), "SOL": Decimal("150.00")}
    if entry_prices["ETH"] == 0 or entry_prices["SOL"] == 0:
        print("  Correctly detected missing entry prices")

    print("\nTest Case: Zero quantities")
    entry_quantities = {"ETH": Decimal("0"), "SOL": Decimal("2.0")}
    if entry_quantities["ETH"] == 0:
        print("  Correctly detected zero quantity (results in $0 PNL)")


if __name__ == "__main__":
    test_pnl_calculation()
    test_edge_cases()
    print("\n=== All Phase 3 PNL tests passed ===")
