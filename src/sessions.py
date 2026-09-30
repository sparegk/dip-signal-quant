"""Regular US session facts and conservative prospective publication classification."""

from datetime import datetime, timezone

import exchange_calendars as xcals
import pandas as pd


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc(value: str) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tzinfo is None:
        raise ValueError("A real timezone-aware timestamp is required")
    return stamp.tz_convert("UTC")


def session_facts(session: str) -> dict:
    """Pinned XNYS proxy, including DST/holidays/early closes, not security halts."""
    day = pd.Timestamp(session)
    if day.tzinfo is not None or day != day.normalize() or session != day.date().isoformat():
        raise ValueError("Session must be an ISO date")
    calendar = xcals.get_calendar("XNYS", start=f"{day.year - 1}-01-01", end=f"{day.year + 1}-12-31")
    if not calendar.is_session(day):
        raise ValueError("Not an XNYS regular session")
    following = calendar.next_session(day)
    start = (day + pd.Timedelta(days=1, minutes=15)).tz_localize("America/New_York")
    return {"session": session, "calendar": "XNYS", "calendar_version": xcals.__version__,
            "close": calendar.session_close(day).isoformat(),
            "collection_start": start.tz_convert("UTC").isoformat(),
            "next_session": following.date().isoformat(),
            "next_open": calendar.session_open(following).isoformat()}


def timing_classification(*, facts: dict, published_at: str, mode: str, effective_session: str,
                          clean_revision: bool, source_times: list[str], latest_sessions: list[str],
                          has_future_input: bool = False, available: bool = True,
                          correction: bool = False) -> str:
    """Classify only after original signal bytes are durably published.

    Corrections remain separate and never enlarge the original prospective cohort.
    A prospective non-event is as important as an event; readiness is not a clock.
    """
    if mode not in {"collect", "replay"}:
        raise ValueError("Unknown collection mode")
    now = utc(published_at)
    if correction:
        return "correction"
    if mode == "replay" or facts["session"] < effective_session:
        return "retrospective"
    if not available:
        return "unavailable"
    if not clean_revision:
        return "unverifiable"
    if len(latest_sessions) != 2 or any(day != facts["session"] for day in latest_sessions):
        return "stale"
    if now >= utc(facts["next_open"]):
        return "late"
    if now < utc(facts["collection_start"]):
        return "early"
    if has_future_input or len(source_times) != 2:
        return "unverifiable"
    try:
        times = [utc(stamp) for stamp in source_times]
    except (TypeError, ValueError):
        return "unverifiable"
    if any(stamp < utc(facts["close"]) or stamp > now for stamp in times):
        return "unverifiable"
    return "prospective"


def due_sessions(start: str, as_of: str) -> list[str]:
    """Expected signal sessions whose next regular-open deadlines have passed."""
    now = utc(as_of)
    if now.date().isoformat() < start:
        return []
    calendar = xcals.get_calendar("XNYS", start=start, end=f"{now.year + 1}-12-31")
    days = calendar.sessions_in_range(start, now.tz_localize(None).normalize())
    return [day.date().isoformat() for day in days if calendar.session_open(calendar.next_session(day)) <= now]
