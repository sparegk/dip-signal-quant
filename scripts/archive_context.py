"""Append signal-time context to a sealed run; never fetch data or score outcomes."""

import argparse
from pathlib import Path

from src.archive_context import preserve_context
from src.paper_archive import ROOT

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=ROOT/"data/paper_archive")
    parser.add_argument("--run-id",required=True)
    args=parser.parse_args()
    result=preserve_context(args.root,args.run_id)
    print(f"Preserved context: {result['run_id']} ({len(result['records'])} requested tickers)")
