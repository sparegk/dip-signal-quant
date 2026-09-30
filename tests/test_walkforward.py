"""Expanding history, membership masking, causal regimes and fold path boundaries."""

import numpy as np
import pandas as pd
import pytest

from src.backtest import compute_forward_outcomes
from src.features import build_features
from src.signals import build_signals
from src.walkforward import annual_folds, evaluate_fold, spy_regimes, validate_folds


def history(ticker="ABT", dates=None):
    dates = pd.bdate_range("2019-01-01", "2021-03-01") if dates is None else dates
    close = 100 + 10 * np.sin(np.arange(len(dates)) / (13 if ticker == "SPY" else 9))
    return pd.DataFrame({"timestamp": dates.astype("datetime64[ns]"), "ticker": pd.Series([ticker] * len(dates), dtype="string"),
                         "open": close, "high": close + 2, "low": close - 2, "close": close,
                         "volume": np.full(len(dates), 100, dtype=np.int64)})


def tagged(data):
    data = data.copy()
    data["dip_ready_v1"] = True
    data["dip_event_v1"] = np.arange(len(data)) % 3 == 0
    data["dip_condition_v1"] = data.dip_event_v1
    data["dip_component_count"] = np.where(data.dip_event_v1, 3, 0)
    return data


def test_annual_folds_have_expanding_history_disjoint_oos_and_partial_final_year():
    dates = pd.bdate_range("2016-09-29", "2026-09-28")
    folds = annual_folds(dates)
    assert folds.fold.tolist() == [str(year) for year in range(2021, 2027)]
    assert folds.history_start.eq(dates[0]).all()
    assert (folds.history_end < folds.test_start).all()
    assert folds.partial_year.tolist() == [False] * 5 + [True]
    for row in folds.itertuples():
        assert row.history_end == dates[dates < row.test_start][-1]
        assert row.test_start.year == row.test_end.year
    validate_folds(folds)


@pytest.mark.parametrize("kind", ["overlap", "history_leak", "origin", "reverse", "id", "gap_history"])
def test_invalid_fold_boundaries(kind):
    folds = annual_folds(pd.bdate_range("2018-01-01", "2022-06-01"), initial_history_years=1)
    if kind == "overlap": folds.loc[1, "test_start"] = folds.test_end.iloc[0]
    elif kind == "history_leak": folds.loc[0, "history_end"] = folds.test_start.iloc[0]
    elif kind == "origin": folds.loc[1, "history_start"] += pd.Timedelta(days=1)
    elif kind == "reverse": folds = folds.iloc[::-1]
    elif kind == "id": folds.loc[1, "fold"] = folds.fold.iloc[0]
    else: folds.loc[1, "history_end"] = folds.history_end.iloc[0]
    with pytest.raises(ValueError): validate_folds(folds)


@pytest.mark.parametrize("years", [0, -1, True, 1.5])
def test_invalid_history_size(years):
    with pytest.raises(ValueError): annual_folds(history().timestamp, initial_history_years=years)


def test_insufficient_calendar_and_duplicate_dates_fail():
    for dates in (pd.bdate_range("2020-01-01", periods=20), pd.to_datetime(["2020-01-01"] * 2)):
        with pytest.raises(ValueError): annual_folds(dates)


def test_partial_december_is_not_called_a_full_year():
    folds = annual_folds(pd.bdate_range("2019-01-01", "2021-12-15"), initial_history_years=1)
    assert folds.partial_year.tolist() == [False, True]


def test_fold_censoring_cannot_borrow_next_year_and_preserves_last_day_audit():
    stock, spy = tagged(history()), history("SPY")
    fold = annual_folds(spy.timestamp, initial_history_years=1).iloc[0]
    stock.loc[stock.timestamp == fold.test_end, ["dip_event_v1", "dip_condition_v1"]] = True
    result = evaluate_fold(stock, spy, fold, ["ABT"])
    last = result["events"].loc[result["events"].timestamp == fold.test_end]
    assert last.status.eq("no_next_bar").all() and len(last) == 5
    assert result["eligible"].end_timestamp.dropna().le(fold.test_end).all()
    assert result["trades"].exit_timestamp.dropna().le(fold.test_end).all()
    stock.loc[stock.timestamp > fold.test_end, ["open", "high", "low", "close"]] *= 10
    spy.loc[spy.timestamp > fold.test_end, ["open", "high", "low", "close"]] *= 20
    modified = evaluate_fold(stock, spy, fold, ["ABT"])
    for name in result: pd.testing.assert_frame_equal(result[name], modified[name])


