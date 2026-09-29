# DipSignal V1

## Research hypothesis and scope

A potentially interesting short-term dip is an observation unusually depressed
relative to its own ticker's recent feature history across several complementary
dimensions. V1 identifies research candidates; it does not say a stock will
rebound or should be bought. V1 is **not validated as a profitable trading strategy**.
No forward outcomes, scores, exits, positions, or trading execution are calculated.

## Prior-only historical thresholds

Defaults are `lookback=252`, `min_history=126`, `quantile=0.20`, and
`required_components=3`. Each feature
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
are available. Candidate generation requires this readiness in addition to
the component count, even when fewer than four active components are requested.
No missing feature or benchmark value is filled.

Identities must be unique and sorted by `(timestamp, ticker)`, with normalized
symbols and timezone-naive midnight session dates. Malformed input is rejected,
not silently sorted, deduplicated, or coerced. Windows count observed bars, not
calendar days, and do not audit missing exchange sessions.

## Count, condition, and event

`dip_component_count` is the integer sum of the four flags (0 through 4).
It retains available component information even on incomplete rows; a count
alone is not a candidate classification.

```text
dip_condition_v1 = dip_ready_v1 AND (dip_component_count >= required_components)
dip_event_v1 = dip_condition_v1 AND NOT previous_same_ticker_condition
```

`required_components` must be an integer from 1 through 4, excluding booleans.
The default is 3, without optimization. All four measurements and thresholds
must still be available even if only one active component is requested.

Conditions mark every qualifying observation. Events mark only an entry into
the condition, treating the first previous condition as false. For conditions
`F F T T T F T T`, events are `F F T F F F T F`. Warm-up cannot fire; the first
eligible qualifying row can. Consecutive means consecutive **observed rows of
the same ticker**, not consecutive calendar dates. Missing measurement/threshold
rows have condition=false and break a run: a subsequent eligible true row is a
new observed entry, not evidence of a distinct economic dip. Entirely absent
sessions do not insert false rows. Event de-duplication does not establish
statistically independent samples. No cooldown, holdings, or position state exists.

## API and availability

- `compute_historical_thresholds(...)`: identity plus four prior-only thresholds.
- `compute_dip_components(...)`: identity, thresholds, four boolean components,
  and the complete-row `dip_ready_v1` flag.
- `detect_dip_events(...)`: identity plus boolean rising-edge events; requires
  a defined boolean `dip_condition_v1` column, never truthy strings/numbers.
- `build_signals(...)`: preserves all feature/input columns and appends four
  thresholds, four components, readiness, count, condition, and event (12 columns).

All APIs preserve nested source provenance without mutating inputs and return a
fresh RangeIndex in canonical observation order. Percentile/component/build APIs
record configuration in `attrs["signal_parameters"]`; event detection preserves
the supplied metadata. The builder refuses to overwrite existing output columns.
pandas performs rolling quantiles and event shifts independently by ticker;
NumPy checks numerical validity. Only a per-ticker loop is needed, with compiled
rolling operations inside each group, not Python loops over observations. No
Polars conversion or new dependency is justified for this daily-data workload.

Example using existing local snapshots only (raises if they are unavailable):

```python
from src.data import DEFAULT_CACHE_DIR, load_parquet
from src.features import build_features
from src.signals import build_signals

aapl = load_parquet(DEFAULT_CACHE_DIR / "AAPL.parquet", ticker="AAPL")
spy = load_parquet(DEFAULT_CACHE_DIR / "SPY.parquet", ticker="SPY")
features = build_features(aapl, benchmark=spy)
candidates = build_signals(features)
events = candidates.loc[candidates["dip_event_v1"]]
```

For multiple stocks, supply their combined canonical feature frame with explicit
SPY benchmark features. Every distribution and previous-condition shift stays
inside the ticker boundary; adding another ticker cannot change existing outputs.

Components can use feature values from the current completed bar, so they become
available after the close. Subsequent execution generally cannot precede t+1;
no execution model is implemented. Provider revisions and adjusted-data vintage
bias remain despite computationally causal windows.

## Validation and limitations

Deterministic coverage includes exact interpolated thresholds, separate current
outlier-exclusion tests for all four features, warm-up and missingness, malformed
input/configuration, all component counts/cutoffs, and explicit event sequences.
Fourteen prefix tests use default/custom settings at seven cutoffs, both append
future observations and drastically change their values, and compare every
historical threshold/flag/count/condition/event exactly. Cross-ticker tests add
and alter extreme histories without changing the calm ticker. An OHLCV-to-feature-
to-signal regression also verifies prefix invariance and the combined warm-up.

With complete nondegenerate default features, the first eligible observation is
bar 186: 59 drawdown warm-up rows plus 126 prior valid drawdown measurements.
Undefined z-scores or missing benchmark endpoints can delay or interrupt readiness.

An offline fixed-default AAPL check with SPY context on 2026-09-30 used 2,512
observations (2016-09-29 through 2026-09-28): 2,327 eligible rows, 376 condition
days, and 117 events. Conditions represented 14.97% of all rows and 16.16% of
eligible rows. Example event dates: 2017-06-27, 2017-06-29, and 2017-09-08.
The frequency was neither effectively zero nor close to all observations; it
does not establish an appropriate frequency or useful outcomes. Defaults were
not changed. No future returns were inspected, no network was used, and no
generated outputs were persisted. Exact counts depend on the cached data vintage.

This validates implementation behavior, not the hypothesis's predictive value.
Correlated components, inclusive ties, changing distributions, overlapping events,
history length, convenience-universe survivorship, and revised adjusted data remain
research limitations. Appending/changing future rows cannot alter past outputs
for a fixed historical prefix; replacing past data or truncating required history
can. Historical bars and SPY provenance are trusted upstream contracts, not verified
here. No probabilities, optimized parameters, or profitability conclusions exist.
