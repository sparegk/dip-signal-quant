"""Observe rejected provider rows without repairing them or changing ingestion rules."""

from io import BytesIO

import numpy as np
import pandas as pd

from src.data import PROVENANCE_KEY, clean_data, normalize_ticker
from src.preservation import get_object, put_object


def preserve_raw(root, raw: pd.DataFrame) -> dict:
    """Preserve every returned row/index/value and provider attrs BEFORE validation."""
    buffer = BytesIO()
    raw.to_parquet(buffer, index=True)
    return {"raw_sha256": put_object(root, buffer.getvalue()),
            "provenance": raw.attrs.get(PROVENANCE_KEY, {}), "rows": len(raw)}


def restore_raw(root, snapshot: dict) -> pd.DataFrame:
    return pd.read_parquet(BytesIO(get_object(root, snapshot["raw_sha256"])))


def audit_ohlc(raw: pd.DataFrame, ticker: str, *, vintage: str) -> tuple[dict, pd.DataFrame]:
    """Measure exact failed inequalities on unmodified single-symbol daily responses.

    This diagnostic supports the downloader's flat-column/DatetimeIndex contract;
    unsupported schemas are explicit, never normalized into apparently good rows.
    Strict ingestion is independently exercised to record its actual verdict.
    """
    ticker = normalize_ticker(ticker)
    if vintage not in {"original_rejected", "new_diagnostic"}:
        raise ValueError("Unknown diagnostic vintage")
    error = None
    try:
        clean_data(raw, ticker)
    except (ValueError, TypeError) as failure:
        error = str(failure)
    summary = {"ticker": ticker, "vintage": vintage, "rows": len(raw), "validation_error": error}
    if (not raw.columns.is_unique or isinstance(raw.columns, pd.MultiIndex)
            or not isinstance(raw.index, pd.DatetimeIndex)
            or not {"Open", "High", "Low", "Close"}.issubset(raw.columns)):
        return summary | {"diagnostic_status": "unsupported_schema"}, pd.DataFrame()
    values = raw[["Open", "High", "Low", "Close"]].apply(pd.to_numeric, errors="coerce")
    rows = []
    for position, (session, row) in enumerate(values.iterrows()):
        prices = {key.lower(): float(value) if pd.notna(value) and np.isfinite(value) else None
                  for key, value in row.items()}
        base = {"ticker": ticker, "row_position": position, "session": session.isoformat(), **prices}
        for column, value in prices.items():
            if value is None or value <= 0:
                rows.append(base | {"rule": "invalid_" + column, "absolute_gap": None,
                                    "relative_gap": None, "spacing_units": None})
        for rule, larger, smaller in (("low_gt_high", "low", "high"),
                                      ("open_lt_low", "low", "open"),
                                      ("open_gt_high", "open", "high"),
                                      ("close_lt_low", "low", "close"),
                                      ("close_gt_high", "close", "high")):
            a, b = prices[larger], prices[smaller]
            if a is not None and b is not None and a > b:
                gap, scale = a - b, max(abs(a), abs(b))
                rows.append(base | {"rule": rule, "absolute_gap": gap,
                                    "relative_gap": gap / scale,
                                    "spacing_units": gap / float(np.spacing(scale))})
    findings = pd.DataFrame(rows, columns=["ticker", "row_position", "session", "open", "high", "low",
                                         "close", "rule", "absolute_gap", "relative_gap", "spacing_units"])
    affected = findings.row_position.nunique()
    summary.update(diagnostic_status="measured", affected_rows=int(affected),
                   affected_fraction=affected / len(raw) if len(raw) else None,
                   violations=len(findings), first_affected=findings.session.min() if affected else None,
                   last_affected=findings.session.max() if affected else None,
                   rules=sorted(findings.rule.unique()))
    for column in ("absolute_gap", "relative_gap", "spacing_units"):
        valid = findings[column].dropna()
        summary["max_" + column] = float(valid.max()) if len(valid) else None
    return summary, findings