def test_membership_filters_observations_not_price_paths_or_event_edges():
    stock, spy = tagged(history()), history("SPY")
    fold = annual_folds(spy.timestamp, initial_history_years=1).iloc[0]
    start = stock.loc[(stock.timestamp >= fold.test_start) & stock.dip_event_v1, "timestamp"].iloc[0]
    end = start + pd.Timedelta(days=1)
    universe = pd.DataFrame({"ticker": ["ABT"], "start_date": [start], "end_date": [end]})
    result = evaluate_fold(stock, spy, fold, universe)
    assert result["events"].timestamp.eq(start).all()
    assert len(result["events"]) == 5
    assert result["events"].status.eq("completed").all()
    assert result["events"].entry_timestamp.gt(start).all()  # Exit after removal allowed.
    stock["dip_event_v1"] = False
    assert evaluate_fold(stock, spy, fold, universe)["events"].empty  # Admission never creates event.


def test_fold_outcomes_and_non_signal_controls_equal_existing_evaluator():
    stock, spy = tagged(history()), history("SPY")
    fold = annual_folds(spy.timestamp, initial_history_years=1).iloc[0]
    result = evaluate_fold(stock, spy, fold, ["ABT"])
    window = stock.loc[stock.timestamp.between(fold.test_start, fold.test_end)].copy()
    window["split"] = "test"
    for selection in ("events", "eligible", "non_signal"):
        expected = compute_forward_outcomes(window, benchmark=spy, selection=selection)
        pd.testing.assert_frame_equal(result[selection][expected.columns], expected)


def test_expanding_signal_history_matches_prefix_recalculation_and_ticker_isolation():
    stock, spy = history(), history("SPY")
    signals = build_signals(build_features(stock, benchmark=spy))
    fold = annual_folds(spy.timestamp, initial_history_years=1).iloc[0]
    prefix = build_signals(build_features(stock.loc[stock.timestamp <= fold.test_end], benchmark=spy.loc[spy.timestamp <= fold.test_end]))
    full = evaluate_fold(signals, spy, fold, ["ABT"])
    truncated = evaluate_fold(prefix, spy, fold, ["ABT"])
    for name in full: pd.testing.assert_frame_equal(full[name], truncated[name])
    second = signals.copy()
    second["ticker"] = "JPM"
    second.loc[:, ["open", "high", "low", "close"]] *= 100
    together = pd.concat([signals, second]).sort_values(["timestamp", "ticker"]).reset_index(drop=True)
    combined = evaluate_fold(together, spy, fold, ["ABT", "JPM"])
    for name in full:
        pd.testing.assert_frame_equal(full[name], combined[name].loc[combined[name].ticker == "ABT"].reset_index(drop=True))


def test_regime_uses_only_current_completed_close_and_prior_history():
    spy = history("SPY")
    result = spy_regimes(spy)
    assert result.regime.iloc[:199].eq("unknown").all()
    expected = np.where(spy.close >= spy.close.rolling(200).mean(), "above", "below")
    assert result.regime.iloc[199:].tolist() == expected[199:].tolist()
    prefix = spy_regimes(spy.iloc[:300])
    spy.loc[300:, ["open", "high", "low", "close"]] *= 100
    pd.testing.assert_frame_equal(prefix, spy_regimes(spy).iloc[:300])
    with pytest.raises(ValueError): spy_regimes(history("ABT"))


def test_unknown_regime_on_absent_benchmark_date_is_not_filled():
    stock, spy = tagged(history()), history("SPY")
    fold = annual_folds(spy.timestamp, initial_history_years=1).iloc[0]
    missing = stock.loc[stock.timestamp >= fold.test_start, "timestamp"].iloc[4]
    result = evaluate_fold(stock, spy.loc[spy.timestamp != missing], fold, ["ABT"])
    assert result["observations"].loc[result["observations"].timestamp == missing, "regime"].iloc[0] == "unknown"
