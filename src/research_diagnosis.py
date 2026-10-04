"""Exploratory diagnostics of frozen events; no policy selection or filtering."""

import numpy as np
import pandas as pd

from src.signals import COMPONENT_COLUMNS


def rebound_paths(observations: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Measure future paths separately from signal-time covariates, within folds."""
    rows = []
    bars = config["path_bars"]
    for (ticker, fold), g in observations.groupby(["ticker", "fold"], sort=True):
        g = g.sort_values("timestamp").reset_index(drop=True)
        for i in np.flatnonzero(g.dip_event_v1.to_numpy(bool)):
            if i + bars >= len(g):
                continue
            path = g.iloc[i + 1:i + 1 + bars]
            entry = float(path.iloc[0].open)
            highs = path.high.to_numpy(float) / entry - 1
            closes = path.close.to_numpy(float) / entry - 1
            row = {"ticker": ticker, "fold": str(fold), "timestamp": g.iloc[i].timestamp,
                   "maturity": path.iloc[-1].timestamp, "signal_low": float(g.iloc[i].low),
                   "entry_gap": entry / float(g.iloc[i].close) - 1,
                   "time_to_mfe": int(highs.argmax()) + 1 if highs.max()>0 else np.nan,
                   "full_mfe": max(0., float(highs.max())),
                   "full_mae": min(0., float((path.low.to_numpy(float) / entry - 1).min()))}
            for name, values, level in [("positive_close", closes, 0.)] + [
                (f"reach_{int(level*100)}pct", highs, level) for level in config["rebound_levels"]]:
                hit = np.flatnonzero(values > level if level == 0 else values >= level)
                row[name] = int(hit[0]) + 1 if len(hit) else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def support_context(observations: pd.DataFrame, paths: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Only mature prior recoveries may describe a current event's price zone."""
    rules = config["support"]
    rows = []
    for ticker, g in observations.loc[observations.dip_event_v1].groupby("ticker", sort=True):
        prior = paths.loc[paths.ticker.eq(ticker)]
        for row in g.sort_values("timestamp").itertuples():
            age = (row.timestamp - prior.timestamp).dt.days
            eligible = prior.loc[(prior.maturity < row.timestamp) & age.between(1, rules["maximum_age_calendar_days"])
                                 & prior.full_mfe.ge(rules["prior_recovery"])]
            nearby = eligible.loc[(row.close / eligible.signal_low - 1).abs().le(rules["zone_distance"])]
            rows.append({"ticker": ticker, "timestamp": row.timestamp,
                         "prior_successful_visits": len(nearby),
                         "support_group": "revisit" if len(nearby) else "no_known_successful_zone",
                         "days_since_visit": (row.timestamp-nearby.timestamp.max()).days if len(nearby) else np.nan})
    return pd.DataFrame(rows)


def describe(g: pd.DataFrame) -> dict:
    complete = g.loc[g.status.eq("completed")]
    r = complete.forward_return
    paired = complete.excess_return.dropna()
    return {"events": len(g), "completed": len(complete), "mean": r.mean(), "median": r.median(),
            "win_rate": r.gt(0).mean() if len(r) else np.nan,
            "mfe": complete.mfe.mean(), "mae": complete.mae.mean(),
            "matched_spy": complete.benchmark_return.mean(), "excess": paired.mean(), "paired_count": len(paired)}


def diagnose(observations: pd.DataFrame, events: pd.DataFrame, config: dict) -> dict[str, pd.DataFrame]:
    """All diagnostic groups retain their losses; no subgroup becomes a rule."""
    obs = observations.sort_values(["ticker", "timestamp"]).copy()
    obs["drawdown_change_5"] = obs.groupby("ticker").drawdown_60d.diff(5)
    obs["combination"] = obs.apply(lambda r: "".join(letter for letter, key in zip("ABCD", COMPONENT_COLUMNS) if r[key]), axis=1)
    paths = rebound_paths(obs, config)
    support = support_context(obs, paths, config)
    covariates = obs.drop(columns=["fold", "regime", "dip_component_count", "dip_event_v1", "dip_condition_v1"])
    joined = events.merge(covariates, on=["ticker", "timestamp"], how="left", validate="many_to_one")
    joined = joined.merge(paths[["ticker", "timestamp", "entry_gap"]], on=["ticker", "timestamp"], how="left", validate="many_to_one")
    joined = joined.merge(support, on=["ticker", "timestamp"], how="left", validate="many_to_one")
    rows = []
    for horizon, g in joined.groupby("horizon", sort=True):
        rows.append({"analysis": "all_events", "group": "all", "horizon": horizon, **describe(g)})
        for key in ["combination", "dip_component_count", "regime", "support_group"]:
            for value, subgroup in g.groupby(key, dropna=False, sort=True):
                rows.append({"analysis": key, "group": str(value), "horizon": horizon, **describe(subgroup)})
        for letter, key in zip("ABCD", COMPONENT_COLUMNS):
            for active in (True, False):
                rows.append({"analysis": "component_presence", "group": f"{letter} {'active' if active else 'inactive'}",
                             "horizon": horizon, **describe(g.loc[g[key].eq(active)])})
        for key, edges in config["groups"].items():
            labels = pd.cut(g[key], [-np.inf, *edges, np.inf], labels=["low", "middle", "high"])
            labels = labels.astype(object).where(g[key].notna(), "unknown")
            for value in ("low", "middle", "high", "unknown"):
                rows.append({"analysis": key, "group": value, "horizon": horizon, **describe(g.loc[labels.eq(value)])})
    timing = []
    for metric in ["positive_close", "time_to_mfe", "reach_2pct", "reach_5pct", "reach_10pct"]:
        for group, p in [("all", paths), *list(paths.groupby("fold", sort=True))]:
            measured = p[metric].dropna()
            timing.append({"group": str(group), "metric": metric, "complete_paths": len(p),
                           "reached": len(measured), "fraction": len(measured)/len(p) if len(p) else np.nan,
                           "median_bars_if_reached": measured.median(), "mean_bars_if_reached": measured.mean()})
    ticker = []
    for name, g in joined.loc[joined.horizon.eq(10)].groupby("ticker", sort=True):
        signal = obs.loc[obs.ticker.eq(name) & obs.dip_event_v1]
        ready = obs.loc[obs.ticker.eq(name) & obs.dip_ready_v1]
        ticker.append({"ticker": name, **describe(g), "events_per_252": len(signal)/len(ready)*252 if len(ready) else np.nan,
                       **{key: signal[key].mean() for key in ("atr_pct_14", "relative_volume_20d", "relative_return_10d", "volatility_20d")}})
    tickers = pd.DataFrame(ticker)
    correlations = []
    for key in ("atr_pct_14", "relative_volume_20d", "relative_return_10d", "volatility_20d", "events_per_252"):
        for outcome in ("mean", "excess"):
            pair = tickers[[key, outcome]].dropna()
            correlations.append({"feature": key, "outcome": outcome, "tickers": len(pair),
                                 "spearman": pair[key].corr(pair[outcome], method="spearman") if len(pair)>2 else np.nan})
    outcomes = []
    ten = joined.loc[joined.horizon.eq(10) & joined.status.eq("completed")]
    for name, cohort in [("positive_gross", ten.loc[ten.forward_return.gt(0)]),
                         ("nonpositive_gross", ten.loc[ten.forward_return.le(0)])]:
        outcomes.append({"group": name, "completed": len(cohort),
                         **{key: cohort[key].mean() for key in ("return_5d", "drawdown_change_5", "atr_pct_14",
                                                                "relative_volume_20d", "relative_return_10d", "entry_gap")}})
    return {"groups": pd.DataFrame(rows), "timing": pd.DataFrame(timing), "tickers": tickers,
            "outcome_covariates": pd.DataFrame(outcomes),
            "correlations": pd.DataFrame(correlations), "support_context": support, "paths": paths}
