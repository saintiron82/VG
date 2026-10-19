"""Generic static surface export from validated common compiled cells.

The sparse geometry remains authoritative. This surface is a disposable render
representation and has no object-specific geometry, animation, or physics rules.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools"))
from core import digest, number, vector
import mesh


def make_render_data(compiled):
    if compiled.get("schema") != "riverstone.voxel.compiled.v1" or not compiled.get("valid"):
        raise ValueError("valid common compiled data required")
    pitch, origin = compiled.get("pitch"), compiled.get("grid_origin")
    if not number(pitch) or pitch <= 0 or not vector(origin):
        raise ValueError("positive pitch and finite grid origin required")
    cells = compiled.get("cells")
    if not isinstance(cells, list) or not cells or digest(cells) != compiled.get("payload_hash"):
        raise ValueError("nonempty verified cell payload required")
    seen = set()
    materials = compiled.get("materials", {})
    for row in cells:
        if (not isinstance(row, list) or len(row) != 7 or
                not all(type(i) is int for i in row[:3]) or row[5] not in materials):
            raise ValueError("malformed common cell or unknown material")
        key = tuple(row[:3])
        if key in seen:
            raise ValueError("duplicate cell coordinate")
        seen.add(key)
    groups = {}
    for corners, material in mesh.greedy_faces([(*row[:3], row[5]) for row in cells]):
        world = [[origin[i] + p[i]*pitch for i in range(3)] for p in corners]
        groups.setdefault(material, []).append(world)
    lo = [origin[i] + min(p[i] for p in seen)*pitch for i in range(3)]
    hi = [origin[i] + (max(p[i] for p in seen)+1)*pitch for i in range(3)]
    return {
        "schema": "riverstone.voxel.render.v1", "unit": "m",
        **{key: compiled[key] for key in ("source_id", "source_revision", "master_hash", "payload_hash", "pitch", "grid_origin", "materials")},
        "cell_count": len(cells), "bounds": {"min": lo, "max": hi},
        "groups": [{"material": key, "quads": groups[key]} for key in sorted(groups)],
        "quad_count": sum(len(v) for v in groups.values()),
        "geometry": "Static exterior surface of final composited occupancy; outward CCW quads in world metres. No hidden dynamic layers.",
        "provenance": {"compiler_source_hash": compiled["compiler_source_hash"],
                       "exporter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                       "mesher_sha256": hashlib.sha256(Path(mesh.__file__).read_bytes()).hexdigest()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("compiled", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = make_render_data(json.loads(args.compiled.read_text()))
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in ("source_id", "pitch", "cell_count", "quad_count", "master_hash", "payload_hash")}))


if __name__ == "__main__":
    main()
