"""Offline exit families, controls, maturity gates and training-only selection."""

from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from scripts import evaluate_exp004 as runner
from scripts.report_exp004 import render_report
from src import backtest
from src import exit_policies as exits


ROOT = Path(__file__).resolve().parents[1]


def configuration(small=False):
    config = json.loads((ROOT / "config/exp004.json").read_text())
    if small:
        config["fixed_pairs_percent"] = [[4, 8], [5, 10]]
        config["stop_multipliers"] = [1, 2]
        config["target_multipliers"] = [1, 2]
        config["reward_risk_ratios"] = [1, 2]
        config["candidates"] = [c for c in config["candidates"] if c["family"] == "control"
            or c["family"] == "fixed" and [100*c["stop"], 100*c["target"]] in config["fixed_pairs_percent"]
            or c["family"] == "atr" and c["stop_multiplier"] in [1, 2] and c["target_multiplier"] in [1, 2]
            or c["family"] == "r_multiple" and c["stop_multiplier"] in [1, 2] and c["reward_risk"] in [1, 2]]
        config["candidate_count"] = len(config["candidates"])
        config["selectable_candidate_count"] = len(config["candidates"]) - 4
        config["selection"]["minimum_training_trades"] = 1
        config["uncertainty"] = dict(n_bootstrap=20, block_size=1, seed=42)
    return config


def bars(n=80, ticker="TEST"):
    result = pd.DataFrame(dict(timestamp=pd.bdate_range("2019-01-01", periods=n),
        ticker=pd.Series([ticker]*n, dtype="string"), open=np.full(n,100.),
        high=np.full(n,101.), low=np.full(n,99.), close=np.full(n,100.),
        volume=np.full(n,100,dtype=np.int64), dip_event_v1=np.isin(np.arange(n), np.arange(0,n,12)),
        dip_ready_v1=np.full(n,True), atr_pct_14=np.full(n,.02)))
    result["dip_condition_v1"] = result.dip_event_v1
    result["dip_component_count"] = np.where(result.dip_event_v1, 3, 0)
    return result


def folds(data):
    t = data.timestamp
    return pd.DataFrame([dict(fold="a", history_start=t.iloc[0], history_end=t.iloc[19], test_start=t.iloc[20], test_end=t.iloc[39]),
                         dict(fold="b", history_start=t.iloc[0], history_end=t.iloc[39], test_start=t.iloc[40], test_end=t.iloc[79])])


def candidate(config, name):
    return next(c for c in config["candidates"] if c["id"] == name)


def test_registered_enumeration_and_configuration_guard(tmp_path):
    config = runner.load_config()
    catalog = exits.candidate_catalog(config)
    assert len(catalog) == 136
    assert pd.Series([c["family"] for c in catalog]).value_counts().to_dict() == dict(atr=56, r_multiple=56, fixed=20, control=4)
    config["candidates"].append(deepcopy(catalog[0]))
    with pytest.raises(ValueError, match="catalogue"):
        exits.candidate_catalog(config)
    path = tmp_path / "changed.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="configuration changed"):
        runner.load_config(path)


@pytest.mark.parametrize("name,stop,target", [("fixed_s04_t08", .04,.08), ("atr_s0.75_t1.5", .015,.03),
                                             ("r_s2_r2.5", .04,.1)])
def test_candidate_fraction_calculations(name, stop, target):
    config = configuration()
    fractions = exits.candidate_fractions(bars(), candidate(config, name), config)
    np.testing.assert_allclose(fractions.stop_fraction, stop)
    np.testing.assert_allclose(fractions.target_fraction, target)


@pytest.mark.parametrize("value,stop,target", [(0,.01,.03), (.5,.20,.30)])
def test_bounds_and_effective_r_after_clipping(value, stop, target):
    config = configuration()
    data = bars()
    data["atr_pct_14"] = value
    fractions = exits.candidate_fractions(data, candidate(config,"r_s4_r3"), config)
    assert fractions.stop_fraction.iloc[0] == stop
    assert fractions.target_fraction.iloc[0] == target


@pytest.mark.parametrize("value", [np.nan, np.inf, -.01])
def test_missing_event_volatility_fails_explicitly(value):
    config = configuration()
    data = bars()
    data.loc[0,"atr_pct_14"] = value
    with pytest.raises(ValueError, match="ATR"):
        exits.simulate_candidate(data,candidate(config,"atr_s1_t1"),config)


def test_future_atr_cannot_change_earlier_fractions():
    config = configuration()
    data = bars()
    old = exits.candidate_fractions(data,candidate(config,"atr_s1_t2"),config)
    data.loc[20:, "atr_pct_14"] = .9
    new = exits.candidate_fractions(data,candidate(config,"atr_s1_t2"),config)
    assert_frame_equal(old.iloc[:20],new.iloc[:20])


