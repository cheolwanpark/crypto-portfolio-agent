"""Unified portfolio advisory tools using BaseTool pattern."""

import json
import re
from datetime import datetime
from typing import Annotated, Any, Dict, Optional

from src.agent.models import ToolContext
from src.models import PortfolioPosition
from src.wrapper import BaseTool, tool

# Asset validation constants
VALID_SPOT_FUTURES_ASSETS = {"BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "LINK"}
VALID_LENDING_ASSETS = {"WETH", "WBTC", "USDC", "USDT", "DAI"}
LENDING_SYMBOL_MAPPING = {"BTC": "WBTC", "ETH": "WETH"}

# Position type constants
VALID_POSITION_TYPES = {
    "spot",
    "futures_long",
    "futures_short",
    "lending_supply",
    "lending_borrow"
}

# Validation ranges
MIN_QUANTITY = 0.0  # exclusive
MIN_ENTRY_PRICE = 0.0  # exclusive
MIN_LEVERAGE = 0.0  # exclusive
MAX_LEVERAGE = 125.0
MIN_LOOKBACK_DAYS = 7
MAX_LOOKBACK_DAYS = 180
MIN_POSITIONS = 1
MAX_POSITIONS = 20

# ISO 8601 UTC datetime regex pattern
ISO8601_UTC_PATTERN = re.compile(
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$'
)


def _validate_asset(asset: str, data_type: str) -> Optional[str]:
    """Validate asset symbol against available assets.

    Args:
        asset: Asset symbol to validate
        data_type: Type of data ("spot", "futures", or "lending")

    Returns:
        Error message if invalid, None if valid
    """
    asset_upper = asset.upper()

    if data_type in ("spot", "futures"):
        if asset_upper not in VALID_SPOT_FUTURES_ASSETS:
            return (
                f"Invalid asset '{asset}' for {data_type} data. "
                f"Available assets: {', '.join(sorted(VALID_SPOT_FUTURES_ASSETS))}"
            )
    elif data_type == "lending":
        # Check if it's a valid lending asset or can be mapped
        mapped_asset = LENDING_SYMBOL_MAPPING.get(asset_upper, asset_upper)
        if mapped_asset not in VALID_LENDING_ASSETS:
            return (
                f"Invalid asset '{asset}' for lending data. "
                f"Available assets: {', '.join(sorted(VALID_LENDING_ASSETS))} "
                f"(BTC and ETH auto-map to WBTC and WETH)"
            )

    return None


def _validate_date_format(date_str: str, field_name: str) -> Optional[str]:
    """Validate ISO 8601 UTC datetime format.

    Args:
        date_str: Date string to validate
        field_name: Name of the field for error message

    Returns:
        Error message if invalid, None if valid
    """
    if not ISO8601_UTC_PATTERN.match(date_str):
        return (
            f"Invalid {field_name} format: '{date_str}'. "
            f"Must be ISO 8601 UTC format (e.g., '2025-01-01T00:00:00Z'). "
            f"Common mistakes: missing 'T' separator, missing 'Z' timezone, "
            f"using space instead of 'T', or omitting time component."
        )

    # Additional validation: try parsing to ensure it's a valid date
    try:
        datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError as e:
        return f"Invalid {field_name}: {str(e)}"

    return None


def _validate_date_range(start: str, end: str, max_days: int) -> Optional[str]:
    """Validate date range doesn't exceed maximum.

    Args:
        start: Start date (ISO 8601 UTC)
        end: End date (ISO 8601 UTC)
        max_days: Maximum allowed range in days

    Returns:
        Error message if invalid, None if valid
    """
    try:
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))

        if end_dt <= start_dt:
            return f"end_date must be after start_date (start: {start}, end: {end})"

        delta_days = (end_dt - start_dt).days
        if delta_days > max_days:
            return (
                f"Date range too large: {delta_days} days (max {max_days} days). "
                f"Please reduce the range or split into multiple queries."
            )
    except Exception as e:
        return f"Failed to parse date range: {str(e)}"

    return None


