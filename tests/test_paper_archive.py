from copy import deepcopy
import json

import numpy as np
import pandas as pd
import pytest

from src import paper_archive as archive
from src.data import PROVENANCE_KEY, save_parquet
from src.features import build_features
from src.preservation import get_object, put_object, read_record
from src.signals import build_signals


@pytest.fixture
def fixture(tmp_path):
    config = archive.load_protocol()
    config['universe'] = ['ABT', 'BMY']
    dates = pd.bdate_range(end='2026-10-01', periods=300).astype('datetime64[ns]')
    cache = tmp_path / 'cache'
    frames = {}
    for n, ticker in enumerate(['ABT', 'BMY', 'SPY']):
        prices = 100 + np.sin(np.arange(300) / 7) * (n + 1) + np.arange(300) * .03
        frame = pd.DataFrame(dict(timestamp=dates, ticker=ticker, open=prices, high=prices+1,
                                  low=prices-1, close=prices, volume=np.full(300,100,dtype=np.int64)))
        frame.attrs[PROVENANCE_KEY] = dict(schema_version=1, provider='yfinance', ticker=ticker,
            interval='1d', retrieved_at='2026-10-02T11:00:00+00:00', requested_start='2016-09-29',
            requested_end='2026-10-02', adjustment='auto_adjust=True; provider-reported volume')
        save_parquet(frame, cache / (ticker+'.parquet'))
        frames[ticker] = frame
    root = tmp_path / 'archive'
    inputs = {ticker: archive.capture_input(root, ticker, config=config, session='2026-10-01', replay_cache=cache)
              for ticker in frames}
    # Only this synthetic fixture emulates a fresh retrieval; CLI never promotes caches.
    for item in inputs.values():
        item['input_kind'] = 'new_provider_vintage'
    return root, cache, config, frames, inputs


def start(fixture, run_id='one', **kwargs):
    root, _, config, _, _ = fixture
    return archive.begin_run(root, run_id, session='2026-10-01', mode='collect', config=config,
                             code={'revision':'synthetic-test-only','dirty':False},
                             clock=lambda:'2026-10-02T10:00:00Z', **kwargs)


def finish(fixture, intent, *, times=None):
    root, _, _, _, inputs = fixture
    clock = iter(times or ['2026-10-02T12:00:00Z', '2026-10-02T12:00:01Z'])
    return archive.finish_run(root, intent, inputs, clock=lambda: next(clock))


def test_preserves_every_ticker_non_event_and_exact_frozen_decisions(fixture):
    root, _, _, frames, inputs = fixture
    intent = start(fixture)
    receipt = finish(fixture, intent)
    assert set(receipt['classifications'].values()) == {'prospective'}
    result = read_record(root/'runs/one/result.json')
    assert result['status'] == 'complete' and len(result['records']) == 2
    for row in result['records']:
        expected = build_signals(build_features(frames[row['ticker']], benchmark=frames['SPY'])).iloc[-1]
        assert row['values'] == {key: archive._scalar(expected[key]) for key in archive.DECISION_COLUMNS}
    assert archive.verify_run(root,'one',replay=True)['status'] == 'complete'
    assert archive.verify_run(root,'one',replay=True) == archive.verify_run(root,'one',replay=True)


def test_ticker_isolation(fixture):
    root, cache, _, frames, inputs = fixture
    intent = start(fixture)
    before = archive.decision_records(root,intent,inputs)
    frame = frames['BMY'].copy()
    frame[['open','high','low','close']] *= 3
    save_parquet(frame,cache/'altered.parquet')
    inputs['BMY']['validated_sha256'] = put_object(root,(cache/'altered.parquet').read_bytes())
    after = archive.decision_records(root,intent,inputs)
    assert before[0] == after[0]


