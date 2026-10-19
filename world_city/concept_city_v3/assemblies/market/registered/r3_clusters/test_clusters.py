import hashlib,json,math,unittest
from pathlib import Path
from world_city.runtime_city.checks import placement as geo
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[5]
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class MarketClusters(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=load(HERE/'resolved_placements.json');cls.old=load(HERE.parent/'resolved_placements.json')
 def test_sources_and_caches(self):
  for a in self.d['assets'].values():
   self.assertEqual(sha(ROOT/a['master_path']),a.get('master_sha256',a.get('master_file_sha256')))
   self.assertEqual(sha(ROOT/a['render_path']),a['render_sha256'])
 def test_fountain_and_public_road_unchanged(self):
  self.assertEqual(self.d['placements'][0],self.old['placements'][0]);self.assertEqual(self.d['access_overlay'],self.old['access_overlay'])
 def test_distinct_native_modules_and_no_scaling(self):
  self.assertEqual(len(self.d['placements']),105);self.assertEqual(len(self.d['assets']),4)
  self.assertEqual(len({p['id'] for p in self.d['placements']}),105)
  for p in self.d['placements'][1:]:self.assertEqual(p['scale'],[1,1,1])
 def test_canopies_do_not_overlap(self):
  stalls=self.d['placements'][1:]
  for i,p in enumerate(stalls):
   for q in stalls[i+1:]:self.assertFalse(geo.positive_area_overlap(p['footprint_xz_m'],q['footprint_xz_m'],0),(p['id'],q['id']))
 def test_all_customer_routes_connected(self):
  r=load(HERE/'walkspace_report.json');self.assertEqual(r['source_pack_sha256'],sha(HERE/'resolved_placements.json'));self.assertEqual(r['passing'],104)
  self.assertEqual({x['stall_id'] for x in r['stall_routes']},{p['id'] for p in self.d['placements'][1:]})
  for x in r['stall_routes']:self.assertTrue(x['path_xz_m']);self.assertEqual(x['width_m'],2.4)
 def test_back_gaps_are_not_declared_walkways(self):
  for r in self.d['rows']:self.assertFalse(r['rear_gap_is_walkway']);self.assertEqual(r['rear_gap_m'],.5)
if __name__=='__main__':unittest.main(verbosity=2)