@pytest.mark.parametrize("name,reason,price", [("v1_control","stop_loss",93),
    ("target_only","take_profit",110),("stop_only","stop_loss",93),("time_only","time_exit",102)])
def test_controls_share_next_open_and_disabled_barriers(name,reason,price):
    config = configuration()
    data = bars(12)
    data.loc[0,["open","high","low","close"]] = 80.
    data.loc[1,["open","high","low","close"]] = [100,112,90,101]
    data.loc[10,["open","high","low","close"]] = [100,103,99,102]
    row = exits.simulate_candidate(data,candidate(config,name),config).iloc[0]
    assert row.entry_price == 100
    assert row.entry_timestamp == data.timestamp.iloc[1]
    assert row.exit_reason == reason
    assert row.exit_price == pytest.approx(price)
    assert row.net_return < row.gross_return


@pytest.mark.parametrize("opening,high,low,reason,price", [(100,105,95,"stop_loss",98),
    (96,101,95,"stop_loss",96),(106,107,99,"take_profit",106),(100,101,99,"time_exit",100)])
def test_variable_engine_uses_conservative_touches_gaps_and_time(opening,high,low,reason,price):
    data = bars(12)
    # Place gap on second holding bar; barriers stay at the first open.
    data.loc[2,["open","high","low","close"]] = [opening,high,low,opening]
    row = exits.simulate_candidate(data,candidate(configuration(),"atr_s1_t2"),configuration()).iloc[0]
    assert row.exit_reason == reason
    assert row.exit_price == pytest.approx(price)


def test_maturity_gate_matches_truncate_before_evaluation_and_nonoverlap():
    config = configuration()
    data = bars()
    data.loc[8,"dip_event_v1"] = data.loc[8,"dip_condition_v1"] = True
    data.loc[8,"dip_component_count"] = 3
    c = candidate(config,"v1_control")
    context = exits.event_context(data)
    gated = exits.boundary_view(exits.simulate_candidate(data,c,config), context,
                               data.timestamp.iloc[0],data.timestamp.iloc[24])
    prefix = data.iloc[:25].copy()
    expected = backtest.simulate_barrier_trades(prefix,commission_rate=.0001,slippage_rate=.0005)
    assert_frame_equal(gated[expected.columns],expected,check_flags=False)
    sequential = exits.non_overlap_view(gated)
    expected = backtest.simulate_barrier_trades(prefix,mode="non_overlapping",commission_rate=.0001,slippage_rate=.0005)
    assert_frame_equal(sequential[expected.columns],expected,check_flags=False)
    assert gated.status.iloc[-1] == "no_next_bar"
    assert gated.loc[gated.status.ne("completed"),"net_return"].isna().all()


def test_train_only_selection_ties_and_minimum():
    surface = pd.DataFrame(dict(candidate_id=["z","a","v1_control"],family=["fixed","atr","control"],
                                trade_count=[200,200,200],expected_value=[.1,.1,.2]))
    assert exits.select_training_candidate(surface,200) == "a"
    assert exits.select_training_candidate(surface,201) == "v1_control"
    assert exits.select_training_candidate(surface,200,"fixed") == "z"


def test_future_prices_cannot_change_first_fold_training_selection():
    config = configuration(small=True)
    data = bars()
    original = exits.evaluate_exit_policies(data,folds(data),config)
    changed = data.copy()
    changed.loc[20:, ["open","high","low","close"]] *= 1.4
    changed.loc[20:,"atr_pct_14"] = .2
    new = exits.evaluate_exit_policies(changed,folds(data),config)
    for name in ("candidate_training_results","selected_policy_by_fold"):
        assert_frame_equal(original[name].query("fold == 'a'").reset_index(drop=True),
                           new[name].query("fold == 'a'").reset_index(drop=True))
    selected = original["selected_policy_by_fold"]
    merged = original["oos_results"].merge(selected[["fold","policy","candidate_id"]],on=["fold","policy"],suffixes=("","_selected"))
    assert merged.candidate_id.eq(merged.candidate_id_selected).all()


def test_r_capture_and_post_stop_recovery_are_diagnostics_only():
    config = configuration()
    data = bars(12)
    data.loc[1,["open","high","low","close"]] = [100,102,95,100]
    data.loc[2,"high"] = 112.
    context = exits.event_context(data)
    ledger = exits.boundary_view(exits.simulate_candidate(data,candidate(config,"fixed_s04_t08"),config),
                                context,data.timestamp.min(),data.timestamp.max())
    enriched = exits.add_exit_diagnostics(ledger,context,10)
    row = enriched.iloc[0]
    assert row.gross_return == pytest.approx(-.04)
    assert row.net_r == pytest.approx(row.net_return/.04)
    assert row.mfe_capture == pytest.approx(-1/3)
    assert row.remaining_mfe == pytest.approx(.10)
    assert row.stopped_recovered_10pct == 1
    for threshold in (2,5,10):
        assert row[f"stopped_recovered_{threshold}pct"] == 1
    # No future diagnostic columns are passed into policy selection.
    assert not any("recover" in key or "capture" in key for key in exits.policy_metrics(ledger))


