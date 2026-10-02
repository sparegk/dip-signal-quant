"""Registered same-entry exit research; all fills come from src.backtest."""

from collections.abc import Callable
import json

import numpy as np
import pandas as pd

from src.backtest import simulate_barrier_trades
from src.metrics import sequential_return_metrics, summarize_returns, trade_metrics
from src.walkforward import validate_folds


OUTCOMES = ("entry_timestamp", "entry_price", "entry_fill_price", "exit_timestamp",
            "exit_price", "exit_fill_price", "exit_reason", "fill_type", "holding_bars",
            "gross_return", "net_return", "mfe", "mae", "excursion_scope")


def candidate_catalog(config: dict) -> list[dict]:
    """Validate the explicit catalogue against its registered enumeration axes."""
    fixed = [dict(id=f"fixed_s{s:02d}_t{t:02d}", family="fixed", stop=s / 100, target=t / 100)
             for s, t in config["fixed_pairs_percent"]]
    atr = [dict(id=f"atr_s{s:g}_t{t:g}", family="atr", stop_multiplier=s, target_multiplier=t)
           for s in config["stop_multipliers"] for t in config["target_multipliers"]]
    r = [dict(id=f"r_s{s:g}_r{r:g}", family="r_multiple", stop_multiplier=s, reward_risk=r)
         for s in config["stop_multipliers"] for r in config["reward_risk_ratios"]]
    controls = [dict(id="v1_control", family="control", stop=.07, target=.10),
                dict(id="target_only", family="control", stop=None, target=.10),
                dict(id="stop_only", family="control", stop=.07, target=None),
                dict(id="time_only", family="control", stop=None, target=None)]
    expected = fixed + atr + r + controls
    if (config["candidates"] != expected or len(expected) != config["candidate_count"]
            or len({c["id"] for c in expected}) != len(expected)):
        raise ValueError("Candidate catalogue disagrees with registered grid")
    bounds = config["bounds"]
    if not (0 < bounds["stop_min"] <= bounds["stop_max"] < 1
            and 0 < bounds["target_min"] <= bounds["target_max"]):
        raise ValueError("Invalid safety bounds")
    return [dict(c) for c in expected]


def candidate_fractions(signals: pd.DataFrame, candidate: dict, config: dict) -> pd.DataFrame:
    """Freeze each fraction from the signal row, never the entry/future ATR."""
    rates = signals[["timestamp", "ticker"]].copy()
    family = candidate["family"]
    if family in ("fixed", "control"):
        rates["stop_fraction"] = candidate["stop"]
        rates["target_fraction"] = candidate["target"]
        return rates
    atr = signals[config["atr_feature"]]
    if (not pd.api.types.is_numeric_dtype(atr) or pd.api.types.is_bool_dtype(atr)
            or pd.api.types.is_complex_dtype(atr)):
        raise ValueError("Signal ATR fraction must be real numeric")
    event_atr = atr.loc[signals.dip_event_v1]
    if not np.isfinite(event_atr).all() or (event_atr < 0).any():
        raise ValueError("Missing/invalid ATR at a V1 event")
    bounds = config["bounds"]
    rates["stop_fraction"] = (atr * candidate["stop_multiplier"]).clip(
        bounds["stop_min"], bounds["stop_max"])
    target = (atr * candidate["target_multiplier"] if family == "atr" else
              rates.stop_fraction * candidate["reward_risk"])
    rates["target_fraction"] = target.clip(bounds["target_min"], bounds["target_max"])
    return rates


