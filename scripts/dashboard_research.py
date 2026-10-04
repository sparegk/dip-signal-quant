"""Small, verified dashboard adapters. No parameter selection or new trades."""

import json
from pathlib import Path

import pandas as pd

from scripts.report_exp004 import read_artifacts


def export_exp004(root: Path, research: dict | None = None) -> dict:
    directory = root / "results/exp_004"
    if not (directory / "metadata.json").exists():
        return {"status": "missing", "reason": "Preserved EXP-004 artifacts unavailable."}
    metadata, tables = read_artifacts(directory)
    names = ("aggregate_summary", "fold_summary", "selected_policy_by_fold",
             "exit_efficiency", "parameter_plateaus", "ticker_summary",
             "stop_distribution", "target_distribution", "paired_uncertainty")
    primary = ["v1_control", "training_selected", "time_only"]
    # Training candidate surfaces belong in ignored research artifacts, not the browser.
    for name in ("stop_distribution", "target_distribution"):
        frame = tables[name] if name in tables else None
        if frame is not None:
            tables[name] = frame.loc[frame.period.eq("oos") & frame.policy.eq("training_selected") & frame.ticker.eq("ALL")]
    if "ticker_summary" in tables:
        tables["ticker_summary"] = tables["ticker_summary"].loc[tables["ticker_summary"].policy.isin(primary)]
    for name in ("aggregate_summary", "fold_summary"):
        tables[name]["expected_dollars_per_1000"] = tables[name].expected_value * 1000
    scorecard = []
    metrics = [("Net EV", "expected_value", "percent"), ("Median return", "median_return", "percent"),
               ("Win rate", "win_rate", "rate"), ("Profit factor", "profit_factor", "number"),
               ("Mean loss", "average_loss", "percent"), ("MFE until exit", "average_mfe", "percent"),
               ("MAE until exit", "average_mae", "percent")]
    for mode, frame in tables["aggregate_summary"].groupby("mode", sort=True):
        by_policy = frame.set_index("policy")
        for metric, column, kind in metrics:
            values = {p: by_policy.loc[p, column] if p in by_policy.index and column in by_policy else None for p in primary}
            difference = values["training_selected"]-values["v1_control"] if all(values[p] is not None for p in ("training_selected","v1_control")) else None
            scorecard.append({"mode":mode,"metric":metric,"kind":kind,**values,"difference":difference,
                              "status":"Observed; pending prospective"})
        for metric, name in (("Positive folds","fold_summary"),("Positive tickers","ticker_summary")):
            source = tables.get(name, pd.DataFrame())
            values = {}
            for p in primary:
                x = source.loc[source["mode"].eq(mode)&source.policy.eq(p),"expected_value"].dropna() if len(source) else pd.Series(dtype=float)
                values[p] = f"{int(x.gt(0).sum())}/{len(x)}" if len(x) else None
            scorecard.append({"mode":mode,"metric":metric,"kind":"text",**values,"difference":None,"status":"Observed; dependent sample"})
        event = next((r for r in (research or {}).get("comparison",[]) if r["horizon"]==10),{})
        for metric,value,kind in (("10-bar gross event return",event.get("mean"),"percent"),
                                  ("Matched-SPY event excess (gross)",event.get("difference_spy"),"percent"),
                                  ("Events / 252 ready observations",(research or {}).get("frequency",{}).get("events_per_252_ready"),"number")):
            scorecard.append({"mode":mode,"metric":metric,"kind":kind,**{p:value for p in primary},
                              "difference":0 if value is not None else None,"status":"Same V1 events; descriptive"})
        criteria=(research or {}).get("criteria",{})
        scorecard.append({"mode":mode,"metric":"Positive ticker SPY excess", "kind":"text",
                          **{p:f"{criteria['positive_excess_tickers']}/{criteria['defined_tickers']}" if criteria else None for p in primary},
                          "difference":None,"status":"Failed breadth criterion" if criteria and not criteria["breadth_passed"] else "Unavailable"})
    tables["scorecard"] = pd.DataFrame(scorecard)
    names = (*names, "scorecard")
    return {"status": "available", "metadata": metadata,
            "tables": {name: tables[name].to_dict("records") for name in names if name in tables}}


def hypothesis_registry(root: Path) -> list[dict]:
    path = root / "config/hypotheses.json"
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    required = {"id", "name", "rank", "motivation", "evidence", "mechanism", "features",
                "lookahead_risk", "future_test", "status", "overfitting_risk"}
    if not isinstance(rows, list) or any(not required <= row.keys() for row in rows):
        raise ValueError("Invalid hypothesis registry")
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate hypothesis ID")
    return sorted(rows, key=lambda row: (row["rank"], row["id"]))


def export_diagnosis(root: Path) -> dict:
    directory = root / "results/research_diagnosis"
    if not (directory / "metadata.json").exists():
        return {"status": "missing", "reason": "Run the offline research diagnosis script."}
    from hashlib import sha256
    metadata = json.loads((directory / "metadata.json").read_bytes())
    tables = {}
    for filename, expected in metadata["artifact_sha256"].items():
        if Path(filename).name != filename:
            raise ValueError("Unsafe diagnosis artifact path")
        path = directory / filename
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Diagnosis artifact changed")
        if path.stem not in {"paths", "support_context"}:
            tables[path.stem] = pd.read_csv(path, float_precision="round_trip").to_dict("records")
    return {"status": "available", "metadata": metadata, "tables": tables}
