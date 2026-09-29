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

## RSI, range, volatility, and volume

All entries below follow the same after-close availability convention above.
Let `r_t = C_t / C_(t-1) - 1`, `V_t` be reported volume, and `H_t`, `L_t` be
adjusted high/low. Ratios and returns are fractions, not percentage points.

| Name | Default window | Definition / measurement | Required data | Warm-up / undefined |
| --- | --- | --- | --- | --- |
| `rsi_{n}` | 14 | `100 * G_t / (G_t + D_t)`; relative smoothed up/down price changes | Close | First n bars NaN; both averages zero => NaN |
| `true_range` | Previous bar | `max(H_t-L_t, abs(H_t-C_(t-1)), abs(L_t-C_(t-1)))`; range including gaps | High, low, close | First bar NaN (previous close unavailable) |
| `atr_{n}` | 14 | Wilder-smoothed True Range; absolute price-unit movement scale | High, low, close | First n bars NaN |
| `atr_pct_{n}` | 14 | `atr_n / C_t`; movement scale relative to price | High, low, close | First n bars NaN |
| `volatility_{n}d` | 20, 60 | `std_n(r) * sqrt(252)`; annualized realized variation | Close | First n bars NaN; constant returns => zero |
| `volume_mean_{n}d` | 20 | `mean_n(V)`; trailing activity scale | Volume | First n-1 bars NaN |
| `relative_volume_{n}d` | 20 | `V_t / mean_n(V)`; volume relative to recent average | Volume | First n-1 bars NaN; zero mean => NaN |
| `volume_zscore_{n}d` | 20 | `(V_t - mean_n(V)) / std_n(V)`; standardized activity | Volume | First n-1 bars NaN; zero std => NaN |

RSI uses gains `max(C_t-C_(t-1), 0)` and losses `max(C_(t-1)-C_t, 0)`.
`G` and `D` begin with the arithmetic mean of the first n changes. Thereafter,
each average follows `S_t = ((n-1)*S_(t-1) + x_t) / n`. Gain-only history gives
100, loss-only history gives zero, and completely flat history stays undefined.
These limiting values are mathematical results, not trading thresholds.

ATR seeds with the mean of the first n defined True Ranges (bars 2 through n+1),
then uses the same Wilder recurrence. No high-minus-low substitute is invented
for the first unavailable previous close. RSI and ATR both first appear on bar
n+1. Wilder averages retain decaying dependence on earlier history; n is a
smoothing period, not a hard truncation after the seed.

