"""Main risk profile calculation orchestration."""

import numpy as np
import pandas as pd
from loguru import logger

from src.analysis import data_service, metrics, scenarios, valuation


async def calculate_risk_profile(request_data: dict) -> dict:
    """
    Calculate comprehensive risk profile for a portfolio.

    Args:
        request_data: Dict with keys:
            - positions: List of position dicts
            - lookback_days: Number of days to look back (default: 30)

    Returns:
        Dict with risk profile data including:
            - current_portfolio_value
            - data_availability_warning
            - sensitivity_analysis
            - risk_metrics
            - scenarios
    """
    positions = request_data["positions"]
    lookback_days = request_data.get("lookback_days", 30)

    logger.info(f"Calculating risk profile for {len(positions)} positions")

    # Validate positions
    _validate_positions(positions)

    # Extract unique assets from positions
    assets = list(set(pos["asset"] for pos in positions))
    logger.info(f"Unique assets in portfolio: {assets}")

    # Step 1: Fetch historical data for all assets
    spot_data, futures_data, actual_days = await data_service.fetch_portfolio_data(
        assets, lookback_days
    )

    # Check data availability
    data_warning = None
    if actual_days < 30:
        data_warning = f"Warning: Only {actual_days} days of data available (recommended: 30+). Risk metrics may be unreliable."
        logger.warning(data_warning)

    # Step 2: Resample to daily intervals
    daily_spot, daily_futures = data_service.resample_to_daily(spot_data, futures_data)

    # Step 3: Align time series
    aligned_data, alignment_warnings = data_service.align_time_series(
        daily_spot, daily_futures
    )

    if alignment_warnings:
        warning_msg = "; ".join(alignment_warnings)
        if data_warning:
            data_warning += f" | {warning_msg}"
        else:
            data_warning = warning_msg

    logger.info(f"Aligned data shape: {aligned_data.shape}")

    # Step 4: Get current prices (most recent in aligned data)
    current_prices = _extract_current_prices(aligned_data, positions)
    logger.info(f"Current prices: {current_prices}")

    # Step 5: Calculate current portfolio value
    current_value = valuation.calculate_portfolio_value(positions, current_prices)
    logger.info(f"Current portfolio value: ${current_value:,.2f}")

    # Step 6: Calculate historical portfolio values and returns
    portfolio_values, portfolio_returns = _calculate_historical_portfolio_series(
        positions, aligned_data
    )

    logger.info(
        f"Historical portfolio: {len(portfolio_values)} values, {len(portfolio_returns)} returns"
    )

    # Step 7: Calculate sensitivity table
    from src.config import settings

    sensitivity_range = [x / 100 for x in settings.SENSITIVITY_RANGE]  # Convert to decimals
    sensitivity_table = valuation.calculate_sensitivity_table(
        positions, current_prices, sensitivity_range
    )

    # Step 8: Calculate risk metrics
    risk_metrics_data = _calculate_risk_metrics(
        portfolio_returns,
        portfolio_values,
        current_value,
        actual_days,
        positions,
        aligned_data,
    )

    # Step 9: Calculate delta exposure
    delta_exposure = valuation.calculate_delta_exposure(positions)
    risk_metrics_data["delta_exposure"] = delta_exposure
    logger.info(f"Delta exposure: {delta_exposure:.4f}")

    # Step 10: Run scenario analysis
    scenario_results = scenarios.run_all_scenarios(positions, current_prices)

    # Step 11: Construct response
    response = {
        "current_portfolio_value": current_value,
        "data_availability_warning": data_warning,
        "sensitivity_analysis": sensitivity_table,
        "risk_metrics": risk_metrics_data,
        "scenarios": scenario_results,
    }

    logger.info("Risk profile calculation completed successfully")
    return response


def _validate_positions(positions: list[dict]) -> None:
    """Validate position data."""
    if not positions:
        raise ValueError("Portfolio must contain at least one position")

    if len(positions) > 20:
        raise ValueError("Maximum 20 positions allowed")

    for i, pos in enumerate(positions):
        required_fields = ["asset", "quantity", "position_type", "entry_price"]
        for field in required_fields:
            if field not in pos:
                raise ValueError(
                    f"Position {i} missing required field: {field}"
                )

        if pos["position_type"] not in ["spot", "futures_long", "futures_short"]:
            raise ValueError(
                f"Position {i} has invalid position_type: {pos['position_type']}"
            )

        if pos["quantity"] <= 0:
            raise ValueError(f"Position {i} has invalid quantity: {pos['quantity']}")

        if pos["entry_price"] <= 0:
            raise ValueError(
                f"Position {i} has invalid entry_price: {pos['entry_price']}"
            )

        leverage = pos.get("leverage", 1.0)
        if leverage <= 0 or leverage > 125:
            raise ValueError(
                f"Position {i} has invalid leverage: {leverage} (must be 0 < leverage <= 125)"
            )