def test_zero_mfe_and_no_stop_r_are_undefined():
    config = configuration()
    data = bars(12)
    data[["high","low"]] = 100.
    context = exits.event_context(data)
    ledger = exits.boundary_view(exits.simulate_candidate(data,candidate(config,"time_only"),config),
                                context,data.timestamp.min(),data.timestamp.max())
    enriched = exits.add_exit_diagnostics(ledger,context,10)
    assert enriched.mfe_capture.isna().all()
    assert enriched.net_r.isna().all()
    assert pd.isna(exits.policy_metrics(ledger)["expectancy_r"])


def test_multi_ticker_isolation_and_frontier():
    config = configuration()
    a,b = bars(24,"ONE"),bars(24,"TWO")
    b[["open","high","low","close"]] *= 2
    b["atr_pct_14"] = .1
    both = pd.concat([a,b]).sort_values(["timestamp","ticker"]).reset_index(drop=True)
    result = exits.simulate_candidate(both,candidate(config,"atr_s1_t2"),config)
    alone = exits.simulate_candidate(a,candidate(config,"atr_s1_t2"),config)
    assert_frame_equal(result.query("ticker == 'ONE'").reset_index(drop=True),alone)
    surface = pd.DataFrame(dict(expected_value=[.1,.09,.08],win_rate=[.4,.7,.6]))
    assert exits.ev_win_frontier(surface).tolist() == [True,True,False]


def test_offline_runner_artifacts_are_reproducible(tmp_path, monkeypatch):
    config = configuration(small=True)
    data = bars()
    monkeypatch.setattr(runner,"load_config",lambda _: config)
    monkeypatch.setattr(runner,"load_frozen_signals",lambda *a,**k: (data,folds(data),dict(usable_count=1, requested_count=1)))
    monkeypatch.setattr(runner,"prospective_status",lambda: dict(status="pending", classification_counts={}))
    first = runner.run_experiment(output_dir=tmp_path/"first")
    second = runner.run_experiment(output_dir=tmp_path/"second")
    assert first["artifact_sha256"] == second["artifact_sha256"]
    assert len(first["artifact_sha256"]) >= 15
    report = render_report(tmp_path/"first")
    assert "pending" in report and "Training-selected" in report
    (tmp_path/"first/aggregate_summary.csv").write_text("corrupted")
    with pytest.raises(ValueError,match="artifact changed"):
        render_report(tmp_path/"first")


def test_runner_refuses_frozen_input_output_overlap():
    with pytest.raises(ValueError,match="overlaps"):
        runner.run_experiment(output_dir=ROOT/"data/market")


def test_post_exit_changes_do_not_enter_maturity_gated_training_metrics():
    config = configuration()
    data = bars()
    context = exits.event_context(data)
    ledger = exits.simulate_candidate(data,candidate(config,"v1_control"),config)
    original = exits.boundary_view(ledger,context,data.timestamp.iloc[0],data.timestamp.iloc[19])
    changed = context.copy()
    changed[[c for c in changed if "mfe" in c or "mae" in c]] = 999.
    gated = exits.boundary_view(ledger,changed,data.timestamp.iloc[0],data.timestamp.iloc[19])
    assert_frame_equal(original,gated)
    diagnostic = exits.add_exit_diagnostics(gated,changed,10)
    assert diagnostic.loc[diagnostic.status.ne("completed"),"full_window_mfe"].isna().all()


def test_training_plateau_depends_on_adjacent_training_candidates_only():
    config = configuration(small=True)
    cs = [c for c in config["candidates"] if c["family"] == "atr"]
    surface = pd.DataFrame(dict(candidate_id=[c["id"] for c in cs], family="atr",
                               expected_value=[.01,.0099,.0098,.0097]))
    result = exits.plateau_summary(surface,cs,.0005)[0]
    assert result["near_best_count"] == 4
    assert result["adjacent_near_best_count"] == 2
    assert result["plateau_flag"]
    surface.loc[1:,"expected_value"] = .001
    assert not exits.plateau_summary(surface,cs,.0005)[0]["plateau_flag"]


def test_no_events_fallback_and_risk_schema():
    config = configuration(small=True)
    data = bars()
    data["dip_event_v1"] = data["dip_condition_v1"] = False
    data["dip_component_count"] = 0
    result = exits.evaluate_exit_policies(data,folds(data),config)
    selections = result["selected_policy_by_fold"]
    selected = selections.loc[selections.policy.str.startswith(("best_", "training_"))]
    assert selected.candidate_id.eq("v1_control").all()
    assert selected.fallback.all()
    assert result["oos_results"].empty
    assert result["aggregate_summary"].trade_count.eq(0).all()
