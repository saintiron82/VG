import unittest,math
from . import author as a
class ParkReservoirInterfaceTests(unittest.TestCase):
 def test_full_inheritance_and_native_water(self):
  c=a.build_contract();self.assertEqual(len(c['water_surfaces']),6);self.assertEqual(len(c['water_domain_polygons']),80);self.assertEqual(len(c['water_support']['exterior_banks']),1199)
  self.assertEqual(len(c['omit_source_waterbed_polygons']),253);self.assertEqual(len(c['omitted_water_bank_indices']),47);self.assertEqual(len(c['ordinary_foundations']),616)
  for r in a.RESERVOIR['superseded_reservoir_bank_faces']:self.assertEqual(c['water_support']['exterior_banks'][r['contract_index']],r['record'])
 def test_native_spill_one_owner(self):
  count=0
  for rec in a.REPORT['mask_lane_conflicts']:
   for p in rec['unowned_polygons_xz_m']:
    x=sum(q[0] for q in p)/len(p);z=sum(q[1] for q in p)/len(p);r=a.owner_at(x,z)
    self.assertEqual(r['kind'],'park_native_common_hole');self.assertFalse(r['render_land']);self.assertEqual(a.source_surface_height_at(r,x,z),8);count+=1
  self.assertGreater(count,0)
 def test_park_road_analytic_grade(self):
  mx=0;eps=.0001
  for x in range(-252*2,-240*2):
   for z in range(-56*2,-37*2):
    x1=x/2;z1=z/2
    dx=(a.road_height_at(a.ROAD,x1+eps,z1)-a.road_height_at(a.ROAD,x1-eps,z1))/(2*eps);dz=(a.road_height_at(a.ROAD,x1,z1+eps)-a.road_height_at(a.ROAD,x1,z1-eps))/(2*eps)
    mx=max(mx,math.hypot(dx,dz))
  self.assertLessEqual(mx,.120001)
 def test_finite_park_outer_seam(self):
  for i in range(65):
   t=i/64;x=a.BOUNDS[0]+t*(a.BOUNDS[2]-a.BOUNDS[0]);z=a.BOUNDS[1]+t*(a.BOUNDS[3]-a.BOUNDS[1])
   for p in [(x,a.BOUNDS[1]),(x,a.BOUNDS[3]),(a.BOUNDS[0],z),(a.BOUNDS[2],z)]:self.assertAlmostEqual(a.height_at(*p),a.prior.height_at(*p),places=8)
 def test_partition_and_traffic_keepout(self):
  for box in [[-248,-48,-240,-40],[-40,-340,-32,-332],[-32,-336,-24,-328]]:
   rs=a.surface_domains(box);self.assertAlmostEqual(sum(a.geo.polygon_area(r['polygon_xz_m']) for r in rs),64,places=5)
   for r in rs:
    if r['kind'] in ('reservoir_excavation_hole','reservoir_native_hole'):
     for owner in a.prior._owners():
      if owner['kind']=='road' and owner.get('road_id')=='RESERVOIR_SERVICE':self.assertLess(a.geo.polygon_area(a.geo.convex_intersection(r['polygon_xz_m'],owner['polygon_xz_m'])),1e-7)
 def test_training_actual_owners_and_exclusions(self):
  self.assertEqual(len(a.training.EXCLUDED),87)
  for rec in a.training.DATA['actual_public_surface_overrides']:
   p=rec['polygon_xz_m'];x=sum(q[0] for q in p)/len(p);z=sum(q[1] for q in p)/len(p);r=a.owner_at(x,z)
   self.assertEqual(r['kind'],'training_native_hole');self.assertEqual(a.source_surface_height_at(r,x,z),rec['actual_compiled_top_y_m'])
  self.assertIn('FAILED',a.training.contract()['status'])
 def test_all_welded_outer_edges(self):
  self.assertEqual(a.landings.SHA,'4808e6126a21750e74fe3ade88139a282c1b820584357783d73c0e64e5c313b4')
  mx=0;count=0
  for s in a.landings.boundary_segments():
   p=s['a_xyz_m'];q=s['b_xyz_m']
   for t in (0,.25,.5,.75,1):
    x=p[0]+t*(q[0]-p[0]);z=p[2]+t*(q[2]-p[2]);y=p[1]+t*(q[1]-p[1])
    h=a.landings.boundary_y(x,z);self.assertIsNotNone(h);mx=max(mx,abs(h-y));count+=1
    self.assertAlmostEqual(a.surface_height_at(dict(kind='road',road_id='TEST',owner_id='TEST'),x,z),y,places=7)
  self.assertLess(mx,1e-7);print('welded outer handoff',count,'samples max error',mx)
 def test_shared_tile_height(self):
  for z in [(-52+i/8) for i in range(129)]:
   x=-248;r=a.owner_at(x,z)
   self.assertEqual(a.surface_height_at(dict(r,review_tile_bounds_xz_m=[x-8,-56,x,-40]),x,z),a.surface_height_at(dict(r,review_tile_bounds_xz_m=[x,-56,x+8,-40]),x,z))
if __name__=='__main__':unittest.main()