def _extract_current_prices(
    aligned_data: pd.DataFrame, positions: list[dict]
) -> dict[tuple[str, str], float]:
    """
    Extract current prices for each position from aligned data.

    Returns:
        Dict with (asset, position_type) tuple keys to handle same asset with different instruments
    """
    current_prices = {}
    latest_row = aligned_data.iloc[-1]

    for pos in positions:
        asset = pos["asset"]
        position_type = pos["position_type"]
        # Use composite key to differentiate spot vs futures for same asset
        price_key = (asset, position_type)

        if position_type == "spot":
            # Use spot price
            col_name = f"{asset}_spot"
            if col_name in aligned_data.columns:
                current_prices[price_key] = float(latest_row[col_name])
            else:
                raise ValueError(f"No spot data available for asset: {asset}")
        else:
            # Use futures mark price (both long and short use same mark price)
            col_name = f"{asset}_futures_mark"
            if col_name in aligned_data.columns:
                current_prices[price_key] = float(latest_row[col_name])
            else:
                raise ValueError(f"No futures data available for asset: {asset}")

    return current_prices


def _calculate_historical_portfolio_series(
    positions: list[dict], aligned_data: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    """
    Calculate historical portfolio values and returns.

    Returns:
        Tuple of (portfolio_values, portfolio_returns)
    """
    portfolio_values = []

    for _, row in aligned_data.iterrows():
        # Build price dict for this date using composite keys
        prices = {}
        for pos in positions:
            asset = pos["asset"]
            position_type = pos["position_type"]
            price_key = (asset, position_type)

            if position_type == "spot":
                col_name = f"{asset}_spot"
            else:
                col_name = f"{asset}_futures_mark"

            if col_name in aligned_data.columns:
                prices[price_key] = float(row[col_name])

        # Calculate portfolio value for this date
        if prices:
            value = valuation.calculate_portfolio_value(positions, prices)
            portfolio_values.append(value)

    portfolio_values = np.array(portfolio_values)
    portfolio_returns = metrics.calculate_returns(portfolio_values)

    return portfolio_values, portfolio_returns


def _calculate_risk_metrics(
    portfolio_returns: np.ndarray,
    portfolio_values: np.ndarray,
    current_value: float,
    actual_days: int,
    positions: list[dict],
    aligned_data: pd.DataFrame,
) -> dict:
    """Calculate all risk metrics."""
    from src.config import settings

    # Volatility
    volatility = metrics.calculate_volatility(
        portfolio_returns, annualize=True, periods_per_year=365
    )

    # VaR at multiple confidence levels
    var_95 = metrics.calculate_var_historical(portfolio_returns, 0.95, current_value)
    var_99 = metrics.calculate_var_historical(portfolio_returns, 0.99, current_value)

    # CVaR (use VaR 95% threshold)
    var_95_threshold = np.quantile(portfolio_returns, 0.05) if len(portfolio_returns) > 0 else 0
    cvar_95 = metrics.calculate_cvar(portfolio_returns, var_95_threshold, current_value)

    # Sharpe ratio
    sharpe = metrics.calculate_sharpe_ratio(
        portfolio_returns,
        risk_free_rate=settings.RISK_FREE_RATE,
        periods_per_year=365,
    )

    # Max drawdown
    max_dd = metrics.calculate_max_drawdown(portfolio_values)

    # Calculate correlation matrix
    asset_returns = _calculate_asset_returns(positions, aligned_data)
    corr_matrix = metrics.calculate_correlation_matrix(asset_returns)

    # Portfolio variance
    # First, calculate position values at current prices
    current_prices = _extract_current_prices(aligned_data, positions)
    positions_with_values = []
    for pos in positions:
        pos_copy = pos.copy()
        pos_value = valuation.calculate_position_value(pos, current_prices)
        pos_copy["value"] = pos_value
        positions_with_values.append(pos_copy)

    portfolio_variance = metrics.calculate_portfolio_variance(
        positions_with_values, asset_returns, corr_matrix
    )

    return {
        "lookback_days_used": actual_days,
        "portfolio_variance": portfolio_variance,
        "portfolio_volatility_annual": volatility,
        "var_95_1day": var_95,
        "var_99_1day": var_99,
        "cvar_95": cvar_95,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd,
        "correlation_matrix": corr_matrix,
    }


def _calculate_asset_returns(
    positions: list[dict], aligned_data: pd.DataFrame
) -> dict[str, np.ndarray]:
    """Calculate returns for each asset in the portfolio."""
    asset_returns = {}
    unique_assets = list(set(pos["asset"] for pos in positions))

    for asset in unique_assets:
        # Try spot first, then futures
        if f"{asset}_spot" in aligned_data.columns:
            prices = aligned_data[f"{asset}_spot"].values
        elif f"{asset}_futures_mark" in aligned_data.columns:
            prices = aligned_data[f"{asset}_futures_mark"].values
        else:
            continue

        returns = metrics.calculate_returns(prices)
        asset_returns[asset] = returns

    return asset_returns
