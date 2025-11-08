"""Portfolio position valuation logic."""

from typing import Any


def calculate_spot_value(quantity: float, current_price: float) -> float:
    """
    Calculate the value of a spot position.

    Args:
        quantity: Number of units held
        current_price: Current market price

    Returns:
        Total value in USD
    """
    return quantity * current_price


def calculate_futures_long_value(
    quantity: float, entry_price: float, current_price: float, leverage: float
) -> float:
    """
    Calculate the value of a futures long position.

    Formula:
        Margin = (quantity × entry_price) / leverage
        PnL = (current_price - entry_price) × quantity
        Value = Margin + PnL

    Args:
        quantity: Number of contracts
        entry_price: Entry price of the position
        current_price: Current futures mark price
        leverage: Position leverage (only affects margin, not PnL)

    Returns:
        Total position value (margin + unrealized PnL)
    """
    margin = (quantity * entry_price) / leverage
    pnl = (current_price - entry_price) * quantity  # Leverage does NOT multiply PnL
    return margin + pnl


def calculate_futures_short_value(
    quantity: float, entry_price: float, current_price: float, leverage: float
) -> float:
    """
    Calculate the value of a futures short position.

    Formula:
        Margin = (quantity × entry_price) / leverage
        PnL = (entry_price - current_price) × quantity
        Value = Margin + PnL

    Args:
        quantity: Number of contracts
        entry_price: Entry price of the position
        current_price: Current futures mark price
        leverage: Position leverage (only affects margin, not PnL)

    Returns:
        Total position value (margin + unrealized PnL)
    """
    margin = (quantity * entry_price) / leverage
    pnl = (entry_price - current_price) * quantity  # Leverage does NOT multiply PnL
    return margin + pnl


def calculate_position_value(
    position: dict[str, Any], current_prices: dict[tuple[str, str] | str, float]
) -> float:
    """
    Calculate the value of a single position.

    Args:
        position: Dict with keys: asset, quantity, position_type, leverage, entry_price
        current_prices: Dict mapping (asset, position_type) tuple or asset string to current price

    Returns:
        Position value in USD
    """
    asset = position["asset"]
    quantity = position["quantity"]
    position_type = position["position_type"]
    entry_price = position["entry_price"]
    leverage = position.get("leverage", 1.0)

    # Try composite key first (asset, position_type), fallback to asset string
    price_key = (asset, position_type)
    current_price = current_prices.get(price_key)
    if current_price is None:
        # Fallback to simple asset key for backwards compatibility
        current_price = current_prices.get(asset)

    if current_price is None:
        raise ValueError(f"No current price available for {asset} ({position_type})")

    if position_type == "spot":
        return calculate_spot_value(quantity, current_price)
    elif position_type == "futures_long":
        return calculate_futures_long_value(quantity, entry_price, current_price, leverage)
    elif position_type == "futures_short":
        return calculate_futures_short_value(quantity, entry_price, current_price, leverage)
    else:
        raise ValueError(f"Unknown position type: {position_type}")


def calculate_portfolio_value(
    positions: list[dict[str, Any]], current_prices: dict[str, float]
) -> float:
    """
    Calculate total portfolio value across all positions.

    Args:
        positions: List of position dicts
        current_prices: Dict mapping asset to current price

    Returns:
        Total portfolio value in USD
    """
    total_value = 0.0
    for position in positions:
        total_value += calculate_position_value(position, current_prices)
    return total_value


def apply_price_shock(
    base_prices: dict[str, float], shock_pct: float
) -> dict[str, float]:
    """
    Apply a percentage price shock to all assets.

    Args:
        base_prices: Dict mapping asset to base price
        shock_pct: Percentage change (e.g., 0.10 for +10%, -0.20 for -20%)

    Returns:
        Dict mapping asset to shocked price
    """
    return {asset: price * (1 + shock_pct) for asset, price in base_prices.items()}


def calculate_delta_exposure(positions: list[dict[str, Any]]) -> float:
    """
    Calculate total delta exposure (market directional risk).

    Delta represents notional exposure to price movements.
    Leverage affects margin requirements but NOT directional exposure.

    Formula:
        Delta = Σ(spot quantities) + Σ(futures_long quantities) - Σ(futures_short quantities)

    Args:
        positions: List of position dicts

    Returns:
        Total delta exposure (positive = net long, negative = net short)
    """
    delta = 0.0

    for position in positions:
        quantity = position["quantity"]
        position_type = position["position_type"]

        if position_type == "spot":
            delta += quantity
        elif position_type == "futures_long":
            delta += quantity  # Leverage does NOT affect delta
        elif position_type == "futures_short":
            delta -= quantity  # Leverage does NOT affect delta

    return delta


def calculate_sensitivity_table(
    positions: list[dict[str, Any]],
    base_prices: dict[str, float],
    shock_range: list[float],
) -> list[dict[str, float]]:
    """
    Calculate portfolio sensitivity to price shocks.

    Args:
        positions: List of position dicts
        base_prices: Dict mapping asset to base (current) price
        shock_range: List of shock percentages (e.g., [-0.30, -0.25, ..., 0.30])

    Returns:
        List of dicts with keys: price_change_pct, portfolio_value, pnl, return_pct
    """
    base_value = calculate_portfolio_value(positions, base_prices)
    sensitivity_table = []

    for shock_pct in shock_range:
        shocked_prices = apply_price_shock(base_prices, shock_pct)
        shocked_value = calculate_portfolio_value(positions, shocked_prices)
        pnl = shocked_value - base_value
        return_pct = pnl / base_value if base_value != 0 else 0.0

        sensitivity_table.append(
            {
                "price_change_pct": shock_pct * 100,  # Convert to percentage
                "portfolio_value": shocked_value,
                "pnl": pnl,
                "return_pct": return_pct * 100,  # Convert to percentage
            }
        )

    return sensitivity_table
