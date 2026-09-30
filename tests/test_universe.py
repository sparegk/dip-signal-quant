"""Universe identity and signal-date membership, independent of market outcomes."""

import pandas as pd
import pytest

from src.universe import membership_mask, select_universe, static_universe, validate_membership


def test_static_selection_is_order_independent_and_excludes_inspected_issuers():
    names = ["MSFT", "jpm", "AAPL", "GOOG", "GOOGL", "NVDA", "AMZN", "SPY", "abT"]
    excluded = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "SPY"]
    assert select_universe(names, exclude=excluded) == ("ABT", "JPM")
    assert select_universe(reversed(names), exclude=excluded) == ("ABT", "JPM")


@pytest.mark.parametrize("symbols", [[], "ABT", ["abT", "ABT"], ["../x"], [None], [""], ["BRK B"]])
def test_invalid_static_universes(symbols):
    with pytest.raises((ValueError, TypeError)):
        static_universe(symbols)


def intervals():
    return pd.DataFrame({"ticker": ["ABT", "ABT", "JPM"],
                         "start_date": ["2020-01-02", "2020-01-06", "2020-01-01"],
                         "end_date": ["2020-01-04", None, None]})


def test_interval_edges_gaps_reentry_and_static_membership():
    observations = pd.DataFrame({"timestamp": pd.date_range("2020-01-01", periods=8),
                                 "ticker": ["ABT"] * 7 + ["ZZZ"]})
    original = observations.copy(deep=True)
    assert membership_mask(observations, intervals()).tolist() == [False, True, True, False, False, True, True, False]
    assert membership_mask(observations, ["ABT"]).tolist() == [True] * 7 + [False]
    pd.testing.assert_frame_equal(observations, original)
    pd.testing.assert_frame_equal(validate_membership(intervals()), validate_membership(intervals().iloc[::-1]))


@pytest.mark.parametrize("change", ["overlap", "open_overlap", "backwards", "missing_start", "timezone", "intraday", "numeric", "duplicate"])
def test_invalid_intervals(change):
    data = intervals()
    if change == "overlap": data.loc[0, "end_date"] = "2020-01-07"
    elif change == "open_overlap": data.loc[0, "end_date"] = None
    elif change == "backwards": data.loc[0, "end_date"] = "2020-01-01"
    elif change == "missing_start": data.loc[0, "start_date"] = None
    elif change == "timezone": data["start_date"] = pd.to_datetime(data.start_date, utc=True)
    elif change == "intraday": data.loc[0, "start_date"] = "2020-01-02 12:00"
    elif change == "numeric": data["start_date"] = [1, 2, 3]
    else: data = pd.concat([data, data.iloc[:1]])
    with pytest.raises(ValueError):
        validate_membership(data)


def test_adjacent_intervals_are_allowed_and_unknown_tickers_are_ineligible():
    data = intervals()
    data.loc[0, "end_date"] = data.loc[1, "start_date"]
    assert len(validate_membership(data)) == 3
    observations = pd.DataFrame({"timestamp": pd.to_datetime(["2020-01-03"]), "ticker": ["ZZZ"]})
    assert not membership_mask(observations, data).any()


@pytest.mark.parametrize("dates", [["2020-01-01"], pd.to_datetime([None]),
                                   pd.to_datetime(["2020-01-01 12:00"]),
                                   pd.to_datetime(["2020-01-01"], utc=True)])
def test_malformed_observation_dates(dates):
    with pytest.raises(ValueError):
        membership_mask(pd.DataFrame({"timestamp": dates, "ticker": ["ABT"]}), ["ABT"])
