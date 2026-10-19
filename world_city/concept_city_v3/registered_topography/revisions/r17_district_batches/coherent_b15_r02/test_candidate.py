"""Run from repository root with PYTHONPATH=. and bytecode disabled."""
import json,math,unittest
from .. import author as a
from .source_preflight import HERE,FABRIC,read

def load(n):return json.loads((HERE/n).read_bytes())
class CandidateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.patch=load('candidate_scene_patch.json');cls.report=load('composition_report.json');cls.owners=load('owners.json')['owners']
 def test_base_binding(self):self.assertEqual(self.patch['base_scene_sha256'],a.SCENE_SHA256)
 def test_unique_source_keys(self):self.assertEqual(len(self.patch['surface_edits']),len({(r['material'],r['triangle_index'])for r in self.patch['surface_edits']}))
 def test_upward_source_emitter(self):
  for order in ([[0,2,0],[0,2,1],[1,2,0]],[[0,2,0],[1,2,0],[0,2,1]]):
   self.assertTrue(all(a.normal_y(t)>0 for t in a.fan_upward(order)))
 def test_all_emitted_vertices_and_winding(self):
  for m,vs in self.patch['appended_surfaces'].items():
   self.assertEqual(len(vs)%3,0)
   for k in range(0,len(vs),3):self.assertGreaterEqual(a.normal_y(vs[k:k+3]),-1e-10);self.assertTrue(all(math.isfinite(v)for p in vs[k:k+3]for v in p))
 def test_no_unknown_source_filling(self):self.assertLessEqual(max(r['unknown_source_area_m2']for r in self.report['fields']),1e-7)
 def test_native_support_and_holes(self):
  d=load('support_review_r01.json');self.assertEqual(d['status'],'PASS_FINITE_EARTH_BEARING');self.assertEqual(len(d['native_bearings']),422);self.assertEqual(len([o for o in self.owners if o['action']=='hole']),422)
 def test_active_route_grade_coverage_and_sides(self):
  d=load('effective_route_audit_r01.json');self.assertEqual(d['status'],'PASS_LOCAL_FIELDS');self.assertFalse(d['failures']);self.assertFalse(d['interior_side_contacts']);self.assertFalse(d['baseline_public_grade_exceedances'])
 def test_water_and_wet_banks(self):self.assertEqual(load('water_review.json')['status'],'PASS')
 def test_public_datum_unchanged(self):self.assertEqual(load('canonical_public_height_parity.json')['status'],'PASS')
 def test_all_physical_doors_and_public_roots(self):
  self.assertEqual(len(load('route_handoff.json')['door_routes']),117);self.assertEqual(load('fixed_public_seams.json')['count'],22)
 def test_complete_retirement(self):
  d=load('retirement.json');self.assertEqual(len(d['records']),67);self.assertEqual({r['removed_foundation_proxy_id']for r in d['records']},set(self.patch['removed_foundation_proxy_ids']))
 def test_new_terminal_native_clearance(self):
  pack=read('resolved_placements.json');routes=load('route_handoff.json');polys=[n['terminal_profile']['polygon_xz_m']for n in routes['nodes']if 'terminal_profile'in n]
  for p in polys:
   for inst in pack['placements']:
    for q in inst.get('native_walking_obstacles_xz_m',[]):
     x=a.clip(p,q)
     self.assertLessEqual(a.geo.polygon_area(x)if x else 0.,1e-7,(inst['id'],p))
 def test_exact_top_partition_and_native_exclusion(self):
  d=load('emission_audit_r01.json');self.assertFalse(d['partition_failures']);self.assertFalse(d['failed_walk_checks']);self.assertFalse(d['native_top_overlaps']);self.assertFalse(d['downward_emitted_tops']);self.assertFalse(d['source_hash_errors'])
if __name__=='__main__':unittest.main()
