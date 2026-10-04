"""Offline exploratory post-mortem. Never selects parameters or runs EXP-005."""

from hashlib import sha256
import json
from pathlib import Path
import subprocess

import pandas as pd

from src.research_diagnosis import diagnose

ROOT = Path(__file__).resolve().parents[1]


def run(root: Path = ROOT) -> dict:
    directory = root / "results/exp_002"
    source = json.loads((directory / "metadata.json").read_bytes())
    for name, expected in source["artifact_sha256"].items():
        if Path(name).name != name or sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Frozen EXP-002 artifact changed: {name}")
    config_bytes = (root / "config/research_diagnosis.json").read_bytes().replace(b"\r\n", b"\n")
    config = json.loads(config_bytes)
    tables = diagnose(pd.read_parquet(directory / "observations.parquet"),
                      pd.read_parquet(directory / "events.parquet"), config)
    output = root / "results/research_diagnosis"
    output.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, frame in tables.items():
        path = output / f"{name}.csv"
        frame.to_csv(path, index=False, float_format="%.17g")
        hashes[path.name] = sha256(path.read_bytes()).hexdigest()
    metadata = {"status": "exploratory_historical_only", "config": config,
                "config_sha256": sha256(config_bytes).hexdigest(), "artifact_sha256": hashes,
                "source_artifact_sha256": source["artifact_sha256"],
                "code_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                "source_sha256": {name:sha256((root/name).read_bytes().replace(b"\r\n",b"\n")).hexdigest()
                                  for name in ("src/research_diagnosis.py","scripts/diagnose_research.py")},
                "limitations": ["Consumed history; no parameter selection", "Dependent events; no causal claims",
                                 "Prior-zone history starts in 2021; earlier successful dips are unobserved",
                                 "Path hits use daily highs, not known intraday fills", "Static survivor-biased universe"]}
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2)+"\n", encoding="utf-8")
    return metadata


if __name__ == "__main__":
    m = run()
    print(json.dumps({"status": m["status"], "artifacts": list(m["artifact_sha256"])}))
