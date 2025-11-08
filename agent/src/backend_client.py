"""Backend API client with retry logic and resilience."""

import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class BackendClient:
    """Client for calling backend API endpoints with retry logic."""

    def __init__(self, base_url: str, http_client: httpx.AsyncClient, api_key: str | None = None):
        """Initialize backend client.

        Args:
            base_url: Base URL of the backend API
            http_client: Shared async HTTP client
            api_key: Optional API key for protected endpoints
        """
        self.base_url = base_url
        self.client = http_client
        self.api_key = api_key

        # Set default headers with API key if provided
        if self.api_key:
            self.client.headers["X-API-Key"] = self.api_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_aggregated_stats(
        self,
        assets: str | list[str],
        start_date: str,
        end_date: str,
        data_types: list[str] = None,
    ) -> dict[str, Any]:
        """Fetch aggregated statistics for crypto assets.

        Args:
            assets: Single asset string or list of assets
            start_date: ISO 8601 UTC timestamp (e.g., "2025-01-01T00:00:00Z")
            end_date: ISO 8601 UTC timestamp
            data_types: List of data types ("spot", "futures", "lending")

        Returns:
            Aggregated statistics dict

        Raises:
            httpx.HTTPStatusError: If request fails after retries
        """
        if data_types is None:
            data_types = ["spot", "futures"]

        logger.debug(
            "get_aggregated_stats called with assets=%s, start_date=%s, end_date=%s, data_types=%s",
            assets,
            start_date,
            end_date,
            data_types,
        )

        if isinstance(assets, list):
            # Multi-asset endpoint
            url = f"{self.base_url}/api/v1/aggregated-stats/multi"
            params = {
                "assets": ",".join(assets),
                "start": start_date,
                "end": end_date,
                "data_types": ",".join(data_types),
            }
        else:
            # Single asset endpoint
            url = f"{self.base_url}/api/v1/aggregated-stats/{assets}"
            params = {
                "start": start_date,
                "end": end_date,
                "data_types": ",".join(data_types),
            }

        logger.debug("Making request to URL=%s with params=%s", url, params)
        response = await self.client.get(url, params=params, timeout=10.0)
        logger.debug("Response status: %d", response.status_code)
        response.raise_for_status()
        result = response.json()
        logger.debug("Response JSON: %s", result)

        # Log if response contains only null data
        data = result.get("data", {})
        if data:
            all_null = all(
                all(v is None for v in asset_data.values()) if isinstance(asset_data, dict) else True
                for asset_data in data.values()
            )
            if all_null:
                logger.warning(
                    "Backend returned all-null data for assets=%s, date_range=%s to %s, data_types=%s",
                    assets if isinstance(assets, str) else ",".join(assets),
                    start_date,
                    end_date,
                    ",".join(data_types)
                )

        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def calculate_risk_profile(
        self,
        positions: list[dict[str, Any]],
        lookback_days: int = 30,
    ) -> dict[str, Any]:
        """Calculate comprehensive risk metrics for a portfolio.

        Args:
            positions: List of position dictionaries
            lookback_days: Historical lookback period (7-180)

        Returns:
            Risk profile dict with metrics, scenarios, etc.

        Raises:
            httpx.HTTPStatusError: If request fails after retries
        """
        logger.debug(
            "calculate_risk_profile called with %d positions, lookback_days=%d",
            len(positions),
            lookback_days,
        )
        logger.debug("Positions: %s", positions)

        url = f"{self.base_url}/api/v1/analysis/risk-profile"
        payload = {
            "positions": positions,
            "lookback_days": lookback_days,
        }

        logger.debug("Making request to URL=%s with payload=%s", url, payload)
        response = await self.client.post(url, json=payload, timeout=30.0)
        logger.debug("Response status: %d", response.status_code)
        response.raise_for_status()
        result = response.json()
        logger.debug("Response JSON: %s", result)
        return result
