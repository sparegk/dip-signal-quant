"""Hand-computable ticker diagnostics and offline EXP-002 reproducibility."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import evaluate_exp002 as runner
from src.data import PROVENANCE_KEY, save_parquet
from src.robustness import concentration, distribution, frequency_summary


def test_distribution_uses_equal_ticker_values_and_keeps_undefined_denominator():
    result = distribution([.1, -.1, .2, 0, np.nan], requested_count=6)
    assert result["defined_count"] == 4
    assert result["undefined_count"] == 2
    assert result["positive_count"] == 2 and result["negative_count"] == 1
    assert result["zero_count"] == 1
    assert result["median"] == pytest.approx(.05)
    assert result["q25"] == pytest.approx(-.025)
    assert result["q75"] == pytest.approx(.125)
    assert result["iqr"] == pytest.approx(.15)
    assert result["positive_fraction_defined"] == .5
    assert np.isnan(distribution([])["median"])
    with pytest.raises(ValueError): distribution([np.inf])
    with pytest.raises(ValueError): distribution([1, 2], requested_count=1)


def test_concentration_sums_by_ticker_without_dividing_by_cancelled_net():
    tickers = ["AA", "BB", "CC", "DD", "EE", "FF", "GG", "HH"]
    ledger = pd.DataFrame({"ticker": tickers[:7] + ["AA"], "net": [.1, .2, .3, .4, .5, .6, -2.2, .1]})
    table, result = concentration(ledger, "net", tickers)
    assert result["total_sum"] == pytest.approx(0)
    assert result["positive_sum"] == pytest.approx(2.2)
    assert result["negative_sum"] == pytest.approx(-2.2)
    assert result["top5_positive_share"] == pytest.approx(2 / 2.2)
    assert result["top5_absolute_share"] == pytest.approx(4 / 4.4)
    assert table.loc[table.ticker == "AA", "count"].iloc[0] == 2
    assert table.loc[table.ticker == "HH", "count"].iloc[0] == 0
    assert np.isnan(table.loc[table.ticker == "HH", "mean"].iloc[0])
    negative = ledger.assign(net=-.1)
    assert np.isnan(concentration(negative, "net", tickers)[1]["top5_positive_share"])
    shuffled = ledger.sample(frac=1, random_state=3)
    pd.testing.assert_frame_equal(table, concentration(shuffled, "net", tickers)[0])


def test_frequency_uses_membership_and_readiness_and_keeps_zero_event_tickers():
    frame = pd.DataFrame({"fold": ["2021"] * 5, "ticker": ["AA"] * 3 + ["BB"] * 2,
                          "timestamp": pd.bdate_range("2021-01-01", periods=5),
                          "member": [False, True, True, True, True],
                          "dip_ready_v1": [True, True, False, True, True],
                          "dip_condition_v1": [True, True, False, False, False],
                          "dip_event_v1": [True, True, False, False, False]})
    result = frequency_summary(frame)
    assert result.events.tolist() == [1, 0]
    assert result.ready.tolist() == [1, 2]
    assert result.eligible.tolist() == [2, 2]
    assert result.condition_fraction_ready.tolist() == [1, 0]
    assert result.condition_fraction_eligible.tolist() == [.5, 0]
    assert result.events_per_252_ready.tolist() == [252, 0]


@pytest.fixture
def cached_experiment(tmp_path):
    config = runner.load_config()
    config.update(source_tickers=["AA", "BB", "CC", "AAPL", "GOOG"],
                  start="2019-01-01", end_exclusive="2021-04-01", initial_history_years=1)
    cache = tmp_path / "market"
    cache.mkdir()
    for symbol in ("SPY", "AA", "BB"):
        dates = pd.bdate_range(config["start"], "2021-03-31")
        close = 100 + 12 * np.sin(np.arange(len(dates)) / (17 if symbol == "SPY" else 9))
        if symbol == "BB": close = np.full(len(dates), 100.)  # No ready z-score, explicitly excluded.
        frame = pd.DataFrame({"timestamp": dates.astype("datetime64[ns]"), "ticker": [symbol] * len(dates),
                              "open": close, "high": close + 1, "low": close - 1, "close": close,
                              "volume": np.full(len(dates), 100, dtype=np.int64)})
        frame.attrs = {PROVENANCE_KEY: {"requested_start": config["start"], "requested_end": config["end_exclusive"]}}
        save_parquet(frame, cache / f"{symbol}.parquet")
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return cache, path, config


def test_complete_offline_runner_replays_identical_artifacts(cached_experiment, tmp_path, monkeypatch):
    cache, path, config = cached_experiment
    monkeypatch.setattr("yfinance.download", lambda *a, **k: pytest.fail("Unit tests must not download"))
    first = runner.run_experiment(cache_dir=cache, config_path=path, output_dir=tmp_path / "one")
    second = runner.run_experiment(cache_dir=cache, config_path=path, output_dir=tmp_path / "two")
    assert first == second
    assert first["artifact_sha256"] == second["artifact_sha256"]
    assert first["requested_count"] == 3 and first["usable_count"] == 1
    exclusions = pd.read_csv(tmp_path / "one" / "exclusions.csv")
    assert set(exclusions.loc[exclusions.fold == "all", "reason"]) == {
        "missing_cache", "insufficient_history", "previously_inspected_issuer"}
    events = pd.read_parquet(tmp_path / "one" / "events.parquet")
    assert events.ticker.eq("AA").all()
    assert set(events.horizon) == {1, 3, 5, 10, 20}
    frequency = pd.read_csv(tmp_path / "one" / "frequency.csv")
    assert len(frequency) == 6 and frequency.loc[frequency.ticker == "CC", "observed"].eq(0).all()
    summary = pd.read_csv(tmp_path / "one" / "ticker_summary.csv")
    for row in summary.loc[summary.selection == "events"].itertuples():
        completed = events.loc[(events.horizon == row.horizon) & (events.status == "completed")]
        assert row.mean == pytest.approx(completed.forward_return.mean())
    assert first["config"]["barrier_parameters"]["commission_rate"] == .0001
    from scripts.report_exp002 import render_report
    report = render_report(tmp_path / "one")
    assert 'Requested 3; usable 1; excluded 2.' in report
    assert report == render_report(tmp_path / "two")
    artifact = tmp_path / "one" / "oos_summary.csv"
    artifact.write_bytes(artifact.read_bytes() + b'changed')
    with pytest.raises(ValueError, match="Artifact hash mismatch"):
        render_report(tmp_path / "one")


def test_cached_corruption_and_missing_benchmark_fail_explicitly(cached_experiment):
    cache, _, config = cached_experiment
    (cache / "AA.parquet").write_bytes(b"corrupt")
    with pytest.raises(Exception): runner.acquire_data(config, cache)
    with pytest.raises(FileNotFoundError): runner.acquire_data(config, cache / "missing")


def test_download_failures_are_audited_and_replayed_without_retrying(cached_experiment, monkeypatch):
    cache, _, config = cached_experiment
    original = runner.get_history
    attempts = []
    def get(ticker, **kwargs):
        if ticker == "CC":
            attempts.append(ticker)
            raise ValueError("Malformed OHLC")
        return original(ticker, **kwargs)
    monkeypatch.setattr(runner, "get_history", get)
    _, failures, _ = runner.acquire_data(config, cache, download=True)
    assert attempts == ["CC", "CC"]
    _, replay, _ = runner.acquire_data(config, cache)
    assert failures == replay
    assert attempts == ["CC", "CC"]


def test_frozen_source_guard_rejects_changes(cached_experiment):
    _, path, config = cached_experiment
    config["frozen_source_sha256"]["src/signals.py"] = "changed"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="Frozen V1 source changed"):
        runner.load_config(path)


def test_registered_benchmark_and_universe_remain_frozen():
    from src.universe import select_universe
    config = runner.load_config()
    assert config['signal_parameters'] == dict(lookback=252, min_history=126, quantile=.2, required_components=3)
    assert config['horizons'] == [1, 3, 5, 10, 20]
    assert config['barrier_parameters'] == dict(take_profit=.1, stop_loss=.07, max_holding_bars=10,
                                               ambiguity_policy='conservative', commission_rate=.0001,
                                               slippage_rate=.0005)
    assert len(config['source_tickers']) == 101
    selected = select_universe(config['source_tickers'], exclude=config['excluded_tickers'])
    assert len(selected) == 95
    assert not set(selected) & {'AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'GOOG', 'SPY'}
