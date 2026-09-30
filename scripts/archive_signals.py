"""Manually collect/replay frozen V1 decisions, or verify/recover a local archive."""

import argparse
import json
from pathlib import Path

from src.paper_archive import (ROOT, begin_run, capture_input, code_identity, coverage,
                              finish_run, load_protocol, recover_run, verify_run)
from src.preservation import safe_key, write_record
from src.sessions import utc_now


def collect(root: Path, *, session: str, run_id: str, replay_cache: Path | None = None,
            corrects: str | None = None, reason: str | None = None) -> dict:
    config = load_protocol()
    mode = "replay" if replay_cache is not None else "collect"
    existed = (root / "runs" / safe_key(run_id) / "intent.json").exists()
    intent = begin_run(root, run_id, session=session, mode=mode, config=config,
                       code=code_identity(), corrects=corrects, reason=reason)
    if existed:
        result = verify_run(root, run_id)
        if result["status"] == "interrupted":
            raise ValueError("Interrupted attempt: recover it, then use a new correction key")
        return result  # no new network request, timestamp, or duplicate observation
    inputs = {}
    for ticker in (config["benchmark"], *intent["universe"]):
        item = capture_input(root, ticker, config=config, session=session, replay_cache=replay_cache)
        inputs[ticker] = item
        write_record(root / "runs" / run_id / "inputs" / (ticker + ".json"), item)
        print(f"{ticker}: {item['status']}", flush=True)
    finish_run(root, intent, inputs)
    return verify_run(root, run_id, replay=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "data/paper_archive")
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("collect")
    command.add_argument("--session", required=True)
    command.add_argument("--run-id", required=True)
    command.add_argument("--replay-cache", type=Path)
    command.add_argument("--corrects")
    command.add_argument("--reason")
    command = sub.add_parser("verify")
    command.add_argument("--run-id", required=True)
    command.add_argument("--replay", action="store_true")
    command = sub.add_parser("recover")
    command.add_argument("--run-id", required=True)
    sub.add_parser("coverage")
    args = vars(parser.parse_args())
    command = args.pop("command")
    if command == "collect":
        result = collect(**args)
    elif command == "verify":
        result = verify_run(**args)
    elif command == "recover":
        result = recover_run(**args)
    else:
        result = coverage(args["root"], load_protocol(), as_of=utc_now())
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