def simulate_candidate(signals: pd.DataFrame, candidate: dict, config: dict) -> pd.DataFrame:
    """Apply candidate fractions using the sole gap/cost/ambiguity engine."""
    rates = candidate_fractions(signals, candidate, config)
    params = {key: config[key] for key in ("max_holding_bars", "commission_rate",
                                          "slippage_rate", "ambiguity_policy")}
    if candidate["family"] in ("fixed", "control"):
        trades = simulate_barrier_trades(signals, stop_loss=candidate["stop"],
                                         take_profit=candidate["target"], **params)
        trades["stop_fraction"] = candidate["stop"]
        trades["target_fraction"] = candidate["target"]
    else:
        base = signals.copy()
        base["exit_stop_fraction"] = rates.stop_fraction
        base["exit_target_fraction"] = rates.target_fraction
        trades = simulate_barrier_trades(base, stop_loss=None, take_profit=None,
            stop_loss_column="exit_stop_fraction", take_profit_column="exit_target_fraction", **params)
    trades["candidate_id"] = candidate["id"]
    trades["family"] = candidate["family"]
    trades.attrs = {}
    return trades


def event_context(signals: pd.DataFrame, holding: int = 10) -> pd.DataFrame:
    """Separate full-window/post-exit outcomes; not inputs to candidate selection."""
    rows = []
    for ticker, group in signals.groupby("ticker", sort=False, observed=True):
        group = group.reset_index(drop=True)
        times = group.timestamp.to_numpy()
        prices = group[["open", "high", "low"]].to_numpy(dtype=float)
        for i in np.flatnonzero(group.dip_event_v1.to_numpy()):
            row = dict(timestamp=times[i], ticker=ticker,
                       next_timestamp=times[i + 1] if i + 1 < len(group) else pd.NaT,
                       window_end_timestamp=times[i + holding] if i + holding < len(group) else pd.NaT,
                       full_window_mfe=np.nan, full_window_mae=np.nan)
            if i + holding < len(group):
                path = prices[i + 1:i + holding + 1]
                entry = path[0, 0]
                row.update(full_window_mfe=max(0.0, path[:, 1].max() / entry - 1),
                           full_window_mae=min(0.0, path[:, 2].min() / entry - 1))
                for h in range(1, holding):
                    row[f"post_mfe_{h}"] = path[h:, 1].max() / entry - 1
            rows.append(row)
    columns = ["timestamp", "ticker", "next_timestamp", "window_end_timestamp",
               "full_window_mfe", "full_window_mae"] + [f"post_mfe_{h}" for h in range(1, holding)]
    result = pd.DataFrame(rows, columns=columns)
    for name in ("timestamp", "next_timestamp", "window_end_timestamp"):
        result[name] = pd.to_datetime(result[name]).astype("datetime64[ns]")
    return result.sort_values(["timestamp", "ticker"]).reset_index(drop=True)


def _clear_outcomes(frame: pd.DataFrame, mask: pd.Series) -> None:
    for column in OUTCOMES:
        frame.loc[mask, column] = (pd.NaT if column.endswith("timestamp") else
                                  None if column in ("exit_reason", "fill_type", "excursion_scope") else np.nan)
    frame.loc[mask, "ambiguous_bar"] = False


