"""Render compact audit findings from verified quarantined inputs, without returns."""

import argparse
from pathlib import Path

from src.data_audit import audit_ohlc, restore_raw
from src.preservation import digest, read_record


def render_audit(root: Path) -> str:
    report = read_record(root / "summary.json")
    if digest((root / "violations.csv").read_bytes()) != report["violations_sha256"]:
        raise ValueError("Violation table hash mismatch")
    rows = ["| Ticker | Rows | Affected | Percent | Maximum absolute gap | Maximum relative gap | Failed rules | Sessions |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |"]
    for row in report["summaries"]:
        if "snapshot" not in row:
            rows.append(f"| {row['ticker']} | unavailable | — | — | — | — | acquisition failed | — |")
            continue
        measured, findings = audit_ohlc(restore_raw(root, row["snapshot"]), row["ticker"], vintage=row["vintage"])
        if any(row[key] != value for key, value in measured.items()):
            raise ValueError("Summary differs from preserved raw input")
        dates = ", ".join(sorted({value[:10] for value in findings.session})) or "none"
        absolute = f"{row['max_absolute_gap']:.5g}" if row['affected_rows'] else "—"
        relative = f"{row['max_relative_gap']:.5g}" if row['affected_rows'] else "—"
        rules = ", ".join(row['rules']) or "none"
        rows.append(f"| {row['ticker']} | {row['rows']} | {row['affected_rows']} | "
                    f"{100 * row['affected_fraction']:.5f}% | {absolute} | {relative} | {rules} | {dates} |")
    return "\n".join(rows) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data/exp003/diagnostic_authorized"))
    parser.add_argument("--check-doc", type=Path)
    args = parser.parse_args()
    rendered = render_audit(args.root)
    if args.check_doc:
        if rendered not in args.check_doc.read_text(encoding="utf-8"):
            raise SystemExit("Audit documentation differs from preserved diagnostics")
        print("Audit documentation matches preserved diagnostics")
    else:
        print(rendered, end="")
