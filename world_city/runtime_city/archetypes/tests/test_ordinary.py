"""Headless checks use the existing common compiler and disposable surface exporter."""
import copy
import itertools
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "voxel_character/common"))
from core import apply, compose, compile_master, prepare_shape, shape_bounds, transform, validate_master
from render_data import make_render_data
from world_city.runtime_city.archetypes.ordinary import make_master, STYLES, ROOF_FORMS


def specimen(**changes):
    result = dict(asset_id="city_specimen", width_m=7, depth_m=8, floors=2,
                  style="merchant", roof_form="gable", height_m=8.5)
    result.update(changes)
    return result


class OrdinaryMasterTests(unittest.TestCase):
    def test_source_palette_and_exact_module(self):
        source = json.loads((ROOT / "voxel_character/common/assets/house/master.json").read_text())
        master = make_master(specimen())
        self.assertEqual(master["materials"], source["materials"])
        rail = lambda m: next(c for c in m["components"] if c["id"] == "eave_rail")
        self.assertEqual(rail(master), rail(source))
        self.assertEqual(master["provenance"]["reused_exact_components"], ["eave_rail"])

    def test_lod_does_not_change_master(self):
        base = make_master(specimen())
        self.assertEqual(base, make_master(specimen(lod="coarse")))
        self.assertEqual(base, make_master(specimen(lod="detailed", detailed=True)))
        base["materials"]["plaster"] = "ffffff"
        self.assertNotEqual(base, make_master(specimen()))

    def test_two_specimens_at_both_pitches(self):
        for style, roof in (("merchant", "gable"), ("old_timber", "twin_gable_z")):
            master = make_master(specimen(style=style, roof_form=roof))
            for pitch in (.5, .25):
                with self.subTest(style=style, pitch=pitch):
                    compiled = compile_master(master, {"pitch": pitch})
                    self.assertTrue(compiled["valid"], compiled["constraints"])
                    self.assertLess(compiled["candidate_cells"], 60000)
                    rendered = make_render_data(compiled)
                    self.assertLess(rendered["quad_count"], 1500)
                    self.assertEqual(rendered["bounds"], {"min": [-3.5, 0, -4], "max": [3.5, 8.5, 4]})
                    self.assertTrue(any(row[5] == "glass" for row in compiled["cells"]))
                    self.assertTrue(any(row[4] == "door" for row in compiled["cells"]))

    def test_all_styles_roofs_and_eras_validate(self):
        for style, roof, era in itertools.product(STYLES, ROOF_FORMS, ("early", "rebuilt", "late")):
            with self.subTest(style=style, roof=roof, era=era):
                master = make_master(specimen(style=style, roof_form=roof, construction_era=era))
                validate_master(master, .5)

    def test_representative_style_samples(self):
        for style, roof in zip(STYLES, ("gable", "steep_gable", "twin_gable_x", "shed", "hip", "flat")):
            master = make_master(specimen(style=style, roof_form=roof))
            compiled = compile_master(master, {"pitch": .5})
            self.assertTrue(compiled["valid"], (style, compiled["constraints"]))

    def test_all_authored_and_expanded_bounds_fit(self):
        for style, roof in itertools.product(STYLES, ROOF_FORMS):
            for width, depth, height, floors in ((7,8,8.5,2),(16.5,28.5,12.5,3),(3,3.5,5,1)):
                master = make_master(specimen(style=style, roof_form=roof, width_m=width,
                                             depth_m=depth, height_m=height, floors=floors))
                components = {c["id"]: c for c in master["components"]}
                envelope = master["metadata"]["envelope"]
                for instance in master["instances"]:
                    for op in components[instance["component"]]["operations"]:
                        if op["action"] == "cut":
                            continue
                        placement = compose(transform(instance.get("transform")), transform(op.get("transform")))
                        bounds = shape_bounds(prepare_shape(op["shape"], .5))
                        corners = [apply(placement, p) for p in itertools.product(*zip(*bounds))]
                        for axis in range(3):
                            lo, hi = min(p[axis] for p in corners), max(p[axis] for p in corners)
                            context = (style, roof, width, depth, instance["id"], op["id"], axis, lo, hi)
                            self.assertGreaterEqual(lo+1e-8, envelope["min"][axis], context)
                            self.assertLessEqual(hi-1e-8, envelope["max"][axis], context)

    def test_era_changes_authored_shapes(self):
        early = make_master(specimen(construction_era="early"))
        late = make_master(specimen(construction_era="late"))
        self.assertNotEqual(early["components"], late["components"])

    def test_required_styles_are_physically_distinct(self):
        masters = {style: make_master(specimen(style=style)) for style in STYLES}
        components = lambda style: {c["id"]: c for c in masters[style]["components"]}
        self.assertIn("shop_canopy", components("merchant"))
        self.assertIn("shop_canopy", components("artisan"))
        self.assertNotIn("shop_canopy", components("garden"))
        self.assertTrue(any(o["id"] == "closed_left_leaf" for o in components("port")["wall_0_front"]["operations"]))
        self.assertTrue(any(o["id"] == "workshop_flue" for o in components("artisan")["chimney"]["operations"]))
        self.assertNotEqual(components("old_timber")["wall_0_front"]["operations"][0]["shape"],
                            components("old_timber")["wall_1_front"]["operations"][0]["shape"])

    def test_invalid_specs_rejected(self):
        for changes in ({"width_m":float("nan")}, {"height_m":3}, {"floors":True},
                        {"floors":0}, {"style":"unknown"}, {"roof_form":"unknown"}):
            with self.assertRaises(ValueError):
                make_master(specimen(**changes))


if __name__ == "__main__":
    unittest.main()
