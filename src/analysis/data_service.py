"""Data fetching and time series alignment for risk analysis."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from loguru import logger

from src import database


async def fetch_portfolio_data(
    assets: list[str], lookback_days: int
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], int]:
    """
    Fetch historical spot and futures data for multiple assets concurrently.

    Args:
        assets: List of asset symbols (e.g., ['BTC', 'ETH'])
        lookback_days: Number of days to look back

    Returns:
        Tuple of (spot_data_dict, futures_data_dict, actual_days_available)
        - spot_data_dict: {asset: DataFrame with columns [timestamp, close]}
        - futures_data_dict: {asset: DataFrame with columns [timestamp, mark_price, funding_rate]}
        - actual_days_available: Minimum days available across all assets
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=lookback_days)

    logger.info(f"Fetching {lookback_days} days of data for assets: {assets}")
    logger.info(f"Date range: {start_time} to {end_time}")

    # Fetch spot data for all assets concurrently
    spot_tasks = [
        database.get_ohlcv_data(asset, start_time, end_time) for asset in assets
    ]
    spot_results = await asyncio.gather(*spot_tasks, return_exceptions=True)

    # Fetch futures data (mark prices and funding rates) concurrently
    mark_price_tasks = [
        database.get_mark_klines(asset, start_time, end_time) for asset in assets
    ]
    funding_rate_tasks = [
        database.get_funding_rates(asset, start_time, end_time) for asset in assets
    ]
    mark_price_results, funding_rate_results = await asyncio.gather(
        asyncio.gather(*mark_price_tasks, return_exceptions=True),
        asyncio.gather(*funding_rate_tasks, return_exceptions=True),
    )

    # Process spot data
    spot_data_dict = {}
    for asset, result in zip(assets, spot_results):
        if isinstance(result, Exception):
            logger.warning(f"Failed to fetch spot data for {asset}: {result}")
            continue

        if not result:
            logger.warning(f"No spot data available for {asset}")
            continue

        df = pd.DataFrame(result)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df[["timestamp", "close"]].sort_values("timestamp")
        spot_data_dict[asset] = df
        logger.info(f"Fetched {len(df)} spot candles for {asset}")

    # Process futures data
    futures_data_dict = {}
    for asset, mark_result, funding_result in zip(
        assets, mark_price_results, funding_rate_results
    ):
        if isinstance(mark_result, Exception) or isinstance(funding_result, Exception):
            logger.warning(
                f"Failed to fetch futures data for {asset}: mark={mark_result}, funding={funding_result}"
            )
            continue

        if not mark_result:
            logger.warning(f"No mark price data available for {asset}")
            continue

        # Process mark prices
        mark_df = pd.DataFrame(mark_result)
        mark_df["timestamp"] = pd.to_datetime(mark_df["timestamp"])
        mark_df = mark_df[["timestamp", "close"]].rename(columns={"close": "mark_price"})

        # Process funding rates
        funding_df = pd.DataFrame(funding_result) if funding_result else pd.DataFrame()
        if not funding_df.empty:
            funding_df["timestamp"] = pd.to_datetime(funding_df["timestamp"])
            funding_df = funding_df[["timestamp", "funding_rate"]]

            # Merge mark prices and funding rates
            futures_df = pd.merge(mark_df, funding_df, on="timestamp", how="left")
        else:
            futures_df = mark_df
            futures_df["funding_rate"] = 0.0  # Default to 0 if no funding data

        futures_df = futures_df.sort_values("timestamp")
        futures_data_dict[asset] = futures_df
        logger.info(
            f"Fetched {len(mark_df)} mark prices and {len(funding_df)} funding rates for {asset}"
        )

    # Calculate actual days available (minimum across all assets)
    min_days = lookback_days
    if spot_data_dict:
        for asset, df in spot_data_dict.items():
            days_available = (df["timestamp"].max() - df["timestamp"].min()).days
            min_days = min(min_days, days_available)

    logger.info(f"Actual data availability: {min_days} days")

    return spot_data_dict, futures_data_dict, min_days


