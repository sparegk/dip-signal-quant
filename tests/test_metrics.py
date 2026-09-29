"""Hand-computable descriptive metrics and deterministic bootstrap checks."""

import numpy as np
import pandas as pd
import pytest

from src import metrics


def trades(returns=(.10, -.05, 0, .20)):
    n = len(returns)
    dates = pd.bdate_range("2024-01-01", periods=2 * n)
    return pd.DataFrame({
        "ticker": ["AAPL"] * n, "status": ["completed"] * n,
        "entry_timestamp": dates[::2], "exit_timestamp": dates[1::2],
        "net_return": list(returns), "gross_return": list(returns),
        "mfe": [.25] * n, "mae": [-.1] * n, "holding_bars": [2] * n,
        "exit_reason": ["take_profit", "stop_loss", "time_exit", "take_profit"][:n],
    })


def test_return_summary_exact_moments_nan_accounting_and_expectancy():
    result = metrics.summarize_returns([.1, -.05, 0, .2, np.nan])
    assert result["count"] == 4
    assert result["missing_count"] == 1
    assert result["mean"] == pytest.approx(.0625)
    assert result["median"] == pytest.approx(.05)
    assert result["std"] == pytest.approx(np.std([.1, -.05, 0, .2], ddof=1))
    assert result["win_rate"] == .5
    assert result["expectancy"] == result["mean"]
    assert result["profit_factor"] == pytest.approx(6)


def test_cluster_block_bootstrap_matches_manual_resampling_with_unequal_date_counts():
    values = np.array([.1, .2, -.1, .05, -.2, .3, .4, -.1])
    dates = pd.DatetimeIndex(["2024-01-01"] + ["2024-01-02"] * 3
                             + ["2024-01-03"] * 2 + ["2024-01-04"] * 2)
    result = metrics.summarize_returns(values, dates=dates, block_size=2, n_bootstrap=8, seed=7)
    rng = np.random.default_rng(7)
    starts = rng.integers(0, 4, size=(8, 2))
    indices = ((starts[:, :, None] + np.arange(2)) % 4).reshape(8, 4)
    sums = np.array([.1, .15, .1, .3])
    counts = np.array([1, 3, 2, 2])
    means = sums[indices].sum(axis=1) / counts[indices].sum(axis=1)
    assert result["standard_error"] == pytest.approx(means.std(ddof=1))
    assert result["ci_lower"] == pytest.approx(np.quantile(means, .025))
    assert result["ci_upper"] == pytest.approx(np.quantile(means, .975))
    assert result["cluster_count"] == 4
    assert result == metrics.summarize_returns(values, dates=dates, block_size=2, n_bootstrap=8, seed=7)


def test_bootstrap_seed_is_reproducible_and_not_global_state():
    values = np.arange(90) / 1000 - .04
    one = metrics.summarize_returns(values, block_size=5, seed=17, n_bootstrap=300)
    metrics.summarize_returns(values, seed=999, n_bootstrap=10)
    two = metrics.summarize_returns(values, block_size=5, seed=17, n_bootstrap=300)
    assert one == two
    different = metrics.summarize_returns(values, block_size=5, seed=18, n_bootstrap=300)
    assert one["standard_error"] != different["standard_error"]


@pytest.mark.parametrize("values", [[], [np.nan], [.1]])
def test_empty_or_short_samples_have_explicit_undefined_uncertainty(values):
    result = metrics.summarize_returns(values)
    assert np.isnan(result["standard_error"])
    assert np.isnan(result["ci_lower"])
    assert np.isnan(result["std"])
    assert np.isnan(result["profit_factor"])


def test_inadequate_date_blocks_do_not_fabricate_confidence():
    result = metrics.summarize_returns(np.arange(39) / 100, block_size=20)
    assert result["count"] == 39
    assert np.isnan(result["ci_upper"])
    constant = metrics.summarize_returns([.1] * 20)
    assert constant["standard_error"] == pytest.approx(0, abs=1e-15)
    assert constant["ci_lower"] == pytest.approx(.1)
    assert constant["ci_upper"] == pytest.approx(.1)


