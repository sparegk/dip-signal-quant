"""Helpers for separately registered, volatility-scaled exit research."""

from numbers import Real

import numpy as np


def atr_scaled_barriers(
    entry_price: float,
    signal_atr: float,
    *,
    stop_atr_multiple: float,
    target_atr_multiple: float,
) -> dict[str, float]:
    """Return long barrier prices from ATR known at signal close.

    The ATR must be computed using bars through the signal session only. This
    function sizes distances; it does not select multipliers or evaluate results.
    """
    values = (entry_price, signal_atr, stop_atr_multiple, target_atr_multiple)
    if any(isinstance(value, (bool, np.bool_)) or not isinstance(value, Real)
           or not np.isfinite(value) for value in values):
        raise ValueError("Prices, ATR, and multipliers must be finite real numbers")
    entry, atr, stop_multiple, target_multiple = map(float, values)
    if entry <= 0 or atr <= 0 or stop_multiple <= 0 or target_multiple <= 0:
        raise ValueError("Prices, ATR, and multipliers must be positive")
    stop_distance = atr * stop_multiple
    target_distance = atr * target_multiple
    stop_price = entry - stop_distance
    target_price = entry + target_distance
    if not np.isfinite([stop_price, target_price]).all() or stop_price <= 0:
        raise ValueError("ATR barriers are not representable as positive finite prices")
    return {
        "stop_price": stop_price,
        "target_price": target_price,
        "stop_fraction": stop_distance / entry,
        "target_fraction": target_distance / entry,
    }
