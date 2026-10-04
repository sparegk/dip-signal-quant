"""Offline regressions for exploratory path definitions and presentation adapters."""

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.dashboard_research import export_exp004, export_diagnosis, hypothesis_registry
from src.research_diagnosis import rebound_paths, support_context, describe

CONFIG = json.loads((Path(__file__).resolve().parents[1]/"config/research_diagnosis.json").read_text())


def observations():
    dates = pd.bdate_range("2025-01-01", periods=25)
    return pd.DataFrame([dict(ticker=ticker, fold="2025", timestamp=day, open=100., high=106.,
                             low=99., close=100., dip_event_v1=i in [0,10,11,24])
                         for ticker in ["AA","BB"] for i,day in enumerate(dates)])


def test_paths_are_ticker_isolated_censored_and_exactly_next_open():
    obs=observations()
    obs.loc[obs.ticker.eq("BB"), "open"] = 200.
    paths=rebound_paths(obs, CONFIG)
    assert len(paths)==6  # last signal lacks next bar/path
    assert paths.loc[paths.ticker.eq("AA"), "reach_5pct"].eq(1).all()
    assert paths.loc[paths.ticker.eq("BB"), "reach_5pct"].isna().all()
    assert paths.loc[paths.ticker.eq("AA"), "entry_gap"].eq(0).all()
    changed=obs.copy()
    changed.loc[changed.timestamp.ge(pd.Timestamp("2025-01-16")), "fold"]="2026"
    p=rebound_paths(changed,CONFIG)
    assert all(p.timestamp.dt.year.eq(p.maturity.dt.year))
    assert len(p)<len(paths)


def test_prior_support_matures_strictly_before_signal_and_future_does_not_change_it():
    obs=observations()
    paths=rebound_paths(obs,CONFIG)
    context=support_context(obs,paths,CONFIG)
    aa=context.loc[context.ticker.eq("AA")].reset_index(drop=True)
    assert aa.prior_successful_visits.iloc[0]==0
    assert aa.prior_successful_visits.iloc[1]==0  # maturity same day is not prior
    assert aa.prior_successful_visits.iloc[2]==1
    future=paths.copy()
    future.loc[future.timestamp.ge(obs.timestamp.unique()[11]),"full_mfe"]=99.
    other=support_context(obs,future,CONFIG)
    pd.testing.assert_frame_equal(context.loc[context.timestamp.le(obs.timestamp.unique()[11])].reset_index(drop=True),
                                  other.loc[other.timestamp.le(obs.timestamp.unique()[11])].reset_index(drop=True))


def test_signal_current_outcome_never_defines_current_support():
    obs=observations()
    paths=rebound_paths(obs,CONFIG)
    first=paths.timestamp.min()
    paths.loc[paths.timestamp.eq(first),"full_mfe"]=999
    context=support_context(obs,paths,CONFIG)
    assert context.loc[context.timestamp.eq(first),"prior_successful_visits"].eq(0).all()


def test_time_to_favorable_excursion_is_undefined_without_a_positive_excursion():
    obs=observations()
    obs['high']=obs['open']
    paths=rebound_paths(obs,CONFIG)
    assert paths.full_mfe.eq(0).all() and paths.time_to_mfe.isna().all()


def test_missing_exports_and_registry_validation(tmp_path):
    assert export_exp004(tmp_path)["status"]=="missing"
    assert export_diagnosis(tmp_path)["status"]=="missing"
    assert hypothesis_registry(tmp_path)==[]
    (tmp_path/"config").mkdir()
    (tmp_path/"config/hypotheses.json").write_text('[{"id":"H1"}]')
    with pytest.raises(ValueError,match="Invalid hypothesis"):
        hypothesis_registry(tmp_path)


def test_corrupt_diagnosis_export_refuses_modified_numbers(tmp_path):
    p=tmp_path/"results/research_diagnosis";p.mkdir(parents=True)
    (p/"metadata.json").write_text(json.dumps({"artifact_sha256":{"groups.csv":"wrong"}}))
    (p/"groups.csv").write_text("mean\n1\n")
    with pytest.raises(ValueError,match="changed"):
        export_diagnosis(tmp_path)


def test_exp004_adapter_uses_verified_statistics_and_labels_dollar_scale(tmp_path):
    from hashlib import sha256
    directory=tmp_path/'results/exp_004';directory.mkdir(parents=True)
    frame=pd.DataFrame([dict(policy='v1_control',mode='independent',expected_value=-.003),
                        dict(policy='training_selected',mode='independent',expected_value=.005),
                        dict(policy='time_only',mode='independent',expected_value=.007)])
    hashes={}
    for name in ('aggregate_summary','fold_summary'):
        path=directory/(name+'.csv');frame.to_csv(path,index=False)
        hashes[path.name]=sha256(path.read_bytes()).hexdigest()
    (directory/'metadata.json').write_text(json.dumps({'artifact_sha256':hashes}))
    result=export_exp004(tmp_path)
    assert result['tables']['aggregate_summary'][0]['expected_value']==-.003
    assert result['tables']['aggregate_summary'][0]['expected_dollars_per_1000']==-3.
    score={r['metric']:r for r in result['tables']['scorecard']}
    assert score['Net EV']['difference']==pytest.approx(.008)
    assert score['Positive folds']['v1_control']=='0/1'
    assert score['Positive folds']['training_selected']=='1/1'
    (directory/'fold_summary.csv').write_text('expected_value\n999\n')
    with pytest.raises(ValueError,match='changed'): export_exp004(tmp_path)


def test_hypothesis_registry_is_unique_ranked_and_not_a_strategy():
    root=Path(__file__).resolve().parents[1]
    rows=hypothesis_registry(root)
    assert len(rows)==10 and len({r['id'] for r in rows})==10
    assert [r['rank'] for r in rows]==list(range(1,11))
    assert rows[0]['id']=='H4' and rows[-1]['id']=='H1'
    assert all('future_test' in r and 'lookahead_risk' in r for r in rows)


def test_describe_uses_only_complete_outcomes_and_paired_excess():
    g=pd.DataFrame(dict(status=["completed","censored"],forward_return=[-.1,999.],mfe=[.02,999.],
                        mae=[-.2,-999.],benchmark_return=[.01,999.],excess_return=[-.11,999.]))
    r=describe(g)
    assert r["events"]==2 and r["completed"]==1
    assert r["mean"]==-.1 and r["excess"]==-.11 and r["win_rate"]==0
