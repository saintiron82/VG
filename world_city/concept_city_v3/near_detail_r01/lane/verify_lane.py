"""Read the saved lane artifacts and independently audit hashes and heights."""
import gzip
import hashlib
import json
from pathlib import Path

from author_lane import HERE, ROOT, author, digest, json_bytes, save_new_or_identical


def verify():
    rules_path = HERE/"inputs/lane_rules.json"
    spec = json.loads(rules_path.read_text())
    bundle = author(spec)
    report = json.loads((HERE/"generated/build_report.json").read_text())
    for name, entry in report["files"].items():
        data = (HERE/name).read_bytes()
        assert len(data) == entry["bytes"], name
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], name
    counts = {}
    for name, pitch in (("surface", spec["pitch"]), ("support", 1.0)):
        master = json.loads((HERE/f"source/lane_{name}.master.json").read_text())
        assert master == bundle[name], "current author and frozen source differ"
        data = json.loads(gzip.decompress((HERE/f"generated/lane_{name}.compiled.json.gz").read_bytes()))
        render = json.loads((HERE/f"generated/lane_{name}.render.json").read_text())
        assert data["valid"] and data["pitch"] == pitch
        assert digest(master) == data["master_hash"] == render["master_hash"]
        assert digest(data["cells"]) == data["payload_hash"] == render["payload_hash"]
        assert len(data["cells"]) == render["cell_count"]
        assert render["quad_count"] == sum(len(group["quads"]) for group in render["groups"])
        assert len({tuple(c[:3]) for c in data["cells"]}) == len(data["cells"])
        assert data["candidate_cells"] <= spec["budgets"]["max_candidate_cells"]
        assert len(data["cells"]) <= spec["budgets"]["max_output_cells"]
        if name == "surface":
            columns, tones, joints = {}, {}, 0
            x0, z0, x1, z1 = bundle["bounds"]
            o = data["grid_origin"]
            for c in data["cells"]:
                x, y, z = [o[i]+c[i]*pitch for i in range(3)]
                assert x >= x0-1e-8 and x+pitch <= x1+1e-8
                assert z >= z0-1e-8 and z+pitch <= z1+1e-8
                assert y+pitch <= 1e-8
                columns[(c[0],c[2])] = max(columns.get((c[0],c[2]), -1), round(y+pitch, 6))
                if c[5] == "joint":
                    assert y+pitch <= -0.025+1e-8
                    joints += 1
                else:
                    tones.setdefault(c[6].rsplit("_", 1)[0], set()).add(c[5])
            assert all(len(t) == 1 for t in tones.values())
            bands = {str(v): sum(y == v for y in columns.values()) for v in sorted(set(columns.values()))}
            assert set(columns.values()) == {-0.025, -0.0125, 0.0}
            counts.update({"planar_columns": len(columns), "height_band_columns": bands, "joint_cells": joints,
                           "occupied_stone_ids": len(tones), "four_coherent_tones": len({next(iter(t)) for t in tones.values()}) == 4})
    collision = json.loads((HERE/"generated/lane_collision.json").read_text())
    assert collision == bundle["collision"]
    assert not collision["surface_collision"] and len(collision["boxes"]) == 1
    assert collision["boxes"][0]["min"] == [-5,-1,7] and collision["boxes"][0]["max"] == [5,0,12]
    assert collision["walking_corridor"]["rect"] == [-1,7,1,12]
    tests = (HERE/"generated/test_results_final.log").read_text()
    assert "Ran 9 tests" in tests and tests.rstrip().endswith("OK")
    file_bytes = sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file())
    assert file_bytes < 20000000
    return {"valid": True, "saved_file_hashes_verified": len(report["files"]), "source_matches_current_author": True,
            "compressed_cell_payloads_verified": 2, "collision_is_single_continuous_flat_box": True,
            "unit_tests": {"passed": 9, "log": "generated/test_results_final.log"}, "geometry": counts,
            "subtree_file_bytes_before_audit": file_bytes, "max_bytes": 20000000,
            "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                              [rules_path,HERE/"author_lane.py",HERE/"verify_lane.py",ROOT/"voxel_character/common/core.py",ROOT/"voxel_character/common/render_data.py",ROOT/"voxel_character/tools/mesh.py"]},
            "limits": "No GUI, visual approval, game runtime integration, or full-city support elevation validation performed."}


if __name__ == "__main__":
    result = verify()
    # Verification reports are immutable too. Print on later runs rather than
    # rewriting a report whose subtree byte count naturally includes itself.
    output = HERE/"generated/audit_report.json"
    if not output.exists():
        save_new_or_identical(output, json_bytes(result))
    print(json.dumps(result, indent=2))
