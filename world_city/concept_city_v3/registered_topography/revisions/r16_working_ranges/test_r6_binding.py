import copy,json,math,unittest
from . import author as a,frozen_r6 as f,footing_courts

class R6BindingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.scene=f.load_scene();cls.patch=json.loads((a.HERE/'footing_court_patch.json').read_bytes());cls.report=json.loads((a.HERE/'footing_court_report.json').read_bytes());cls.fixed=f.apply_edits(cls.scene,cls.patch)
 def test_scene_and_finite_edit_scope(self):
  self.assertEqual(self.patch['base_scene_sha256'],f.SCENE_SHA256);self.assertEqual(len(self.patch['surface_edits']),72);self.assertEqual(self.patch['removed_foundation_proxy_ids'],[])
 def test_all26_candidate_ids_retained(self):
  rows=self.report['all26_candidate_ledger'];self.assertEqual(len(rows),26);self.assertEqual(len({r['parcel_id'] for r in rows}),26);self.assertEqual(sum(r['r16_stage']=='native_footing_and_access_source_candidate' for r in rows),4)
 def test_all_source_coverage_and_threshold_heights(self):
  for r in self.report['owner_checks']:
   self.assertLess(r['uncovered_m2'],1e-8);self.assertAlmostEqual(r['minimum_source_y_m'],2.5);self.assertAlmostEqual(r['maximum_source_y_m'],2.5);self.assertAlmostEqual(r['area_m2'],r['removed_source_top_m2'],places=6)
 def test_actual_native_bearing_union_matches_holes(self):
  pack=a.read('resolved_placements.json');actual=[]
  for p in pack['placements']:
   asset=pack['assets'][p['asset_key']];path=a.ROOT/asset['render_path'];self.assertEqual(a.sha(path),asset['render_sha256']);render=json.loads(path.read_bytes());c=math.cos(p['yaw_rad']);s=math.sin(p['yaw_rad']);pos=p['position_m'];foot=[]
   for g in render['groups']:
    for q in g['quads']:
     if f.normal_y(q[:3])>=-1e-10 or max(abs(v[1]) for v in q)>1e-9:continue
     foot.append([[pos[0]+c*v[0]+s*v[2],pos[2]-s*v[0]+c*v[2]] for v in q])
   declared=[r['polygon_xz_m'] for r in a.native_holes() if r['parcel_id']==p['id']]
   self.assertTrue(declared,p['id']);self.assertLess(sum(a.geo.polygon_area(q) for q in a.subtract(foot,declared)),1e-7);self.assertLess(sum(a.geo.polygon_area(q) for q in a.subtract(declared,foot)),1e-7);actual.extend(foot)
 def test_new_tops_are_upward_and_retain_original_planes(self):
  for e in self.patch['surface_edits']:
   source=self.scene['surfaces'][e['material']][e['triangle_index']*3:e['triangle_index']*3+3];plane=a.plane(source)
   for t in e['replacement_triangles_xyz_m']:
    self.assertGreater(f.normal_y(t),0)
    for v in t:self.assertLess(abs(v[1]-a.height(plane,[v[0],v[2]])),1e-9)
  for vs in self.patch['appended_surfaces'].values():
   for i in range(0,len(vs),3):self.assertGreater(f.normal_y(vs[i:i+3]),0)
 def test_courts_complete_no_duplicate_faces_or_native_overlap(self):
  vs=self.patch['appended_surfaces']['ground_stone'];ts=[[[v[0],v[2]] for v in vs[i:i+3]] for i in range(0,len(vs),3)]
  for c in a.court_regions():self.assertLess(sum(a.geo.polygon_area(q) for q in a.subtract([c['polygon_xz_m']],ts)),1e-8)
  self.assertAlmostEqual(sum(a.geo.polygon_area(p) for p in ts),110)
  for i,p in enumerate(ts):
   for q in ts[i+1:]:self.assertLess(a.geo.polygon_area(a.geo.convex_intersection(p,q)),1e-8)
   for h in a.native_holes():self.assertLess(a.geo.polygon_area(a.geo.convex_intersection(p,h['polygon_xz_m'])),1e-8)
 def test_all_unaffected_triangles_order_exact(self):
  for k,v in self.scene.items():
   if k!='surfaces':self.assertIs(v,self.fixed[k])
  by={}
  for e in self.patch['surface_edits']:by.setdefault(e['material'],{})[e['triangle_index']]=e
  for m,src in self.scene['surfaces'].items():
   if m not in by and m not in self.patch['appended_surfaces']:self.assertIs(src,self.fixed['surfaces'][m]);continue
   j=0
   for i in range(0,len(src),3):
    e=by.get(m,{}).get(i//3)
    if e:j+=3*len(e['replacement_triangles_xyz_m'])
    else:
     self.assertEqual(src[i:i+3],self.fixed['surfaces'][m][j:j+3]);j+=3
 def test_wrong_base_or_duplicate_index_rejected(self):
  with self.assertRaises(ValueError):f.apply_edits(self.scene,dict(self.patch,base_scene_sha256='bad'))
  with self.assertRaises(ValueError):f.apply_edits(self.scene,dict(self.patch,surface_edits=self.patch['surface_edits']+[self.patch['surface_edits'][0]]))
 def test_future_top_emission_cw_and_ccw(self):
  p=[[0,2.5,0],[2,2.5,0],[2,2.5,3],[0,2.5,3]]
  for points in [p,list(reversed(p))]:
   t=list(f.fan_upward(points));self.assertEqual(len(t),2);self.assertTrue(all(f.normal_y(v)>0 for v in t));self.assertAlmostEqual(sum(f.normal_y(v)/2 for v in t),6)
if __name__=='__main__':unittest.main()
