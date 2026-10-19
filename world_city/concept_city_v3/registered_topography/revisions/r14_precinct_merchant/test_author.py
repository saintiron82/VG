import json,math,unittest
from . import author as a
class Interfaces(unittest.TestCase):
 def test_sources_and_supports(self):
  for p,h in {**a.REFERENCES,**a.SUPPORT_REFERENCES}.items():self.assertEqual(a.R04.sha(a.CITY/p),h)
  self.assertEqual(a.SUPPORT['bounds']['max'][1],7.5);self.assertEqual(a.MERCHANT_SUPPORT['top_y_m'],3.5)
  self.assertEqual(len(a.GUARD['placements']),1);self.assertFalse(a.GUARD['owned_floors'])
 def test_all_gate_floors(self):
  for p in a.HANDOFF['properties']:
   for q in p['finite_gate_approach']['polygon_xz_m']:
    r=a.owner_at(*q);self.assertAlmostEqual(a.source_surface_height_at(r,*q),p['finished_floor_y_m'],8)
    self.assertAlmostEqual(a.surface_height_at(r,*q),p['finished_floor_y_m'],8)
 def test_profile_planes(self):
  for r in a.collar.TRIANGLES:
   x,z,c=r['plane_y_xz_m'];self.assertLessEqual(math.hypot(x,z),.12000001)
   for p in r['vertices_xyz_m']:self.assertAlmostEqual(x*p[0]+z*p[2]+c,p[1],9)
 def test_repaired_native_coverage(self):
  report=json.loads((a.HERE/'ownership_audit_repaired.json').read_bytes())
  self.assertEqual(len(report['groups']),18)
  for r in report['groups']:
   self.assertLess(abs(r['missing_native_mask_area_m2']),1e-7);self.assertFalse(r['positive_overlaps']);self.assertLess(abs(r['partition_area_delta_m2']),1e-6)
 def test_bounded_tiles_partition_and_materials(self):
  for b in ([24,40,32,48],[24,48,32,56],[16,16,24,24],[-152,216,-144,224]):
   rs=a.surface_domains(b);self.assertAlmostEqual(sum(a.geo.polygon_area(r['polygon_xz_m']) for r in rs),(b[2]-b[0])*(b[3]-b[1]),6)
   idx=a.geo._SpatialIndex(4)
   for i,r in enumerate(rs):
    p=r['polygon_xz_m']
    if r['kind'].startswith('r14_') and r.get('render_land',True):self.assertTrue(r.get('material'))
    for j in idx.candidates(p):self.assertLess(a.geo.polygon_area(a.geo.convex_intersection(p,rs[j]['polygon_xz_m'])),1e-7)
    idx.add(i,p)
 def test_inherited_water_and_old_exclusions(self):
  self.assertIs(a.finite_water_polygons,a.prior.finite_water_polygons)
  self.assertIs(a.water_height_at,a.prior.water_height_at)
  self.assertTrue(set(a.MERCHANT['replaced_placement_ids']).issubset(a.EXCLUDED));self.assertEqual(len(a.MERCHANT['replaced_placement_ids']),39)
 def test_finite_recovered_corner(self):
  r=a.recovered_corner.RECORDS[0];mid=[sum(p[k] for p in r['polygon_xz_m'])/3 for k in (0,1)]
  self.assertEqual(a.owner_at(*mid)['owner_id'],r['owner_id'])
  for p in r['triangle_xyz_m']:self.assertEqual(a.source_surface_height_at(r,p[0],p[2]),p[1])
  rs=[q for q in a.surface_domains([-248,-8,-240,0]) if q['owner_id']==r['owner_id']]
  self.assertAlmostEqual(sum(a.geo.polygon_area(q['polygon_xz_m']) for q in rs),a.recovered_corner.DATA['area_m2'],14)
 def test_no_new_rendered_public_seam(self):
  d=json.loads((a.HERE/'profile_interfaces.json').read_bytes())
  self.assertEqual(len(d['public_seam_failures']),84)
  self.assertTrue(all(r['classification']!='new_rendered_seam_failure' for r in d['public_seam_failures']))
  for k in ('r14_merchant_gate/r14_public_profile','r14_public_profile/road','r14_public_profile/road_shoulder'):
   self.assertLess(d['shared_edges'][k]['maximum_rendered_linear_edge_difference_m'],1e-9)
if __name__=='__main__':unittest.main()
