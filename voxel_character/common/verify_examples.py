"""Bounded two-slice repeat/structure check; writes only an explicitly new report."""
import argparse
import json
from pathlib import Path

from core import compile_master

ROOT = Path(__file__).resolve().parent


def verify():
    reports = []
    for name in ("wall_window", "basin_support"):
        source = ROOT/"examples"/f"{name}.json"
        master = json.loads(source.read_text())
        for pitch in (.2, .1):
            first = compile_master(master, {"pitch": pitch})
            repeat = compile_master(master, {"pitch": pitch})
            reports.append({"example": name, "pitch": pitch, "master_hash": first["master_hash"],
                            "compiler_source_hash": first["compiler_source_hash"],
                            "cell_count": len(first["cells"]), "candidate_cells": first["candidate_cells"],
                            "payload_hash": first["payload_hash"], "repeat_equal": first == repeat,
                            "valid": first["valid"], "constraints": first["constraints"]})
    return {"scope": "two real-source partial slices through one common compiler",
            "valid": all(r["valid"] and r["repeat_equal"] for r in reports),
            "visual_review": "not_run", "full_asset_migration": "not_completed", "runs": reports}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify()
    rendered = json.dumps(result, indent=2)+"\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(rendered)
    print(rendered)
    raise SystemExit(0 if result["valid"] else 1)
