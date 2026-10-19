"""Independent bounded source/patch/input checks. Does not run a game or modify its sources."""
import unittest,json,hashlib,math
from pathlib import Path
import numpy as np
from world_city.runtime_city.checks import placement as g
H=Path(__file__).resolve().parent;R=H.parents[4];O=H/'candidate_r01';M=H.parents[1]/'r9/market_clusters'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def area(t):return float(np.linalg.norm(np.cross(np.array(t[1])-t[0],np.array(t[2])-t[0]))*.5)
class Tests(unittest.TestCase):
 def test_frozen_input_hashes(self):
  for f in load(O/'freeze_manifest.json')['files']:self.assertEqual(sha(R/f['path']),f['sha256'],f['path'])
 def test_source_triangle_binding(self):
  faces={(f['material'],f['triangle_index']):f for f in load(H/'source_excerpt.json')['source_faces']};patch=load(O/'surface_patch.json');seen=set()
  for e in patch['surface_edits']:
   k=(e['material'],e['triangle_index']);self.assertNotIn(k,seen);seen.add(k);self.assertEqual(faces[k]['source_triangle_xyz_m'],e['source_triangle_xyz_m']);self.assertEqual(faces[k]['source_triangle_sha256'],e['source_triangle_sha256']);self.assertEqual(e['material'],'space_civic')
  self.assertEqual(len(seen),36);self.assertEqual(patch['source_surface_hashes']['space_civic'],load(H/'source_excerpt.json')['source_surface_hashes']['space_civic'])
 def test_finish_has_no_overlay_height_or_source_area_loss(self):
  p=load(O/'surface_patch.json');app=p['appended_surfaces']['ground_stone'];after=sum(area(t)for e in p['surface_edits']for t in e['replacement_triangles_xyz_m'])+sum(area(app[i:i+3])for i in range(0,len(app),3));before=sum(area(e['source_triangle_xyz_m'])for e in p['surface_edits']);self.assertAlmostEqual(before,after,8)
  for t in [t for e in p['surface_edits']for t in e['replacement_triangles_xyz_m']]+[app[i:i+3]for i in range(0,len(app),3)]:
   self.assertTrue(all(v[1]==4 for v in t));self.assertGreater(area(np.array(t,dtype=np.float32)),1e-9)
  self.assertAlmostEqual(sum(area(app[i:i+3])for i in range(0,len(app),3)),41.88675208225146,7)
 def test_protected_geometry_and_lowwater(self):
  s=load(O/'static_audit.json');self.assertFalse(any(s['pad_hits'].values()));self.assertFalse(s['off_road_branch_existing_market_link_conflicts']);self.assertFalse(s['cart_envelope_native_bound_hits']);self.assertEqual(s['patch_source_overlap_with_market_low_water'],0)
  self.assertEqual(len(load(M/'pack.json')['add_instances']),66);self.assertEqual(len(load(M/'layout.json')['routes']),132)
 def test_route_heights_include_every_original_material(self):
  a=load(H/'all_materials_verification.json');self.assertEqual(a['status'],'PASS_ALL_SOURCE_MATERIALS');self.assertFalse(a['height_disagreements']);self.assertGreater(a['exact_top_face_checks'],3000);self.assertEqual(len(a['supplemental_material_hashes'])+len(load(H/'source_excerpt.json')['source_surface_hashes']),19)
 def test_cart_fixture_and_grade(self):
  s=load(O/'static_audit.json');self.assertEqual(s['fixture']['width_m'],1.8);self.assertEqual(s['fixture']['length_m'],3.2);self.assertEqual(s['fixture']['overall_height_m'],2.2);self.assertEqual(s['fixture']['ground_clearance_m'],.15);self.assertEqual(s['fixture']['support_track_m'],1.5);self.assertEqual(s['fixture']['support_wheelbase_m'],2.5);self.assertLess(s['maximum_four_wheel_plane_residual_m'],.05);self.assertLess(max(r['maximum_sampled_longitudinal_grade']for r in s['cross_section_grade_samples']),.075);self.assertEqual(s['maximum_pad_outer_edge_height_delta_m'],0)
 def test_route_joins_and_same_position_forward_return(self):
  d=load(O/'routes.json');j=d['exact_joins'];a,b=j['last_port_chain_segment'];p=j['procession_entry'];self.assertLess(g.point_segment_distance([p[0],p[2]],[a[0],a[2]],[b[0],b[2]]),1e-8)
  c=d['routes'][0]['points'];self.assertEqual(c[0],c[-1]);f=np.array(c[1])-c[0];r=np.array(c[-1])-c[-2];self.assertLess(float(np.dot(f,r)),0)
  for q,r in zip(c,c[1:]):self.assertGreater(math.dist(q,r),1e-7)
  self.assertAlmostEqual(j['old_port_chain_terminal_preserved'][1],3.936936178443468,10)
 def test_bay_capacity_one_whole_cart_and_connection(self):
  d=load(O/'geometry_ownership.json');p=d['geometry']['pad'];mid=d['geometry']['mid'];t=[7/math.sqrt(58),3/math.sqrt(58)];n=[t[1],-t[0]];body=[[mid[k]+f*t[k]+l*n[k]for k in(0,1)]for l,f in [(-.9,-1.6),(.9,-1.6),(.9,1.6),(-.9,1.6)]]
  self.assertTrue(g.convex_polygon_contains(p,body,0));self.assertEqual(load(O/'static_audit.json')['simultaneous_cart_capacity'],1);self.assertEqual(load(O/'routes.json')['routes'][-1]['points'][-1],[114.,4.,7.])
if __name__=='__main__':unittest.main(verbosity=2)
