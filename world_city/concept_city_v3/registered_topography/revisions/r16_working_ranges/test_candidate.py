"""Final finite R16 producer regression against actual corrected R6 bytes."""
import json,math,unittest
from . import author as a,frozen_r6 as f,candidate as c

class CandidateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.scene=f.load_scene();cls.patch=json.loads((a.HERE/'scene_patch.json').read_bytes());cls.fixed=f.apply_edits(cls.scene,cls.patch);cls.profile,cls.court,cls.connector=c.source_inputs();cls.owners=c.owner_records(cls.profile,cls.court,cls.connector);cls.holes=[r['polygon_xz_m'] for r in cls.owners if r['action']=='hole'];cls.index=f.SurfaceIndex(cls.fixed,windows=[f.bounds(r['polygon_xz_m']) for r in cls.owners],margin=0);cls.routes=json.loads((a.HERE/'route_handoff.json').read_bytes())
 def test_exact_reproducible_composition(self):
  patch,report,_=c.build(self.scene);self.assertEqual(patch,self.patch);self.assertEqual(report,json.loads((a.HERE/'producer_report.json').read_bytes()))
 def test_every_new_and_final_top_upward(self):
  for r in self.patch['surface_edits']:
   for t in r['replacement_triangles_xyz_m']:self.assertGreater(f.normal_y(t),0)
  for m,vs in self.fixed['surfaces'].items():
   for i in range(0,len(vs),3):self.assertGreaterEqual(f.normal_y(vs[i:i+3]),-1e-10,m)
 def test_native_holes_have_no_terrain_top(self):
  for p in self.holes:
   coverage=self.index.cover(p)
   self.assertLess(sum(a.geo.polygon_area(r['intersection_polygon_xz_m']) for r in coverage),1e-7)
 def test_courts_connectors_and_new_routes_have_complete_floor(self):
  for owner in self.owners:
   if owner['action']=='hole':continue
   parts=a.subtract([owner['polygon_xz_m']],self.holes)
   for p in parts:
    covered=self.index.cover(p);polys=[r['intersection_polygon_xz_m'] for r in covered]
    self.assertLess(sum(a.geo.polygon_area(q) for q in a.subtract([p],polys)),1e-7,owner['id'])
    for r in covered:
     for v in r['intersection_polygon_xz_m']:self.assertAlmostEqual(a.height(r['plane_y_xz_m'],v),2.5,places=7)
 def test_all_emitted_paint_has_single_owner(self):
  ts=[];ix=a.geo._SpatialIndex(8)
  for m,vs in self.patch['appended_surfaces'].items():
   for i in range(0,len(vs),3):
    p=[[v[0],v[2]] for v in vs[i:i+3]]
    for j in ix.candidates(p):self.assertLess(a.geo.polygon_area(a.geo.convex_intersection(p,ts[j])),1e-7,(m,i//3,j))
    ix.add(len(ts),p);ts.append(p)
 def test_all_new_profiles_keep_actual_original_planes(self):
  for r in self.profile['triangles']:
   src=r['source_r6'];actual=self.scene['surfaces'][src['material']][src['triangle_index']*3:src['triangle_index']*3+3];self.assertEqual(actual,src['vertices_xyz_m']);plane=a.plane(actual)
   for v in r['vertices_xyz_m']:self.assertLess(abs(v[1]-a.height(plane,[v[0],v[2]])),1e-9)
   self.assertLessEqual(math.hypot(*a.plane(r['vertices_xyz_m'])[:2]),.12+1e-9)
 def test_court_bearing_masks_match_native_render_faces(self):
  pack=json.loads(c.COURT_PACK.read_bytes());poses={p['id']:p for p in pack['placements']}
  for r in self.court['native_bearing_owners']:
   p=poses[r['placement_id']];asset=pack['assets'][p['asset_key']];render_path=a.ROOT/asset['render_path'];self.assertEqual(a.sha(render_path),r['render_sha256']);render=json.loads(render_path.read_bytes());q=render['groups'][r['group_index']]['quads'][r['quad_index']];self.assertLess(f.normal_y(q[:3]),0);self.assertEqual([[v[0],v[2]] for v in q],r['polygon_local_xz_m'])
   co,si=math.cos(p['yaw_rad']),math.sin(p['yaw_rad']);pos=p['position_m'];world=[[pos[0]+co*v[0]+si*v[2],pos[2]-si*v[0]+co*v[2]] for v in q]
   self.assertLess(sum(a.geo.polygon_area(v) for v in a.subtract([world],[r['polygon_xz_m']])),1e-8);self.assertLess(sum(a.geo.polygon_area(v) for v in a.subtract([r['polygon_xz_m']],[world])),1e-8)
 def test_preserved_source_arrays_fields_and_triangle_order(self):
  by={}
  for r in self.patch['surface_edits']:by.setdefault(r['material'],{})[r['triangle_index']]=r
  for key,value in self.scene.items():
   if key!='surfaces':self.assertIs(value,self.fixed[key])
  for m,vs in self.scene['surfaces'].items():
   if m not in by and m not in self.patch['appended_surfaces']:self.assertIs(vs,self.fixed['surfaces'][m]);continue
   cursor=0
   for i in range(0,len(vs),3):
    edit=by.get(m,{}).get(i//3)
    if edit:cursor+=3*len(edit['replacement_triangles_xyz_m'])
    else:self.assertEqual(vs[i:i+3],self.fixed['surfaces'][m][cursor:cursor+3]);cursor+=3
 def test_route_handoff_complete_and_exact_endpoints(self):
  self.assertEqual(len(self.routes['native_door_routes']),15);self.assertEqual(len(self.routes['court_links']),2);self.assertEqual(self.routes['expected_case_count'],36)
  external={r['id']:r for r in self.routes['external_routes']}
  for r in self.routes['native_door_routes']:
   self.assertEqual(r['public_to_lip_polyline_xyz_m'][0],external[r['connects_route_id']]['public_endpoint_xyz_m']);self.assertEqual(r['public_to_lip_polyline_xyz_m'][-1],r['threshold_lip_xyz_m'])
  for r in self.routes['court_links']:
   self.assertEqual(r['public_to_court_polyline_xyz_m'][0],external[r['connects_route_id']]['public_endpoint_xyz_m']);v=r['public_to_court_polyline_xyz_m'][-1];self.assertTrue(a.geo.point_in_convex_polygon([v[0],v[2]],r['polygon_xz_m'],1e-8))
 def test_no_new_sides_or_height_excursions(self):
  self.assertEqual(self.profile['retaining_sides'],[]);self.assertEqual(self.profile['affected_old_side_masks'],[]);self.assertIs(self.scene['surfaces']['bank'],self.fixed['surfaces']['bank']);self.assertIs(self.scene['surfaces']['water'],self.fixed['surfaces']['water'])
  for vs in self.patch['appended_surfaces'].values():
   for v in vs:self.assertAlmostEqual(v[1],2.5,places=7)
if __name__=='__main__':unittest.main()
