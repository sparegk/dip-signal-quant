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

Research foundation established; historical daily data ingestion is the first
implementation milestone. The initial test universe is AAPL, MSFT, NVDA, AMZN,
GOOGL, and SPY (planned market benchmark). Strategy modules remain placeholders.

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