@pytest.mark.parametrize("kwargs", [
    {"confidence": 0}, {"confidence": 1}, {"confidence": np.nan}, {"confidence": True},
    {"n_bootstrap": 1}, {"n_bootstrap": 2.5}, {"block_size": 0}, {"block_size": True},
    {"seed": -1}, {"seed": True},
])
def test_invalid_uncertainty_configuration(kwargs):
    with pytest.raises(ValueError):
        metrics.summarize_returns([.1, .2], **kwargs)


@pytest.mark.parametrize("values", [[np.inf], [-np.inf], [True], [".1"], [1j]])
def test_malformed_returns_rejected(values):
    with pytest.raises(ValueError):
        metrics.summarize_returns(values)


@pytest.mark.parametrize("dates", [
    ["2024-01-01", "2024-01-02"], pd.to_datetime(["2024-01-02", "2024-01-01"]),
    pd.to_datetime(["2024-01-01", None]), pd.date_range("2024-01-01", periods=2, tz="UTC"),
    pd.to_datetime(["2024-01-01"]), pd.to_datetime(["2024-01-01 12:00", "2024-01-02 12:00"]),
])
def test_invalid_bootstrap_date_alignment(dates):
    with pytest.raises(ValueError):
        metrics.summarize_returns([.1, .2], dates=dates)


def test_regular_period_sharpe_and_sortino_exact_definitions():
    values = [.1, -.05, 0, .2]
    result = metrics.risk_adjusted_metrics(values, periods_per_year=1)
    assert result["sharpe"] == pytest.approx(.0625 / np.std(values, ddof=1))
    assert result["sortino"] == pytest.approx(.0625 / .025)
    annual = metrics.risk_adjusted_metrics(values, periods_per_year=252)
    assert annual["sharpe"] == pytest.approx(result["sharpe"] * np.sqrt(252))
    changed = metrics.risk_adjusted_metrics(values, periods_per_year=1,
                                           risk_free_per_period=.01, target_per_period=.02)
    assert changed["sharpe"] == pytest.approx(.0525 / np.std(values, ddof=1))
    assert changed["sortino"] == pytest.approx(.0425 / np.sqrt((.07**2 + .02**2) / 4))


def test_risk_ratios_undefined_for_short_flat_or_no_downside_samples():
    assert np.isnan(metrics.risk_adjusted_metrics([])["sharpe"])
    assert np.isnan(metrics.risk_adjusted_metrics([.1])["sortino"])
    assert np.isnan(metrics.risk_adjusted_metrics([0, 0])["sharpe"])
    assert np.isnan(metrics.risk_adjusted_metrics([.1, .2])["sortino"])
    for values in ([np.nan, .1], [-1.1, .1]):
        with pytest.raises(ValueError):
            metrics.risk_adjusted_metrics(values)


@pytest.mark.parametrize("kwargs", [{"periods_per_year": 0}, {"periods_per_year": True},
                                   {"risk_free_per_period": np.inf}, {"target_per_period": "0"}])
def test_risk_ratio_configuration(kwargs):
    with pytest.raises(ValueError):
        metrics.risk_adjusted_metrics([.1, -.1], **kwargs)


def test_sequential_compounding_and_initial_wealth_drawdown():
    result = metrics.sequential_return_metrics([.1, -.05, 0, .2])
    assert result["cumulative_return"] == pytest.approx(1.1 * .95 * 1.2 - 1)
    assert result["maximum_drawdown"] == pytest.approx(-.05)
    first_loss = metrics.sequential_return_metrics([-.2, .25])
    assert first_loss["maximum_drawdown"] == pytest.approx(-.2)
    assert first_loss["cumulative_return"] == pytest.approx(0)
    assert np.isnan(metrics.sequential_return_metrics([])["maximum_drawdown"])
    for values in ([np.nan], [-1], [-1.1]):
        with pytest.raises(ValueError):
            metrics.sequential_return_metrics(values)


