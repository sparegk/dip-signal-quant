"""Post-signal research outcomes, not a broker or allocated portfolio simulator.

Never import these outputs into feature/signal creation. Entry is the next
same-ticker observed open. See docs/BACKTESTING.md for censoring and fill rules.
"""

from collections.abc import Iterable
from copy import deepcopy
from numbers import Integral, Real

import numpy as np
import pandas as pd

from src.data import validate_data


HORIZONS = (1, 3, 5, 10, 20)
SPLITS = ("research", "validation", "test")
IDENTITY = ("timestamp", "ticker", "dip_component_count", "split")


def _positive_integer(value: int, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _rate(value: float, name: str, *, positive: bool = False) -> float:
    if (isinstance(value, (bool, np.bool_)) or not isinstance(value, Real)
            or not np.isfinite(value) or not 0 <= value < 1 or (positive and value == 0)):
        raise ValueError(f"{name} must be finite and {'0 <' if positive else '0 <='} value < 1")
    return float(value)


def _session(value: str | pd.Timestamp, name: str) -> pd.Timestamp:
    if not isinstance(value, (str, pd.Timestamp)):
        raise ValueError(f"{name} must be a session date")
    result = pd.Timestamp(value)
    if pd.isna(result) or result.tz is not None or result != result.normalize():
        raise ValueError(f"{name} must be a timezone-naive midnight session date")
    return result


def assign_research_splits(
    data: pd.DataFrame, *, validation_start: str | pd.Timestamp | None = None,
    test_start: str | pd.Timestamp | None = None,
    research_fraction: float = .6, validation_fraction: float = .2,
) -> pd.DataFrame:
    """Copy bars and assign common chronological, left-inclusive date partitions.

    Default cut points use floor(N*.6) and floor(N*.8) on the sorted UNION of
    observed session dates, never row counts or event outcomes. Freeze the dates
    for repeat experiments; deriving again after appending dates changes the cuts.
    """
    validate_data(data)
    if "split" in data:
        raise ValueError("Refusing to overwrite split")
    research = _rate(research_fraction, "research_fraction", positive=True)
    validation = _rate(validation_fraction, "validation_fraction", positive=True)
    if research + validation >= 1:
        raise ValueError("Research and validation fractions must leave a test period")
    dates = pd.DatetimeIndex(data.timestamp.unique())
    if (validation_start is None) != (test_start is None):
        raise ValueError("Supply both split boundaries or neither")
    if validation_start is None:
        a, b = int(len(dates) * research), int(len(dates) * (research + validation))
        if not 0 < a < b < len(dates):
            raise ValueError("Not enough dates for three nonempty splits")
        validation_start, test_start = dates[a], dates[b]
    first = _session(validation_start, "validation_start")
    second = _session(test_start, "test_start")
    if not dates[0] < first < second <= dates[-1]:
        raise ValueError("Split boundaries must be ordered inside the data range")
    result = data.reset_index(drop=True).copy()
    result["split"] = np.where(result.timestamp < first, "research",
                               np.where(result.timestamp < second, "validation", "test"))
    if result["split"].nunique() != 3:
        raise ValueError("Each split must contain observations")
    result.attrs = deepcopy(data.attrs)
    result.attrs["research_splits"] = {
        "validation_start": first.date().isoformat(), "test_start": second.date().isoformat(),
        "assignment": "signal_date", "outcome_boundary": "full_window_same_split",
    }
    return result


def _prepare(data: pd.DataFrame) -> pd.DataFrame:
    validate_data(data)
    for column in ("dip_event_v1", "dip_condition_v1", "dip_ready_v1"):
        if (column not in data or not pd.api.types.is_bool_dtype(data[column].dtype)
                or data[column].isna().any()):
            raise ValueError(f"{column} must be boolean without missing values")
    if ((data.dip_event_v1 & ~data.dip_condition_v1)
            | (data.dip_condition_v1 & ~data.dip_ready_v1)).any():
        raise ValueError("Events require a ready condition")
    if ("dip_component_count" not in data
            or not pd.api.types.is_integer_dtype(data.dip_component_count.dtype)
            or pd.api.types.is_bool_dtype(data.dip_component_count.dtype)
            or data.dip_component_count.isna().any()
            or not data.dip_component_count.between(0, 4).all()):
        raise ValueError("dip_component_count must contain integers in [0, 4]")
    result = data.reset_index(drop=True).copy()
    if "split" not in result:
        result["split"] = "all"
    else:
        if result["split"].isna().any() or not result["split"].isin(SPLITS).all():
            raise ValueError("Invalid research split labels")
        if result.groupby("timestamp")["split"].nunique().gt(1).any():
            raise ValueError("All tickers must share split boundaries")
        ranks = result["split"].map(dict(zip(SPLITS, range(3))))
        if not ranks.is_monotonic_increasing:
            raise ValueError("Research splits must be chronological")
    return result


def extract_events(data: pd.DataFrame) -> pd.DataFrame:
    """Return a separate identity/count/split table without changing signals."""
    base = _prepare(data)
    result = base.loc[base.dip_event_v1, list(IDENTITY)].reset_index(drop=True)
    result.attrs = deepcopy(data.attrs)
    return result


def _window_status(group: pd.DataFrame, signal: int, horizon: int) -> str:
    if signal + 1 >= len(group):
        return "no_next_bar"
    if signal + horizon >= len(group):
        return "incomplete_window"
    if group["split"].iloc[signal] != group["split"].iloc[signal + horizon]:
        return "split_boundary"
    return "completed"


def _frame(rows: list[dict], columns: tuple[str, ...], source: pd.DataFrame, **params) -> pd.DataFrame:
    result = pd.DataFrame(rows, columns=columns)
    for column in columns:
        if column.endswith("timestamp"):
            result[column] = pd.to_datetime(result[column]).astype("datetime64[ns]")
    result = result.sort_values(["timestamp", "ticker"] + (["horizon"] if "horizon" in result else [])).reset_index(drop=True)
    result.attrs = deepcopy(source.attrs)
    result.attrs["evaluation_parameters"] = params
    numeric = result.select_dtypes("number")
    if np.isinf(numeric.to_numpy(dtype=float)).any():
        raise ValueError("Numerical overflow in outcome calculation")
    return result


def compute_forward_outcomes(
    data: pd.DataFrame, *, horizons: Iterable[int] = HORIZONS,
    selection: str = "events", benchmark: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Long-form gross open-to-close outcomes; entry bar counts as horizon bar 1.

    MFE=max(high[entry:end])/entry_open-1; MAE=min(low[entry:end])/entry_open-1.
    Both include the entry and endpoint bars. Missing complete windows are audited,
    not shortened. Benchmark return uses its open/close on the EXACT stock endpoints.
    'eligible' is unconditional ready rows; 'non_signal' is ready AND not condition.
    """
    sizes = tuple(sorted(set(_positive_integer(n, "horizon") for n in horizons)))
    if not sizes:
        raise ValueError("At least one horizon is required")
    if selection not in ("events", "eligible", "non_signal"):
        raise ValueError("selection must be events, eligible, or non_signal")
    base = _prepare(data)
    reference = None
    if benchmark is not None:
        validate_data(benchmark)
        if benchmark.ticker.nunique() != 1:
            raise ValueError("benchmark must contain exactly one ticker")
        reference = benchmark.set_index("timestamp")
    rows = []
    for _, group in base.groupby("ticker", sort=False, observed=True):
        group = group.reset_index(drop=True)
        mask = (group.dip_event_v1 if selection == "events" else group.dip_ready_v1
                if selection == "eligible" else group.dip_ready_v1 & ~group.dip_condition_v1)
        for i in np.flatnonzero(mask.to_numpy(dtype=bool)):
            identity = group.loc[i, list(IDENTITY)].to_dict()
            for n in sizes:
                row = dict(identity, horizon=n, selection=selection,
                           status=_window_status(group, i, n), entry_timestamp=pd.NaT,
                           end_timestamp=pd.NaT, entry_price=np.nan, forward_return=np.nan,
                           mfe=np.nan, mae=np.nan, benchmark_return=np.nan, excess_return=np.nan)
                if row["status"] == "completed":
                    path = group.iloc[i + 1:i + n + 1]
                    entry = float(path.open.iloc[0])
                    row.update(entry_timestamp=path.timestamp.iloc[0],
                               end_timestamp=path.timestamp.iloc[-1], entry_price=entry,
                               forward_return=float(path.close.iloc[-1]) / entry - 1,
                               mfe=float(path.high.max()) / entry - 1,
                               mae=float(path.low.min()) / entry - 1)
                    if (reference is not None and row["entry_timestamp"] in reference.index
                            and row["end_timestamp"] in reference.index):
                        value = (float(reference.loc[row["end_timestamp"], "close"])
                                 / float(reference.loc[row["entry_timestamp"], "open"]) - 1)
                        row.update(benchmark_return=value, excess_return=row["forward_return"] - value)
                rows.append(row)
    columns = (*IDENTITY, "horizon", "selection", "status", "entry_timestamp", "end_timestamp",
               "entry_price", "forward_return", "mfe", "mae", "benchmark_return", "excess_return")
    return _frame(rows, columns, data, kind="forward_outcomes", horizons=sizes, selection=selection,
                  entry="next_observed_open", entry_bar_counts_as_one=True,
                  benchmark=None if benchmark is None else str(benchmark.ticker.iloc[0]))


def apply_costs(
    entry_price: float, exit_price: float, *, commission_rate: float = 0,
    slippage_rate: float = 0,
) -> dict[str, float]:
    """Adverse per-side slippage; commission on each slipped transaction notional.

    Net = exit*(1-s)*(1-c) / (entry*(1+s)*(1+c)) - 1. Prices/returns are
    per-share and fraction units; this does not implement allocation or quantity.
    """
    commission = _rate(commission_rate, "commission_rate")
    slippage = _rate(slippage_rate, "slippage_rate")
    for price in (entry_price, exit_price):
        if (isinstance(price, (bool, np.bool_)) or not isinstance(price, Real)
                or not np.isfinite(price) or price <= 0):
            raise ValueError("Execution prices must be finite positive numbers")
    buy = float(entry_price) * (1 + slippage)
    sell = float(exit_price) * (1 - slippage)
    outlay, proceeds = buy * (1 + commission), sell * (1 - commission)
    if not np.isfinite([buy, sell, outlay, proceeds]).all() or min(outlay, proceeds) <= 0:
        raise ValueError("Numerical overflow/underflow in cost arithmetic")
    result = {"entry_fill_price": buy, "exit_fill_price": sell,
              "gross_return": float(exit_price) / float(entry_price) - 1,
              "net_return": proceeds / outlay - 1}
    if not np.isfinite(list(result.values())).all():
        raise ValueError("Numerical overflow in cost arithmetic")
    return result


def _touch(value: float, level: float, *, above: bool) -> bool:
    # Only machine-roundoff tolerance: 100 * 1.10 must be touched by a high of 110.
    tolerance = 8 * np.finfo(float).eps * max(abs(value), abs(level))
    return value >= level - tolerance if above else value <= level + tolerance


def simulate_barrier_trades(
    data: pd.DataFrame, *, take_profit: float = .10, stop_loss: float = .07,
    max_holding_bars: int = 10, ambiguity_policy: str = "conservative",
    mode: str = "independent", commission_rate: float = 0, slippage_rate: float = 0,
) -> pd.DataFrame:
    """Audit every event; simulate long next-open entry and first-hit fixed exits.

    Non-overlapping mode refuses a proposed entry on/before that ticker's prior
    exit date (no same-open recycling). Incomplete MAX windows are excluded before
    inspecting outcomes, even if a barrier would hit early. No terminal liquidation.
    Trade MFE/MAE are full-bar envelopes through an intraday exit bar, not exact
    pre-exit excursions; for open exits, only that open is included on the exit day.
    """
    if (isinstance(take_profit, (bool, np.bool_)) or not isinstance(take_profit, Real)
            or not np.isfinite(take_profit) or take_profit <= 0):
        raise ValueError("take_profit must be a finite positive fraction")
    target = float(take_profit)
    stop = _rate(stop_loss, "stop_loss", positive=True)
    holding = _positive_integer(max_holding_bars, "max_holding_bars")
    commission = _rate(commission_rate, "commission_rate")
    slippage = _rate(slippage_rate, "slippage_rate")
    if ambiguity_policy not in ("conservative", "optimistic"):
        raise ValueError("ambiguity_policy must be conservative or optimistic")
    if mode not in ("independent", "non_overlapping"):
        raise ValueError("mode must be independent or non_overlapping")
    base = _prepare(data)
    rows = []
    for _, group in base.groupby("ticker", sort=False, observed=True):
        group = group.reset_index(drop=True)
        last_exit = -1
        for i in np.flatnonzero(group.dip_event_v1.to_numpy(dtype=bool)):
            status = _window_status(group, i, holding)
            if mode == "non_overlapping" and i + 1 <= last_exit:
                status = "overlap"
            row = dict(group.loc[i, list(IDENTITY)].to_dict(), status=status,
                       entry_timestamp=pd.NaT, entry_price=np.nan, entry_fill_price=np.nan,
                       exit_timestamp=pd.NaT, exit_price=np.nan, exit_fill_price=np.nan,
                       exit_reason=None, fill_type=None, holding_bars=np.nan,
                       gross_return=np.nan, net_return=np.nan, mfe=np.nan, mae=np.nan,
                       ambiguous_bar=False, excursion_scope=None)
            if status != "completed":
                rows.append(row)
                continue
            entry_index = i + 1
            entry = float(group.open.iloc[entry_index])
            upper, lower = entry * (1 + target), entry * (1 - stop)
            if not np.isfinite([upper, lower]).all():
                raise ValueError("Numerical overflow in barrier prices")
            if not 0 < lower < entry < upper:
                raise ValueError("Barrier prices must be representably separated from entry")
            best, worst = entry, entry
            for j in range(entry_index, entry_index + holding):
                bar = group.iloc[j]
                opening = float(bar.open)
                reason, price, fill = None, np.nan, None
                ambiguous = False
                if _touch(opening, lower, above=False):
                    reason, price, fill = "stop_loss", opening, "open"
                elif _touch(opening, upper, above=True):
                    reason, price, fill = "take_profit", opening, "open"
                else:
                    tp = _touch(float(bar.high), upper, above=True)
                    sl = _touch(float(bar.low), lower, above=False)
                    ambiguous = tp and sl
                    if sl and (not tp or ambiguity_policy == "conservative"):
                        reason, price, fill = "stop_loss", lower, "barrier"
                    elif tp:
                        reason, price, fill = "take_profit", upper, "barrier"
                    elif j == entry_index + holding - 1:
                        reason, price, fill = "time_exit", float(bar.close), "close"
                best = max(best, opening if fill == "open" else float(bar.high))
                worst = min(worst, opening if fill == "open" else float(bar.low))
                if reason is not None:
                    last_exit = j
                    row.update(entry_timestamp=group.timestamp.iloc[entry_index], entry_price=entry,
                               exit_timestamp=bar.timestamp, exit_price=price, exit_reason=reason,
                               fill_type=fill, holding_bars=j - entry_index + 1,
                               mfe=best / entry - 1, mae=worst / entry - 1,
                               ambiguous_bar=ambiguous,
                               excursion_scope="through_exit_open" if fill == "open" else "through_exit_bar",
                               **apply_costs(entry, price, commission_rate=commission, slippage_rate=slippage))
                    break
            rows.append(row)
    columns = (*IDENTITY, "status", "entry_timestamp", "entry_price", "entry_fill_price",
               "exit_timestamp", "exit_price", "exit_fill_price", "exit_reason", "fill_type",
               "holding_bars", "gross_return", "net_return", "mfe", "mae", "ambiguous_bar", "excursion_scope")
    return _frame(rows, columns, data, kind="barrier_trades", take_profit=target, stop_loss=stop,
                  max_holding_bars=holding, ambiguity_policy=ambiguity_policy, mode=mode,
                  commission_rate=commission, slippage_rate=slippage,
                  entry="next_observed_open", barriers="un-slipped_entry_open")
