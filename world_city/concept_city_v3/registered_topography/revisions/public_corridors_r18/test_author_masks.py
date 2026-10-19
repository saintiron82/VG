"""Regression for accepted-domain rebinding and union-valued water masks."""
import json,unittest
from . import author_patch as p
from ..r17_district_batches import author as a
class MaskContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.masks,cls.refs=p.input_masks(a.load_scene());cls.ids={r['id']for r in cls.masks};cls.paths={r['path']for r in cls.refs}
 def test_current_binding(self):
  self.assertTrue(any(q.endswith('/district_bound_r04.json')for q in self.paths))
  self.assertTrue(any('/coherent_b15_r02/scene_patch.json'in q for q in self.paths))
  self.assertFalse(any('/coherent_b15_r01/'in q for q in self.paths))
  self.assertTrue(any(q.endswith('/cemetery_surface_patch.json')for q in self.paths))
 def test_side_only_water_repair_is_not_a_ground_hole(self):
  patch=json.loads((a.CITY/'assemblies/waterworks/registered_water_completion_r01/approaches_r03/surface_patch.json').read_bytes())
  self.assertFalse(any(q.startswith(patch['id']+':')for q in self.ids))
 def test_exact_water_ownership(self):
  d=json.loads((a.CITY/'assemblies/waterworks/registered_water_completion_r01/approaches_r02/public_handoff.json').read_bytes())
  for r in d['finite_field_owners']:
   for j,poly in enumerate(r['polygons_xz_m']):
    matches=[m for m in self.masks if m['id']==r['id']+':'+str(j)]
    self.assertEqual([m['polygon_xz_m']for m in matches],[poly])
  for r in d['native_deck_holes']:self.assertIn(r['id'],self.ids)
 def test_all_masks_are_finite(self):
  for r in self.masks:
   self.assertGreaterEqual(len(r['polygon_xz_m']),3)
   self.assertGreater(a.geo.polygon_area(r['polygon_xz_m']),0)
 def test_source_refs_readback(self):
  for r in self.refs:self.assertEqual(a.sha(a.ROOT/r['path']),r['sha256'])
if __name__=='__main__':unittest.main()
