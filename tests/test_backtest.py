"""Deterministic execution, censoring, baseline, and causal-boundary contracts."""

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from src import backtest


def bars(rows, *, events=(0,), ticker="AAPL", dates=None):
    """Rows are open/high/low/close; retain all dates, including non-events."""
    data = pd.DataFrame(rows, columns=["open", "high", "low", "close"], dtype=float)
    data.insert(0, "ticker", pd.Series([ticker] * len(data), dtype="string"))
    data.insert(0, "timestamp", pd.bdate_range("2024-01-01", periods=len(data))
                if dates is None else pd.DatetimeIndex(dates))
    data["volume"] = np.full(len(data), 100, dtype=np.int64)
    data["dip_event_v1"] = np.isin(np.arange(len(data)), events)
    data["dip_condition_v1"] = data.dip_event_v1
    data["dip_ready_v1"] = True
    data["dip_component_count"] = np.where(data.dip_event_v1, 4, 0)
    return data


def flat(n=30, **kwargs):
    return bars([(100, 101, 99, 100)] * n, **kwargs)


def combine(*frames):
    return pd.concat(frames, ignore_index=True).sort_values(["timestamp", "ticker"]).reset_index(drop=True)


def test_entry_is_next_open_not_signal_close_and_exact_forward_excursions():
    data = bars([(80, 200, 20, 80), (100, 103, 98, 102), (102, 106, 97, 105), (104, 111, 99, 108)])
    result = backtest.compute_forward_outcomes(data, horizons=(1, 3))
    assert result.entry_timestamp.eq(data.timestamp.iloc[1]).all()
    assert result.entry_price.eq(100).all()
    np.testing.assert_allclose(result.forward_return, [.02, .08])
    np.testing.assert_allclose(result.mfe, [.03, .11])
    np.testing.assert_allclose(result.mae, [-.02, -.03])
    assert result.end_timestamp.tolist() == list(data.timestamp.iloc[[1, 3]])


def test_all_default_horizon_endpoints():
    data = bars([(100 + i,) * 4 for i in range(22)])
    result = backtest.compute_forward_outcomes(data)
    assert result.horizon.tolist() == [1, 3, 5, 10, 20]
    for row in result.itertuples():
        assert row.forward_return == pytest.approx((100 + row.horizon) / 101 - 1)
        assert row.end_timestamp == data.timestamp.iloc[row.horizon]


def test_known_target_path_and_first_hit():
    data = bars([(80, 80, 80, 80), (100, 103, 99, 102), (102, 106, 100, 105), (105, 111, 102, 108)])
    trade = backtest.simulate_barrier_trades(data, max_holding_bars=3).iloc[0]
    assert trade.entry_timestamp == data.timestamp.iloc[1]
    assert trade.exit_timestamp == data.timestamp.iloc[3]
    assert trade.entry_price == 100
    assert trade.exit_price == pytest.approx(110)
    assert trade.exit_reason == "take_profit"
    assert trade.holding_bars == 3
    assert trade.gross_return == pytest.approx(.10)
    assert trade.net_return == trade.gross_return
    assert trade.mfe == pytest.approx(.11)  # Explicit full-exit-bar envelope, not pre-fill MFE.
    assert trade.mae == pytest.approx(-.01)


@pytest.mark.parametrize("policy, reason, price", [
    ("conservative", "stop_loss", 93), ("optimistic", "take_profit", 110),
])
def test_same_entry_bar_ambiguity_is_explicit(policy, reason, price):
    data = bars([(80, 80, 80, 80), (100, 111, 92, 100)])
    trade = backtest.simulate_barrier_trades(data, max_holding_bars=1, ambiguity_policy=policy).iloc[0]
    assert trade.exit_reason == reason
    assert trade.exit_price == pytest.approx(price)
    assert trade.exit_timestamp == data.timestamp.iloc[1]
    assert trade.holding_bars == 1
    assert trade.ambiguous_bar


