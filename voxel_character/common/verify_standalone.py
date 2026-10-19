"""Compile twice in isolated directories containing only core.py and master.json.

Archived recipes, adapters, and reference files are absent from the input bundle.
This demonstrates generation independence, not an OS security sandbox or a
cross-platform determinism proof. Every run preserves logs and fresh outputs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(master, output, pitch, max_candidates=5_000_000, timeout=180):
    master, output = Path(master).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    runs = []
    result = {"schema": "riverstone.voxel.standalone-proof.v1", "master_file_sha256": sha(master),
              "compiler_sha256": sha(HERE/"core.py"), "pitch": pitch,
              "input_bundle": ["core.py", "master.json"],
              "legacy_source_required": False, "timeout_seconds_per_run": timeout,
              "max_candidate_cells": max_candidates, "runs": runs, "pass": False}
    try:
        for index in (1, 2):
            with tempfile.TemporaryDirectory(prefix="voxel-standalone-") as temporary:
                isolated = Path(temporary)
                shutil.copyfile(HERE/"core.py", isolated/"core.py")
                shutil.copyfile(master, isolated/"master.json")
                started = time.monotonic()
                command = [sys.executable, "-I", "core.py", "master.json", "--pitch", str(pitch),
                           "--max-candidates", str(max_candidates), "--output", "compiled.json"]
                with (output/f"run_{index}.log").open("x") as log:
                    completed = subprocess.run(command, cwd=isolated, stdout=log, stderr=subprocess.STDOUT,
                                               timeout=timeout, check=False)
                record = {"index": index, "returncode": completed.returncode,
                          "elapsed_seconds": round(time.monotonic()-started, 3),
                          "child_peak_rss_kib_linux_cumulative": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                          "input_bundle_exact": sorted(p.name for p in isolated.iterdir() if p.name != "compiled.json") == ["core.py", "master.json"]}
                if (isolated/"compiled.json").exists():
                    destination = output/ f"compiled_{index}.json"
                    shutil.copyfile(isolated/"compiled.json", destination)
                    data = json.loads(destination.read_text())
                    record.update({"compiled_sha256": sha(destination), "valid": data["valid"],
                                   "master_hash": data["master_hash"], "payload_hash": data["payload_hash"],
                                   "cell_count": len(data["cells"]), "candidate_cells": data["candidate_cells"],
                                   "constraints": data["constraints"]})
                runs.append(record)
                if completed.returncode:
                    raise RuntimeError(f"standalone compiler run {index} failed; see preserved log")
        result["byte_identical"] = runs[0]["compiled_sha256"] == runs[1]["compiled_sha256"]
        result["pass"] = result["byte_identical"] and all(r["valid"] and r["input_bundle_exact"] for r in runs)
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        result["error"] = str(exc)
    finally:
        with (output/"standalone_validation.json").open("x") as stream:
            json.dump(result, stream, indent=2); stream.write("\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pitch", type=float, required=True)
    parser.add_argument("--max-candidates", type=int, default=5_000_000)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    result = verify(args.master, args.output_dir, args.pitch, args.max_candidates, args.timeout)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["pass"] else 1)
