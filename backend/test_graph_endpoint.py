"""Test script for the graph endpoint."""

import asyncio
import json
from datetime import datetime, timedelta, timezone

from src.analysis.graph import (
    calculate_sensitivity_graph,
    calculate_delta_gauge,
    calculate_risk_contribution,
    calculate_alert_dashboard,
)
from src.models import GraphRequest, GraphResponse


def test_sensitivity_graph():
    """Test sensitivity graph calculation."""
    print("\n=== Testing Sensitivity Graph ===")

    # Sample sensitivity table
    sensitivity_table = [
        {"price_change_pct": -30.0, "portfolio_value": 70000, "return_pct": -30.0, "pnl": -30000},
        {"price_change_pct": -20.0, "portfolio_value": 80000, "return_pct": -20.0, "pnl": -20000},
        {"price_change_pct": -10.0, "portfolio_value": 90000, "return_pct": -10.0, "pnl": -10000},
        {"price_change_pct": 0.0, "portfolio_value": 100000, "return_pct": 0.0, "pnl": 0},
        {"price_change_pct": 10.0, "portfolio_value": 110000, "return_pct": 10.0, "pnl": 10000},
        {"price_change_pct": 20.0, "portfolio_value": 120000, "return_pct": 20.0, "pnl": 20000},
        {"price_change_pct": 30.0, "portfolio_value": 130000, "return_pct": 30.0, "pnl": 30000},
    ]

    result = calculate_sensitivity_graph(sensitivity_table)

    print(f"Data points: {len(result['data_points'])}")
    print(f"Current position index: {result['current_position']}")
    print(f"Value range: ${result['value_range']['min']:,.2f} - ${result['value_range']['max']:,.2f}")
    print(f"Current value: ${result['value_range']['current']:,.2f}")

    assert len(result['data_points']) == 7
    assert result['current_position'] == 3
    assert result['value_range']['current'] == 100000

    print("✅ Sensitivity graph test passed!")


def test_delta_gauge():
    """Test delta gauge calculation."""
    print("\n=== Testing Delta Gauge ===")

    # Sample data
    delta_exposure = 150.5
    portfolio_value = 100000
    positions = [
        {"asset": "BTC", "quantity": 1.0, "position_type": "spot"},
        {"asset": "BTC", "quantity": -0.99, "position_type": "futures_short"},
    ]
    current_prices = {
        ("BTC", "spot"): 95000,
        ("BTC", "futures_short"): 95500,
    }

    result = calculate_delta_gauge(delta_exposure, portfolio_value, positions, current_prices)

    print(f"Delta raw: {result['delta_raw']:.2f}")
    print(f"Delta normalized: {result['delta_normalized']:.4f}")
    print(f"Status: {result['status']}")
    print(f"Directional exposure: {result['directional_exposure_pct']:.2f}%")

    assert result['status'] in ["neutral", "slight_long", "slight_short", "high_long", "high_short"]
    assert -1.0 <= result['delta_normalized'] <= 1.0

    print("✅ Delta gauge test passed!")


def test_risk_contribution():
    """Test risk contribution calculation."""
    print("\n=== Testing Risk Contribution ===")

    import numpy as np

    # Sample data
    positions = [
        {"asset": "BTC", "value": 60000},
        {"asset": "ETH", "value": 40000},
    ]

    asset_returns = {
        "BTC": np.array([0.02, -0.01, 0.03, -0.02, 0.01]),
        "ETH": np.array([0.015, -0.012, 0.025, -0.018, 0.008]),
    }

    correlation_matrix = {
        "BTC": {"BTC": 1.0, "ETH": 0.8},
        "ETH": {"BTC": 0.8, "ETH": 1.0},
    }

    portfolio_variance = 0.0004  # Sample variance

    result = calculate_risk_contribution(
        positions, asset_returns, correlation_matrix, portfolio_variance
    )

    print(f"Number of contributions: {len(result['contributions'])}")
    for contrib in result['contributions']:
        print(f"  {contrib['asset']}: {contrib['risk_pct']:.2f}% risk, {contrib['value_pct']:.2f}% value")
    print(f"Diversification benefit: {result['diversification_benefit']:.2f}%")

    assert len(result['contributions']) == 2

    print("✅ Risk contribution test passed!")


def test_alert_dashboard():
    """Test alert dashboard calculation."""
    print("\n=== Testing Alert Dashboard ===")

    # Sample risk metrics
    risk_metrics = {
        "portfolio_volatility_annual": 0.45,
        "sharpe_ratio": 1.8,
        "var_95_1day": -5000,
        "delta_exposure": 200,
    }

    current_value = 100000

    positions = [
        {"asset": "BTC", "quantity": 1.0, "position_type": "spot", "entry_price": 95000, "leverage": 1.0},
        {"asset": "BTC", "quantity": -0.95, "position_type": "futures_short", "entry_price": 95500, "leverage": 3.0},
    ]

    current_prices = {
        ("BTC", "spot"): 96000,
        ("BTC", "futures_short"): 96200,
    }

    delta_exposure = 200

    result = calculate_alert_dashboard(
        risk_metrics, current_value, positions, current_prices, delta_exposure
    )

    print(f"Health score: {result['health_score']}/100")
    print("Health components:")
    for component, data in result['health_components'].items():
        print(f"  {component}: {data['score']}/25 ({data['status']})")
    print(f"Liquidation risk: {result['liquidation_risk']['overall_risk']}")
    print(f"Rebalancing needed: {result['rebalancing_signal']['needed']}")

    assert 0 <= result['health_score'] <= 100
    assert result['liquidation_risk']['overall_risk'] in ["low", "moderate", "high"]

    print("✅ Alert dashboard test passed!")


def test_graph_request_validation():
    """Test GraphRequest model validation."""
    print("\n=== Testing GraphRequest Validation ===")

    # Valid request
    valid_request = {
        "positions": [
            {
                "asset": "BTC",
                "quantity": 1.0,
                "position_type": "spot",
                "entry_price": 95000,
            }
        ],
        "lookback_days": 30,
        "graph_types": ["sensitivity", "delta"],
    }

    try:
        request = GraphRequest(**valid_request)
        print(f"Valid request created: {len(request.positions)} positions, {len(request.graph_types)} graph types")
        assert len(request.graph_types) == 2
        print("✅ Valid request passed!")
    except Exception as e:
        print(f"❌ Valid request failed: {e}")
        raise

    # Invalid graph type
    invalid_request = {
        "positions": [
            {
                "asset": "BTC",
                "quantity": 1.0,
                "position_type": "spot",
                "entry_price": 95000,
            }
        ],
        "lookback_days": 30,
        "graph_types": ["invalid_type"],
    }

    try:
        request = GraphRequest(**invalid_request)
        print("❌ Should have raised validation error for invalid graph type")
        assert False, "Should have raised validation error"
    except ValueError as e:
        print(f"✅ Correctly rejected invalid graph type: {str(e)[:50]}...")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Graph Endpoint Test Suite")
    print("=" * 60)

    try:
        test_sensitivity_graph()
        test_delta_gauge()
        test_risk_contribution()
        test_alert_dashboard()
        test_graph_request_validation()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ Test failed: {e}")
        print("=" * 60)
        raise


if __name__ == "__main__":
    main()
