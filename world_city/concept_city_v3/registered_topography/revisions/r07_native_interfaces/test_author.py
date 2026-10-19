import unittest, math
from . import author as a

def center(p):return [sum(v[k] for v in p)/len(p) for k in (0,1)]
def grade(t):
 p,q,r=t;dx=q[0]-p[0];dz=q[2]-p[2];ex=r[0]-p[0];ez=r[2]-p[2];det=dx*ez-dz*ex
 if abs(det)<1e-12:return 0
 return math.hypot(((q[1]-p[1])*ez-(r[1]-p[1])*dz)/det,((r[1]-p[1])*dx-(q[1]-p[1])*ex)/det)

class NativeInterfacesTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.contract=a.build_contract();a._owners()
 def test_full_inherited_contract(self):
  c=self.contract
  self.assertEqual(len(c['water_surfaces']),6);self.assertEqual(len(c['water_domain_polygons']),80)
  self.assertEqual(len(c['water_support']['exterior_banks']),1199);self.assertEqual(len(c['ordinary_foundations']),616)
  self.assertEqual(c['source_plan_sha256'],a.R04.old.SOURCE_SHA);self.assertEqual(len(c['excluded_source_ids']),85)
  self.assertEqual(len(c['native_density_components']),45);self.assertEqual(len(c['density_ground_ledger']['grounds']),19)
  self.assertTrue(c['density_ground_ledger']['no_new_floor_planes']);self.assertIn('review_bounds_xz_m',c)
 def test_exact_replacement_owners(self):
  self.assertFalse(any(a.R04.prior.is_excluded(r,a.EXCLUDED) for r in a.OWNERS))
  self.assertEqual(sum(r['kind']=='building_body_hole' and r['owner_id'].startswith('DENS_') for r in a.OWNERS),45)
  self.assertFalse(any(r['kind']=='port_common_hole' for r in a.OWNERS))
  self.assertTrue(all(r['source_mass_id'] not in a.EXCLUDED for r in a.ordinary_foundation_contracts()))
 def test_port_native_masks_and_tie(self):
  self.assertEqual(len(a.FLOORS),14)
  self.assertAlmostEqual(sum(a.geo.polygon_area(r['polygon_xz_m']) for r in a.actual_shared_port_regions()),59.186101074655,places=6)
  for r in a.actual_shared_port_regions():
   p=center(r['polygon_xz_m']);o=a.owner_at(*p)
   self.assertIn(o['kind'],('native_port_hole','bridge_hole'))
   self.assertAlmostEqual(a.source_surface_height_at(o,*p),2.2,places=7)
  wet=[r for r in a.FLOORS if r['datum']=='pier_top_plus2.2'];self.assertEqual(len(wet),3)
  self.assertFalse(any(r.get('owner_id') in {f['owner_id'] for f in wet} for r in a.OWNERS))
 def test_courts_are_bounded_level(self):
  for r in a.DENSITY['courts']:
   p=center(r['polygon_xz_m']);o=a.owner_at(*p)
   self.assertEqual(o['kind'],'density_court');self.assertEqual(a.source_surface_height_at(o,*p),2.5)
 def test_partition_coverage_and_no_water_render(self):
  boxes=[[304,98,312,106],[352,88,360,96],[-288,-208,-280,-200],[160,-200,168,-192],[-128,120,-120,128],[104,424,112,432]]
  for box in boxes:
   rs=a.surface_domains(box);self.assertAlmostEqual(sum(a.geo.polygon_area(r['polygon_xz_m']) for r in rs),64,places=5)
   for i,r in enumerate(rs):
    if r['kind']=='water_hole':self.assertFalse(r['render_land'])
    for q in rs[:i]:self.assertLess(a.geo.polygon_area(a.geo.convex_intersection(r['polygon_xz_m'],q['polygon_xz_m'])),1e-6)
 def test_exact_approach_triangle_planes(self):
  self.assertEqual(len(a.approaches.TRIANGLES),36868)
  for r in a.approaches.TRIANGLES[::31]:
   self.assertLessEqual(grade(r['triangle_xyz_m']),.120001)
   p=center(r['polygon_xz_m']);self.assertAlmostEqual(a.approaches.height_at(*p),a.R04.point_y(r['triangle_xyz_m'],*p),places=6)
  out=a.supplemental_surface_domains([-288,-208,-280,-200]);self.assertTrue(out)
  for r in out:
   for p in r['vertices_xyz_m']:self.assertAlmostEqual(p[1],a.R04.point_y(r['triangle_xyz_m'],p[0],p[2]),places=8)
   self.assertIn('support',r);self.assertIn('material',r)
 def test_landing_outer_handoff(self):
  self.assertEqual(len(a.landings.TRIANGLES),17243)
  for s in a.landings.boundary_segments()[::7]:
   p=s['a_xyz_m'];q=s['b_xyz_m']
   for t in (0,.37,1):
    x=p[0]+t*(q[0]-p[0]);z=p[2]+t*(q[2]-p[2]);y=p[1]+t*(q[1]-p[1])
    self.assertAlmostEqual(a.landings.boundary_y(x,z),y,places=7)
    self.assertAlmostEqual(a.surface_height_at(dict(kind='road',owner_id='TEST',road_id='TEST'),x,z),y,places=7)
 def test_unchanged_outside_bounds(self):
  for p in [(-500,-450),(500,550),(-450,200)]:
   self.assertEqual(a.height_at(*p),a.prior.height_at(*p))
if __name__=='__main__':unittest.main()
