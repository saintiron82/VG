"""Bounded native source tests; canonical approach patch remains explicit dependency."""
import json,math,collections,unittest
from .audit import *
from .build_crossings import poly
from voxel_character.common import coordinate_planes,render_data
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import side_clearance
from world_city.concept_city_v3.registered_integration.r6 import apply_packs
class CrossingsTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.scene=a.load_scene();cls.pack=json.loads((HERE/'resolved_placements.json').read_text());cls.handoff=json.loads((HERE/'crossing_interfaces.json').read_text());cls.rows=[]
  for asset,p,h in zip(cls.pack['assets'],cls.pack['placements'],cls.handoff['crossings']):
   source=json.loads((ROOT/asset['source']['path']).read_text());c=coordinate_planes.compile_master(source,{'pitch':.2},max_candidate_cells=500000,max_output_cells=180000);r=render_data.make_render_data(c);cls.rows.append((asset,p,h,c,r))
 def test_common_replay_unit_scale_and_budget(self):
  for asset,p,h,c,r in self.rows:
   self.assertTrue(c['valid']);self.assertEqual(r,json.loads((ROOT/asset['cache']['path']).read_text()));self.assertEqual(ref(ROOT/asset['source']['path']),asset['source']);self.assertEqual(ref(ROOT/asset['cache']['path']),asset['cache']);self.assertEqual(p['scale'],[1,1,1]);self.assertLess(len(c['cells']),12000);self.assertLess(r['quad_count'],300)
 def test_actual_footprint_and_seams(self):
  for asset,p,h,c,r in self.rows:
   mn,mx=r['bounds']['min'],r['bounds']['max'];actual=poly(mn[0],mx[0],mx[2],[p['position_m'][0],p['position_m'][2]],p['yaw_rad']);self.assertLess(max(math.dist(x,y)for x,y in zip(actual,h['native_ownership_polygon_xz_m'])),1e-10);self.assertAlmostEqual(-mn[2],mx[2]);self.assertAlmostEqual(mx[1],1.2)
   for seam in h['approach_seams']:
    self.assertAlmostEqual(math.dist(*seam['xyz_m']),h['road_width_m']);self.assertTrue(all(v[1]==h['deck_top_y_m']for v in seam['xyz_m']))
 def test_full_width_actual_deck(self):
  for asset,p,h,c,r in self.rows:
   covers=[]
   for group in r['groups']:
    for q in group['quads']:
     if a.normal_y(q[:3])<=0 or any(abs(v[1])>1e-8 for v in q):continue
     covers.append([[v[0],v[2]]for v in map(lambda v:pose(v,p),q)])
   self.assertLess(sum(g.polygon_area(q)for q in a.common.subtract([h['traffic_polygon_xz_m']],covers)),1e-7)
   for group in r['groups']:
    for q in group['quads']:
     self.assertLess(side_clearance.area3d(side_clearance.clip_clear_volume([pose(v,p)for v in q],poly(h['local_x_limits_m'][0]+1e-5,h['local_x_limits_m'][1]-1e-5,h['road_width_m']/2-1e-5,[p['position_m'][0],p['position_m'][2]],p['yaw_rad']),[0,0,h['deck_top_y_m']],headroom_m=2.8)),1e-7)
 def test_connected_solids(self):
  for asset,p,h,c,r in self.rows:
   cells={tuple(v[:3])for v in c['cells']};seen={next(iter(cells))};todo=collections.deque(seen)
   while todo:
    x,y,z=todo.popleft()
    for q in[(x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)]:
     if q in cells and q not in seen:seen.add(q);todo.append(q)
   self.assertEqual(len(cells-seen),0)
 def test_wet_domain_clear_and_abutments_dry(self):
  report=[]
  for asset,p,h,c,r in self.rows:
   minimum=math.inf
   for w in h['actual_water']:
    for q in h['abutment_polygons_xz_m']:self.assertLess(g.polygon_area(g.convex_intersection(w['polygon_xz_m'],q)),1e-7)
    for group in r['groups']:
     for q in group['quads']:
      vs=[pose(v,p)for v in q];pp=[[v[0],v[2]]for v in vs];clip=g.convex_intersection(pp,w['polygon_xz_m'])
      if g.polygon_area(clip)<1e-8:continue
      plane=a.common.plane(vs[:3]);delta=min(a.common.height(plane,v)-a.common.height(w['plane_y_xz_m'],v)for v in clip);self.assertGreater(delta,.2);minimum=min(minimum,delta)
   if h['id'].startswith('EAST_'):self.assertGreater(minimum,2.2)
   report.append(dict(id=h['id'],minimum_actual_solid_clearance_above_water_m=minimum,abutment_water_overlap_m2=0))
  write('wet_clearances.json',dict(base_scene=ref(a.SCENE_PATH),crossings=report))
 def test_native_footprints_disjoint(self):
  proj=json.loads((CITY/'registered_integration/r8/coverage_plan/native_projection.json').read_text());ix=g._SpatialIndex(16);rows=[]
  for x in proj['instances']:
   for p in x['native_owner_parts_xz_m']:ix.add(len(rows),p);rows.append((x['id'],p))
  for i,(_,_,h,_,_)in enumerate(self.rows):
   p=h['native_ownership_polygon_xz_m']
   for j in ix.candidates(p):self.assertLess(g.polygon_area(g.convex_intersection(p,rows[j][1])),1e-7,rows[j][0])
   for _,_,other,_,_ in self.rows[:i]:self.assertLess(g.polygon_area(g.convex_intersection(p,other['native_ownership_polygon_xz_m'])),1e-7)
 def test_scene_application_does_not_edit_water_or_banks(self):
  out,ledger=apply_packs.apply_pack(self.scene,self.pack,'registered_water_completion_r01');self.assertIs(out['surfaces'],self.scene['surfaces']);self.assertEqual(len(ledger['inserted_runtime_ids']),4);self.assertEqual(ledger['retired_native_ids'],[])
if __name__=='__main__':unittest.main(verbosity=2)
