"""Deterministic static selection and dated signal eligibility, never price filling."""

from collections.abc import Iterable

import pandas as pd

from src.data import normalize_ticker


def static_universe(tickers: Iterable[str]) -> tuple[str, ...]:
    """Validate unique symbols and return canonical alphabetical order."""
    if isinstance(tickers, str):
        raise ValueError("Supply a collection of tickers, not one string")
    symbols = tuple(normalize_ticker(ticker) for ticker in tickers)
    if not symbols or len(set(symbols)) != len(symbols):
        raise ValueError("Universe must be nonempty without duplicate symbols")
    return tuple(sorted(symbols))


def select_universe(tickers: Iterable[str], *, exclude: Iterable[str] = ()) -> tuple[str, ...]:
    """Select all non-excluded symbols without ranking, sampling or replacement."""
    symbols = static_universe(tickers)
    if isinstance(exclude, str):
        raise ValueError("Exclusions must be a collection")
    excluded = {normalize_ticker(ticker) for ticker in exclude}
    return static_universe(ticker for ticker in symbols if ticker not in excluded)


def validate_membership(intervals: pd.DataFrame) -> pd.DataFrame:
    """Canonical disjoint [start_date, end_date) intervals; null end is unbounded.

    Format support does not certify point-in-time provenance. Dates can be ISO
    strings or naive midnight timestamps. Re-entry is allowed; overlap is not.
    """
    columns = ["ticker", "start_date", "end_date"]
    if (not isinstance(intervals, pd.DataFrame) or not intervals.columns.is_unique
            or not set(columns).issubset(intervals) or intervals.empty):
        raise ValueError("Membership requires ticker/start_date/end_date rows")
    result = intervals[columns].copy()
    result["ticker"] = result.ticker.map(normalize_ticker)
    for column in columns[1:]:
        if pd.api.types.is_numeric_dtype(result[column]) and result[column].notna().any():
            raise ValueError("Numeric membership dates are ambiguous")
        result[column] = pd.to_datetime(result[column], errors="raise")
        if (not pd.api.types.is_datetime64_dtype(result[column])
                or not result[column].dropna().eq(result[column].dropna().dt.normalize()).all()):
            raise ValueError("Membership dates must be naive midnight sessions")
    if result.start_date.isna().any() or (result.end_date <= result.start_date).any():
        raise ValueError("Membership needs a start strictly before its optional end")
    result = result.sort_values(["ticker", "start_date"]).reset_index(drop=True)
    for _, group in result.groupby("ticker"):
        if (group.end_date.iloc[:-1].isna().any()
                or (group.start_date.iloc[1:].to_numpy() < group.end_date.iloc[:-1].to_numpy()).any()):
            raise ValueError("Membership intervals overlap")
    return result


def membership_mask(observations: pd.DataFrame, universe: Iterable[str] | pd.DataFrame) -> pd.Series:
    """Eligibility at signal date only; retain full histories for feature/outcome paths."""
    if (not observations.columns.is_unique or not {"ticker", "timestamp"}.issubset(observations)
            or not pd.api.types.is_datetime64_dtype(observations.timestamp)
            or observations.timestamp.isna().any()
            or not observations.timestamp.eq(observations.timestamp.dt.normalize()).all()):
        raise ValueError("Observations require valid ticker and naive session date")
    symbols = observations.ticker.map(normalize_ticker)
    if not isinstance(universe, pd.DataFrame):
        return symbols.isin(static_universe(universe))
    intervals = validate_membership(universe)
    mask = pd.Series(False, index=observations.index)
    for interval in intervals.itertuples():
        mask |= (symbols.eq(interval.ticker) & observations.timestamp.ge(interval.start_date)
                 & (True if pd.isna(interval.end_date) else observations.timestamp.lt(interval.end_date)))
    return mask
