"""Source, finite ownership, fixed seam, width and clipping regressions."""
import json,math,copy,unittest
from . import select_profiles as s,finite,build_patch as b,audit_patch
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.concept_city_v3.registered_integration.r6 import merge_patches
from world_city.runtime_city.checks import placement as g
HERE=s.HERE

def read(name):return json.loads((HERE/name).read_text())
class Approaches(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.scene=a.load_scene();cls.patch=read('surface_patch.json');cls.fields=read('fields.json');cls.audit=read('exact_audit.json');cls.graph=read('connectivity_audit.json');cls.report=read('patch_report.json')
 def test_corrected_scene_and_frozen_bridge_refs(self):
  self.assertEqual(self.fields['base_scene_sha256'],a.SCENE_SHA256);self.assertEqual(self.fields['source_interfaces_sha256'],a.sha(HERE.parent/'crossing_interfaces.json'));self.assertEqual(self.fields['source_profiles_sha256'],a.sha(HERE/'profiles.json'))
 def test_three_existing_seals_unchanged(self):
  for folder in[HERE.parent,HERE.parent.parent/'registered_services_r01',HERE.parent.parent/'registered_mill_r01']:
   manifest=json.loads((folder/'freeze_manifest.json').read_text());files=manifest['owned_files']
   for path,digest in files.items():self.assertEqual(a.sha(folder/path),digest,str(folder/path))
 def test_all_exact_checks_current_and_pass(self):
  self.assertEqual(self.audit['patch_sha256'],a.sha(HERE/'surface_patch.json'));self.assertEqual(self.audit['field_sha256'],a.sha(HERE/'fields.json'));self.assertEqual(self.audit['status'],'PASS');self.assertTrue(all(self.audit['checks'].values()))
 def test_network_components_and_named_road_coverage(self):
  self.assertEqual(self.graph['fields_sha256'],a.sha(HERE/'fields.json'));self.assertEqual(self.graph['status'],'PASS');self.assertEqual(len(self.graph['components']),2);self.assertFalse(self.graph['incompatible_edges']);self.assertLess(max(r['unowned_named_road_area_m2']for r in self.graph['named_road_coverage']),1e-7)
 def test_all_eight_full_width_deck_edges(self):
  self.assertEqual(len(self.audit['deck_edges']),8)
  for r in self.audit['deck_edges']:self.assertLess(r['uncovered_length_m'],1e-6);self.assertLess(r['maximum_height_delta_m'],1e-6)
 def test_five_public_terminal_profiles(self):
  hand=read('public_handoff.json');self.assertEqual(hand['field_source_sha256'],a.sha(HERE/'fields.json'));self.assertEqual(len(hand['exact_public_terminals']),5);self.assertEqual(len(self.audit['public_terminals']),5)
  for r in self.audit['public_terminals']:self.assertLess(r['uncovered_length_m'],1e-6);self.assertLess(r['maximum_height_delta_m'],1e-6)
 def test_analytic_full_width_all_cross_sections(self):
  for p in self.fields['profiles']:
   for r in p.get('width_proof',[]):self.assertGreaterEqual(r['minimum_full_transverse_width_m'],p['road_width_m']-1e-8)
 def test_normals_and_gradients(self):
  for p in self.fields['profiles']:
   for t in p['triangles']:self.assertGreater(a.normal_y(t['vertices_xyz_m']),1e-10);self.assertLessEqual(math.hypot(*t['plane_y_xz_m'][:2]),.12000001)
 def test_original_hash_binding_rejects_stale_source(self):
  patch=copy.deepcopy(self.patch);patch['surface_edits'][0]['source_triangle_sha256']='0'*64
  with self.assertRaises(ValueError):merge_patches.validate_against_scene(self.scene,patch)
 def test_original_indices_unique_and_valid(self):
  merge_patches.merge([self.patch],a.SCENE_SHA256);self.assertTrue(merge_patches.validate_against_scene(self.scene,self.patch))
 def test_water_and_submerged_geometry_unchanged(self):
  self.assertNotIn('water',self.patch['source_surface_hashes']);self.assertNotIn('water',self.patch['appended_surfaces']);self.assertFalse(self.audit['submerged_removal_contacts']);self.assertTrue(self.audit['checks']['old_water_values_and_order_unchanged'])
 def test_finite_top_and_bank_area_partitions(self):
  for r in self.report['dry_top_partitions']:self.assertAlmostEqual(r['old_area_m2'],r['retained_area_m2']+r['removed_area_m2'],places=7)
  for r in self.report['side_partitions']:self.assertAlmostEqual(r['before_area_m2'],r['retained_area_m2']+r['removed_area_m2'],places=6)
 def test_bank_cut_thresholds_and_lateral_support(self):
  self.assertFalse(self.report['missing_boundary_segments']);self.assertFalse(self.audit['interior_bank_contacts'])
  for r in self.report['removed_side_pieces']:
   self.assertIn(r['cut_kind'],['native_deck_above_underside','approach_above_finished_floor'])
   for v in r['vertices_xyz_m']:self.assertGreaterEqual(v[1]-a.common.height(r['cut_plane_y_xz_m'],[v[0],v[2]]),-1e-7)
 def test_empty_and_reversed_clipping(self):
  box=[[0,0],[2,0],[2,2],[0,2]];mask=[[1,-1],[3,-1],[3,1],[1,1]]
  self.assertEqual(finite.intersect(box,[]),[]);self.assertEqual(finite.difference(box,[]),[box]);self.assertAlmostEqual(g.polygon_area(finite.intersect(box,mask)),1);self.assertAlmostEqual(g.polygon_area(finite.intersect(box,mask[::-1])),1);self.assertAlmostEqual(sum(g.polygon_area(p)for p in finite.difference(box,mask)),3)
 def test_near_collinear_actual_road_edge_interval(self):
  p=[317.46481338275066,298.2493169869308];q=[317.64179033184485,299.52075673514736];tri=self.scene['surfaces']['ground_earth'][8260*3:8260*3+3];poly=[[v[0],v[2]]for v in tri];span=finite.interval(p,q,poly)
  self.assertIsNotNone(span);self.assertGreater((span[1]-span[0])*math.dist(p,q),.2)
 def test_short_edge_actual_source_coverage_regression(self):
  p=next(r for r in read('profiles.json')['profiles']if r['id']=='MARKET_NORTH:END_APPROACH');ix=a.TriangleIndex(self.scene,[p['polygon_xz_m']]);check=finite.audit(ix,p['polygon_xz_m']);self.assertLess(check['missing_area_m2'],1e-7);self.assertLess(check['excess_area_m2'],1e-7);q=[75.6,-300.5];self.assertTrue(any(r['triangle_index']==2230 and r['material']=='road'and g.point_in_convex_polygon(q,r['polygon_xz_m'])for r in ix.rows))
if __name__=='__main__':unittest.main(verbosity=2)
