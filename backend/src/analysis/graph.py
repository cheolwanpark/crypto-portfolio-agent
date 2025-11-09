"""Graph-ready data calculations for risk visualization dashboards.

This module transforms risk profile calculations into chart-ready data structures
for various visualization types including sensitivity analysis, delta gauges,
risk contribution charts, and alert dashboards.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from src.analysis import data_service, metrics, valuation
from src.config import settings


def calculate_sensitivity_graph(sensitivity_table: list[dict]) -> dict[str, Any]:
    """
    Transform sensitivity analysis into line chart data.

    Creates data for visualizing portfolio value changes across price movements
    from -30% to +30%, suitable for line charts with shaded areas.

    Args:
        sensitivity_table: List of sensitivity rows from risk profile

    Returns:
        Dict with:
            - data_points: List of {x: price_change_pct, y: portfolio_value, return_pct, pnl}
            - current_position: Index where price_change_pct = 0
            - value_range: {min, max, current}
    """
    if not sensitivity_table:
        return {
            "data_points": [],
            "current_position": 0,
            "value_range": {"min": 0, "max": 0, "current": 0},
        }

    # Extract data points
    data_points = []
    current_idx = 0
    current_value = 0

    for idx, row in enumerate(sensitivity_table):
        data_point = {
            "x": row["price_change_pct"],
            "y": row["portfolio_value"],
            "return_pct": row["return_pct"],
            "pnl": row["pnl"],
        }
        data_points.append(data_point)

        # Find current position (0% price change)
        if row["price_change_pct"] == 0.0:
            current_idx = idx
            current_value = row["portfolio_value"]

    # Calculate value range
    values = [p["y"] for p in data_points]
    value_range = {
        "min": min(values) if values else 0,
        "max": max(values) if values else 0,
        "current": current_value,
    }

    logger.debug(
        f"Sensitivity graph: {len(data_points)} points, "
        f"range ${value_range['min']:,.2f} - ${value_range['max']:,.2f}"
    )

    return {
        "data_points": data_points,
        "current_position": current_idx,
        "value_range": value_range,
    }


def calculate_delta_gauge(
    delta_exposure: float,
    portfolio_value: float,
    positions: list[dict],
    current_prices: dict[tuple[str, str], float],
) -> dict[str, Any]:
    """
    Calculate normalized delta for gauge chart display.

    Normalizes delta exposure to a -1.0 to +1.0 scale where:
    - -1.0 = Fully short
    - 0.0 = Market neutral
    - +1.0 = Fully long

    Args:
        delta_exposure: Raw delta exposure in USD
        portfolio_value: Total portfolio value
        positions: List of position dicts
        current_prices: Dict of (asset, position_type) -> price

    Returns:
        Dict with:
            - delta_raw: Original delta exposure
            - delta_normalized: Delta scaled to -1.0 to +1.0
            - status: "neutral" | "slight_long" | "slight_short" | "high_long" | "high_short"
            - portfolio_value: Total portfolio value
            - directional_exposure: Absolute delta as % of portfolio
    """
    # Calculate average asset price for normalization
    prices = [p for p in current_prices.values() if p > 0]
    avg_price = np.mean(prices) if prices else 1.0

    # Normalize delta: divide by (portfolio_value / avg_price) to get position-equivalent
    # Then scale by avg_price to get back to -1 to +1 range
    if portfolio_value > 0 and avg_price > 0:
        position_equivalent = portfolio_value / avg_price
        delta_normalized = delta_exposure / position_equivalent if position_equivalent != 0 else 0
    else:
        delta_normalized = 0.0

    # Clamp to -1.0 to +1.0 range
    delta_normalized = max(-1.0, min(1.0, delta_normalized))

    # Determine status based on thresholds
    abs_delta = abs(delta_normalized)
    if abs_delta <= 0.05:
        status = "neutral"
    elif abs_delta <= 0.2:
        status = "slight_long" if delta_normalized > 0 else "slight_short"
    else:
        status = "high_long" if delta_normalized > 0 else "high_short"

    # Calculate directional exposure as percentage
    directional_exposure_pct = abs(delta_exposure) / portfolio_value * 100 if portfolio_value > 0 else 0

    logger.debug(
        f"Delta gauge: raw={delta_exposure:.2f}, normalized={delta_normalized:.4f}, "
        f"status={status}, directional={directional_exposure_pct:.2f}%"
    )

    return {
        "delta_raw": delta_exposure,
        "delta_normalized": delta_normalized,
        "status": status,
        "portfolio_value": portfolio_value,
        "directional_exposure_pct": directional_exposure_pct,
    }


def calculate_risk_contribution(
    positions: list[dict],
    asset_returns: dict[str, np.ndarray],
    correlation_matrix: dict[str, dict[str, float]],
    portfolio_variance: float,
) -> dict[str, Any]:
    """
    Calculate risk contribution by asset for pie chart visualization.

    Uses marginal contribution to risk (MCR) approach:
    Risk_Contribution_i = (w_i × Cov(R_i, R_p)) / σ_p²

    Args:
        positions: List of position dicts with 'asset' and 'value' keys
        asset_returns: Dict mapping asset to returns array
        correlation_matrix: Asset correlation matrix
        portfolio_variance: Portfolio variance

    Returns:
        Dict with:
            - contributions: List of {asset, risk_pct, value_pct, risk_value}
            - total_risk: Sum of absolute risk contributions
            - diversification_benefit: How much risk is reduced by diversification
    """
    if not positions or portfolio_variance == 0:
        return {
            "contributions": [],
            "total_risk": 0.0,
            "diversification_benefit": 0.0,
        }

    # Calculate total portfolio value
    total_value = sum(pos.get("value", 0) for pos in positions)
    if total_value == 0:
        return {
            "contributions": [],
            "total_risk": 0.0,
            "diversification_benefit": 0.0,
        }

    # Calculate weights and volatilities
    weights = {pos["asset"]: pos.get("value", 0) / total_value for pos in positions}
    volatilities = {
        asset: np.std(returns, ddof=1) if len(returns) > 0 else 0.0
        for asset, returns in asset_returns.items()
    }

    # Calculate portfolio standard deviation
    portfolio_std = np.sqrt(portfolio_variance)

    # Calculate risk contributions using marginal contribution approach
    contributions_list = []
    total_weighted_risk = 0.0

    for pos in positions:
        asset = pos["asset"]
        w_i = weights.get(asset, 0)
        sigma_i = volatilities.get(asset, 0)
        value = pos.get("value", 0)

        # Calculate covariance with portfolio
        # Cov(R_i, R_p) = Σ_j (w_j × σ_i × σ_j × ρ_ij)
        cov_with_portfolio = 0.0
        for other_asset, w_j in weights.items():
            sigma_j = volatilities.get(other_asset, 0)
            rho_ij = correlation_matrix.get(asset, {}).get(other_asset, 0)
            cov_with_portfolio += w_j * sigma_i * sigma_j * rho_ij

        # Marginal contribution to risk
        # MCR_i = Cov(R_i, R_p) / σ_p
        mcr = cov_with_portfolio / portfolio_std if portfolio_std > 0 else 0

        # Risk contribution = w_i × MCR_i
        risk_contribution = w_i * mcr

        # Convert to percentage
        risk_pct = risk_contribution * 100 if portfolio_std > 0 else 0
        value_pct = w_i * 100

        contributions_list.append({
            "asset": asset,
            "risk_pct": risk_pct,
            "value_pct": value_pct,
            "risk_value": risk_contribution,
            "position_value": value,
        })

        total_weighted_risk += abs(risk_contribution)

    # Sort by absolute risk contribution
    contributions_list.sort(key=lambda x: abs(x["risk_pct"]), reverse=True)

    # Calculate diversification benefit
    # Sum of individual risks vs portfolio risk
    individual_risks = sum(
        weights.get(asset, 0) * volatilities.get(asset, 0)
        for asset in weights.keys()
    )
    diversification_benefit = (
        (individual_risks - portfolio_std) / individual_risks * 100
        if individual_risks > 0
        else 0.0
    )

    logger.debug(
        f"Risk contribution: {len(contributions_list)} assets, "
        f"diversification benefit: {diversification_benefit:.2f}%"
    )

    return {
        "contributions": contributions_list,
        "total_risk": total_weighted_risk,
        "diversification_benefit": diversification_benefit,
    }


def calculate_alert_dashboard(
    risk_metrics: dict,
    current_value: float,
    positions: list[dict],
    current_prices: dict[tuple[str, str], float],
    delta_exposure: float,
) -> dict[str, Any]:
    """
    Calculate risk alert dashboard data with health indicators.

    Provides real-time risk monitoring metrics including:
    - Portfolio health score (0-100)
    - Liquidation risk assessment
    - Funding rate status (for perp positions)
    - Rebalancing recommendations

    Args:
        risk_metrics: Dict of calculated risk metrics
        current_value: Current portfolio value
        positions: List of position dicts
        current_prices: Dict of current prices
        delta_exposure: Portfolio delta exposure

    Returns:
        Dict with:
            - health_score: Overall health score (0-100)
            - health_components: Dict of individual health factors
            - liquidation_risk: Dict with liquidation assessment
            - funding_status: Dict with funding rate info (if applicable)
            - rebalancing_signal: Dict with rebalancing recommendation
    """
    # Calculate health score components
    health_components = {}

    # 1. Delta neutrality check (25 points)
    # Linear scoring: 0-5% = 25pts, 5-50% = 25-0pts linearly
    delta_normalized = abs(delta_exposure) / current_value if current_value > 0 else 0
    if delta_normalized <= 0.05:
        delta_score = 25
        delta_status = "excellent"
    elif delta_normalized <= 0.5:
        # Linear interpolation: 5% -> 25pts, 50% -> 0pts
        delta_score = max(0, 25 - ((delta_normalized - 0.05) / 0.45) * 25)
        if delta_score >= 18:
            delta_status = "good"
        elif delta_score >= 10:
            delta_status = "fair"
        elif delta_score >= 5:
            delta_status = "warning"
        else:
            delta_status = "poor"
    else:
        delta_score = 0
        delta_status = "poor"

    health_components["delta_neutral"] = {"score": round(delta_score, 1), "status": delta_status}

    # 2. Volatility check (25 points)
    # Linear scoring: 0-30% = 25pts, 30-100% = 25-0pts linearly
    volatility = risk_metrics.get("portfolio_volatility_annual", 0)
    if volatility <= 0.3:
        vol_score = 25
        vol_status = "excellent"
    elif volatility <= 1.0:
        # Linear interpolation: 30% -> 25pts, 100% -> 0pts
        vol_score = max(0, 25 - ((volatility - 0.3) / 0.7) * 25)
        if vol_score >= 18:
            vol_status = "good"
        elif vol_score >= 10:
            vol_status = "fair"
        elif vol_score >= 5:
            vol_status = "warning"
        else:
            vol_status = "poor"
    else:
        vol_score = 0
        vol_status = "poor"

    health_components["volatility"] = {"score": round(vol_score, 1), "status": vol_status}

    # 3. Sharpe ratio check (25 points)
    # More realistic scoring for crypto markets:
    # - Market-neutral strategies (delta ~0): base score of 12.5pts (neutral)
    # - Directional strategies: Sharpe-based scoring
    # Thresholds: >=1.0 = excellent, 0.5-1.0 = good, 0-0.5 = fair, <0 = poor
    sharpe = risk_metrics.get("sharpe_ratio", 0)

    # Check if portfolio is market-neutral (delta < 5% of portfolio value)
    delta_normalized = abs(delta_exposure) / current_value if current_value > 0 else 0
    is_market_neutral = delta_normalized < 0.05

    if is_market_neutral:
        # For market-neutral strategies, give base score regardless of Sharpe
        # Since returns should be near zero by design (profit from funding/basis)
        sharpe_score = 12.5  # Neutral score
        sharpe_status = "fair"
        logger.debug(f"Market-neutral portfolio detected, using base Sharpe score: {sharpe_score}")
    elif sharpe >= 1.0:
        # Excellent: Sharpe >= 1.0 (institutional quality)
        sharpe_score = 25
        sharpe_status = "excellent"
    elif sharpe >= 0.5:
        # Good: Sharpe 0.5-1.0 (solid performance)
        sharpe_score = 18 + ((sharpe - 0.5) / 0.5) * 7  # 18-25 pts
        sharpe_status = "good"
    elif sharpe >= 0.0:
        # Fair: Sharpe 0.0-0.5 (acceptable but not great)
        sharpe_score = 10 + (sharpe / 0.5) * 8  # 10-18 pts
        sharpe_status = "fair"
    elif sharpe >= -0.5:
        # Warning: Sharpe -0.5 to 0.0 (poor risk-adjusted returns)
        sharpe_score = 5 + ((sharpe + 0.5) / 0.5) * 5  # 5-10 pts
        sharpe_status = "warning"
    else:
        # Poor: Sharpe < -0.5 (losing money with high risk)
        sharpe_score = 0
        sharpe_status = "poor"

    health_components["sharpe_ratio"] = {"score": round(sharpe_score, 1), "status": sharpe_status}

    # 4. Liquidity/leverage check (25 points)
    # Linear scoring: 1-2x = 25pts, 2-20x = 25-0pts linearly
    max_leverage = max((pos.get("leverage", 1.0) for pos in positions), default=1.0)
    if max_leverage <= 2.0:
        lev_score = 25
        lev_status = "excellent"
    elif max_leverage <= 20.0:
        # Linear interpolation: 2x -> 25pts, 20x -> 0pts
        lev_score = max(0, 25 - ((max_leverage - 2.0) / 18.0) * 25)
        if lev_score >= 18:
            lev_status = "good"
        elif lev_score >= 10:
            lev_status = "fair"
        elif lev_score >= 5:
            lev_status = "warning"
        else:
            lev_status = "poor"
    else:
        lev_score = 0
        lev_status = "poor"

    health_components["leverage"] = {"score": round(lev_score, 1), "status": lev_status}

    # Calculate total health score
    health_score = sum(comp["score"] for comp in health_components.values())

    # Calculate liquidation risk for leveraged positions
    liquidation_risks = []
    for pos in positions:
        if pos["position_type"] in ["futures_long", "futures_short"] and pos.get("leverage", 1) > 1:
            asset = pos["asset"]
            position_type = pos["position_type"]
            leverage = pos.get("leverage", 1.0)
            entry_price = pos.get("entry_price", 0)

            # Get current price
            price_key = (asset, position_type)
            current_price = current_prices.get(price_key, entry_price)

            # Calculate liquidation price (simplified)
            # For long: liquidation when loss = margin (1/leverage)
            # For short: similar but opposite direction
            if position_type == "futures_long":
                liquidation_price = entry_price * (1 - 0.9 / leverage)
                price_distance_pct = ((current_price - liquidation_price) / current_price) * 100
            else:  # futures_short
                liquidation_price = entry_price * (1 + 0.9 / leverage)
                price_distance_pct = ((liquidation_price - current_price) / current_price) * 100

            risk_level = "safe" if price_distance_pct > 50 else (
                "moderate" if price_distance_pct > 25 else "high"
            )

            liquidation_risks.append({
                "asset": asset,
                "position_type": position_type,
                "liquidation_price": liquidation_price,
                "current_price": current_price,
                "price_distance_pct": abs(price_distance_pct),
                "risk_level": risk_level,
            })

    overall_liquidation_risk = "low"
    if liquidation_risks:
        if any(r["risk_level"] == "high" for r in liquidation_risks):
            overall_liquidation_risk = "high"
        elif any(r["risk_level"] == "moderate" for r in liquidation_risks):
            overall_liquidation_risk = "moderate"

    # Rebalancing signal
    rebalancing_needed = delta_normalized > 0.05
    rebalancing_urgency = "high" if delta_normalized > 0.15 else (
        "medium" if delta_normalized > 0.05 else "none"
    )

    logger.debug(
        f"Alert dashboard: health={health_score}/100, "
        f"liquidation_risk={overall_liquidation_risk}, "
        f"rebalancing={rebalancing_urgency}"
    )

    return {
        "health_score": health_score,
        "health_components": health_components,
        "liquidation_risk": {
            "overall_risk": overall_liquidation_risk,
            "positions": liquidation_risks,
        },
        "rebalancing_signal": {
            "needed": rebalancing_needed,
            "urgency": rebalancing_urgency,
            "current_delta": delta_exposure,
            "delta_normalized": delta_normalized,
        },
    }


# Phase 2 functions (to be implemented)

def calculate_funding_waterfall(
    positions: list[dict],
    aligned_data: pd.DataFrame,
    current_prices: dict[tuple[str, str], float],
    current_value: float,
) -> dict[str, Any]:
    """
    Calculate P&L waterfall decomposition for perp/spot/lending strategies.

    Breaks down total P&L into components:
    - Spot position P&L
    - Futures position P&L
    - Cumulative funding payments/receipts
    - Lending interest (if applicable)
    - Transaction fees (if tracked)

    Args:
        positions: List of position dicts
        aligned_data: Aligned DataFrame with historical data
        current_prices: Dict of current prices
        current_value: Current portfolio value

    Returns:
        Dict with waterfall components and cumulative values
    """
    # TODO: Implement in Phase 2
    logger.warning("Funding waterfall calculation not yet implemented (Phase 2)")
    return {
        "components": [],
        "total_pnl": 0.0,
        "initial_value": 0.0,
        "final_value": current_value,
    }


def calculate_rolling_metrics(
    positions: list[dict],
    lookback_days: int = 30,
    window_size: int = 7,
) -> dict[str, Any]:
    """
    Calculate rolling risk metrics over time.

    Computes time series of:
    - Rolling volatility (30-day window)
    - Rolling VaR 95% and 99%
    - Rolling Sharpe ratio
    - Portfolio value over time

    Args:
        positions: List of position dicts
        lookback_days: Total days to analyze
        window_size: Rolling window size in days

    Returns:
        Dict with time series data for each metric
    """
    # TODO: Implement in Phase 2
    logger.warning("Rolling metrics calculation not yet implemented (Phase 2)")
    return {
        "timestamps": [],
        "volatility": [],
        "var_95": [],
        "var_99": [],
        "sharpe_ratio": [],
        "portfolio_value": [],
    }


def calculate_monte_carlo_fan(
    positions: list[dict],
    asset_returns: dict[str, np.ndarray],
    correlation_matrix: dict[str, dict[str, float]],
    current_value: float,
    time_horizon_days: int = 30,
    num_simulations: int = 10000,
) -> dict[str, Any]:
    """
    Calculate Monte Carlo simulation fan chart for future portfolio values.

    Uses multivariate normal distribution with historical correlations
    to simulate portfolio paths and generate probability bands.

    Args:
        positions: List of position dicts
        asset_returns: Dict of historical returns
        correlation_matrix: Asset correlation matrix
        current_value: Current portfolio value
        time_horizon_days: Days to simulate forward
        num_simulations: Number of Monte Carlo paths

    Returns:
        Dict with:
            - timestamps: Future dates
            - percentiles: {p5, p25, p50, p75, p95} for each timestamp
            - probability_metrics: Loss probability, target achievement probability
    """
    # TODO: Implement in Phase 2
    logger.warning("Monte Carlo fan chart calculation not yet implemented (Phase 2)")
    return {
        "timestamps": [],
        "p5": [],
        "p25": [],
        "p50": [],
        "p75": [],
        "p95": [],
        "probability_metrics": {
            "loss_probability": 0.0,
            "target_achievement_probability": 0.0,
        },
    }