def _validate_position(position: Dict[str, Any], index: int) -> Optional[str]:
    """Validate a single position structure and values.

    Args:
        position: Position dictionary to validate
        index: Position index for error messages

    Returns:
        Error message if invalid, None if valid
    """
    # Check required base fields
    if "asset" not in position:
        return f"Position {index}: Missing required field 'asset'"

    if "quantity" not in position:
        return f"Position {index}: Missing required field 'quantity'"

    if "position_type" not in position:
        return f"Position {index}: Missing required field 'position_type'"

    # Validate position_type
    pos_type = position["position_type"]
    if pos_type not in VALID_POSITION_TYPES:
        return (
            f"Position {index}: Invalid position_type '{pos_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_POSITION_TYPES))}. "
            f"Common mistakes: using 'long' instead of 'futures_long', "
            f"'short' instead of 'futures_short'."
        )

    # Validate quantity
    quantity = position.get("quantity", 0)
    if not isinstance(quantity, (int, float)) or quantity <= MIN_QUANTITY:
        return f"Position {index}: quantity must be a positive number (got {quantity})"

    # Validate type-specific required fields
    if pos_type in ("spot", "futures_long", "futures_short"):
        # Spot and futures require entry_price
        if "entry_price" not in position:
            return f"Position {index}: Missing required field 'entry_price' for {pos_type}"

        entry_price = position["entry_price"]
        if not isinstance(entry_price, (int, float)) or entry_price <= MIN_ENTRY_PRICE:
            return f"Position {index}: entry_price must be a positive number (got {entry_price})"

        # Futures require leverage
        if pos_type in ("futures_long", "futures_short"):
            leverage = position.get("leverage", 1.0)
            if not isinstance(leverage, (int, float)) or leverage <= MIN_LEVERAGE or leverage > MAX_LEVERAGE:
                return (
                    f"Position {index}: leverage must be between {MIN_LEVERAGE} (exclusive) "
                    f"and {MAX_LEVERAGE} (got {leverage})"
                )

    elif pos_type in ("lending_supply", "lending_borrow"):
        # Lending requires entry_timestamp
        if "entry_timestamp" not in position:
            return (
                f"Position {index}: Missing required field 'entry_timestamp' for {pos_type}. "
                f"Provide the ISO 8601 UTC timestamp when the position was opened "
                f"(e.g., '2025-01-01T00:00:00Z')"
            )

        # Validate timestamp format
        timestamp = position["entry_timestamp"]
        error = _validate_date_format(timestamp, "entry_timestamp")
        if error:
            return f"Position {index}: {error}"

        # Borrow positions need borrow_type
        if pos_type == "lending_borrow" and "borrow_type" not in position:
            return (
                f"Position {index}: Missing required field 'borrow_type' for lending_borrow. "
                f"Must be either 'variable' or 'stable'"
            )

        if pos_type == "lending_borrow":
            borrow_type = position.get("borrow_type")
            if borrow_type not in ("variable", "stable"):
                return (
                    f"Position {index}: borrow_type must be 'variable' or 'stable' "
                    f"(got '{borrow_type}')"
                )

    # Validate asset based on position type
    asset = position["asset"]
    if pos_type in ("spot", "futures_long", "futures_short"):
        error = _validate_asset(asset, "spot")  # spot and futures use same asset list
        if error:
            return f"Position {index}: {error}"
    else:  # lending positions
        error = _validate_asset(asset, "lending")
        if error:
            return f"Position {index}: {error}"

    return None