def test_trade_summary_rates_and_no_fictitious_portfolio_metrics():
    result = metrics.trade_metrics(trades())
    assert result["trade_count"] == result["candidate_count"] == 4
    assert result["excluded_count"] == 0
    assert result["win_rate"] == .5
    assert result["average_return"] == result["expectancy"] == pytest.approx(.0625)
    assert result["median_return"] == pytest.approx(.05)
    assert result["take_profit_rate"] == .5
    assert result["stop_loss_rate"] == result["time_exit_rate"] == .25
    assert result["profit_factor"] == pytest.approx(6)
    assert result["average_holding_bars"] == 2
    assert result["average_mfe"] == .25
    assert result["average_mae"] == -.1
    for name in ("cumulative_return", "maximum_drawdown", "sharpe", "sortino"):
        assert np.isnan(result[name])
    sequential = metrics.trade_metrics(trades(), sequential=True)
    assert sequential["cumulative_return"] == pytest.approx(.254)
    assert sequential["maximum_drawdown"] == pytest.approx(-.05)
    assert np.isnan(sequential["sharpe"])  # Still no regular-period equity curve.


def test_trade_summary_reports_censored_and_skipped_rows():
    data = trades()
    data.loc[1, "status"] = "overlap"
    data.loc[1, ["gross_return", "net_return", "mfe", "mae", "holding_bars"]] = np.nan
    result = metrics.trade_metrics(data)
    assert result["candidate_count"] == 4
    assert result["trade_count"] == 3
    assert result["excluded_count"] == 1
    assert result["average_return"] == pytest.approx(.1)
    assert np.isnan(result["profit_factor"])
    empty = metrics.trade_metrics(data.iloc[:0])
    assert empty["trade_count"] == 0
    assert np.isnan(empty["win_rate"])


@pytest.mark.parametrize("kind", ["multiple", "overlap", "unsorted", "backwards", "missing_date"])
def test_sequential_metrics_reject_nonsequential_trades(kind):
    data = trades()
    if kind == "multiple": data.loc[1, "ticker"] = "MSFT"
    elif kind == "overlap": data.loc[1, "entry_timestamp"] = data.exit_timestamp.iloc[0]
    elif kind == "unsorted": data = data.iloc[::-1]
    elif kind == "backwards": data.loc[1, "exit_timestamp"] = data.entry_timestamp.iloc[0]
    else: data.loc[1, "entry_timestamp"] = pd.NaT
    with pytest.raises(ValueError):
        metrics.trade_metrics(data, sequential=True)


@pytest.mark.parametrize("column,value", [("net_return", np.nan), ("net_return", np.inf),
                                         ("holding_bars", 0), ("mfe", -.1), ("mae", .1),
                                         ("status", "made_up"), ("exit_reason", "profit")])
def test_bad_completed_trade_metrics_fail(column, value):
    data = trades()
    data.loc[0, column] = value
    with pytest.raises(ValueError):
        metrics.trade_metrics(data)


def test_grouped_outcomes_paired_baselines_counts_and_components():
    data = pd.DataFrame({
        "timestamp": pd.bdate_range("2024-01-01", periods=4),
        "split": ["research"] * 4, "horizon": [5] * 4,
        "dip_component_count": [3, 3, 4, 4],
        "status": ["completed", "completed", "completed", "incomplete_window"],
        "forward_return": [.1, -.1, .3, np.nan], "benchmark_return": [.05, np.nan, .1, np.nan],
        "mfe": [.2, .1, .3, np.nan], "mae": [-.1, -.2, -.1, np.nan],
    })
    result = metrics.summarize_outcomes(data, block_size=1, n_bootstrap=20).iloc[0]
    assert result["count"] == 3
    assert result.observations == 4
    assert result.excluded == 1
    assert result.benchmark_count == 2
    assert result.paired_stock_mean == pytest.approx(.2)
    assert result.benchmark_mean == pytest.approx(.075)
    assert result.mean_excess_return == pytest.approx(.125)
    groups = metrics.summarize_outcomes(data, group_by=("split", "horizon", "dip_component_count"))
    assert groups["count"].tolist() == [2, 1]
    assert np.isnan(groups.ci_lower).all()  # Too few date blocks, honestly undefined.


@pytest.mark.parametrize("column,value", [("forward_return", np.nan), ("benchmark_return", np.inf),
                                         ("status", "fabricated")])
def test_invalid_completed_outcomes_rejected(column, value):
    data = pd.DataFrame({"split": ["test"], "horizon": [5], "timestamp": pd.to_datetime(["2024-01-01"]),
                         "status": ["completed"], "forward_return": [.1], "mfe": [.2],
                         "mae": [-.1], "benchmark_return": [.05]})
    data.loc[0, column] = value
    with pytest.raises(ValueError):
        metrics.summarize_outcomes(data)
