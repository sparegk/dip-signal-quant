# dip-signal-quant

Quantitative research into short-term equity dips and mean-reversion opportunities.
The central question is whether statistically unusual dips and historical bounce
zones predict repeatable rebounds after realistic costs and out-of-sample testing.

This is a research/backtesting project, not investment advice. No strategy or
profitability claim has been validated.

## Planned pipeline

```text
Historical market data
        ↓
Quantitative feature engine
        ↓
Dip detection
        ↓
Support-memory analysis
        ↓
DipScore / rebound probability
        ↓
Risk + exit model
        ↓
Backtesting / walk-forward validation
        ↓
Signal archive
        ↓
Live paper scanner
        ↓
Dashboard / alerts
```

## Current status

Research foundation, validated daily OHLCV ingestion, Parquet caching, a trailing
quantitative feature engine, and DipSignal V1 candidates are deterministically tested.
The initial test universe is AAPL, MSFT, NVDA, AMZN, GOOGL, and SPY (market
benchmark). V1 flags unusual observations, not buy instructions. Scoring, support,
outcome evaluation, and backtesting remain future milestones.

Core stack: Python, NumPy, pandas, PyArrow/Parquet, yfinance, and pytest. Polars
will be used where processing scale justifies it; later research may use VectorBT,
Numba, scikit-learn/XGBoost, and DuckDB when needed.

## Project layout

- `src/`: data infrastructure and future research modules.
- `tests/`: deterministic tests, with network calls mocked.
- `data/`: generated local datasets, excluded from Git.
- `notebooks/`: exploratory research; `results/`: research artifacts.
- [Roadmap](ROADMAP.md), [research log](docs/RESEARCH_LOG.md),
  [decisions](docs/DECISIONS.md), and [experiments](docs/EXPERIMENTS.md).
- [AGENTS.md](AGENTS.md): persistent project instructions.

## Getting started

The checked-in dependency snapshot comes from the existing Windows/Python 3.14
environment and includes platform-specific packages. It is not yet a portable lockfile.
No unrelated dependency versions were changed for the data layer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q -W error
```

```python
from src.data import get_history, get_histories

aapl = get_history("AAPL")       # Download ten years on first use; otherwise offline cache.
universe = get_histories()        # AAPL, MSFT, NVDA, AMZN, GOOGL, SPY.
updated = get_history("AAPL", refresh=True)
```

Generated files live in `data/market/` and are excluded from Git. Prices are adjusted;
missing required values raise and are never filled. Existing caches do not refresh
automatically. See [the market-data API and limitations](docs/MARKET_DATA.md) for
date ranges, provenance, storage behavior, and the optional live smoke check.

```python
from src.features import build_features

spy = universe.loc[universe["ticker"].eq("SPY")]
measurements = build_features(universe, benchmark=spy)
```

The [feature guide](docs/FEATURES.md) documents returns, price location, RSI/ATR,
volatility, volume, and benchmark-relative measurements. Features use data through
the current close, retain warm-up NaNs, and contain no trading thresholds. Any
later execution must respect their after-close availability.

```python
from src.signals import build_signals

# SPY supplies market context; classify the non-benchmark stocks here.
candidates = build_signals(measurements.loc[measurements["ticker"].ne("SPY")])
events = candidates.loc[candidates["dip_event_v1"]]
```

[DipSignal V1](docs/SIGNALS.md) uses prior-only ticker-relative percentiles across
four features, requiring complete measurements/history and at least three active
components by default. It exposes condition-days separately from entry events.
The candidate hypothesis has not been validated as a profitable strategy.
