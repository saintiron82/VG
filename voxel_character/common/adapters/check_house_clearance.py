"""Supplement final-owner checks with static-only and isolated joint-child sampling.

No common-core change or physics execution. This is the same pitch 0.1 shadow
condition, and tests sample cell centres rather than continuous swept volumes.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import apply, compile_master, contains, inverse, prepare_shape, transform


def static_only_master(master):
    result = copy.deepcopy(master)
    result["instances"] = [i for i in result["instances"] if not i.get("metadata", {}).get("dynamic")]
    result["constraints"] = [c for c in result["constraints"] if c["kind"] == "empty_region"]
    return result


def check(master, pitch=.1):
    if pitch != .1:
        raise ValueError("this migration check is scoped to pitch 0.1")
    static = compile_master(static_only_master(master), {"pitch": pitch})
    entry = next(c for c in master["constraints"] if c["id"] == "authored_entry_clearance")
    shape = prepare_shape(entry["shape"], pitch)
    placement = transform(entry.get("transform"))
    joints = []
    for joint in master["extensions"]["rigid_joint_contracts"]:
        if joint["axis_world"] != [0, 1, 0]:
            raise ValueError("authored joint check currently supports Y-axis rigid motion")
        isolated = copy.deepcopy(master)
        isolated["instances"] = [i for i in isolated["instances"] if i["id"] == joint["child"]]
        isolated["constraints"] = []; isolated["assembly_cuts"] = []
        body = compile_master(isolated, {"pitch": pitch})
        angle = math.radians(joint["open_degrees"])
        rotation = transform({"basis": [[math.cos(angle), 0, math.sin(angle)], [0, 1, 0], [-math.sin(angle), 0, math.cos(angle)]]})
        pivot = joint["pivot_world"]
        obstruct = []
        for row in body["cells"]:
            world = [(index+.5)*pitch+offset for index, offset in zip(row[:3], body["grid_origin"])]
            turned = apply(rotation, [p-o for p, o in zip(world, pivot)])
            turned = [p+o for p, o in zip(turned, pivot)]
            if contains(shape, inverse(placement, turned), epsilon=pitch*1e-9):
                obstruct.append(row[:3])
        joints.append({"id": joint["id"], "child": joint["child"], "angle_degrees": joint["open_degrees"],
                       "isolated_child_cells": len(body["cells"]), "blocked_entry_centres": len(obstruct),
                       "pass": bool(body["cells"]) and not obstruct,
                       "isolated_master_hash": body["master_hash"], "isolated_payload_hash": body["payload_hash"]})
    return {"scope": "static-only protected voids plus isolated child at authored open angle; pitch 0.1",
            "pass": static["valid"] and all(j["pass"] for j in joints),
            "static_only_checks": static["constraints"], "joint_checks": joints,
            "static_only_master_hash": static["master_hash"], "static_only_payload_hash": static["payload_hash"],
            "compiler_source_hash": static["compiler_source_hash"],
            "limits": "Cell-centre endpoint checks; no swept-volume, navmesh, rendering or dynamic physics certification. Final-owner static selectors alone can hide blockers behind dynamic geometry, so static-only compilation is intentional."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = check(json.loads(args.master.read_text()))
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["pass"] else 1)