@pytest.mark.parametrize("high, low, reason, expected", [
    (103, 92, "stop_loss", 93), (110, 99, "take_profit", 110),
    (103, 93, "stop_loss", 93), (109.99999999, 99, "time_exit", 100),
])
def test_exact_barrier_touches_and_roundoff(high, low, reason, expected):
    data = bars([(100, 100, 100, 100), (100, high, low, 100)])
    trade = backtest.simulate_barrier_trades(data, max_holding_bars=1).iloc[0]
    assert trade.exit_reason == reason
    assert trade.exit_price == pytest.approx(expected)


@pytest.mark.parametrize("opening, high, low, reason", [
    (90, 112, 89, "stop_loss"), (115, 120, 90, "take_profit"),
])
def test_later_open_gap_precedes_intraday_barriers(opening, high, low, reason):
    data = bars([(80, 80, 80, 80), (100, 102, 99, 100), (opening, high, low, opening)])
    trade = backtest.simulate_barrier_trades(data, max_holding_bars=2).iloc[0]
    assert trade.exit_price == opening
    assert trade.exit_reason == reason
    assert trade.fill_type == "open"
    assert not trade.ambiguous_bar  # The open establishes the first hit.
    assert trade.mfe == pytest.approx(max(102, opening) / 100 - 1)
    assert trade.mae == pytest.approx(min(99, opening) / 100 - 1)
    assert trade.excursion_scope == "through_exit_open"


def test_entry_gap_is_not_a_stop_relative_to_signal_close():
    data = bars([(100, 100, 100, 100), (80, 81, 79, 80)])
    trade = backtest.simulate_barrier_trades(data, max_holding_bars=1).iloc[0]
    assert trade.entry_price == 80
    assert trade.exit_reason == "time_exit"
    assert trade.gross_return == 0


def test_time_exit_is_max_bar_close_and_barriers_take_precedence():
    data = bars([(80, 80, 80, 80), (100, 102, 99, 101), (101, 104, 98, 103), (103, 120, 90, 110)])
    trade = backtest.simulate_barrier_trades(data, max_holding_bars=2).iloc[0]
    assert trade.exit_timestamp == data.timestamp.iloc[2]
    assert trade.exit_reason == "time_exit"
    assert trade.exit_price == 103
    assert trade.mfe == pytest.approx(.04)
    assert trade.mae == pytest.approx(-.02)


def test_costs_on_both_slipped_notionals_do_not_change_barriers():
    expected = 110 * .995 * .999 / (100 * 1.005 * 1.001) - 1
    costs = backtest.apply_costs(100, 110, commission_rate=.001, slippage_rate=.005)
    assert costs["net_return"] == pytest.approx(expected)
    assert costs["entry_fill_price"] == pytest.approx(100.5)
    assert costs["exit_fill_price"] == pytest.approx(109.45)
    assert costs["gross_return"] == pytest.approx(.1)
    data = bars([(100, 100, 100, 100), (100, 111, 99, 105)])
    trade = backtest.simulate_barrier_trades(data, max_holding_bars=1,
                                            commission_rate=.001, slippage_rate=.005).iloc[0]
    assert trade.net_return == pytest.approx(expected)
    assert trade.exit_reason == "take_profit"


def test_missing_next_bar_and_short_windows_are_audited_not_filled():
    data = flat(3, events=(0, 2))
    outcomes = backtest.compute_forward_outcomes(data, horizons=(1, 3))
    assert outcomes.status.tolist() == ["completed", "incomplete_window", "no_next_bar", "no_next_bar"]
    assert outcomes.forward_return.iloc[1:].isna().all()
    trades = backtest.simulate_barrier_trades(data, max_holding_bars=3)
    assert trades.status.tolist() == ["incomplete_window", "no_next_bar"]
    assert trades.exit_reason.isna().all()
    assert trades.net_return.isna().all()


def test_early_target_near_end_does_not_escape_full_window_censoring():
    data = bars([(100, 100, 100, 100), (100, 120, 99, 110)])
    trade = backtest.simulate_barrier_trades(data).iloc[0]
    assert trade.status == "incomplete_window"
    assert pd.isna(trade.exit_price)


