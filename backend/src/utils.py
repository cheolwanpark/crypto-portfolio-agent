"""Utility functions for data sanitization and validation."""

import math
from typing import Any


# Maximum safe value for health factor (represents "infinite" health with no debt)
MAX_HEALTH_FACTOR = 999999.0


def sanitize_float(value: float | None, default: float | None = None) -> float | None:
    """Sanitize a float value to ensure JSON compliance.

    Converts inf/-inf/NaN to None or a default value to prevent JSON serialization errors.

    Args:
        value: Float value to sanitize
        default: Default value to return for invalid floats (None if not specified)

    Returns:
        Sanitized float value or None if invalid
    """
    if value is None:
        return default

    if not isinstance(value, (int, float)):
        return default

    # Check for inf or NaN
    if math.isinf(value) or math.isnan(value):
        return default

    return float(value)


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize all float values in a dictionary.

    Replaces inf/-inf/NaN with None to ensure JSON compliance.

    Args:
        data: Dictionary to sanitize

    Returns:
        Sanitized dictionary with all inf/NaN values replaced
    """
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        if isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = sanitize_list(value)
        elif isinstance(value, float):
            sanitized[key] = sanitize_float(value)
        else:
            sanitized[key] = value

    return sanitized


def sanitize_list(data: list[Any]) -> list[Any]:
    """Recursively sanitize all float values in a list.

    Replaces inf/-inf/NaN with None to ensure JSON compliance.

    Args:
        data: List to sanitize

    Returns:
        Sanitized list with all inf/NaN values replaced
    """
    if not isinstance(data, list):
        return data

    sanitized = []
    for item in data:
        if isinstance(item, dict):
            sanitized.append(sanitize_dict(item))
        elif isinstance(item, list):
            sanitized.append(sanitize_list(item))
        elif isinstance(item, float):
            sanitized.append(sanitize_float(item))
        else:
            sanitized.append(item)

    return sanitized


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero or result is invalid.

    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Default value to return if division is invalid

    Returns:
        Result of division or default if invalid
    """
    if denominator == 0 or abs(denominator) < 1e-10:
        return default

    result = numerator / denominator

    # Check if result is valid
    if math.isinf(result) or math.isnan(result):
        return default

    return result
