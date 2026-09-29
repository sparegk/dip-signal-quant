# Project instructions

## Project purpose

dip-signal-quant researches short-term equity dips and mean-reversion opportunities.
This is a research-first project, not a generic trading bot. Strategies must be
empirically tested; arbitrary trading rules are hypotheses, not established edges.

## Quantitative methodology

- Never introduce look-ahead bias or use information unavailable at signal time.
- Avoid survivorship bias where possible; document universe and data limitations.
- Keep research, validation, and true out-of-sample periods separate. Never optimize
  directly on the final test period. Use walk-forward testing in later validation.
- Include realistic transaction costs and slippage in backtests.
- Compare against simple baselines and prefer robust parameter regions over
  highly specific, overfit parameters.
- Record failed experiments as well as successful ones.
- Never present backtest performance as proof of future profitability.
- Today's adjusted prices may include later corporate actions and revisions.
  Do not describe them as point-in-time data or assume daily bars were available
  before their session closed.

## Engineering principles

- Prefer simple, testable, modular code; do not over-engineer.
- Use type hints and concise docstrings. Avoid unnecessary classes and global
  mutable state.
- Preserve useful existing work and do not modify unrelated files.
- Make tests deterministic where practical; mock network calls in unit tests.
- Never forward-fill missing stock prices or fabricate weekend/holiday bars.
- Validate data at ingestion and storage boundaries; make failures explicit.
- Keep generated historical market files out of Git.

## Preferred quant/data stack

- NumPy for numerical and vectorized computation.
- pandas for ecosystem compatibility, especially yfinance and later VectorBT.
- Polars when it offers a genuine performance or data-processing advantage;
  avoid pointless pandas/Polars conversions.
- PyArrow/Parquet for columnar storage.
- VectorBT later for fast research/backtesting; Numba later for custom numerical
  kernels when the benefit is material.
- scikit-learn / XGBoost later for statistical or ML ranking.
- DuckDB may be introduced for larger research and signal archives.
- Every dependency needs a reason; never add technology merely for resume value.

## Git workflow

- Work in meaningful logical milestones, then run relevant tests/checks.
- Commit only when the milestone works, using concise descriptive messages.
- Push completed milestone commits when the task authorizes Git work.
- Do not create artificial micro-commits or contribution-farming commits.
  Contribution history should represent real functionality or research progress.

## Documentation and scope

- Document important research decisions in `docs/DECISIONS.md`.
- Record significant experiments in `docs/EXPERIMENTS.md`, including poor results.
- Update `ROADMAP.md` when milestones are actually complete and maintain the
  chronological `docs/RESEARCH_LOG.md`.
- The foundation task covers documentation, historical daily market data, and
  deterministic tests only. Leave features, signals, scoring, support, backtests,
  exits, ML, trading, live alerts, and UI/API work for explicitly requested tasks.