def test_overlapping_events_and_no_same_bar_recycling():
    data = flat(10, events=(0, 1, 2, 3, 6))
    independent = backtest.simulate_barrier_trades(data, max_holding_bars=3)
    stream = backtest.simulate_barrier_trades(data, max_holding_bars=3, mode="non_overlapping")
    assert independent.status.eq("completed").all()
    assert stream.status.tolist() == ["completed", "overlap", "overlap", "completed", "completed"]
    assert stream.loc[stream.status == "completed", "entry_timestamp"].tolist() == list(data.timestamp.iloc[[1, 4, 7]])
    assert len(backtest.compute_forward_outcomes(data, horizons=(3,))) == 5


@pytest.mark.parametrize("function", [backtest.compute_forward_outcomes, backtest.simulate_barrier_trades])
def test_multi_ticker_future_path_isolation(function):
    a = flat(35, events=(0, 2, 10))
    b = bars([(1000, 1100, 500, 900)] * 31, ticker="MSFT", events=(0, 3, 8), dates=a.timestamp.iloc[4:])
    solo = function(a)
    together = function(combine(a, b))
    assert_frame_equal(together.loc[together.ticker == "AAPL"].reset_index(drop=True), solo)
    b.loc[:, ["open", "high", "low", "close"]] *= 10
    modified = function(combine(a, b))
    assert_frame_equal(modified.loc[modified.ticker == "AAPL"].reset_index(drop=True), solo)


def test_common_splits_use_unique_dates_not_ticker_row_counts():
    a = flat(10)
    b = flat(4, ticker="MSFT", dates=a.timestamp.iloc[-4:])
    result = backtest.assign_research_splits(combine(a, b))
    assert result.attrs["research_splits"]["validation_start"] == str(a.timestamp.iloc[6].date())
    assert result.attrs["research_splits"]["test_start"] == str(a.timestamp.iloc[8].date())
    assert result.loc[result.ticker == "AAPL", "split"].tolist() == ["research"] * 6 + ["validation"] * 2 + ["test"] * 2
    assert result.groupby("timestamp")["split"].nunique().eq(1).all()


def test_explicit_boundaries_are_inclusive_and_full_outcomes_cannot_cross():
    data = flat(10, events=(3, 4, 5, 7, 8, 9))
    split = backtest.assign_research_splits(data, validation_start=data.timestamp.iloc[5], test_start=data.timestamp.iloc[8])
    result = backtest.compute_forward_outcomes(split, horizons=(1, 2))
    at_four = result.loc[result.timestamp == data.timestamp.iloc[4]]
    assert at_four.status.eq("split_boundary").all()
    assert result.loc[(result.timestamp == data.timestamp.iloc[3]) & (result.horizon == 1), "status"].iloc[0] == "completed"
    trades = backtest.simulate_barrier_trades(split, max_holding_bars=2)
    assert trades.status.tolist() == ["split_boundary", "split_boundary", "completed", "split_boundary", "incomplete_window", "no_next_bar"]


def test_unconditional_and_non_signal_baselines_use_same_entry_and_eligibility():
    data = flat(6, events=(1,))
    data.loc[0, "dip_ready_v1"] = False
    data.loc[2, "dip_condition_v1"] = True  # Persistent condition is not a non-signal date.
    unconditional = backtest.compute_forward_outcomes(data, selection="eligible", horizons=(1,))
    controls = backtest.compute_forward_outcomes(data, selection="non_signal", horizons=(1,))
    assert unconditional.timestamp.tolist() == list(data.timestamp.iloc[1:])
    assert controls.timestamp.tolist() == list(data.timestamp.iloc[3:])
    assert unconditional.entry_timestamp.iloc[0] == data.timestamp.iloc[2]


