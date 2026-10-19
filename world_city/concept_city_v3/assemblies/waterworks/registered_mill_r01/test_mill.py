"""Native and finite-field checks for the registered industrial canal mill."""
import collections,json,math,unittest
from .build import HERE,CITY,ROOT,ref
from .select_site import pose
from voxel_character.common import coordinate_planes,render_data
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a,side_clearance
from world_city.concept_city_v3.registered_integration.r6 import apply_packs,merge_patches
from world_city.concept_city_v3.assemblies.waterworks.registered_services_r01.select_drawhouses import rect,ribbon
from world_city.runtime_city.checks import placement as g
class MillTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.scene=a.load_scene();cls.pack=json.loads((HERE/'resolved_placements.json').read_text());cls.patch=json.loads((HERE/'surface_patch.json').read_text());cls.interface=json.loads((HERE/'interface_contract.json').read_text());cls.site=cls.interface['site'];cls.asset=cls.pack['assets'][0];cls.master=json.loads((ROOT/cls.asset['source']['path']).read_text());cls.comp=coordinate_planes.compile_master(cls.master,{'pitch':.2},max_candidate_cells=500000,max_output_cells=160000);cls.render=render_data.make_render_data(cls.comp);cls.cells={tuple(c[:3]):c for c in cls.comp['cells']};cls.p=cls.pack['placements'][0];cls.o=cls.site['position_xz_m'];cls.yaw=cls.site['yaw_rad'];cls.floor=cls.site['ground_y_m']
 def world(self,v):
  q=pose([v[0],v[2]],self.o,self.yaw);return[q[0],v[1]+self.floor,q[1]]
 def test_source_cache_and_budget(self):
  self.assertTrue(self.comp['valid']);self.assertEqual(self.render,json.loads((ROOT/self.asset['cache']['path']).read_text()));self.assertEqual(ref(ROOT/self.asset['source']['path']),self.asset['source']);self.assertEqual(ref(ROOT/self.asset['cache']['path']),self.asset['cache']);self.assertEqual(self.p['scale'],[1,1,1]);self.assertLess(len(self.cells),20000);self.assertLess(self.render['quad_count'],1000)
 def test_actual_water_and_wheel_wetting(self):
  w=self.interface['actual_water'];tri=self.scene['surfaces']['water'][w['triangle_index']*3:w['triangle_index']*3+3];self.assertEqual(a.canonical_sha(tri),w['source_triangle_sha256']);self.assertAlmostEqual(a.common.height(w['plane_y_xz_m'],self.o),self.interface['head_y_m'])
  differences=[];wheel=[]
  for c in self.comp['cells']:
   if c[3]!='wheel':continue
   v=self.world([(c[0]+.5)*.2,(c[1]+.5)*.2,(c[2]+.5)*.2]);differences.append(v[1]-a.common.height(w['plane_y_xz_m'],[v[0],v[2]]));wheel.append(v)
  self.assertLess(min(differences),-.4);self.assertGreater(max(differences),1.5);self.assertGreater(min(v[1]for v in wheel),self.interface['canal_bed_contract_y_m']+.1);self.assertFalse(any('water'in k['material']for k in self.render['groups']))
 def test_wheel_rotor_bank_and_wet_domain_clearance(self):
  # Entire swept paddle volume is inside wet channel and clear of retained terrain sides.
  p=[pose(q,self.o,self.yaw)for q in [[-.9,-1.65],[.9,-1.65],[.9,1.65],[-.9,1.65]]];head=self.interface['head_y_m'];si=side_clearance.SideIndex(self.scene,[p]);check=si.audit([dict(id='rotor_sweep',polygon_xz_m=p,floor_y_m=head-.7,headroom_m=3.4)]);self.assertEqual(check['contacts'],[])
  water_polys=[]
  for j in range(0,len(self.scene['surfaces']['water']),3):
   t=self.scene['surfaces']['water'][j:j+3];q=[[v[0],v[2]]for v in t];clip=g.convex_intersection(p,q)
   if g.polygon_area(clip)>1e-8:water_polys.append(clip)
  self.assertLess(sum(g.polygon_area(q)for q in a.common.subtract([p],water_polys)),1e-7)
 def test_two_point_four_metre_navigation_ribbon(self):
  nav=self.interface['navigation_polygon_xz_m'];self.assertAlmostEqual(g.polygon_area(nav),24.,places=5)
  for group in self.render['groups']:
   for q in group['quads']:
    world=[self.world(v)for v in q];p=[[v[0],v[2]]for v in world];self.assertLess(g.polygon_area(g.convex_intersection(nav,p)),1e-7)
  check=side_clearance.SideIndex(self.scene,[nav]).audit([dict(id='navigation',polygon_xz_m=nav,plane_y_xz_m=self.interface['actual_water']['plane_y_xz_m'],headroom_m=2.2)]);self.assertEqual(check['contacts'],[])
 def test_dry_floor_and_public_access(self):
  windows=[self.site['body_polygon_xz_m']]+self.site['walk_polygons_xz_m'];ix=a.TriangleIndex(self.scene,windows);ground=a.audit_polygon(ix,windows[0],self.floor);self.assertTrue(ground['passes_existing_surface']);self.assertAlmostEqual(ground['area_m2'],31.2,places=5)
  owners=[]
  for p in windows[1:]:
   r=a.audit_polygon(ix,p);self.assertTrue(r['passes_existing_surface']);owners.extend(dict(id='mill_access',polygon_xz_m=q['polygon_xz_m'],plane_y_xz_m=q['plane_y_xz_m'])for q in r['source_pieces'])
   self.assertLess(g.polygon_area(g.convex_intersection(p,windows[0])),1e-7)
  self.assertEqual(side_clearance.SideIndex(self.scene,windows).audit(owners)['contacts'],[])
  contract=json.loads((CITY/'registered_topography/revisions/r14_precinct_merchant/contract.json').read_text());road=next(r for r in contract['roads']if r['id']==self.site['public_road_id']);j=self.site['public_road_segment'];p=ribbon(*road['polyline_xz_m'][j:j+2],road['width_m']);target=self.site['walk_centerline_xz_m'][-1];self.assertTrue(g.point_in_convex_polygon(target,p));self.assertEqual(road['id'],'POOR_NORTH_CROSS')
 def test_native_structure_and_existing_projection(self):
  # The coherent static assembly must have one connected native solid.
  cells=set(self.cells);seen={next(iter(cells))};todo=collections.deque(seen)
  while todo:
   x,y,z=todo.popleft()
   for q in [(x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)]:
    if q in cells and q not in seen:seen.add(q);todo.append(q)
  self.assertEqual(len(cells-seen),0)
  projection=json.loads((CITY/'registered_integration/r8/coverage_plan/native_projection.json').read_text());rows=[];ix=g._SpatialIndex(8)
  for r in projection['instances']:
   for p in r['native_owner_parts_xz_m']:ix.add(len(rows),p);rows.append((r['id'],p))
  for group in self.render['groups']:
   for q in group['quads']:
    p=[[v[0],v[2]]for v in map(self.world,q)]
    if g.polygon_area(p)<1e-9:continue
    for i in ix.candidates(p):self.assertLess(g.polygon_area(g.convex_intersection(p,rows[i][1])),1e-7,rows[i][0])
 def test_approach_clear_of_own_walls(self):
  for group in self.render['groups']:
   for q in group['quads']:
    world=list(map(self.world,q))
    for p in self.site['walk_polygons_xz_m']:
     self.assertLess(side_clearance.area3d(side_clearance.clip_clear_volume(world,p,[0,0,self.floor])),1e-7)
 def test_patch_preserves_existing_water_and_banks(self):
  merge_patches.merge([self.patch],a.SCENE_SHA256);merge_patches.validate_against_scene(self.scene,self.patch);self.assertNotIn('water',self.patch['source_surface_hashes']);self.assertNotIn('bank',self.patch['source_surface_hashes']);self.assertNotIn('water',self.patch['appended_surfaces']);self.assertNotIn('bank',self.patch['appended_surfaces']);placed,_=apply_packs.apply_pack(self.scene,self.pack,'registered_mill_r01');self.assertIs(placed['surfaces'],self.scene['surfaces'])
if __name__=='__main__':unittest.main(verbosity=2)
