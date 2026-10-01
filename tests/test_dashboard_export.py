import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.build_dashboard_data import (build_dashboard, checked_bytes, comparisons,
                                         feature_catalog, history_payload)
from src.preservation import digest


def test_missing_artifacts_export_honest_empty_states_and_deterministic_generation(tmp_path, monkeypatch):
    (tmp_path/'config').mkdir()
    (tmp_path/'docs').mkdir()
    (tmp_path/'config/exp003.json').write_text(json.dumps({'effective_session':'2026-10-01','universe':['AA']}))
    monkeypatch.setattr('scripts.build_dashboard_data.load_protocol', lambda: {'effective_session':'2026-10-01','universe':['AA']})
    (tmp_path/'docs/RESEARCH_LOG.md').write_text('## 2026-10-01 - Audit\n\n- Result: mixed.\n')
    (tmp_path/'docs/EXPERIMENTS.md').write_text('## EXP-001 - Baseline\n\nNegative evidence retained.\n')
    (tmp_path/'ROADMAP.md').write_text('- [x] Foundation\n- [ ] Live scanner\n')
    monkeypatch.setattr('yfinance.download',lambda *a,**k:pytest.fail('Offline export'))
    one=build_dashboard(tmp_path,tmp_path/'one',as_of='2026-10-01T00:00:00Z')
    two=build_dashboard(tmp_path,tmp_path/'two',as_of='2026-10-01T00:00:00Z')
    assert one==two and one['ticker_files']==0
    manifest=json.loads((tmp_path/'one/manifest.json').read_bytes())
    dashboard=json.loads((tmp_path/'one'/manifest['dashboard']).read_bytes())
    assert dashboard['exp002']['status']=='missing'
    assert dashboard['archive']['prospective_count']==0 and dashboard['archive']['records']==[]
    assert dashboard['experiments'][0]['id']=='EXP-001'
    assert dashboard['roadmap'][1]['status']=='not_started'
    assert digest((tmp_path/'one'/manifest['dashboard']).read_bytes())==manifest['sha256']['dashboard.json']
    original_manifest=(tmp_path/'one/manifest.json').read_bytes()
    def interrupted_switch(*args):
        raise OSError('Simulated interrupted manifest publication')
    monkeypatch.setattr('scripts.build_dashboard_data.os.replace',interrupted_switch)
    with pytest.raises(OSError,match='interrupted manifest'):
        build_dashboard(tmp_path,tmp_path/'one',as_of='2026-10-01T01:00:00Z')
    assert (tmp_path/'one/manifest.json').read_bytes()==original_manifest
    assert not list((tmp_path/'one').glob('.manifest-*'))


def test_corrupt_inputs_fail_closed(tmp_path):
    file=tmp_path/'input.csv';file.write_bytes(b'actual')
    with pytest.raises(ValueError,match='hash mismatch'): checked_bytes(file,digest(b'other'))


def test_export_refuses_configuration_drift_before_publishing(tmp_path, monkeypatch):
    (tmp_path/'config').mkdir()
    (tmp_path/'config/exp003.json').write_text(json.dumps({'signal_parameters':{'quantile':.3}}))
    monkeypatch.setattr('scripts.build_dashboard_data.load_protocol',lambda:{'signal_parameters':{'quantile':.2}})
    with pytest.raises(ValueError,match='differs from frozen registration'):
        build_dashboard(tmp_path,tmp_path/'output',as_of='2026-10-01T00:00:00Z')
    assert not (tmp_path/'output').exists()


def test_comparison_keeps_paired_spy_excess_and_independent_baseline_differences():
    rows=[dict(selection=s,horizon=10,mean=m,mean_excess_return=.004,benchmark_mean=.009)
          for s,m in [('events',.01),('eligible',.008),('non_signal',.007)]]
    result=comparisons(pd.DataFrame(rows))[0]
    assert result['difference_unconditional']==pytest.approx(.002)
    assert result['difference_non_signal']==pytest.approx(.003)
    assert result['difference_spy']==.004  # paired result, NOT unpaired .01 - .009


def test_explorer_separates_known_information_future_outcomes_and_tickers():
    observed=pd.DataFrame({'timestamp':pd.to_datetime(['2026-01-02','2026-01-02']),
                           'ticker':['AA','BB'],'close':[10.,20.],'dip_event_v1':[True,False],
                           'dip_component_count':[3,0],'drawdown_60d_threshold':[-.2,-.3]})
    future=pd.DataFrame({'timestamp':pd.to_datetime(['2026-01-02']),'ticker':['AA'],
                         'horizon':[10],'forward_return':[.5],'status':['completed']})
    trades=pd.DataFrame(columns=['timestamp','ticker'])
    result=history_payload(observed,future,trades,'AA','EXP-002')
    assert len(result['known_at_signal']['rows'])==1
    assert 'forward_return' not in result['known_at_signal']['columns']
    assert result['future_outcomes']['2026-01-02']['horizons'][0]['forward_return']==.5
    assert result['known_at_signal']['rows'][0][result['known_at_signal']['columns'].index('split')]=='test'


def test_feature_catalog_matches_frozen_feature_families():
    catalog=feature_catalog()
    assert len(catalog)==26 and len({f['key'] for f in catalog})==26
    assert {f['key'] for f in catalog if f['used_in_v1']}=={
        'drawdown_60d','price_zscore_20d','distance_from_low_20d','relative_return_10d'}
    assert all(f['warmup'] and f['availability'] and f['formula'] for f in catalog)


def test_archive_adapter_preserves_record_status_classification_and_missing_coverage(tmp_path, monkeypatch):
    from scripts.build_dashboard_data import export_archive
    directory=tmp_path/'data/paper_archive/runs/replay'
    directory.mkdir(parents=True)
    (directory/'intent.json').touch()
    intent={'run_id':'replay','session':'2026-09-28','mode':'replay','started_at':'2026-10-01T00:00:00Z',
            'code':{'revision':'abc','dirty':True},'config_sha256':'config','corrects':None}
    result={'records':[{'ticker':'AA','status':'available','values':{'dip_event_v1':False},'error':None},
                       {'ticker':'BB','status':'unavailable','values':None,'error':'private/local/path'}],
            'inputs':{'AA':{'validated_sha256':'input','provenance':{'retrieved_at':'vintage'}},'BB':{}}}
    monkeypatch.setattr('scripts.build_dashboard_data.read_record',lambda p:intent if p.name=='intent.json' else result)
    monkeypatch.setattr('scripts.build_dashboard_data.verify_run',lambda *a:{'status':'partial','published_at':'time',
                         'classifications':{'AA':'retrospective','BB':'retrospective'}})
    monkeypatch.setattr('scripts.build_dashboard_data.coverage',lambda *a,**k:[{'session':'2026-10-01','status':'missing_run','classifications':{}}])
    export=export_archive(tmp_path,{'universe':['AA','BB']},'2026-10-02T20:00:00Z')
    assert export['records'][0]['status']=='available'
    assert export['records'][0]['run_status']=='partial'
    assert export['records'][1]['status']=='unavailable'
    assert 'private/local/path' not in json.dumps(export)
    assert export['prospective_count']==0 and export['retrospective_count']==2
    assert export['failure_count']==1 and export['non_event_count']==1
    assert export['coverage']==[{'session':'2026-10-01','status':'missing_run','prospective':0,'expected':2}]
    assert all(row['outcome'] is None for row in export['records'])
