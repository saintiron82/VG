"""Finite sliver and route ownership regression checks; no replay acceptance claim."""
import pathlib,sys,json,math,unittest
ROOT=next(p for p in pathlib.Path(__file__).resolve().parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.assemblies.waterworks.registered_water_completion_r01.approaches_r03 import audit_residuals as a,build
from world_city.concept_city_v3.registered_integration.r6 import merge_patches as m
class RepairSources(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.base=a.read(a.BASE);c.actual=a.read(a.ACTUAL);c.patch=a.read(a.H/'surface_patch.json');c.audit=a.read(a.H/'residual_audit.json');c.old=a.read(a.OLD/'surface_patch.json');c.route=a.read(a.H/'route_handoff.json');c.field=next(p for p in a.read(a.OLD/'fields.json')['profiles']if p['id']=='NORTH_SHARED_JUNCTION')
 def test_exact_bound_scenes(self):
  self.assertEqual(a.sha(a.BASE),self.audit['base_scene']['sha256']);self.assertEqual(a.sha(a.ACTUAL),self.audit['actual_scene']['sha256']);m.validate_against_scene(self.base,self.patch)
 def test_exact_four_retired_originals(self):
  self.assertEqual({r['triangle_index']for r in self.patch['surface_edits']},{1931,1968,1989,2130});self.assertTrue(all(r['material']=='road'and r['replacement_triangles_xyz_m']==[]for r in self.patch['surface_edits']));self.assertEqual(self.patch['appended_surfaces'],{})
 def test_genuine_failed_triangle_fixture(self):
  r=next(r for r in self.audit['candidates']if r['triangle_index']==1931);self.assertEqual(r['vertices_xyz_m'],self.actual['surfaces']['road'][1833*3:1833*3+3]);self.assertAlmostEqual(r['actual_3d_area_m2'],.040501245719884046);self.assertGreater(r['projected_area_m2'],1e-10);self.assertLess(r['projected_area_m2']/r['actual_3d_area_m2'],1e-6);self.assertGreater(r['clearance_above_finished_surface_m'][0],.4)
 def test_every_source_edge_has_actual_flat_support(self):
  masks=[t['polygon_xz_m']for t in self.field['triangles']]
  for r in self.audit['candidates']:
   for p,q in zip(r['vertices_xyz_m'],r['vertices_xyz_m'][1:]+r['vertices_xyz_m'][:1]):
    spans=a.spans([p[0],p[2]],[q[0],q[2]],masks);self.assertEqual(len(spans),1);self.assertLess(spans[0][0],1e-7);self.assertGreater(spans[0][1],1-1e-7)
 def test_disjoint_source_composition_and_no_other_edits(self):
  old={(r['material'],r['triangle_index'])for r in self.old['surface_edits']};self.assertFalse(old&{(r['material'],r['triangle_index'])for r in self.patch['surface_edits']});merged=m.merge([self.old,self.patch],a.sha(a.BASE));self.assertEqual(len(merged['surface_edits']),len(self.old['surface_edits'])+4);self.assertEqual(merged['appended_surfaces'],self.old['appended_surfaces']);self.assertFalse(self.patch['removed_foundation_proxy_ids'])
 def test_route_avoids_closed_terminal_but_retains_axes(self):
  failed=a.read(a.CITY/'traversal_r5/revisions/r06_r8_precinct/district_services_r02/prepared_runtime.json');old=next(r for r in failed['routes']if r['id']=='NORTH_TWO_BRIDGE_NETWORK')['points'];new=self.route['points_xyz_m'];self.assertEqual(new[:10],old[:10]);self.assertEqual(new[12:],old[11:]);self.assertEqual(self.route['reverse_points_xyz_m'],list(reversed(new)));self.assertNotIn(old[10],new)
 def test_conservative_capsule_tube_fully_supported(self):
  masks=[t['polygon_xz_m']for t in self.field['triangles']]+[b['traffic_polygon_xz_m']for b in a.read(a.H.parent/'crossing_interfaces.json')['crossings']if b['id']in self.field['bridge_ids']];missing=sum(a.g.polygon_area(q)for p in self.route['tube_polygons_xz_m']for q in a.finite.subtract([p],masks));self.assertLess(missing,1e-7);self.assertGreater(self.route['conservative_clear_tube_radius_m'],self.route['capsule_radius_m'])
 def test_prior_sealed_files_unchanged(self):
  for folder in[a.OLD,a.CITY/'traversal_r5/revisions/r06_r8_precinct/district_services_r02']:
   seal=a.read(folder/'freeze_manifest.json')
   for p,h in seal['owned_files'].items():self.assertEqual(a.sha(folder/p),h)
if __name__=='__main__':unittest.main(verbosity=2)