def test_benchmark_exact_stock_endpoints_without_forward_fill():
    stock = bars([(100, 100, 100, 100), (100, 102, 99, 102), (102, 110, 100, 110)])
    spy = bars([(200, 200, 200, 200), (200, 220, 190, 210), (210, 240, 205, 230)], ticker="SPY")
    result = backtest.compute_forward_outcomes(stock, benchmark=spy, horizons=(1, 2))
    np.testing.assert_allclose(result.benchmark_return, [.05, .15])
    np.testing.assert_allclose(result.excess_return, [-.03, -.05])
    absent = backtest.compute_forward_outcomes(stock, benchmark=spy.drop(index=1), horizons=(1, 2))
    assert absent.benchmark_return.isna().all()
    assert absent.forward_return.notna().all()
    interior = backtest.compute_forward_outcomes(stock, benchmark=spy.drop(index=0), horizons=(2,))
    assert interior.benchmark_return.iloc[0] == pytest.approx(.15)


@pytest.mark.parametrize("function", [backtest.extract_events, backtest.compute_forward_outcomes, backtest.simulate_barrier_trades])
def test_empty_event_set_has_schema_and_no_input_mutation(function):
    data = flat(events=())
    data.attrs = {"source": {"vintage": "fixed"}}
    original = data.copy(deep=True)
    result = function(data)
    assert result.empty
    assert "timestamp" in result and "ticker" in result
    assert_frame_equal(data, original)
    result.attrs["source"]["vintage"] = "changed"
    assert data.attrs["source"]["vintage"] == "fixed"


@pytest.mark.parametrize("kwargs", [
    {"take_profit": 0}, {"take_profit": np.inf}, {"stop_loss": 1}, {"stop_loss": -.1},
    {"stop_loss": True}, {"max_holding_bars": 0}, {"max_holding_bars": 1.5},
    {"max_holding_bars": True}, {"commission_rate": -1}, {"commission_rate": 1},
    {"slippage_rate": np.nan}, {"slippage_rate": "0.01"},
    {"ambiguity_policy": "favorable"}, {"mode": "portfolio"},
])
def test_invalid_simulation_configuration(kwargs):
    with pytest.raises(ValueError):
        backtest.simulate_barrier_trades(flat(), **kwargs)


@pytest.mark.parametrize("horizons", [(), (0,), (-1,), (1.5,), (True,)])
def test_invalid_horizons(horizons):
    with pytest.raises(ValueError):
        backtest.compute_forward_outcomes(flat(), horizons=horizons)


@pytest.mark.parametrize("kwargs", [
    {"research_fraction": 0}, {"validation_fraction": .5}, {"research_fraction": True},
    {"validation_start": "2024-01-02"},
    {"validation_start": "2024-01-03", "test_start": "2024-01-02"},
    {"validation_start": "2024-01-03 12:00", "test_start": "2024-01-05"},
])
def test_invalid_split_configuration(kwargs):
    with pytest.raises(ValueError):
        backtest.assign_research_splits(flat(), **kwargs)


@pytest.mark.parametrize("kind", ["nan", "inf", "duplicate", "unsorted", "missing", "flag", "count", "inconsistent", "split"])
def test_malformed_signal_price_input_rejected(kind):
    data = flat()
    if kind == "nan": data.loc[1, "open"] = np.nan
    elif kind == "inf": data.loc[1, "high"] = np.inf
    elif kind == "duplicate": data = pd.concat([data, data.iloc[-1:]])
    elif kind == "unsorted": data = data.iloc[::-1]
    elif kind == "missing": data = data.drop(columns="dip_event_v1")
    elif kind == "flag": data["dip_event_v1"] = 1
    elif kind == "count": data["dip_component_count"] = 5
    elif kind == "inconsistent": data["dip_ready_v1"] = False
    else: data["split"] = "random"
    for function in (backtest.compute_forward_outcomes, backtest.simulate_barrier_trades):
        with pytest.raises(ValueError):
            function(data)


def test_evaluation_never_changes_signal_history_or_feeds_back_future_prices():
    from src.features import build_features
    from src.signals import build_signals

    x = 100 + 10 * np.sin(np.arange(400) / 13)
    stock = bars([(p, p + 1, p - 1, p) for p in x]).iloc[:, :7]
    spy = flat(400, ticker="SPY").iloc[:, :7]
    signals = build_signals(build_features(stock, benchmark=spy))
    original = signals.copy(deep=True)
    backtest.compute_forward_outcomes(signals, benchmark=spy)
    backtest.simulate_barrier_trades(signals)
    assert_frame_equal(signals, original, check_exact=True)
    altered = stock.copy()
    altered.loc[300:, ["open", "high", "low", "close"]] *= 5
    changed = build_signals(build_features(altered, benchmark=spy))
    backtest.compute_forward_outcomes(changed, benchmark=spy)
    backtest.simulate_barrier_trades(changed)
    assert_frame_equal(changed.iloc[:300], original.iloc[:300], check_exact=True)
    assert not any(c.startswith("forward_") for c in signals)