def boundary_view(ledger: pd.DataFrame, context: pd.DataFrame,
                  start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Gate maturity BEFORE statistics; identical to truncated independent evaluation."""
    result = ledger.loc[ledger.timestamp.between(start, end)].copy()
    timing = context[["timestamp", "ticker", "next_timestamp", "window_end_timestamp"]]
    result = result.merge(timing, on=["timestamp", "ticker"], validate="one_to_one")
    no_next = result.next_timestamp.isna() | result.next_timestamp.gt(end)
    incomplete = result.window_end_timestamp.isna() | result.window_end_timestamp.gt(end)
    result.loc[incomplete, "status"] = "incomplete_window"
    result.loc[no_next, "status"] = "no_next_bar"
    _clear_outcomes(result, result.status.ne("completed"))
    return result.sort_values(["timestamp", "ticker"]).reset_index(drop=True)


def non_overlap_view(ledger: pd.DataFrame) -> pd.DataFrame:
    """Thin an executed ledger with the engine's same-ticker no-recycling rule."""
    result = ledger.copy()
    last_exit = {}
    excluded = []
    for row in result.itertuples():
        previous = last_exit.get(row.ticker)
        if previous is not None and pd.notna(row.next_timestamp) and row.next_timestamp <= previous:
            excluded.append(row.Index)
        elif row.status == "completed":
            last_exit[row.ticker] = row.exit_timestamp
    mask = result.index.isin(excluded)
    result.loc[mask, "status"] = "overlap"
    _clear_outcomes(result, mask)
    return result


def policy_metrics(ledger: pd.DataFrame) -> dict:
    """EV/R/downside summaries; no artificial pooled capital return or drawdown."""
    result = trade_metrics(ledger)
    completed = ledger.loc[ledger.status.eq("completed")]
    for reason in ("take_profit", "stop_loss", "time_exit"):
        result[reason + "_count"] = int(completed.exit_reason.eq(reason).sum())
    risk = pd.to_numeric(completed.stop_fraction, errors="raise")
    r = completed.net_return / risk.where(risk.gt(0))
    valid = r.dropna()
    result.update(r_count=len(valid), expectancy_r=valid.mean(), average_r=valid.mean(),
                  median_r=valid.median(), average_winning_r=valid[valid > 0].mean(),
                  average_losing_r=valid[valid < 0].mean(),
                  r_win_rate=(valid > 0).mean() if len(valid) else np.nan,
                  fifth_percentile_net=completed.net_return.quantile(.05))
    sequential = non_overlap_view(ledger)
    drawdowns = [sequential_return_metrics(group.net_return)["maximum_drawdown"]
                 for _, group in sequential.loc[sequential.status.eq("completed")].groupby("ticker", observed=True)]
    result.update(worst_ticker_trade_close_drawdown=min(drawdowns) if drawdowns else np.nan,
                  median_ticker_trade_close_drawdown=np.median(drawdowns) if drawdowns else np.nan)
    return result


def select_training_candidate(surface: pd.DataFrame, minimum: int,
                              family: str | None = None) -> str:
    """Select on training metrics only; callers never supply OOS summaries."""
    eligible = surface.loc[surface.family.ne("control") & surface.trade_count.ge(minimum)
                           & surface.expected_value.notna()]
    if family is not None:
        eligible = eligible.loc[eligible.family.eq(family)]
    if eligible.empty:
        return "v1_control"
    return str(eligible.sort_values(["expected_value", "candidate_id"], ascending=[False, True]).iloc[0].candidate_id)


def ev_win_frontier(surface: pd.DataFrame) -> np.ndarray:
    ev = surface.expected_value.to_numpy(dtype=float)
    win = surface.win_rate.to_numpy(dtype=float)
    dominated = ((ev[:, None] >= ev[None, :]) & (win[:, None] >= win[None, :])
                 & ((ev[:, None] > ev[None, :]) | (win[:, None] > win[None, :]))).any(axis=0)
    return ~dominated & np.isfinite(ev) & np.isfinite(win)


def plateau_summary(surface: pd.DataFrame, candidates: list[dict], tolerance: float) -> list[dict]:
    rows = []
    for family in ("fixed", "atr", "r_multiple"):
        group = surface.loc[surface.family.eq(family)].sort_values(
            ["expected_value", "candidate_id"], ascending=[False, True])
        if group.empty or group.expected_value.isna().all():
            continue
        winner = group.iloc[0]
        near = set(group.loc[group.expected_value.ge(winner.expected_value - tolerance), "candidate_id"])
        keys = ("stop", "target") if family == "fixed" else ("stop_multiplier", "target_multiplier" if family == "atr" else "reward_risk")
        configs = [c for c in candidates if c["family"] == family]
        axes = [sorted({c[key] for c in configs}) for key in keys]
        coordinates = {c["id"]: tuple(axis.index(c[key]) for axis, key in zip(axes, keys)) for c in configs}
        xy = coordinates[winner.candidate_id]
        adjacent = sum(sum(abs(a - b) for a, b in zip(xy, coordinates[name])) == 1 for name in near)
        rows.append(dict(family=family, winner=winner.candidate_id, near_best_count=len(near),
                         adjacent_near_best_count=adjacent, plateau_flag=len(near) >= 3 and adjacent >= 2))
    return rows


def add_exit_diagnostics(ledger: pd.DataFrame, context: pd.DataFrame, holding: int) -> pd.DataFrame:
    """Future excursion diagnostics are attached only AFTER policy selection."""
    diagnostic = context.drop(columns=["next_timestamp", "window_end_timestamp"])
    result = ledger.merge(diagnostic, on=["timestamp", "ticker"], validate="one_to_one")
    complete = result.status.eq("completed")
    for column in diagnostic.columns.difference(["timestamp", "ticker"]):
        result.loc[~complete, column] = np.nan
    denominator = result.full_window_mfe.where(result.full_window_mfe.gt(0))
    result["mfe_capture"] = result.gross_return / denominator
    result["net_mfe_capture"] = result.net_return / denominator
    result["remaining_mfe"] = (result.full_window_mfe - result.mfe).clip(lower=0)
    result["net_r"] = result.net_return / pd.to_numeric(result.stop_fraction).where(result.stop_fraction.gt(0))
    result["post_exit_mfe"] = np.nan
    for h in range(1, holding):
        mask = complete & result.holding_bars.eq(h)
        result.loc[mask, "post_exit_mfe"] = result.loc[mask, f"post_mfe_{h}"]
    stopped = complete & result.exit_reason.eq("stop_loss") & result.post_exit_mfe.notna()
    for threshold in (.02, .05, .10):
        result[f"stopped_recovered_{int(threshold * 100)}pct"] = np.where(
            stopped, result.post_exit_mfe.ge(threshold).astype(float), np.nan)
    return result.drop(columns=[f"post_mfe_{h}" for h in range(1, holding)])


def distribution_rows(ledger: pd.DataFrame, column: str, **tags) -> list[dict]:
    rows = []
    complete = ledger.loc[ledger.status.eq("completed")]
    groups = [("ALL", complete), *complete.groupby("ticker", observed=True)]
    for ticker, group in groups:
        values = pd.to_numeric(group[column]).dropna()
        rows.append(dict(tags, ticker=ticker, count=len(values), mean=values.mean(), median=values.median(),
                         minimum=values.min(), maximum=values.max(), q25=values.quantile(.25), q75=values.quantile(.75)))
    return rows


def evaluate_exit_policies(signals: pd.DataFrame, folds: pd.DataFrame, config: dict,
                          *, progress: Callable[[str], None] | None = None) -> dict[str, pd.DataFrame]:
    """Evaluate fixed catalogue once; select mature prefix outcomes per fold."""
    validate_folds(folds)
    candidates = candidate_catalog(config)
    catalog = {c["id"]: c for c in candidates}
    context = event_context(signals, config["max_holding_bars"])
    cached = {}
    for c in candidates:
        if progress:
            progress(f"Simulating {c['id']}")
        cached[c["id"]] = simulate_candidate(signals, c, config)
    surfaces, selections, oos, summaries, plateaus, stops, targets = [], [], [], [], [], [], []
    for fold in folds.itertuples():
        if progress:
            progress(f"Selecting fold {fold.fold} from prior training only")
        training = {key: boundary_view(value, context, fold.history_start, fold.history_end)
                    for key, value in cached.items()}
        surface = pd.DataFrame([dict(candidate_id=c["id"], family=c["family"], **policy_metrics(training[c["id"]]))
                                for c in candidates])
        surface["fold"] = fold.fold
        surface["ev_win_frontier"] = ev_win_frontier(surface)
        surfaces.append(surface)
        plateaus.extend([dict(row, fold=fold.fold) for row in plateau_summary(
            surface, candidates, config["selection"]["plateau_ev_tolerance"])])
        for c in candidates:
            tags = dict(fold=fold.fold, period="training", candidate_id=c["id"], family=c["family"])
            stops.extend(distribution_rows(training[c["id"]], "stop_fraction", **tags))
            targets.extend(distribution_rows(training[c["id"]], "target_fraction", **tags))
        chosen = {"training_selected": select_training_candidate(surface, config["selection"]["minimum_training_trades"])}
        chosen.update({f"best_{family}": select_training_candidate(surface, config["selection"]["minimum_training_trades"], family)
                       for family in ("fixed", "atr", "r_multiple")})
        chosen.update({name: name for name in ("v1_control", "target_only", "stop_only", "time_only")})
        for policy, candidate_id in chosen.items():
            fit = surface.loc[surface.candidate_id.eq(candidate_id)].iloc[0]
            selections.append(dict(fold=fold.fold, policy=policy, candidate_id=candidate_id,
                parameters=json.dumps(catalog[candidate_id], sort_keys=True), training_net_ev=fit.expected_value,
                training_trades=int(fit.trade_count), history_end=fold.history_end,
                test_start=fold.test_start, test_end=fold.test_end,
                fallback=policy.startswith(("best_", "training_")) and candidate_id == "v1_control"))
            independent = boundary_view(cached[candidate_id], context, fold.test_start, fold.test_end)
            for mode, ledger in (("independent", independent), ("non_overlapping", non_overlap_view(independent))):
                tags = dict(fold=fold.fold, policy=policy, mode=mode)
                summaries.append(dict(tags, candidate_id=candidate_id, **policy_metrics(ledger)))
                enriched = add_exit_diagnostics(ledger, context, config["max_holding_bars"])
                for key, value in tags.items():
                    enriched[key] = value
                oos.append(enriched)
                stops.extend(distribution_rows(ledger, "stop_fraction", period="oos", **tags))
                targets.extend(distribution_rows(ledger, "target_fraction", period="oos", **tags))
    oos = pd.concat(oos, ignore_index=True)
    ticker_rows, aggregate, paired, uncertainty = [], [], [], []
    for policy, mode in sorted({(row["policy"], row["mode"]) for row in summaries}):
        group = oos.loc[oos.policy.eq(policy) & oos["mode"].eq(mode)]
        aggregate.append(dict(policy=policy, mode=mode, **policy_metrics(group)))
        for ticker, part in group.groupby("ticker", observed=True):
            ticker_rows.append(dict(policy=policy, mode=mode, ticker=ticker, **policy_metrics(part)))
        if mode == "independent" and policy != "v1_control":
            control = oos.loc[oos.policy.eq("v1_control") & oos["mode"].eq(mode),
                              ["fold", "timestamp", "ticker", "status", "net_return"]]
            comparison = group.merge(control, on=["fold", "timestamp", "ticker"], suffixes=("", "_control"), validate="one_to_one")
            comparison = comparison.loc[comparison.status.eq("completed") & comparison.status_control.eq("completed")].copy()
            comparison["paired_net_difference"] = comparison.net_return - comparison.net_return_control
            paired.append(comparison[["fold", "timestamp", "ticker", "policy", "candidate_id", "net_return", "net_return_control", "paired_net_difference"]])
            comparison = comparison.sort_values(["timestamp", "ticker"])
            uncertainty.append(dict(policy=policy, **summarize_returns(comparison.paired_net_difference,
                dates=comparison.timestamp, **config["uncertainty"])))
    return dict(candidate_training_results=pd.concat(surfaces, ignore_index=True),
                selected_policy_by_fold=pd.DataFrame(selections), folds=folds,
                oos_results=oos, fold_summary=pd.DataFrame(summaries),
                aggregate_summary=pd.DataFrame(aggregate), ticker_summary=pd.DataFrame(ticker_rows),
                parameter_plateaus=pd.DataFrame(plateaus), stop_distribution=pd.DataFrame(stops),
                target_distribution=pd.DataFrame(targets), paired_comparison=pd.concat(paired, ignore_index=True),
                paired_uncertainty=pd.DataFrame(uncertainty))
