"""Cache-only integrity and exact finite native floor checks."""
import json,math,unittest
from build_unions import HERE,ROOT,REGISTERED,ref,geo,terrain
from voxel_character.common import core

class UnionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.p=json.loads((HERE/'resolved_placements.json').read_text());cls.r=json.loads((HERE/'compile_report.json').read_text());cls.o=json.loads((HERE/'replacement_overlay.json').read_text());cls.old=json.loads((ROOT/cls.p['base_pack']['path']).read_text())
 def test_sealed_inputs_and_source_cache_hashes(self):
  self.assertEqual(ref(ROOT/self.p['base_pack']['path']),self.p['base_pack'])
  for a in self.p['assets']:
   self.assertEqual(ref(ROOT/a['source']['path']),a['source']);self.assertEqual(ref(ROOT/a['cache']['path']),a['cache']);s=json.loads((ROOT/a['source']['path']).read_text());r=json.loads((ROOT/a['cache']['path']).read_text());self.assertEqual(core.digest(s),a['master_hash']);self.assertEqual(r['master_hash'],a['master_hash'])
 def test_only_four_runs_replace_thirty_three_modules(self):
  self.assertEqual(len(self.o['remove_placement_ids']),33);self.assertEqual(len(self.o['add_placement_ids']),4);self.assertEqual(len(self.p['placements']),39)
  old={x['id']:x for x in self.old['placements']};new={x['id']:x for x in self.p['placements']}
  for id,p in old.items():
   if id not in self.o['remove_placement_ids']:self.assertEqual(p,new[id])
  for p in self.p['placements']:self.assertEqual(p['scale'],[1,1,1])
 def test_no_internal_run_end_faces(self):
  self.assertEqual(self.r['internal_joints_closed'],29)
  for a in self.p['assets']:
   if '_union_r03' not in a['id']:continue
   r=json.loads((ROOT/a['cache']['path']).read_text());self.assertEqual(r['quad_count'],14)
   for g in r['groups']:
    for quad in g['quads']:
     if max(p[0] for p in quad)-min(p[0] for p in quad)<1e-8:self.assertTrue(any(abs(quad[0][0]-r['bounds'][key][0])<1e-8 for key in ('min','max')))
 def test_floor_rectangles_have_native_backing_and_dry_ownership(self):
  water=terrain.finite_water_polygons()
  for f in self.p['owned_floors']:
   if not f['placement_id'].startswith('PORT_QUAY_RUN'):continue
   self.assertTrue(geo.convex_polygon_contains(f['native_section_polygon_xz_m'],f['polygon_xz_m'],1e-7))
   self.assertTrue(all(geo.intersection_area(f['polygon_xz_m'],w['polygon_xz_m'])<1e-7 for w in water))
  for r in self.r['requests']:self.assertFalse(r['missing_floor_cells']);self.assertTrue(all(j['all_occupied'] for j in r['former_internal_joints']));self.assertLess(r['candidate_cells'],400000)
 def test_bridge_and_navigation_reservations(self):
  b=json.loads((ROOT/'world_city/concept_city_v3/assemblies/waterworks/registered_bridge/candidate.json').read_text());reserves=[r['polygon_xz_m'] for key in ('deck_regions','approach_regions') for r in b[key]]+[b['navigation_channel']['underdeck_polygon_xz_m']]+b['navigation_channel']['proposed_water_approach_polygons_xz_m']
  for p in self.p['placements']:
   if p['id'].startswith('PORT_QUAY_RUN'):self.assertTrue(all(geo.intersection_area(p['outer_footprint_xz_m'],q)<1e-7 for q in reserves))
 def test_rebound_flat_tie_and_no_view_claim(self):
  c=json.loads((HERE/'finite_coownership_addendum.json').read_text());self.assertEqual(c['source_pack'],ref(HERE/'resolved_placements.json'));self.assertTrue(c['proof']['whole_field_flat']);self.assertLess(c['proof']['coverage_error_m2'],1e-6);self.assertFalse(self.p['completion_claims']['actual_visual_review'])

if __name__=='__main__':unittest.main(verbosity=2)
