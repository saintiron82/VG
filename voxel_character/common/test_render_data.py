import copy
import json
from pathlib import Path
import tempfile
import unittest

from core import compile_master, digest
from render_data import make_render_data
from verify_standalone import verify

HERE = Path(__file__).resolve().parent


def fixture():
    return {"schema": "riverstone.voxel.master.v1", "id": "unnamed_fixture", "revision": 1,
            "axes": {"up": "+Y", "front": "+Z", "right": "+X"},
            "materials": {"one": "ab1200"}, "components": [{"id": "shape", "parts": [{"id": "part", "pivot": [0,0,0]}],
            "operations": [{"id": "volume", "part": "part", "action": "paint", "material": "one",
                            "shape": {"kind": "box", "min": [-1,0,0], "max": [1,1,1]}}]}],
            "instances": [{"id": "placed", "component": "shape"}], "constraints": []}


class RenderExportTests(unittest.TestCase):
    def test_rectangular_volume_greedy_six_faces(self):
        result = make_render_data(compile_master(fixture(), {"pitch": .5}))
        self.assertEqual(result["quad_count"], 6)
        self.assertEqual(result["cell_count"], 16)
        self.assertEqual(result["bounds"], {"min": [-1,0,0], "max": [1,1,1]})

    def test_world_origin_and_pitch_applied_once(self):
        master = fixture(); master["grid_origin"] = [.1,.2,.3]
        compiled = compile_master(master, {"pitch": .5})
        render = make_render_data(compiled)
        points = [p for g in render["groups"] for q in g["quads"] for p in q]
        for axis in range(3):
            self.assertEqual(min(p[axis] for p in points), render["bounds"]["min"][axis])
            self.assertEqual(max(p[axis] for p in points), render["bounds"]["max"][axis])

    def test_face_winding_points_outward(self):
        render = make_render_data(compile_master(fixture(), {"pitch": .5}))
        centre = [0,.5,.5]
        for quad in render["groups"][0]["quads"]:
            a = [quad[1][i]-quad[0][i] for i in range(3)]
            b = [quad[2][i]-quad[0][i] for i in range(3)]
            normal = [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
            self.assertGreater(sum(normal[i]*(quad[0][i]-centre[i]) for i in range(3)),0)

    def test_same_input_deterministic(self):
        compiled = compile_master(fixture(), {"pitch": .5})
        self.assertEqual(make_render_data(compiled), make_render_data(compiled))

    def test_tampered_payload_rejected(self):
        compiled = compile_master(fixture(), {"pitch": .5}); compiled["cells"][0][0] += 1
        with self.assertRaisesRegex(ValueError,"verified cell payload"):
            make_render_data(compiled)

    def test_duplicate_coordinate_rejected(self):
        compiled = compile_master(fixture(), {"pitch": .5}); compiled["cells"].append(compiled["cells"][0]); compiled["payload_hash"]=digest(compiled["cells"])
        with self.assertRaisesRegex(ValueError,"duplicate"):
            make_render_data(compiled)

    def test_invalid_geometry_rejected(self):
        compiled = compile_master(fixture(), {"pitch": .5}); compiled["valid"] = False
        with self.assertRaises(ValueError): make_render_data(compiled)

    def test_unknown_material_rejected(self):
        compiled = compile_master(fixture(), {"pitch": .5}); compiled["cells"][0][5] = "absent"; compiled["payload_hash"]=digest(compiled["cells"])
        with self.assertRaises(ValueError): make_render_data(compiled)

    def test_standalone_bundle_and_repeat(self):
        with tempfile.TemporaryDirectory() as td:
            master = Path(td)/"input.json"; master.write_text(json.dumps(fixture()))
            result=verify(master,Path(td)/"evidence",.5,1000,10)
            self.assertTrue(result["pass"])
            self.assertTrue(result["byte_identical"])
            self.assertTrue(all(r["input_bundle_exact"] for r in result["runs"]))

    def test_standalone_failure_preserves_log_and_report(self):
        with tempfile.TemporaryDirectory() as td:
            master = Path(td)/"input.json"; master.write_text(json.dumps(fixture()))
            output=Path(td)/"evidence"
            result=verify(master,output,.5,1,10)
            self.assertFalse(result["pass"])
            self.assertTrue((output/"run_1.log").exists())
            self.assertTrue((output/"standalone_validation.json").exists())

    def test_promotion_does_not_change_geometry(self):
        master=json.loads((HERE/"assets/house/master.json").read_text())
        prior=json.loads((HERE/"adapters/results/house_r2_pitch_0.1/master.json").read_text())
        for key in ("components","instances","materials","constraints","assembly_cuts","extensions"):
            self.assertEqual(master[key],prior[key])
        self.assertEqual(master["revision"],3)


if __name__ == "__main__": unittest.main()
