"""
Test script for risk profile analysis API.

This script demonstrates how to use the risk profile endpoint with sample portfolios.
"""

import asyncio
import json

from src.models import PositionInput, RiskProfileRequest
from src.analysis.riskprofile import calculate_risk_profile


async def test_spot_only_portfolio():
    """Test risk profile for a simple spot-only portfolio."""
    print("\n" + "=" * 80)
    print("TEST 1: Spot-Only Portfolio (BTC + ETH)")
    print("=" * 80)

    # Create sample positions
    positions = [
        PositionInput(
            asset="BTC",
            quantity=1.5,
            position_type="spot",
            entry_price=45000.0,
            leverage=1.0,
        ),
        PositionInput(
            asset="ETH",
            quantity=20.0,
            position_type="spot",
            entry_price=2500.0,
            leverage=1.0,
        ),
    ]

    request = RiskProfileRequest(positions=positions, lookback_days=30)

    # Convert to dict for processing
    request_data = {
        "positions": [pos.model_dump() for pos in request.positions],
        "lookback_days": request.lookback_days,
    }

    try:
        result = await calculate_risk_profile(request_data)

        print(f"\nCurrent Portfolio Value: ${result['current_portfolio_value']:,.2f}")
        print(f"Data Warning: {result['data_availability_warning']}")

        print("\n--- Risk Metrics ---")
        metrics = result["risk_metrics"]
        print(f"Lookback Days Used: {metrics['lookback_days_used']}")
        print(f"Annual Volatility: {metrics['portfolio_volatility_annual']:.2%}")
        print(f"VaR (95%, 1-day): ${metrics['var_95_1day']:,.2f}")
        print(f"VaR (99%, 1-day): ${metrics['var_99_1day']:,.2f}")
        print(f"CVaR (95%): ${metrics['cvar_95']:,.2f}")
        print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.4f}")
        print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
        print(f"Delta Exposure: {metrics['delta_exposure']:.2f}")

        print("\n--- Sensitivity Analysis (Sample) ---")
        for row in result["sensitivity_analysis"][::3]:  # Show every 3rd row
            print(
                f"Price Change: {row['price_change_pct']:+6.1f}% | "
                f"Portfolio Value: ${row['portfolio_value']:,.2f} | "
                f"P&L: ${row['pnl']:+,.2f} ({row['return_pct']:+.1f}%)"
            )

        print("\n--- Scenarios (Sample) ---")
        for scenario in result["scenarios"][:3]:  # Show first 3 scenarios
            print(
                f"{scenario['name']:20s}: ${scenario['portfolio_value']:,.2f} | "
                f"P&L: ${scenario['pnl']:+,.2f} ({scenario['return_pct']:+.1f}%)"
            )

        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_mixed_portfolio():
    """Test risk profile for a mixed spot + futures portfolio."""
    print("\n" + "=" * 80)
    print("TEST 2: Mixed Portfolio (BTC Spot + ETH Futures Long + SOL Futures Short)")
    print("=" * 80)

    positions = [
        PositionInput(
            asset="BTC",
            quantity=1.0,
            position_type="spot",
            entry_price=45000.0,
            leverage=1.0,
        ),
        PositionInput(
            asset="ETH",
            quantity=15.0,
            position_type="futures_long",
            entry_price=2500.0,
            leverage=3.0,
        ),
        PositionInput(
            asset="SOL",
            quantity=100.0,
            position_type="futures_short",
            entry_price=100.0,
            leverage=2.0,
        ),
    ]

    request = RiskProfileRequest(positions=positions, lookback_days=30)

    request_data = {
        "positions": [pos.model_dump() for pos in request.positions],
        "lookback_days": request.lookback_days,
    }

    try:
        result = await calculate_risk_profile(request_data)

        print(f"\nCurrent Portfolio Value: ${result['current_portfolio_value']:,.2f}")

        print("\n--- Risk Metrics ---")
        metrics = result["risk_metrics"]
        print(f"Annual Volatility: {metrics['portfolio_volatility_annual']:.2%}")
        print(f"VaR (95%, 1-day): ${metrics['var_95_1day']:,.2f}")
        print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.4f}")
        print(f"Delta Exposure: {metrics['delta_exposure']:.2f}")

        print("\n--- Correlation Matrix ---")
        corr = metrics["correlation_matrix"]
        if "BTC" in corr and "ETH" in corr and "BTC" in corr:
            print(f"BTC-ETH Correlation: {corr.get('BTC', {}).get('ETH', 0):.4f}")
            print(f"BTC-SOL Correlation: {corr.get('BTC', {}).get('SOL', 0):.4f}")
            print(f"ETH-SOL Correlation: {corr.get('ETH', {}).get('SOL', 0):.4f}")

        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("RISK PROFILE ANALYSIS - TEST SUITE")
    print("=" * 80)

    # Note: These tests require a running database with historical data
    print(
        "\nNOTE: These tests require:"
        "\n  1. PostgreSQL database running"
        "\n  2. Database initialized (schema created)"
        "\n  3. Historical data for BTC, ETH, SOL (spot and futures)"
        "\n  4. At least 30 days of data available"
    )

    print("\nStarting tests...")

    results = []

    # Test 1: Spot-only portfolio
    results.append(await test_spot_only_portfolio())

    # Test 2: Mixed portfolio
    results.append(await test_mixed_portfolio())

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")

    if all(results):
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed. Check error messages above.")


if __name__ == "__main__":
    asyncio.run(main())
