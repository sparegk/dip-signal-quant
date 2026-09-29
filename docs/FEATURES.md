# Quantitative features

Features are measurements, not trading recommendations, labels, or entry rules.

## Availability and input contract

Inputs use the validated schema from [MARKET_DATA.md](MARKET_DATA.md). They must
be sorted by `(timestamp, ticker)`, unique by observation identity, and contain
finite positive OHLC and nonnegative integer volume. Bad input raises; the feature
engine does not clean it. Input data and nested provenance are not mutated.

A feature at session `t` uses observations at or before `t` and is available only
after that session closes. Later execution generally starts at `t+1` or later;
these columns do not justify a same-close fill. Windows count observed bars per
ticker, not elapsed calendar days. No resampling, price filling, backward filling,
centered windows, future returns, or threshold rules are used.

Trailing extrema and moments include the current observation. Require the full
window (`min_periods=window`); warm-up NaNs remain explicit. Current adjusted
history can still contain later provider/corporate-action revisions: computational
causality does not turn the inputs into a point-in-time dataset.

## Price features

Write `C_t` for adjusted close and `mean_n`, `std_n`, `min_n`, `max_n` for
statistics over the most recent `n` observations ending at `t`.

| Name | Default windows | Definition / measurement | Required data | Warm-up / undefined |
| --- | --- | --- | --- | --- |
| `return_{n}d` | 1, 5, 10, 20 | `C_t / C_(t-n) - 1`; trailing fractional price change | Close | First n bars NaN |
| `drawdown_{n}d` | 20, 60 | `C_t / max_n(C) - 1`; distance below recent highest close | Close | First n-1 bars NaN |
| `distance_from_high_{n}d` | 20, 60 | Same definition as drawdown; computed once internally | Close | First n-1 bars NaN |
| `distance_from_low_{n}d` | 20, 60 | `C_t / min_n(C) - 1`; distance above recent lowest close | Close | First n-1 bars NaN |
| `price_zscore_{n}d` | 20 | `(C_t - mean_n(C)) / std_n(C)`; standardized price location | Close | First n-1 bars NaN; zero std => NaN |

All standard deviations use sample normalization (`ddof=1`). Price z-score
windows must be at least two. Other price windows must be positive integers.
Window collections are nonempty, deduplicated, and sorted. A 60-bar price z-score
can be requested explicitly; it is not a second default measurement.

## API

`compute_returns`, `compute_price_location_features`, and `compute_price_zscores`
return `timestamp`, `ticker`, and their feature family. Each accepts cleaned
single- or multi-ticker data and configurable windows. `build_features` appends
the feature families to a copy of all input columns, retaining source provenance.
Output rows remain in `(timestamp, ticker)` order with a fresh RangeIndex. Existing
columns that collide with generated features raise instead of being overwritten.

Calculations split by ticker before any shift or rolling operation. The builder
validates/group-splits once and concatenates once. pandas handles labelled
trailing calculations; NumPy handles safe vectorized arithmetic. Polars is not
needed for this in-memory daily workload. No new dependency is required.

```python
from src.data import get_history
from src.features import build_features

prices = get_history("AAPL")
measured = build_features(prices, zscore_windows=(20, 60))
```

Volume, volatility, Wilder RSI/ATR, and benchmark-relative measurements will be
documented as their implementation milestones are completed.
