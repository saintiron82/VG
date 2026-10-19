"""Actual common occupancy/render proof for the bounded support candidate."""
import sys
sys.dont_write_bytecode=True
import json,math,unittest,hashlib
from pathlib import Path
import build_support as s

class CandidateSupportTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.pre=json.loads((s.HERE/'preflight.json').read_text());cls.pack=json.loads((s.HERE/'resolved_support.json').read_text());cls.g={g['asset_key']:g for g in cls.pre['groups']};cls.c={r['asset_key']:json.loads((s.a.ROOT/r['compiled']['path']).read_text()) for r in cls.pack['placements']};cls.r={r['asset_key']:json.loads((s.a.ROOT/r['cache']['path']).read_text()) for r in cls.pack['placements']}
 def test_immutable_inputs_and_common_hashes(self):
  self.assertEqual(s.sha(s.a.HERE/'source_contract.json'),s.CONTRACT_SHA)
  self.assertEqual(s.sha(s.a.HERE/'author.py'),self.pre['source_author_sha256'])
  for path,expected in s.a.REFERENCES.items():self.assertEqual(s.sha(s.a.CITY/path),expected)
  for path,expected in self.pack['compiler_sources'].items():self.assertEqual(s.sha(s.a.ROOT/path),expected)
  self.assertEqual(s.sha(s.HERE/'build_support.py'),self.pack['builder_sha256'])
  for p in self.pack['placements']:
   for field in ('source','compiled','cache'):self.assertEqual(s.sha(s.a.ROOT/p[field]['path']),p[field]['sha256'])
   self.assertEqual(s.sha(s.a.ROOT/p['native_render_path']),p['native_render_sha256'])
 def test_scope_and_budget(self):
  self.assertFalse(self.pack['active']);self.assertEqual(self.pre['all_native_regions'],194);self.assertEqual(self.pre['selected_regions'],71);self.assertEqual(self.pre['selected_holdings'],9);self.assertEqual(len(self.pack['placements']),15);self.assertEqual(self.pre['additional_selected_regions'],[]);self.assertEqual(self.pre['unresolved_regions'],[])
  self.assertEqual(len(self.pre['retired_native_ids']),58)
  total=sum(c['candidate_cells'] for c in self.c.values());self.assertEqual(total,self.pre['exact_candidate_visits']);self.assertEqual(total,43887);self.assertLessEqual(total,s.TOTAL_CAP)
  for c in self.c.values():self.assertLessEqual(c['candidate_cells'],s.PER_ASSET_CAP);self.assertTrue(c['valid'])
 def test_exact_cells_under_native_only(self):
  for p in self.pack['placements']:
   g=self.g[p['asset_key']];want=set()
   for r in g['regions']:
    for x,z in s.cells_2d(r['local_polygon_xz_m']):
     for y in range(round(r['local_bottom_y_m']/s.PITCH),0):want.add((x,y,z))
   got={tuple(c[:3]) for c in self.c[p['asset_key']]['cells']};self.assertEqual(got,want)
   native,_=s.native_bottom_columns(s.POSES[p['native_owner_id']]);self.assertTrue({(x,z) for x,y,z in got}<=native)
 def test_actual_top_contact_and_area(self):
  total_area=0
  for p in self.pack['placements']:
   top_cols=set();top_area=0
   for g in self.r[p['asset_key']]['groups']:
    for q in g['quads']:
     u=[q[1][i]-q[0][i] for i in range(3)];v=[q[2][i]-q[0][i] for i in range(3)];ny=u[2]*v[0]-u[0]*v[2]
     if ny>1e-9:
      self.assertTrue(all(abs(v[1])<1e-12 for v in q));poly=[[v[0],v[2]] for v in q];top_area+=s.area(poly);top_cols.update(s.cells_2d(poly))
   want={(c[0],c[2]) for c in self.c[p['asset_key']]['cells']};self.assertEqual(top_cols,want);self.assertAlmostEqual(top_area,len(want)*.25,places=7);self.assertAlmostEqual(top_area,p['contact_proof']['support_area_m2'],places=7);total_area+=top_area
   self.assertEqual(p['position_m'],s.POSES[p['native_owner_id']]['position_m']);self.assertEqual(p['yaw_rad'],s.POSES[p['native_owner_id']]['yaw_rad']);self.assertEqual(p['position_m'][1],p['top_y_m'])
  self.assertAlmostEqual(total_area,3501.,places=6)
 def test_exact_footprint_transform(self):
  for p in self.pack['placements']:
   pose=s.POSES[p['native_owner_id']]
   for r in p['ownership_regions']:
    expected=r['polygon_xz_m'];actual=[s.world(pose,q) for q in r['local_polygon_xz_m']]
    self.assertEqual(len(actual),len(expected))
    for a,b in zip(actual,expected):self.assertLess(math.dist(a,b),1e-10)
 def test_actual_rendered_bottoms(self):
  for p in self.pack['placements']:
   bottoms={}
   for x,y,z,*_ in self.c[p['asset_key']]['cells']:bottoms[x,z]=min(bottoms.get((x,z),0),y*s.PITCH)
   face_columns=set()
   for g in self.r[p['asset_key']]['groups']:
    for q in g['quads']:
     u=[q[1][i]-q[0][i] for i in range(3)];v=[q[2][i]-q[0][i] for i in range(3)];ny=u[2]*v[0]-u[0]*v[2]
     if ny< -1e-9:
      self.assertTrue(all(abs(v[1]-q[0][1])<1e-12 for v in q))
      for col in s.cells_2d([[v[0],v[2]] for v in q]):self.assertEqual(bottoms[col],q[0][1]);face_columns.add(col)
   self.assertEqual(face_columns,set(bottoms))
 def test_certified_burial_and_nonrequired_contact(self):
  self.assertLessEqual(self.pre['ground_lipschitz_proof']['constant_m_per_m'],.120000001)
  for r in self.pre['regions']:
   self.assertAlmostEqual(sum(d['area_m2'] for d in r['source_domain_proof']),s.area(r['world_polygon_xz_m']),places=6)
   self.assertAlmostEqual(r['certified_lower_y_m'],min(d['certified_lower_y_m'] for d in r['source_domain_proof']),places=9)
   if r['selected']:
    self.assertGreaterEqual(r['certified_lower_y_m']-r['bottom_world_y_m'],.5-1e-9);self.assertLess(r['bottom_world_y_m'],r['native_top_y_m'])
   else:self.assertGreaterEqual(r['certified_lower_y_m']-r['native_top_y_m'],0.)
 def test_no_water_traffic_or_r14_conflict(self):
  contract=json.loads((s.a.HERE/'source_contract.json').read_text());ids={r['region_id'] for r in self.pre['regions'] if r['selected']};proof=s.conflict_proof([r for r in contract['support_requirements'] if r['id'] in ids]);self.assertEqual(proof['positive_area_conflicts'],[])
 def test_no_support_in_gates_yards_or_other_holdings(self):
  by={p['property_id']:p for p in s.a.HANDOFF['properties']}
  for r in self.pre['regions']:
   if not r['selected']:continue
   own=by[r['property_id']]
   self.assertAlmostEqual(s.area(s.clip(r['world_polygon_xz_m'],own['platform_polygon_xz_m'])),s.area(r['world_polygon_xz_m']),places=6)
   gate=own['finite_gate_approach']['polygon_xz_m'];hit=s.clip(r['world_polygon_xz_m'],gate);self.assertLess(s.area(hit) if hit else 0.,1e-7)
   for yard in own['retained_lower_ground']['polygons_xz_m']:
    hit=s.clip(r['world_polygon_xz_m'],yard);self.assertLess(s.area(hit) if hit else 0.,1e-7)
   for other in by.values():
    if other['property_id']==r['property_id']:continue
    hit=s.clip(r['world_polygon_xz_m'],other['platform_polygon_xz_m']);self.assertLess(s.area(hit) if hit else 0.,1e-7)
 def test_render_bounds_and_native_vertical_exclusion(self):
  for p in self.pack['placements']:
   c=self.c[p['asset_key']];r=self.r[p['asset_key']]
   self.assertEqual(r['bounds']['max'][1],0.);self.assertLess(r['bounds']['min'][1],0.);self.assertTrue(all(cell[1]<0 for cell in c['cells']))
   self.assertEqual(r['pitch'],.5);self.assertEqual(r['grid_origin'],[0,0,0]);self.assertEqual(r['payload_hash'],c['payload_hash'])

if __name__=='__main__':unittest.main(verbosity=2)