@pytest.mark.parametrize('symbol,status',[('BMY','partial'),('SPY','failed')])
def test_failed_inputs_and_benchmark_are_visible(fixture,symbol,status):
    root,_,_,_,inputs=fixture
    inputs[symbol]={'ticker':symbol,'status':'unavailable','error':'provider failed'}
    intent=start(fixture)
    finish(fixture,intent)
    result=read_record(root/'runs/one/result.json')
    assert result['status']==status
    unavailable=[r for r in result['records'] if r['status']=='unavailable']
    assert unavailable and all(r['values'] is None and r['error'] for r in unavailable)


def test_missing_session_is_stale_not_actionable(fixture):
    root,cache,config,frames,inputs=fixture
    save_parquet(frames['BMY'].iloc[:-1].copy(),cache/'BMY.parquet')
    inputs['BMY']=archive.capture_input(root,'BMY',config=config,session='2026-10-01',replay_cache=cache)
    intent=start(fixture)
    receipt=finish(fixture,intent)
    assert receipt['classifications']['BMY']=='stale'
    assert read_record(root/'runs/one/result.json')['records'][1]['values'] is None


def test_actual_postpublication_clock_controls_late_status(fixture):
    intent=start(fixture)
    receipt=finish(fixture,intent,times=['2026-10-02T13:29:59Z','2026-10-02T13:30:00Z'])
    assert set(receipt['classifications'].values())=={'late'}


def test_old_cache_never_counts_as_new_provider_vintage(fixture):
    _,_,_,_,inputs=fixture
    inputs['ABT']['input_kind']='historical_cache_replay'
    receipt=finish(fixture,start(fixture))
    assert receipt['classifications']['ABT']=='unverifiable'


def test_retrieval_must_precede_calculation_not_just_publication(fixture):
    receipt=finish(fixture,start(fixture),times=['2026-10-02T10:30:00Z','2026-10-02T12:00:00Z'])
    assert set(receipt['classifications'].values())=={'unverifiable'}


def test_stable_identity_retry_conflict_and_correction(fixture):
    root,_,config,_,_=fixture
    intent=start(fixture)
    assert start(fixture)==intent
    first=finish(fixture,intent)
    with pytest.raises(ValueError,match='Result already'):
        finish(fixture,intent)
    with pytest.raises(ValueError,match='Another run'):
        start(fixture,'second')
    with pytest.raises(ValueError,match='Conflicting run identity'):
        archive.begin_run(root,'one',session='2026-10-02',mode='collect',config=config,code={})
    correction=start(fixture,'two',corrects='one',reason='New provider vintage; preserve original')
    second=finish(fixture,correction)
    assert set(second['classifications'].values())=={'correction'}
    assert archive.verify_run(root,'one')['published_at']==first['published_at']
    with pytest.raises(ValueError,match='successor'):
        start(fixture,'three',corrects='one',reason='Competing version')


def test_interrupted_intent_recovery_never_backdates(fixture):
    root,*_=fixture
    intent=start(fixture)
    assert archive.verify_run(root,'one')['status']=='interrupted'
    recovery=archive.recover_run(root,'one',clock=lambda:'2026-10-03T15:00:00Z')
    assert archive.recover_run(root,'one')==recovery
    with pytest.raises(ValueError,match='Recovered incomplete'):
        finish(fixture,intent)
    correction=start(fixture,'two',corrects='one',reason='Retry after interrupted run')
    assert set(finish(fixture,correction)['classifications'].values())=={'correction'}


def test_interruption_between_result_and_receipt_remains_ineligible(fixture,monkeypatch):
    root,*_=fixture
    intent=start(fixture)
    original=archive.write_record
    def fail(path,payload):
        if path.name=='receipt.json':
            raise OSError('interrupted')
        return original(path,payload)
    monkeypatch.setattr(archive,'write_record',fail)
    with pytest.raises(OSError):
        finish(fixture,intent)
    assert (root/'runs/one/result.json').exists()
    assert archive.verify_run(root,'one')['status']=='interrupted'
    with pytest.raises(ValueError,match='Result already'):
        finish(fixture,intent)


