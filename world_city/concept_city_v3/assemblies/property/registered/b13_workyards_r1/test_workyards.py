import json,hashlib,unittest
from pathlib import Path
from world_city.runtime_city.checks import placement as geo
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[3];ROOT=CITY.parents[1]
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class WorkyardTests(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.d=read(HERE/'resolved_placements.json');c.g={g['id']:g for g in read(CITY/'assemblies/ordinary/registered/r1/owned_grounds.json')['grounds']}
 def test_source_and_native_hashes(self):
  for a in self.d['inputs']:self.assertEqual(sha(ROOT/a['path']),a['sha256'])
  for a in self.d['assets'].values():
   self.assertEqual(sha(ROOT/a['master_path']),a['master_sha256']);self.assertEqual(sha(ROOT/a['render_path']),a['render_sha256'])
 def test_whole_native_bounds_and_working_space_owned(self):
  for p in self.d['placements']:
   poly=p['reserved_working_polygon_xz_m'];regions=self.g[p['ground_id']]['polygons_xz_m'];self.assertAlmostEqual(sum(geo.polygon_area(geo.convex_intersection(poly,q)) for q in regions),geo.polygon_area(poly),places=6)
 def test_reservations_disjoint(self):
  rows=self.d['placements']
  for i,p in enumerate(rows):
   for q in rows[:i]:self.assertLess(geo.polygon_area(geo.convex_intersection(p['reserved_working_polygon_xz_m'],q['reserved_working_polygon_xz_m'])),1e-7)
 def test_geometry_is_rigid_and_no_floor(self):
  self.assertTrue(self.d['no_floor_geometry_added']);self.assertEqual(len({p['id'] for p in self.d['placements']}),len(self.d['placements']))
  for p in self.d['placements']:self.assertEqual(p['scale'],[1,1,1]);self.assertEqual(p['position_m'][1],2.5);self.assertGreater(p['footing_embed_m'],0)
 def test_no_privy_force_fit(self):
  self.assertFalse(any(p['role']=='privy_shed' for p in self.d['placements']));self.assertEqual(sum(p['kind']=='privy_shed' for p in self.d['unplaced']),2)
if __name__=='__main__':unittest.main(verbosity=2)
