# DipSignal V1

## Research hypothesis and scope

A potentially interesting short-term dip is an observation unusually depressed
relative to its own ticker's recent feature history across several complementary
dimensions. V1 identifies research candidates; it does not say a stock will
rebound or should be bought. V1 is **not validated as a profitable trading strategy**.
No forward outcomes, scores, exits, positions, or trading execution are calculated.

## Prior-only historical thresholds

Defaults are `lookback=252`, `min_history=126`, and `quantile=0.20`. Each feature
uses at most the previous 252 observed bar positions of its own ticker, ending
at t-1. Within that window, NaNs are excluded from the quantile sample but still
occupy bar positions. Require at least 126 valid prior values per feature;
otherwise that feature's threshold is NaN. Do not reach further back to replace
missing observations. Different features can therefore become available on
different dates or lose availability when valid observations roll out.

Implementation: split by ticker, then `feature.shift(1).rolling(lookback,
min_periods=min_history).quantile(quantile, interpolation="linear")`.
The current feature value never affects the threshold used to classify that row.
For m sorted valid historical values, use index `h=(m-1)*q` and linearly interpolate
between the surrounding order statistics. See the [pandas quantile reference](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.api.typing.Rolling.quantile.html).

Configuration requires integer `lookback >= 1`, integer `1 <= min_history <=
lookback`, and finite numeric `0 <= quantile <= 1`. Boolean configuration values
are rejected. Quantile endpoints represent the historical minimum/maximum;
the V1 research default remains 0.20. These defaults are hypotheses, not optimized
parameters or estimates of optimal settings.

## Four interpretable components

Each threshold column is named `{feature}_threshold`. Each component is true only
when the current value and its prior threshold exist and `current <= threshold`.

| Feature | Component column | Lower-tail interpretation |
| --- | --- | --- |
| `drawdown_60d` | `dip_drawdown_component` | Deeper recent close drawdown |
| `price_zscore_20d` | `dip_price_zscore_component` | Lower standardized price location |
| `distance_from_low_20d` | `dip_low_proximity_component` | Closer to the trailing low |
| `relative_return_10d` | `dip_relative_weakness_component` | Weaker recent performance relative to SPY |

These dimensions are correlated, not four independent confirmations. Counts
are for interpretation only and must not be converted to fake probabilities.
Inclusive comparisons honor ties: a constant available feature can activate on
every eligible row. A 20th-percentile threshold does not promise a 20% future
activation frequency, especially with ties or changing distributions. SPY relative
to itself is identically zero, so its relative component is not informative.

## Missingness and input contract

Required inputs are `timestamp`, `ticker`, and all four feature columns. Full
feature-engine output is accepted; standalone feature frames are also supported.
The caller must supply correctly defined SPY-relative features from a consistent
data vintage. Values are not recomputed or independently verified against a feed.
An absent required column raises, including missing benchmark-relative features;
it is never substituted with zero. Required features must be real numeric values
or NaN; infinities, booleans, numeric strings, and complex values raise.

NaNs from feature warm-up, zero-variance calculations, or unmatched benchmark
dates are valid missing measurements. Their components are false.
`dip_ready_v1` is true only if **all four current values and all four thresholds**
are available. Candidate generation will require this readiness in addition to
the component count, even when fewer than four active components are requested.
No missing feature or benchmark value is filled.

Identities must be unique and sorted by `(timestamp, ticker)`, with normalized
symbols and timezone-naive midnight session dates. Malformed input is rejected,
not silently sorted, deduplicated, or coerced. Windows count observed bars, not
calendar days, and do not audit missing exchange sessions.

## API and availability

- `compute_historical_thresholds(...)`: identity plus four prior-only thresholds.
- `compute_dip_components(...)`: identity, thresholds, four boolean components,
  and the complete-row `dip_ready_v1` flag.

Both APIs preserve nested source provenance without mutating inputs, return a
fresh RangeIndex in canonical observation order, and record configuration in
`attrs["signal_parameters"]`. pandas performs rolling quantiles independently
by ticker; NumPy checks numerical validity. No new dependency is introduced.

Components can use feature values from the current completed bar, so they become
available after the close. Subsequent execution generally cannot precede t+1;
no execution model is implemented. Provider revisions and adjusted-data vintage
bias remain despite computationally causal windows.

Condition/event generation is the next implementation step in this milestone.
