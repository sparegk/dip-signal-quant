"""Descriptive cross-sectional diagnostics; no allocation or parameter selection."""

from collections.abc import Iterable

import numpy as np
import pandas as pd

from src.metrics import summarize_outcomes, trade_metrics
from src.universe import static_universe


def frequency_summary(observations: pd.DataFrame) -> pd.DataFrame:
    """Per observed ticker-year counts, including zero events and partial exposure."""
    rows = []
    for (fold, ticker), group in observations.groupby(["fold", "ticker"], sort=True):
        member = group.member
        ready = member & group.dip_ready_v1
        conditions = ready & group.dip_condition_v1
        events = ready & group.dip_event_v1
        rows.append({"fold": fold, "ticker": ticker, "first_date": group.timestamp.min(),
                     "last_date": group.timestamp.max(), "observed": len(group),
                     "eligible": int(member.sum()), "ready": int(ready.sum()),
                     "conditions": int(conditions.sum()), "events": int(events.sum()),
                     "condition_fraction_ready": conditions.sum() / ready.sum() if ready.any() else np.nan,
                     "condition_fraction_eligible": conditions.sum() / member.sum() if member.any() else np.nan,
                     "events_per_252_ready": 252 * events.sum() / ready.sum() if ready.any() else np.nan})
    return pd.DataFrame(rows)


def distribution(values: Iterable[float], *, requested_count: int | None = None) -> dict:
    """Equal-ticker sign counts and spread; undefined tickers are not silently lost."""
    raw = pd.Series(values, dtype=float)
    if np.isinf(raw.to_numpy()).any():
        raise ValueError("Infinite ticker statistics")
    total = len(raw) if requested_count is None else requested_count
    if total < len(raw):
        raise ValueError("Requested count cannot be smaller than observed values")
    valid = raw.dropna()
    return {"requested_count": total, "defined_count": len(valid), "undefined_count": total - len(valid),
            "positive_count": int(valid.gt(0).sum()), "negative_count": int(valid.lt(0).sum()),
            "zero_count": int(valid.eq(0).sum()),
            "positive_fraction_defined": valid.gt(0).mean(), "equal_ticker_mean": valid.mean(),
            "median": valid.median() if len(valid) else np.nan,
            "q25": valid.quantile(.25), "q75": valid.quantile(.75),
            "iqr": valid.quantile(.75) - valid.quantile(.25),
            "minimum": valid.min(), "maximum": valid.max()}


def concentration(ledger: pd.DataFrame, value_column: str, tickers: Iterable[str]) -> tuple[pd.DataFrame, dict]:
    """Equal-notional sums, with stable positive/absolute denominators, never portfolio P&L."""
    symbols = static_universe(tickers)
    if not {"ticker", value_column}.issubset(ledger) or not ledger.ticker.isin(symbols).all():
        raise ValueError("Contributions require known tickers and a return column")
    values = pd.to_numeric(ledger[value_column], errors="raise")
    if np.isinf(values.to_numpy(dtype=float)).any():
        raise ValueError("Infinite contribution")
    valid = ledger.loc[values.notna(), ["ticker", value_column]].copy()
    sums = valid.groupby("ticker")[value_column].sum().reindex(symbols, fill_value=0.)
    counts = valid.groupby("ticker").size().reindex(symbols, fill_value=0)
    positive, negative, absolute = sums.clip(lower=0).sum(), sums.clip(upper=0).sum(), sums.abs().sum()
    table = pd.DataFrame({"ticker": symbols, "count": counts.to_numpy(), "return_sum": sums.to_numpy()})
    table["mean"] = table.return_sum.div(table["count"].replace(0, np.nan))
    table["positive_share"] = table.return_sum.clip(lower=0) / positive if positive else np.nan
    table["absolute_share"] = table.return_sum.abs() / absolute if absolute else np.nan
    ordered = table.sort_values(["return_sum", "ticker"], ascending=[False, True])
    top = ordered.loc[ordered.return_sum > 0].head(5)
    return table, {"total_sum": float(sums.sum()), "positive_sum": float(positive),
                   "negative_sum": float(negative), "absolute_sum": float(absolute),
                   "top5_positive_tickers": top.ticker.tolist(),
                   "top5_positive_share": float(top.return_sum.sum() / positive) if positive else np.nan,
                   "top5_absolute_share": float(sums.abs().nlargest(5).sum() / absolute) if absolute else np.nan,
                   "units": "sum_of_equal_notional_return_fractions_not_portfolio_return"}