The implementation explicitly inserts the arithmetic seed before using pandas
[`ewm(alpha=1/n, adjust=False)`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.ewm.html).
This avoids seeding with just the first observation. The recurrence is consistent
with the established [RSI](https://github.com/TA-Lib/ta-lib/blob/main/src/ta_func/ta_RSI.c)
and [ATR](https://github.com/TA-Lib/ta-lib/blob/main/src/ta_func/ta_ATR.c) formulations;
the all-flat RSI NaN convention is explicit and may differ from other libraries.

Volume moments include current volume. A zero-volume bar with a positive trailing
mean has relative volume zero; an all-zero volume window has undefined relative
volume and z-score. Prices, raw volume, and warm-up values are never filled.
Volatility and volume windows require n >= 2, RSI n >= 2, and ATR n >= 1.
`annualization=252` is configurable; `annualization=1` reports daily std instead.
These features neither infer liquidity nor impose a market-regime classification.

## Benchmark-relative measurements

Supply a separate validated, single-ticker benchmark frame, normally SPY. The
engine neither downloads a benchmark nor implicitly chooses one from the input.
Benchmark context is computed once using its full supplied history, before
aligning to stocks. The stock row set and order are preserved.

Let `B(t)` be benchmark close on the exact stock session date `t`, and `s` the
date n observed stock bars before `t`.

| Name | Default window | Definition / measurement | Required data | Warm-up / undefined |
| --- | --- | --- | --- | --- |
| `relative_return_{n}d` | 5, 10, 20 | `(C_t/C_s - 1) - (B(t)/B(s) - 1)`; difference in trailing returns over identical endpoints | Stock and benchmark close, exact timestamps | First n stock bars NaN; missing benchmark endpoint => NaN |
| `benchmark_return_{n}d` | 20 | Benchmark's own n-bar trailing simple return; market price change | Benchmark close | First n benchmark bars NaN; unmatched stock date => NaN |
| `benchmark_drawdown_{n}d` | 20 | Benchmark close / trailing highest benchmark close - 1; market price location | Benchmark close | First n-1 benchmark bars NaN; unmatched date => NaN |
| `benchmark_volatility_{n}d` | 20 | Sample std of benchmark daily simple returns times sqrt(annualization) | Benchmark close | First n benchmark bars NaN; unmatched date => NaN |

Only exact-date joins are allowed: no forward-fill, backward-fill, nearest-date,
or as-of substitution. An absent benchmark endpoint invalidates that relative
return even if other nearby observations exist. An absent interior benchmark bar
does not invalidate a close-to-close return when both endpoints exist. The two
endpoints still describe the same stock/benchmark holding interval.

With mismatched calendars, `relative_return_20d` need not equal `return_20d`
minus `benchmark_return_20d`: the relative feature uses the stock's two endpoints,
whereas market context uses the benchmark's own 20-bar horizon. This avoids
comparing different intervals by accident. Missing stock rows never compress the
benchmark history used for context. Context can be available at stock inception
if earlier benchmark data was supplied; relative returns still need stock history.

All benchmark features obey the after-close convention. Matching session dates
assumes both bars are available at calculation time, as for the initial US equity
universe/SPY. Cross-market close times require additional availability metadata;
session-date equality alone does not establish simultaneous publication.

## API

`compute_returns`, `compute_price_location_features`, `compute_price_zscores`,
`compute_rsi`, `compute_atr`, `compute_volatility`, `compute_volume_features`, and
`compute_relative_features`
return `timestamp`, `ticker`, and their feature family. Each accepts cleaned
single- or multi-ticker data and configurable windows. `build_features` appends
the feature families to a copy of all input columns, retaining source provenance.
`compute_relative_features(data, benchmark, windows=(5, 10, 20), context_window=20)`
adds relative returns and all three context measurements. The builder enables
these only when `benchmark=` is supplied. Output rows remain in
`(timestamp, ticker)` order with a fresh RangeIndex. Existing
columns that collide with generated features raise instead of being overwritten.

Calculations split by ticker before any shift or rolling operation. The builder
validates/group-splits once and concatenates once. pandas handles labelled
trailing calculations and the compiled Wilder recurrence; NumPy handles
vectorized True Range and safe arithmetic. Iteration is over tickers and window
configurations, not individual rows. Polars is not needed for this in-memory daily
workload. No new dependency is required or performance benchmark claimed.

`build_features` records normalized configuration in `attrs["feature_parameters"]`.
Benchmark-enabled outputs also record benchmark identity and source provenance
in `attrs["feature_benchmark"]`. Preserve source snapshots, configuration, and
code commit for research reproducibility. No derived-data persistence layer is
introduced here; do not pass feature frames to the raw market snapshot writer,
which intentionally persists only OHLCV columns.

```python
from src.data import get_histories
from src.features import build_features

prices = get_histories(("AAPL", "SPY"))
spy = prices.loc[prices["ticker"].eq("SPY")]
measured = build_features(prices, benchmark=spy)
# Optional additional window; no parameter selection or optimization is performed.
with_longer_zscore = build_features(prices, benchmark=spy, zscore_windows=(20, 60))
```

Default builder configuration produces 20 feature columns (27 with OHLCV), or
26 feature columns (33 with OHLCV) when a benchmark is supplied. High/low distance
windows are configured together with drawdown via `location_windows`; the shared
high-distance/drawdown calculation is not repeated. The three benchmark context
columns share `context_window`. Other options are `return_windows`,
`zscore_windows`, `rsi_window`, `atr_window`, `volatility_windows`, `volume_windows`,
`annualization`, and `relative_windows`.

## Numerical policy, verification, and limitations

Full-window warm-up NaNs and mathematically undefined zero-denominator results
are preserved. Invalid OHLCV, duplicate observations/columns, bad configuration,
nonfinite inputs, and detected numerical overflow raise. No clipping is applied
to force feature values into expected ranges. Raw NaNs are rejected by the data
contract; generated NaNs carry warm-up/alignment/undefined-division meaning.

Deterministic tests use small synthetic data with hand-computable outputs. They
check exact seeds and Wilder updates, all feature families, constant series,
zero volume, multi-ticker isolation, unmatched benchmark dates, and warm-up/range
invariants. Four prefix tests cover unbenchmarked features. Sixteen further
cases cover eight cutoffs and default/custom windows, comparing every historical
column both after adding future rows and after changing future stock/benchmark
OHLCV. Prefixes must match exactly, including NaN positions.

```powershell
python -m pytest -q -W error --tb=short
```

The completed milestone passes 175 tests: 81 existing data tests and 94 feature
tests. An offline smoke check of the existing AAPL/SPY snapshots produced 5,024
rows and 33 columns, expected warm-up counts for both tickers, and no infinities.
Recent rows were inspected only for structural/numerical sanity, not signal value.

Limitations: observed-bar windows do not audit missing trading sessions. A return
across an omitted session is treated as one observed interval in volatility;
252-session annualization is a convention. Wilder values depend on the supplied
history's starting point, so truncating its beginning can change later values.
Current adjusted inputs and survivor-selected universes retain their existing
research limitations. These measurements are not future-return labels, rebound
probabilities, calibrated predictors, or evidence of an investable edge.