@pytest.mark.parametrize("function", [backtest.compute_forward_outcomes, backtest.simulate_barrier_trades])
def test_later_split_prices_cannot_change_earlier_split_outcomes(function):
    data = backtest.assign_research_splits(flat(100, events=(0, 10, 55, 58, 60, 80)))
    expected = function(data)
    data.loc[data["split"] != "research", ["open", "high", "low", "close"]] *= 10
    changed = function(data)
    assert_frame_equal(changed.loc[changed["split"] == "research"].reset_index(drop=True),
                       expected.loc[expected["split"] == "research"].reset_index(drop=True))


def test_irregular_stock_calendar_uses_stock_horizon_and_exact_spy_dates():
    spy = bars([(100 + 10 * i,) * 4 for i in range(8)], ticker="SPY")
    stock = bars([(100,) * 4] * 4, dates=spy.timestamp.iloc[[0, 2, 5, 7]])
    result = backtest.compute_forward_outcomes(stock, benchmark=spy, horizons=(3,)).iloc[0]
    assert result.entry_timestamp == spy.timestamp.iloc[2]
    assert result.end_timestamp == spy.timestamp.iloc[7]
    assert result.benchmark_return == pytest.approx(170 / 120 - 1)


def test_offline_experiment_runner_uses_fixed_configuration_and_no_network(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import json
    from scripts import evaluate_v1
    from src.data import save_parquet

    for symbol in ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "SPY"):
        close = 100 + 12 * np.sin(np.arange(300) / (17 if symbol == "SPY" else 9))
        frame = bars([(p, p + 1, p - 1, p) for p in close], ticker=symbol)
        save_parquet(frame.iloc[:, :7], tmp_path / f"{symbol}.parquet")
    monkeypatch.setattr(evaluate_v1.subprocess, "run", lambda args, **kwargs:
                        SimpleNamespace(stdout="fixed_revision" if "rev-parse" in args else ""))
    report = evaluate_v1.run_experiment(tmp_path)
    assert report["working_tree_dirty"] is False
    assert report["signal_parameters"]["quantile"] == .2
    assert report["exit_parameters"]["take_profit"] == .1
    assert report["exit_parameters"]["commission_rate"] == .0001
    assert report["uncertainty"]["seed"] == 42
    assert [r["split"] for r in report["splits"]] == ["research", "validation", "test"]
    assert len(report["trade_summaries"]) == 6
    assert len(report["per_ticker_non_overlapping"]) == 15
    assert len(report["snapshots"]["SPY"]["sha256"]) == 64
    json.dumps(report, allow_nan=False)  # Undefined metrics are portable JSON null.


def test_target_can_exceed_one_hundred_percent_but_stop_cannot():
    data = bars([(100, 100, 100, 100), (100, 220, 99, 110)])
    result = backtest.simulate_barrier_trades(data, take_profit=1.1, max_holding_bars=1).iloc[0]
    assert result.exit_price == pytest.approx(210)
    assert result.gross_return == pytest.approx(1.1)


def test_unrepresentable_barriers_and_cost_overflow_are_rejected():
    with pytest.raises(ValueError, match="representably"):
        backtest.simulate_barrier_trades(flat(), take_profit=1e-30)
    with pytest.raises(ValueError, match="overflow"):
        backtest.apply_costs(1e308, 1e308, commission_rate=.9, slippage_rate=.1)


@pytest.mark.parametrize("price", [0, -1, np.nan, np.inf, True, "100"])
def test_cost_api_invalid_prices(price):
    with pytest.raises(ValueError):
        backtest.apply_costs(price, 100)