def _trade_groups(trades: pd.DataFrame, groups: tuple[str, ...]) -> pd.DataFrame:
    rows = []
    for key, group in trades.groupby(list(groups), sort=True):
        key = key if isinstance(key, tuple) else (key,)
        row = dict(zip(groups, key)) | trade_metrics(group)
        for status in ("overlap", "no_next_bar", "incomplete_window", "split_boundary"):
            row[status] = int(group.status.eq(status).sum())
        row["ambiguous_exits"] = int(group.ambiguous_bar.sum())
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_robustness(tables: dict[str, pd.DataFrame], tickers: Iterable[str],
                         *, uncertainty: dict | None = None) -> tuple[dict[str, pd.DataFrame], dict]:
    """All predeclared fold/pooled/ticker/regime/component summaries without ranking selection."""
    symbols = static_universe(tickers)
    kwargs = uncertainty or {"block_size": 20, "n_bootstrap": 2000, "seed": 42}
    forward_tables = []
    for selection in ("events", "eligible", "non_signal"):
        data = tables[selection].copy()
        data["selection"] = selection
        forward_tables.append(data)
    forward = pd.concat(forward_tables, ignore_index=True)
    output = {}
    for name, group in {
        "fold_summary": ("selection", "fold", "horizon"),
        "oos_summary": ("selection", "horizon"),
        "ticker_summary": ("selection", "ticker", "horizon"),
        "regime_summary": ("selection", "regime", "horizon"),
        "fold_regime_summary": ("selection", "fold", "regime", "horizon"),
    }.items():
        output[name] = summarize_outcomes(forward, group_by=group, **kwargs)
    output["component_summary"] = summarize_outcomes(
        tables["events"].loc[tables["events"].horizon == 10],
        group_by=("fold", "dip_component_count", "horizon"), **kwargs)
    output["component_oos_summary"] = summarize_outcomes(
        tables["events"].loc[tables["events"].horizon == 10],
        group_by=("dip_component_count", "horizon"), **kwargs)
    trades = tables["trades"]
    for name, group in {
        "trade_fold_summary": ("mode", "fold"), "trade_oos_summary": ("mode",),
        "trade_ticker_summary": ("mode", "ticker"), "trade_regime_summary": ("mode", "regime"),
        "trade_fold_regime_summary": ("mode", "fold", "regime"),
    }.items():
        output[name] = _trade_groups(trades, group)
    frequency = frequency_summary(tables["observations"])
    output["frequency"] = frequency
    output["frequency_fold"] = frequency.groupby("fold", as_index=False)[
        ["observed", "eligible", "ready", "conditions", "events"]].sum()
    for denominator in ("ready", "eligible"):
        output["frequency_fold"]["condition_fraction_" + denominator] = (
            output["frequency_fold"].conditions / output["frequency_fold"][denominator].replace(0, np.nan))
    output["frequency_fold"]["events_per_252_ready"] = (
        252 * output["frequency_fold"].events / output["frequency_fold"].ready.replace(0, np.nan))
    diagnostics = []
    ticker_summary = output["ticker_summary"]
    if len(ticker_summary):
        for horizon, group in ticker_summary.loc[ticker_summary.selection == "events"].groupby("horizon"):
            for metric in ("mean", "mean_excess_return"):
                diagnostics.append({"kind": "event", "horizon": horizon, "metric": metric,
                                    **distribution(group[metric], requested_count=len(symbols))})
    ticker_trades = output["trade_ticker_summary"]
    if len(ticker_trades):
        group = ticker_trades.loc[ticker_trades["mode"] == "non_overlapping"]
        diagnostics.append({"kind": "trade", "horizon": 10, "metric": "net_expectancy",
                            **distribution(group.average_return, requested_count=len(symbols))})
    totals = frequency.groupby("ticker").events.sum().reindex(symbols, fill_value=0)
    diagnostics.append({"kind": "frequency", "horizon": 0, "metric": "total_events",
                        **distribution(totals)})
    output["distribution"] = pd.DataFrame(diagnostics)
    concentration_report = {}
    sources = {
        "net_trades": (trades.loc[(trades["mode"] == "non_overlapping") & (trades.status == "completed")], "net_return"),
        "event_excess_10": (tables["events"].loc[(tables["events"].horizon == 10)
                                                & (tables["events"].status == "completed")], "excess_return"),
    }
    for name, (ledger, value) in sources.items():
        output["contribution_" + name], concentration_report[name] = concentration(ledger, value, symbols)
    return output, concentration_report