class PortfolioTools(BaseTool):
    """Complete tool collection for crypto portfolio risk advisory.

    Provides tools for historical data analysis, risk profiling, and
    portfolio management using the MCP BaseTool pattern.
    """

    tool_server_name = "portfolio_advisor"
    tool_server_version = "1.0.0"

    def __init__(self, context: ToolContext) -> None:
        """Initialize portfolio tools with shared context.

        Args:
            context: Tool context with chat_id, backend_client, and portfolio state
        """
        self.context = context
        super().__init__()

    # Historical Data Tools

    @tool()
    async def get_aggregated_stats(
        self,
        assets: Annotated[
            str,
            "Single asset symbol (e.g., 'BTC') or comma-separated list (e.g., 'BTC,ETH,SOL') for multiple assets. Max 10 assets.",
        ],
        start_date: Annotated[
            str,
            "Start date in ISO 8601 UTC format (e.g., '2025-01-01T00:00:00Z'). Max 90 days from end_date.",
        ],
        end_date: Annotated[
            str,
            "End date in ISO 8601 UTC format (e.g., '2025-02-01T00:00:00Z')",
        ],
        data_types: Annotated[
            str,
            "Comma-separated data types to include. Options: 'spot', 'futures', 'lending'. Default: 'spot,futures'",
        ] = "spot,futures",
    ) -> Dict[str, Any]:
        """Fetch aggregated statistics for crypto assets from the backend API.

        Use this to get historical price data, volatility, returns, funding rates,
        lending rates, and other aggregated metrics for analysis.

        Returns JSON with aggregated statistics including:
        - Spot stats: current_price, min/max/mean price, total return, volatility,
          Sharpe ratio, max drawdown
        - Futures stats: funding rates, basis premium, open interest
        - Lending stats: supply/borrow APY, spread
        - Correlation matrix (for multiple assets)
        """
        import logging
        logger = logging.getLogger(__name__)

        # Parse inputs
        asset_list = [a.strip() for a in assets.split(",")] if "," in assets else [assets.strip()]
        data_type_list = [dt.strip() for dt in data_types.split(",")]

        logger.debug("get_aggregated_stats: assets=%s, dates=%s to %s", asset_list, start_date, end_date)

        # Validate assets
        for asset in asset_list:
            # Determine which asset list to check based on data types
            for data_type in data_type_list:
                if data_type in ("spot", "futures"):
                    error = _validate_asset(asset, "spot")
                elif data_type == "lending":
                    error = _validate_asset(asset, "lending")
                else:
                    continue

                if error:
                    return {
                        "error": error,
                        "hint": "Check the BACKEND API REFERENCE section in your system prompt for the complete list of available assets."
                    }

        # Validate max 10 assets
        if len(asset_list) > 10:
            return {
                "error": f"Too many assets: {len(asset_list)} (max 10 allowed)",
                "provided_assets": asset_list,
                "hint": "Split your request into multiple calls with ≤10 assets each."
            }

        # Validate date formats
        start_error = _validate_date_format(start_date, "start_date")
        if start_error:
            return {
                "error": start_error,
                "hint": "Use ISO 8601 UTC format like '2025-01-01T00:00:00Z'. Include the 'T' separator and 'Z' timezone."
            }

        end_error = _validate_date_format(end_date, "end_date")
        if end_error:
            return {
                "error": end_error,
                "hint": "Use ISO 8601 UTC format like '2025-01-01T00:00:00Z'. Include the 'T' separator and 'Z' timezone."
            }

        try:
            # Call backend
            result = await self.context.backend_client.get_aggregated_stats(
                assets=asset_list,
                start_date=start_date,
                end_date=end_date,
                data_types=data_type_list,
            )

            # Check if result contains any actual data
            data = result.get("data", {})
            if data:
                # Check if all assets have null/None stats
                all_null = all(
                    all(v is None for v in asset_data.values()) if isinstance(asset_data, dict) else True
                    for asset_data in data.values()
                )

                if all_null:
                    return {
                        "error": "No data available for the requested date range",
                        "requested_assets": asset_list,
                        "requested_date_range": f"{start_date} to {end_date}",
                        "requested_data_types": data_type_list,
                        "hint": "The database may not have data for this period. Try: 1) Check if the backend has completed initial backfill, 2) Use a more recent date range (e.g., last 30 days), 3) Verify the backend service is running and collecting data.",
                        "debug_response": result
                    }

            return result

        except Exception as e:
            # Extract 'detail' field from HTTP error response
            import httpx

            error_detail = str(e)
            if isinstance(e, httpx.HTTPStatusError):
                try:
                    error_json = e.response.json()
                    if 'detail' in error_json:
                        error_detail = error_json['detail']
                except:
                    pass

            return {
                "error": f"Backend API error: {error_detail}",
                "requested_assets": asset_list,
                "requested_date_range": f"{start_date} to {end_date}",
                "hint": "Check the error message above and adjust your parameters accordingly."
            }

    # Risk Profile Tools

    @tool()
    async def calculate_risk_profile(
        self,
        positions_json: Annotated[
            str,
            """JSON array of position objects. Each position must have:
- asset (str): Asset symbol (e.g., 'BTC', 'ETH', 'WETH', 'USDC')
- quantity (float): Position size, must be > 0
- position_type (str): One of 'spot', 'futures_long', 'futures_short', 'lending_supply', 'lending_borrow'
- entry_price (float): Entry price in USD (required for spot/futures, ignored for lending)
- leverage (float, optional): 1.0-125.0, default 1.0 (for futures only)
- entry_timestamp (str, optional): ISO 8601 timestamp for lending positions
- borrow_type (str, optional): 'variable' or 'stable' for lending_borrow

Example: [{"asset": "BTC", "quantity": 1.5, "position_type": "spot", "entry_price": 45000.0, "leverage": 1.0}]""",
        ],
        lookback_days: Annotated[
            int,
            "Historical lookback period in days (7-180). Default: 30. Used to calculate historical volatility, correlations, VaR.",
        ] = 30,
    ) -> Dict[str, Any]:
        """Calculate comprehensive risk metrics for a portfolio.

        Use this to analyze the risk characteristics of a portfolio including VaR,
        volatility, Sharpe ratio, stress test scenarios, and lending metrics.

        Returns JSON with comprehensive risk analysis including:
        - current_portfolio_value: Total portfolio value in USD
        - sensitivity_analysis: Portfolio value at various price changes (-30% to +30%)
        - risk_metrics: volatility, VaR (95%, 99%), CVaR, Sharpe ratio, max drawdown,
          correlation matrix
        - scenarios: 8 predefined market scenarios (bull, bear, flash crash, etc.)
        - lending_metrics: If lending positions exist - LTV, health factor,
          net APY, liquidation risk
        """
        # Parse JSON
        try:
            positions = json.loads(positions_json)
        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON syntax: {str(e)}",
                "hint": "Ensure positions_json is a valid JSON array. Check for missing commas, quotes, or brackets.",
                "example": '[{"asset": "BTC", "quantity": 1.5, "position_type": "spot", "entry_price": 45000.0}]'
            }

        # Validate basic structure
        if not isinstance(positions, list):
            return {
                "error": f"positions_json must be a JSON array, got {type(positions).__name__}",
                "hint": "Wrap your position(s) in square brackets [...] even if there's only one position."
            }

        if len(positions) < MIN_POSITIONS:
            return {
                "error": f"At least {MIN_POSITIONS} position is required (got {len(positions)})",
                "hint": "Provide at least one position to analyze."
            }

        if len(positions) > MAX_POSITIONS:
            return {
                "error": f"Too many positions: {len(positions)} (max {MAX_POSITIONS} allowed)",
                "hint": "Split large portfolios into smaller groups or focus on the most significant positions."
            }

        # Validate lookback_days range
        if not (MIN_LOOKBACK_DAYS <= lookback_days <= MAX_LOOKBACK_DAYS):
            return {
                "error": f"lookback_days must be between {MIN_LOOKBACK_DAYS} and {MAX_LOOKBACK_DAYS} (got {lookback_days})",
                "hint": "For portfolios with futures positions, use lookback_days ≤ 30 due to data availability limits."
            }

        # Validate each position
        for i, position in enumerate(positions, start=1):
            error = _validate_position(position, i)
            if error:
                return {
                    "error": error,
                    "position_index": i,
                    "provided_position": position,
                    "hint": "Check the BACKEND API REFERENCE section in your system prompt for required fields per position type."
                }

        # Check if any futures positions exist and warn if lookback is > 30 days
        has_futures = any(
            p.get("position_type") in ("futures_long", "futures_short")
            for p in positions
        )
        if has_futures and lookback_days > 30:
            return {
                "error": f"Portfolio contains futures positions but lookback_days={lookback_days} exceeds data availability",
                "hint": "Futures funding rate data is only available for ~30 days. Use lookback_days ≤ 30 for portfolios with futures positions.",
                "affected_positions": [
                    i+1 for i, p in enumerate(positions)
                    if p.get("position_type") in ("futures_long", "futures_short")
                ]
            }

        try:
            # Call backend
            result = await self.context.backend_client.calculate_risk_profile(
                positions=positions,
                lookback_days=lookback_days,
            )

            return result

        except Exception as e:
            # Extract 'detail' field from HTTP error response
            import httpx

            error_detail = str(e)
            if isinstance(e, httpx.HTTPStatusError):
                try:
                    error_json = e.response.json()
                    if 'detail' in error_json:
                        error_detail = error_json['detail']
                except:
                    pass

            return {
                "error": f"Backend API error: {error_detail}",
                "requested_positions_count": len(positions),
                "requested_lookback_days": lookback_days,
                "hint": "Check the error message above. The backend may be unable to calculate risk for this portfolio."
            }

    # Portfolio Management Tools

    @tool()
    async def set_portfolio(
        self,
        positions_json: Annotated[
            str,
            """JSON array of position objects. Same format as calculate_risk_profile.
Each position must have: asset, quantity, position_type, entry_price,
leverage (optional), and lending-specific fields if applicable.

Example: [
    {"asset": "BTC", "quantity": 0.5, "position_type": "spot", "entry_price": 45000.0},
    {"asset": "ETH", "quantity": 5.0, "position_type": "futures_long", "entry_price": 2500.0, "leverage": 2.0}
]""",
        ],
        explanation: Annotated[
            str,
            "Clear explanation of WHY you're recommending this portfolio composition. Include reasoning about risk/return trade-offs, diversification, and how it meets the user's constraints.",
        ],
    ) -> Dict[str, Any]:
        """Update the portfolio recommendation for this chat.

        Call this when you have a portfolio recommendation to make. The portfolio
        will be stored and visible to the user immediately.
        """
        # Parse JSON
        try:
            positions_data = json.loads(positions_json)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON syntax: {str(e)}",
                "hint": "Ensure positions_json is a valid JSON array. Check for missing commas, quotes, or brackets.",
                "example": '[{"asset": "BTC", "quantity": 0.5, "position_type": "spot", "entry_price": 45000.0}]'
            }

        # Validate basic structure
        if not isinstance(positions_data, list):
            return {
                "success": False,
                "error": f"positions_json must be a JSON array, got {type(positions_data).__name__}",
                "hint": "Wrap your position(s) in square brackets [...] even if there's only one position."
            }

        if len(positions_data) < MIN_POSITIONS:
            return {
                "success": False,
                "error": f"At least {MIN_POSITIONS} position is required (got {len(positions_data)})",
                "hint": "Provide at least one position to set the portfolio."
            }

        if len(positions_data) > MAX_POSITIONS:
            return {
                "success": False,
                "error": f"Too many positions: {len(positions_data)} (max {MAX_POSITIONS} allowed)",
                "hint": "Focus on the most significant positions or split into multiple portfolios."
            }

        # Validate each position before creating Pydantic models
        for i, position in enumerate(positions_data, start=1):
            error = _validate_position(position, i)
            if error:
                return {
                    "success": False,
                    "error": error,
                    "position_index": i,
                    "provided_position": position,
                    "hint": "Check the BACKEND API REFERENCE section in your system prompt for required fields per position type."
                }

        # Validate using Pydantic models (this provides additional type checking)
        try:
            positions = [PortfolioPosition(**p) for p in positions_data]
        except Exception as e:
            return {
                "success": False,
                "error": f"Pydantic validation failed: {str(e)}",
                "hint": "The position structure is valid but field types or values don't match the schema. Check that all numeric fields are numbers, not strings."
            }

        # Validate explanation is not empty
        if not explanation or not explanation.strip():
            return {
                "success": False,
                "error": "explanation is required and must not be empty",
                "hint": "Provide a clear explanation of WHY you're recommending this portfolio. Include reasoning about risk/return trade-offs and how it meets user constraints."
            }

        # Update context (will be committed by worker atomically)
        self.context.current_portfolio = positions
        self.context.reasonings.append(f"Portfolio Update: {explanation}")

        return {
            "success": True,
            "positions_count": len(positions),
            "message": f"Portfolio updated with {len(positions)} position(s)",
            "explanation": explanation,
        }

    @tool()
    async def get_current_portfolio(self) -> Dict[str, Any]:
        """Get the current portfolio for this chat.

        Use this to check what portfolio is currently recommended before making updates.
        """
        if self.context.current_portfolio:
            positions_data = [p.model_dump() for p in self.context.current_portfolio]
            return {
                "has_portfolio": True,
                "positions": positions_data,
                "count": len(positions_data),
            }
        else:
            return {
                "has_portfolio": False,
                "message": "No portfolio has been set yet",
            }