@pytest.mark.parametrize('target',['input','record','receipt'])
def test_integrity_failure(fixture,target):
    root,_,_,_,inputs=fixture
    finish(fixture,start(fixture))
    if target=='input':
        path=root/'objects'/inputs['ABT']['validated_sha256']
        path.write_bytes(b'corrupt')
    else:
        path=root/'runs/one'/('result.json' if target=='record' else 'receipt.json')
        path.write_bytes(path.read_bytes().replace(b'prospective',b'retrospectiv') if target=='receipt'
                         else path.read_bytes().replace(b'complete',b'partial'))
    with pytest.raises(ValueError,match='hash mismatch'):
        archive.verify_run(root,'one')


@pytest.mark.parametrize('change',['omit','duplicate','count','flag','feature','component'])
def test_archive_schema_rejects_inconsistent_records(fixture,change):
    root,_,_,_,inputs=fixture
    intent=start(fixture)
    records=archive.decision_records(root,intent,inputs)
    if change=='omit': records.pop()
    elif change=='duplicate': records.append(records[0])
    elif change=='count': records[0]['values']['dip_component_count']=99
    elif change=='flag': records[0]['values']['dip_event_v1']=1
    elif change=='feature': records[0]['values']['drawdown_60d']='bad'
    else: records[0]['values']['dip_drawdown_component']=not records[0]['values']['dip_drawdown_component']
    with pytest.raises(ValueError): archive.validate_records(intent,records)


def test_missing_runs_distinct_from_zero_event_runs(fixture):
    root,_,config,_,_=fixture
    assert archive.coverage(root,config,as_of='2026-10-02T14:00:00Z')[0]['status']=='missing_run'
    finish(fixture,start(fixture))
    rows=archive.coverage(root,config,as_of='2026-10-05T14:00:00Z')
    assert [r['status'] for r in rows]==['complete','missing_run']


def test_changed_config_rejected(tmp_path,monkeypatch):
    (tmp_path/'config').mkdir()
    (tmp_path/'config/exp003.json').write_text('{}')
    monkeypatch.setattr(archive,'ROOT',tmp_path)
    with pytest.raises(ValueError,match='configuration changed'): archive.load_protocol()


def test_raw_is_preserved_even_when_cleaning_rejects(fixture,monkeypatch):
    root,_,config,frames,_=fixture
    raw=frames['ABT'].drop(columns=['ticker']).set_index('timestamp').rename(columns=str.title)
    raw.iloc[0,raw.columns.get_loc('Close')]=999.
    monkeypatch.setattr(archive,'download_raw_data',lambda *a,**k:raw)
    item=archive.capture_input(root,'ABT',config=config,session='2026-10-01')
    assert item['status']=='unavailable' and 'Malformed OHLC' in item['error']
    assert get_object(root,item['raw_sha256'])


def test_cli_replay_is_offline_idempotent_and_preserves_original_bytes(fixture,monkeypatch):
    from scripts import archive_signals as runner
    root,cache,config,_,_=fixture
    monkeypatch.setattr(runner,'load_protocol',lambda:config)
    monkeypatch.setattr('yfinance.download',lambda *a,**k:pytest.fail('Offline replay'))
    first=runner.collect(root,session='2026-10-01',run_id='replay',replay_cache=cache)
    assert set(first['classifications'].values())=={'retrospective'}
    assert runner.collect(root,session='2026-10-01',run_id='replay',replay_cache=cache)==first
    result=read_record(root/'runs/replay/result.json')
    for ticker,item in result['inputs'].items():
        assert get_object(root,item['validated_sha256'])==(cache/(ticker+'.parquet')).read_bytes()