def resample_to_daily(
    spot_data: dict[str, pd.DataFrame], futures_data: dict[str, pd.DataFrame]
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    """
    Resample 12h spot OHLCV and 8h futures data to daily (24h) intervals.

    Args:
        spot_data: Dict of {asset: DataFrame with 12h interval data}
        futures_data: Dict of {asset: DataFrame with 8h interval data}

    Returns:
        Tuple of (daily_spot_data, daily_futures_data)
    """
    logger.info("Resampling data to daily intervals")

    daily_spot = {}
    for asset, df in spot_data.items():
        if df.empty:
            continue

        # Resample to daily, taking the last close price of each day
        df_copy = df.copy()
        df_copy.set_index("timestamp", inplace=True)
        daily = df_copy.resample("D")["close"].last()
        daily = daily.dropna()

        daily_df = pd.DataFrame({"timestamp": daily.index, "close": daily.values})
        daily_spot[asset] = daily_df
        logger.debug(
            f"Resampled {asset} spot: {len(df)} -> {len(daily_df)} daily candles"
        )

    daily_futures = {}
    for asset, df in futures_data.items():
        if df.empty:
            continue

        df_copy = df.copy()
        df_copy.set_index("timestamp", inplace=True)

        # Resample mark price (take last of day)
        daily_mark = df_copy.resample("D")["mark_price"].last()

        # Resample funding rate (take mean of day, as it's a rate)
        daily_funding = df_copy.resample("D")["funding_rate"].mean()

        daily_df = pd.DataFrame(
            {
                "timestamp": daily_mark.index,
                "mark_price": daily_mark.values,
                "funding_rate": daily_funding.values,
            }
        )
        daily_df = daily_df.dropna()
        daily_futures[asset] = daily_df
        logger.debug(
            f"Resampled {asset} futures: {len(df)} -> {len(daily_df)} daily data points"
        )

    return daily_spot, daily_futures


def align_time_series(
    spot_data: dict[str, pd.DataFrame], futures_data: dict[str, pd.DataFrame]
) -> tuple[pd.DataFrame, list[str]]:
    """
    Align spot and futures time series to common timestamps with forward-fill.

    Args:
        spot_data: Dict of {asset: DataFrame with daily spot prices}
        futures_data: Dict of {asset: DataFrame with daily futures data}

    Returns:
        Tuple of (aligned_df, warnings)
        - aligned_df: Multi-column DataFrame with columns: timestamp, {asset}_spot, {asset}_futures_mark, {asset}_funding
        - warnings: List of warning messages about data gaps
    """
    logger.info("Aligning time series across assets")

    warnings = []

    # Combine all timestamps from all assets
    all_timestamps = set()
    for df in spot_data.values():
        all_timestamps.update(df["timestamp"])
    for df in futures_data.values():
        all_timestamps.update(df["timestamp"])

    if not all_timestamps:
        raise ValueError("No data available for any asset")

    # Create a date range from min to max timestamp
    min_ts = min(all_timestamps)
    max_ts = max(all_timestamps)
    date_range = pd.date_range(start=min_ts, end=max_ts, freq="D")

    # Build aligned DataFrame
    aligned = pd.DataFrame({"timestamp": date_range})

    # Add spot prices
    for asset, df in spot_data.items():
        aligned = pd.merge(aligned, df, on="timestamp", how="left", suffixes=("", "_dup"))
        aligned = aligned.rename(columns={"close": f"{asset}_spot"})

        # Forward-fill gaps
        aligned[f"{asset}_spot"] = aligned[f"{asset}_spot"].ffill()

        # Check for remaining NaN (gaps at the start)
        if aligned[f"{asset}_spot"].isna().any():
            na_count = aligned[f"{asset}_spot"].isna().sum()
            warnings.append(
                f"{asset} spot: {na_count} missing values at the beginning (no forward-fill source)"
            )
            # Backward fill for start gaps
            aligned[f"{asset}_spot"] = aligned[f"{asset}_spot"].bfill()

    # Add futures data
    for asset, df in futures_data.items():
        # Add mark price
        mark_df = df[["timestamp", "mark_price"]].rename(
            columns={"mark_price": f"{asset}_futures_mark"}
        )
        aligned = pd.merge(aligned, mark_df, on="timestamp", how="left")
        aligned[f"{asset}_futures_mark"] = aligned[f"{asset}_futures_mark"].ffill()

        # Add funding rate
        funding_df = df[["timestamp", "funding_rate"]].rename(
            columns={"funding_rate": f"{asset}_funding"}
        )
        aligned = pd.merge(aligned, funding_df, on="timestamp", how="left")
        aligned[f"{asset}_funding"] = aligned[f"{asset}_funding"].ffill()

        # Check for gaps
        if aligned[f"{asset}_futures_mark"].isna().any():
            na_count = aligned[f"{asset}_futures_mark"].isna().sum()
            warnings.append(f"{asset} futures: {na_count} missing mark prices")
            aligned[f"{asset}_futures_mark"] = aligned[f"{asset}_futures_mark"].bfill()

        if aligned[f"{asset}_funding"].isna().any():
            na_count = aligned[f"{asset}_funding"].isna().sum()
            warnings.append(f"{asset} funding: {na_count} missing funding rates")
            # Fill missing funding rates with 0 (neutral)
            aligned[f"{asset}_funding"] = aligned[f"{asset}_funding"].fillna(0.0)

    logger.info(f"Aligned data: {len(aligned)} daily data points")
    if warnings:
        for warning in warnings:
            logger.warning(f"Data gap: {warning}")

    return aligned, warnings
