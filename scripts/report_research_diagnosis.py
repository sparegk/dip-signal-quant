"""Render exploratory tables from verified diagnosis outputs; no new research."""

import argparse
from pathlib import Path

import pandas as pd

from scripts.dashboard_research import export_diagnosis

ROOT=Path(__file__).resolve().parents[1]
START="<!-- DIAGNOSIS_RESULTS_START -->"
END="<!-- DIAGNOSIS_RESULTS_END -->"


def render(root: Path=ROOT) -> str:
    data=export_diagnosis(root)
    if data["status"]!="available": raise ValueError("Missing diagnosis artifacts")
    tables={k:pd.DataFrame(v) for k,v in data["tables"].items()}
    groups=tables["groups"]
    ten=groups.loc[groups.horizon.eq(10)]
    zone=ten.loc[ten.analysis.eq("support_group")].set_index("group")
    lines=["## Findings — exploratory, generated from verified artifacts", "",
           "**No validated improvement emerged.** Positive raw rebounds coexist with weak",
           "ticker-level SPY breadth. Exit choice changes risk as well as profit. More",
           "components and repeated prior successful zones do not automatically help.", "",
           f"The recorded revisit group has {int(zone.loc['revisit','completed'])} complete ten-bar events: "
           f"gross mean {zone.loc['revisit','mean']:.3%}, SPY excess {zone.loc['revisit','excess']:.3%}. "
           f"The no-known-zone group has gross mean {zone.loc['no_known_successful_zone','mean']:.3%} "
           f"and excess {zone.loc['no_known_successful_zone','excess']:.3%}. "
           "This definition does not support the original repeated-support intuition; it is not a reason to tune the zone.", "",
           "### What the failure modes suggest", "",
           "- Frequency alone does not establish that V1 is too permissive. EXP-002's condition/frequency rates remain unchanged.",
           "- Exact component combinations differ, but the largest returns are not independent component effects. Some groups are small.",
           "- Strong negative recent momentum is not uniformly worse: deeper dips can also rebound more. A falling-knife filter is not justified.",
           "- High ATR events have larger rebound means **and deeper MAE**. This is a scale/risk relationship, not a free improvement.",
           "- Below-SPY-average events have larger gross mean but lower excess and deeper MAE than above-average events. Regime filtering is unvalidated.",
           "- High relative-volume events have weaker gross/excess means in this description. No volume filter follows.",
           "- Next-open gaps vary with later outcomes, but are future information relative to the original signal. They cannot retroactively filter V1.",
           "- Ticker-average ATR/volatility correlate with return and excess; survivor selection, sample size and market exposure remain confounders.",
           "- EXP-004 isolates exit behavior on the same independent entries. Time-only EV is highest among the primary comparison, but tail risk prevents declaring it superior.",
           "- EXP-001 roughly broke even after costs on its inspected holdout; EXP-002 failed its breadth criterion; EXP-003 exposed data/provenance limits. None is erased by later findings.", "",
           "### Scorecard and what would count as stronger", "",
           "Primary: net EV, paired SPY excess and consistency across chronological periods.",
           "Secondary: median, win rate, average win/loss, profit factor, tail loss, ticker",
           "drawdown, MFE capture and frequency. Robustness: positive folds/tickers, equal-ticker",
           "median, concentration and parameter stability. There is no combined score.", "",
           "Before any future test, define a risk budget and registered acceptable deterioration",
           "relative to V1. A positive EV difference with worse downside is mixed evidence.",
           "Review only at the original archive gates; insufficient fresh evidence remains pending.", ""]
    def table(title,frame,columns,percent=()):
        lines.extend([f"<details><summary>{title}</summary>", "", "| "+" | ".join(columns)+" |",
                      "| "+" | ".join(["---"]*len(columns))+" |"])
        for _,row in frame.iterrows():
            cells=[]
            for key in columns:
                v=row[key]
                cells.append("undefined" if pd.isna(v) else f"{v:.3%}" if key in percent
                             else f"{v:.3f}" if isinstance(v,float) else str(v))
            lines.append("| "+" | ".join(cells)+" |")
        lines.extend(["", "</details>", ""])
    columns=["analysis","group","completed","mean","median","excess","mfe","mae"]
    table("Ten-bar groups — including unfavorable results",ten,columns,["mean","median","excess","mfe","mae"])
    table("Forward-return horizons",groups.loc[groups.analysis.eq("all_events")],
          ["horizon","events","completed","mean","median","excess","mfe","mae"],["mean","median","excess","mfe","mae"])
    table("Rebound timing",tables["timing"].loc[lambda x:x.group.eq("all")],
          ["metric","complete_paths","reached","fraction","median_bars_if_reached"],["fraction"])
    table("Ticker relationships",tables["correlations"],["feature","outcome","tickers","spearman"])
    table("Features of positive and nonpositive ten-bar outcomes",tables["outcome_covariates"],
          list(tables["outcome_covariates"].columns),["return_5d","drawdown_change_5","atr_pct_14","relative_return_10d","entry_gap"])
    lines.extend(["Timing fractions include paths that never reached a level; conditional timing",
                  "medians include only those that did. MFE includes opportunity after earlier",
                  "policy exits. Overlap, adjusted vintages, survivorship and incomplete prior-zone",
                  "history prevent causal or prospective claims. Horizon counts differ due to censoring.", "",
                  f"Diagnostic configuration SHA256: `{data['metadata']['config_sha256']}`.",
                  "Reproduce: `python -m scripts.diagnose_research`, then `python -m scripts.report_research_diagnosis --write-doc`."])
    return "\n".join(lines)+"\n"


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-doc",action="store_true")
    parser.add_argument("--check-doc",action="store_true")
    args=parser.parse_args(); report=render()
    path=ROOT/"docs/RESEARCH_DIAGNOSIS.md"; text=path.read_text(encoding="utf-8")
    if args.check_doc:
        if START not in text or text.split(START,1)[1].split(END,1)[0].strip()!=report.strip():
            raise ValueError("Diagnosis documentation differs from verified results")
        print("Diagnosis documentation matches verified results")
    elif args.write_doc:
        prefix=text.split(START,1)[0].rstrip()
        path.write_text(prefix+"\n\n"+START+"\n"+report+END+"\n",encoding="utf-8")
    else: print(report)