def test_successful_new_capture_uses_existing_api_and_preserves_raw(fixture,monkeypatch):
    root,_,config,frames,_=fixture
    raw=frames['ABT'].drop(columns=['ticker']).set_index('timestamp').rename(columns=str.title)
    calls=[]
    def download(ticker,**kwargs):
        calls.append((ticker,kwargs))
        return raw
    monkeypatch.setattr(archive,'download_raw_data',download)
    item=archive.capture_input(root,'ABT',config=config,session='2026-10-01')
    assert item['status']=='available' and item['input_kind']=='new_provider_vintage'
    assert item['raw_sha256'] and item['validated_sha256']
    assert calls==[('ABT',{'start':'2016-09-29','end':'2026-10-02'})]


def test_new_capture_rejects_future_rows_but_keeps_raw(fixture,monkeypatch):
    root,_,config,frames,_=fixture
    raw=frames['ABT'].drop(columns=['ticker']).set_index('timestamp').rename(columns=str.title)
    monkeypatch.setattr(archive,'download_raw_data',lambda *a,**k:raw)
    item=archive.capture_input(root,'ABT',config=config,session='2026-09-30')
    assert item['status']=='unavailable' and 'outside requested dates' in item['error']
    assert item['raw_sha256']


def test_future_input_in_replay_does_not_change_prefix_decision(fixture):
    root,cache,_,frames,inputs=fixture
    intent=start(fixture)
    before=archive.decision_records(root,intent,inputs)
    frame=frames['ABT'].copy()
    future=frame.iloc[[-1]].copy()
    future['timestamp']=pd.Timestamp('2026-10-02')
    future[['open','high','low','close']]*=10
    frame=pd.concat([frame,future],ignore_index=True)
    frame.attrs=frames['ABT'].attrs
    save_parquet(frame,cache/'future.parquet')
    inputs['ABT'].update(validated_sha256=put_object(root,(cache/'future.parquet').read_bytes()),
                         rows=301,latest_session='2026-10-02')
    assert archive.decision_records(root,intent,inputs)==before
    assert finish(fixture,intent)['classifications']['ABT']!='prospective'


def test_descriptor_mismatch_fails_replay(fixture):
    root,_,_,_,inputs=fixture
    inputs['ABT']['latest_session']='2026-09-30'
    with pytest.raises(ValueError,match='descriptor differs'):
        archive.decision_records(root,start(fixture),inputs)


def test_all_signal_flags_unready_are_retained(fixture):
    root,cache,config,frames,inputs=fixture
    save_parquet(frames['ABT'].iloc[-20:].copy(),cache/'ABT.parquet')
    inputs['ABT']=archive.capture_input(root,'ABT',config=config,session='2026-10-01',replay_cache=cache)
    inputs['ABT']['input_kind']='new_provider_vintage'
    receipt=finish(fixture,start(fixture))
    row=read_record(root/'runs/one/result.json')['records'][0]
    assert row['values']['dip_ready_v1'] is False and row['values']['dip_event_v1'] is False
    assert receipt['classifications']['ABT']=='prospective'


def test_backward_clock_leaves_unsealed_result(fixture):
    root,*_=fixture
    with pytest.raises(ValueError,match='Clock moved backwards'):
        finish(fixture,start(fixture),times=['2026-10-02T12:00:00Z','2026-10-02T11:59:59Z'])
    assert archive.verify_run(root,'one')['status']=='interrupted'


def test_frozen_source_guard_independent_of_configuration(tmp_path,monkeypatch):
    import shutil
    root=archive.ROOT
    (tmp_path/'config').mkdir()
    (tmp_path/'src').mkdir()
    for file in ['config/exp003.json','config/exp002.json','src/features.py','src/signals.py']:
        shutil.copyfile(root/file,tmp_path/file)
    (tmp_path/'src/signals.py').write_bytes(b'changed')
    monkeypatch.setattr(archive,'ROOT',tmp_path)
    with pytest.raises(ValueError,match='Frozen V1 source'):
        archive.load_protocol()
