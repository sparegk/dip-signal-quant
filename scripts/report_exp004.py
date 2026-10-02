"""Render EXP-004 findings from hash-verified artifacts, without new selection."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
START = "<!-- EXP004_RESULTS_START -->"
END = "<!-- EXP004_RESULTS_END -->"


def pct(value) -> str:
    return "undefined" if pd.isna(value) else f"{100 * value:+.3f}%"


def number(value) -> str:
    return "undefined" if pd.isna(value) else f"{value:.3f}"


def table(title: str, headers: list[str], rows: list[list]) -> str:
    lines = [f"### {title}", "", "| " + " | ".join(headers) + " |",
             "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines += ["| " + " | ".join(map(str, row)) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def read_artifacts(directory: Path) -> tuple[dict, dict]:
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    tables = {}
    for filename, expected in metadata["artifact_sha256"].items():
        path = directory / filename
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"EXP-004 artifact changed: {filename}")
        tables[path.stem] = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, float_precision="round_trip")
    return metadata, tables


def render_report(directory: Path) -> str:
    metadata, t = read_artifacts(directory)
    aggregate = t["aggregate_summary"]
    primary = aggregate.loc[aggregate["mode"].eq("independent")].set_index("policy")
    secondary = aggregate.loc[aggregate["mode"].eq("non_overlapping")].set_index("policy")
    selected, control = primary.loc["training_selected"], primary.loc["v1_control"]
    folds = t["fold_summary"]
    p = folds.loc[folds["mode"].eq("independent")].pivot(index="fold", columns="policy", values="expected_value")
    fold_diff = p.training_selected - p.v1_control
    paired = t["paired_comparison"]
    ticker_excess = paired.loc[paired.policy.eq("training_selected")].groupby("ticker").paired_net_difference.mean()
    selections = t["selected_policy_by_fold"]
    choices = selections.loc[selections.policy.eq("training_selected")]
    efficiency = t["exit_efficiency"].query("fold == 'ALL' and mode == 'independent'").set_index("policy")
    plateau = t["parameter_plateaus"]
    intervals = t["paired_uncertainty"].set_index("policy")
    ci = intervals.loc["training_selected"]
    lines = ["## EXP-004 results (generated from verified artifacts)", "",
        f"Registered in `{metadata['preregistration_commit']}` before evaluation. Execution revision "
        f"`{metadata['code_commit']}`; dirty tree: `{metadata['working_tree_dirty']}`.", "",
        f"**Training-selected pooled fold-OOS net EV: {pct(selected.expected_value)} versus "
        f"V1 {pct(control.expected_value)}; paired difference {pct(ci['mean'])}.** "
        f"Positive EV differences occur in {int((fold_diff > 0).sum())}/{len(fold_diff)} folds and "
        f"{int((ticker_excess > 0).sum())}/{len(ticker_excess)} tickers. "
        f"The time-only control has higher EV ({pct(primary.loc['time_only','expected_value'])}); "
        f"selected EV in R is {number(selected.expectancy_r)} versus V1 {number(control.expectancy_r)}, "
        "and worst-ticker drawdown is deeper. These reused historical periods do not establish future profitability.", "",
        f"{metadata['candidate_count']} configurations ({metadata['selectable_candidate_count']} searchable, "
        f"{metadata['family_count']} families, four controls); {metadata['requested_count']} requested / "
        f"{metadata['usable_count']} usable tickers, with the original exclusions retained. "
        f"Config SHA256: `{metadata['config_sha256']}`. Primary mode uses the same "
        "independent event entries; secondary streams accept policy-dependent subsets.", "",
        "### Decision questions", "",
        f"1. Net EV difference versus V1 is {pct(ci['mean'])}; date-block bootstrap interval "
        f"[{pct(ci.ci_lower)}, {pct(ci.ci_upper)}]. This is descriptive uncertainty, not a correction for model search.",
        f"2. Median-return difference: {pct(selected.median_return - control.median_return)}.",
        f"3. Profit factor: {number(selected.profit_factor)} versus {number(control.profit_factor)}.",
        f"4. Win rate: {pct(selected.win_rate)} versus {pct(control.win_rate)}.",
        f"5. Fifth-percentile trade return: {pct(selected.fifth_percentile_net)} versus "
        f"{pct(control.fifth_percentile_net)}; worst ticker secondary trade-close drawdown: "
        f"{pct(secondary.loc['training_selected','worst_ticker_trade_close_drawdown'])} versus "
        f"{pct(secondary.loc['v1_control','worst_ticker_trade_close_drawdown'])}. Risk measures can disagree.",
        f"6. Fold improvement: {int((fold_diff > 0).sum())}/{len(fold_diff)}; selected policy loses money "
        f"in {int((p.training_selected < 0).sum())}/{len(p)} folds.",
        f"7. Positive paired ticker EV differences: {int((ticker_excess > 0).sum())}/{len(ticker_excess)}; "
        f"median ticker difference {pct(ticker_excess.median())}.",
        f"8. Selected IDs: {choices.candidate_id.nunique()} distinct across {len(choices)} folds; "
        f"{int(choices.candidate_id.ne(choices.candidate_id.shift()).iloc[1:].sum())} changes between folds.",
        f"9. Training plateau flags: {int(plateau.plateau_flag.sum())}/{len(plateau)} family/fold surfaces. "
        "Full surfaces/frontiers are retained, including losing configurations.",
        f"10. Median signed full-window MFE capture: {number(efficiency.loc['training_selected','median_capture'])} "
        f"versus V1 {number(efficiency.loc['v1_control','median_capture'])}. Negative ratios remain included.",
        "11. Post-stop recoveries are shown below with measurable-stop denominators. Different stop cohorts "
        "prevent interpreting a conditional recovery rate as a causal improvement.",
        f"12. {metadata['prospective']['status']} Archived classifications: "
        f"`{metadata['prospective']['classification_counts']}`; no prospective outcomes were evaluated.", ""]
    rows = []
    for fold, choice in choices.set_index("fold").iterrows():
        rows.append([fold, choice.candidate_id, int(choice.training_trades), pct(choice.training_net_ev),
                     pct(p.loc[fold,"training_selected"]), pct(p.loc[fold,"v1_control"]), pct(fold_diff.loc[fold])])
    lines.append(table("Primary selections by fold", ["Fold","Selected ID","Train N","Train net EV","OOS net EV","V1 OOS EV","Difference"],rows))
    rows = []
    for row in selections.loc[selections.policy.str.startswith("best_")].itertuples():
        rows.append([row.fold,row.policy,row.candidate_id,pct(row.training_net_ev),pct(p.loc[row.fold,row.policy])])
    lines.append(table("Training-selected winner within each family", ["Fold","Family policy","Selected ID","Training EV","OOS EV"], rows))
    for title, frame in [("Pooled independent event comparison",primary),("Secondary non-overlapping trade comparison",secondary)]:
        rows = []
        for policy,row in frame.iterrows():
            exits = "/".join(str(int(row[name+"_count"])) for name in ("take_profit","stop_loss","time_exit"))
            rows.append([policy,int(row.trade_count),pct(row.expected_value),pct(row.median_return),pct(row.win_rate),
                number(row.profit_factor),pct(row.average_win),pct(row.average_loss),number(row.expectancy_r),
                number(row.average_holding_bars),exits,pct(row.worst_ticker_trade_close_drawdown)])
        lines.append(table(title,["Policy","N","Net EV","Median","Win rate","PF","Avg win","Avg loss","EV in R","Bars","TP/SL/time","Worst ticker trade-close DD"],rows))
    lines.append("Drawdowns above are per-ticker strictly non-overlapping trade-close compounding. "
                 "Pooled portfolio drawdown is undefined; intratrade and daily losses are not measured. "
                 "No-stop controls have undefined R.\n")
    lines.append(table("Independent-event risk-normalized returns",["Policy","Defined R N","Mean R / EV in R","Median R","Win rate in R","Average winning R","Average losing R"],
        [[policy,int(row.r_count),number(row.expectancy_r),number(row.median_r),pct(row.r_win_rate),
          number(row.average_winning_r),number(row.average_losing_r)] for policy,row in primary.iterrows()]))
    lines.append(table("All fold independent net EV",["Fold",*list(p.columns)],
                       [[index,*[pct(value) for value in row]] for index,row in p.iterrows()]))
    ledger = t["oos_results"]
    complete = ledger.loc[ledger.status.eq("completed") & ledger["mode"].eq("independent")]
    rows = []
    for policy,group in complete.groupby("policy",sort=True):
        for name in ("stop_fraction","target_fraction"):
            x = pd.to_numeric(group[name]).dropna()
            rows.append([policy,name,len(x),*[pct(value) for value in (x.mean(),x.median(),x.quantile(.25),x.quantile(.75),x.min(),x.max())]])
    lines.append(table("Actual OOS barrier distributions",["Policy","Distance","N","Mean","Median","Q25","Q75","Min","Max"],rows))
    rows = []
    for policy,row in efficiency.iterrows():
        rows.append([policy,pct(row.mean_full_window_mfe),pct(row.mean_full_window_mae),number(row.mean_capture),
            number(row.median_capture),int(row.capture_count),pct(row.mean_remaining_mfe),int(row.stopped_count),
            *[f"{int(row[f'recovery_{v}pct_count'])}/{int(row[f'recovery_{v}pct_measurable_stops'])} ({pct(row[f'recovery_{v}pct_rate'])})" for v in (2,5,10)]])
    lines.append(table("Excursion capture and post-exit recovery",["Policy","Full MFE","Full MAE","Mean capture","Median capture","Defined capture N","Remaining MFE","Stops","Entry+2% after exit","Entry+5%","Entry+10%"],rows))
    lines.append("Signed capture ratios can be very negative when a losing trade has near-zero positive MFE. "
                 "The negative means are retained; the median is more stable. Neither is used for selection.\n")
    rows = []
    for policy,group in paired.groupby("policy",sort=True):
        x = group.groupby("ticker").paired_net_difference.mean()
        rows.append([policy,len(x),int(x.gt(0).sum()),int(x.lt(0).sum()),pct(x.median()),pct(x.quantile(.25)),pct(x.quantile(.75))])
    lines.append(table("Cross-sectional paired EV difference versus V1",["Policy","Tickers","Positive","Negative","Median","Q25","Q75"],rows))
    ticker = t["ticker_summary"].query("policy == 'training_selected' and mode == 'independent'")
    extremes = pd.concat([ticker.nsmallest(5,"expected_value"),ticker.nlargest(5,"expected_value")]).drop_duplicates("ticker")
    lines.append(table("Retained ticker heterogeneity: five lowest/highest selected-policy EVs",["Ticker","N","Net EV","Median","Win rate","PF"],
        [[r.ticker,int(r.trade_count),pct(r.expected_value),pct(r.median_return),pct(r.win_rate),number(r.profit_factor)] for r in extremes.itertuples()]))
    lines.append(table("Training parameter plateaus",["Fold","Family","Winner","Near-best N","Adjacent near-best","Plateau flag"],
        [[r.fold,r.family,r.winner,r.near_best_count,r.adjacent_near_best_count,r.plateau_flag] for r in plateau.itertuples()]))
    frontier = t["candidate_training_results"].query("ev_win_frontier == True")
    lines.append(table("Training EV/win-rate frontier (controls included)",["Fold","Candidate","Net EV","Win rate","Avg win","Avg loss"],
        [[r.fold,r.candidate_id,pct(r.expected_value),pct(r.win_rate),pct(r.average_win),pct(r.average_loss)] for r in frontier.itertuples()]))
    lines += ["### Scientific interpretation and limitations", "",
        "The tables compare training-selected policies; no candidate was selected on its OOS score. "
        "Higher EV may buy greater tail loss or deeper ticker drawdown. Target-only/time-only controls "
        "must remain visible when interpreting barrier value. A favorable comparison on these consumed "
        "dates is exploratory historical evidence. There is no prospective confirmation.", "",
        "Current-constituent survivorship selection, 21 retained data-quality exclusions, revised adjusted "
        "prices, daily OHLC ambiguity, overlapping outcomes, unequal histories and uncalibrated "
        "execution/capital assumptions remain. Date-block intervals do not resolve multiple testing or "
        "all ticker dependence. MFE includes high/low information whose intraday ordering is unknown; "
        "recovery highs after stop exits are descriptive and may not be executable.", "",
        "Next hypothesis (not implemented): test whether signal-time price structure can control tail "
        "loss without surrendering rebound capture. Keep it separate as EXP-005; first review the "
        "recorded trade-offs and preserve a policy before genuine prospective comparison.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory",type=Path,default=ROOT/"results/exp_004")
    parser.add_argument("--write-doc",type=Path)
    parser.add_argument("--check-doc",type=Path)
    args = parser.parse_args()
    report = render_report(args.directory)
    if args.write_doc:
        text = args.write_doc.read_text(encoding="utf-8")
        prefix = text.split(START)[0].rstrip()
        args.write_doc.write_text(prefix+"\n\n"+START+"\n"+report+END+"\n",encoding="utf-8")
        print(f"Updated {args.write_doc}")
    elif args.check_doc:
        existing = args.check_doc.read_text(encoding="utf-8").split(START)[1].split(END)[0].strip()
        if existing != report.strip():
            raise ValueError("Generated EXP-004 documentation differs from artifacts")
        print("EXP-004 documentation matches verified artifacts")
    else:
        print(report)


if __name__ == "__main__":
    main()
