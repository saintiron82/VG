"""Cheap source-only regressions; no native compile or scene export."""
import json,unittest
from . import author as a

class SourceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.plan=a.build_contract();cls.audit=a.bounded_source_audit()
 def test_inputs_are_exact(self):
  for name,value in a.EXPECTED.items():self.assertEqual(a.sha(a.SOURCE/name),value)
 def test_all26_ids_preserved(self):
  before=a.read('selection.json')['all_candidate_status'];after=self.plan['all26_candidate_ledger']
  self.assertEqual([r['parcel_id'] for r in before],[r['parcel_id'] for r in after]);self.assertEqual(len(after),26)
  self.assertEqual(sum(r['r16_stage']=='native_footing_and_access_source_candidate' for r in after),4);self.assertFalse(any(r['r16_active'] for r in after))
 def test_exact_native_bottom_masks(self):
  self.assertEqual(len(a.native_holes()),22);self.assertAlmostEqual(sum(a.geo.polygon_area(r['polygon_xz_m']) for r in a.native_holes()),934.75,7)
  for r in a.native_holes():self.assertEqual(r['native_bottom_y_m'],2.0);self.assertEqual(r['finished_threshold_y_m'],2.5);self.assertFalse(r['render_land']);self.assertFalse(r['additional_support_required'])
 def test_courts_are_plane_material_only(self):
  self.assertEqual(len(a.court_regions()),2);self.assertAlmostEqual(sum(a.geo.polygon_area(r['polygon_xz_m']) for r in a.court_regions()),110.,7)
  for r in a.court_regions():self.assertEqual(r['kind'],'existing_plane_court_material');self.assertFalse(r['activation'])
 def test_no_native_court_overlap(self):
  rows=a.native_holes()+a.court_regions();overlap=0.
  for i,r in enumerate(rows):
   for q in rows[i+1:]:overlap+=a.geo.polygon_area(a.geo.convex_intersection(r['polygon_xz_m'],q['polygon_xz_m']))
  self.assertLess(overlap,1e-8)
 def test_all_ground_coverage_exact(self):
  for r in self.audit['owner_checks']:
   self.assertLess(r['missing_area_m2'],1e-8);self.assertLess(r['overlap_area_m2'],1e-8);self.assertEqual(r['height_delta_from_2_5_m'],0.)
 def test_threshold_datum_and_internal_reservations(self):
  doors=self.plan['source_thresholds'];self.assertEqual(len(doors),15)
  for r in doors:self.assertEqual(r['actual_door_xyz_m'][1],2.5)
  reserved={r['route_id'] for r in a.walk_reservations()};self.assertEqual(len(reserved),17)
  for r in a.read('terrain_handoff.json')['internal_walkspaces']:self.assertIn(r['id'],reserved)
 def test_terminal_widths_and_disjoint_unions(self):
  self.assertEqual({r['width_m'] for r in a.terminal_domains()},{2.,3.5});self.assertEqual(self.audit['terminal_overlap_m2'],0.)
  rows=a.terminal_domains();overlap=0.
  for i,r in enumerate(rows):
   for q in rows[i+1:]:overlap+=a.geo.polygon_area(a.geo.convex_intersection(r['polygon_xz_m'],q['polygon_xz_m']))
  self.assertLess(overlap,1e-7)
 def test_water_ownership_protected(self):
  ref=a.read('terrain_handoff.json')['bound_terrain_contract'];p=a.ROOT/ref['path'];self.assertEqual(a.sha(p),ref['sha256']);water=json.loads(p.read_bytes())['water_domain_polygons']
  for r in a.native_holes()+a.court_regions()+a.terminal_domains():
   for w in water:self.assertLess(a.geo.polygon_area(a.geo.convex_intersection(r['polygon_xz_m'],w['polygon_xz_m'])),1e-7)
 def test_no_implicit_activation_or_retirement(self):
  p=self.plan;self.assertFalse(p['active']);self.assertIsNone(p['r6_scene_binding']);self.assertEqual(p['retired_native_ids'],[]);self.assertEqual(p['whole_holding_pad_domains'],[]);self.assertEqual(p['additional_support_compile_budget_cells'],0)

if __name__=='__main__':unittest.main(verbosity=2)
