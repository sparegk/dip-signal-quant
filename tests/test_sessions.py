import pytest

from src.sessions import due_sessions, session_facts, timing_classification, utc


@pytest.mark.parametrize("day", ["2026-11-26", "2026-12-25", "2026-10-03"])
def test_holidays_and_weekends_are_not_sessions(day):
    with pytest.raises(ValueError, match="Not an XNYS"):
        session_facts(day)


def test_early_close_weekend_and_dst():
    facts = session_facts("2026-11-27")
    assert utc(facts["close"]).hour == 18
    assert facts["next_session"] == "2026-11-30"
    assert utc(facts["next_open"]).hour == 14
    summer = session_facts("2026-10-30")
    assert utc(summer["close"]).hour == 20
    assert utc(summer["next_open"]).hour == 14  # DST ends between sessions
    spring = session_facts("2026-03-06")
    assert utc(spring["close"]).hour == 21
    assert utc(spring["next_open"]).hour == 13


@pytest.fixture
def timing():
    return dict(facts=session_facts("2026-10-01"), published_at="2026-10-02T12:00:00Z",
                mode="collect", effective_session="2026-10-01", clean_revision=True,
                source_times=["2026-10-02T11:00:00Z"] * 2, latest_sessions=["2026-10-01"] * 2)


@pytest.mark.parametrize("change,expected", [
    ({}, "prospective"), ({"mode": "replay"}, "retrospective"),
    ({"published_at": "2026-10-02T13:30:00Z"}, "late"),
    ({"published_at": "2026-10-02T04:14:59Z"}, "early"),
    ({"latest_sessions": ["2026-09-30", "2026-10-01"]}, "stale"),
    ({"available": False}, "unavailable"), ({"clean_revision": False}, "unverifiable"),
    ({"has_future_input": True}, "unverifiable"), ({"correction": True}, "correction"),
    ({"source_times": ["2026-10-01T19:59:00Z"] * 2}, "unverifiable"),
    ({"source_times": ["2026-10-02T12:01:00Z"] * 2}, "unverifiable"),
    ({"source_times": ["2026-10-02", "bad"]}, "unverifiable"),
    ({"source_times": []}, "unverifiable"),
    ({"effective_session": "2026-10-02"}, "retrospective")])
def test_timing_gate(timing, change, expected):
    assert timing_classification(**(timing | change)) == expected


def test_due_sessions_distinguish_missing_runs():
    assert due_sessions("2026-10-01", "2026-10-02T13:29:59Z") == []
    assert due_sessions("2026-10-01", "2026-10-02T13:30:00Z") == ["2026-10-01"]
    assert due_sessions("2026-10-01", "2026-10-05T13:30:00Z") == ["2026-10-01", "2026-10-02"]


def test_naive_timestamp_is_never_assumed_utc():
    with pytest.raises(ValueError, match="timezone-aware"):
        utc("2026-10-02T12:00:00")
