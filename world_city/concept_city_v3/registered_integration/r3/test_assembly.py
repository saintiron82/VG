import hashlib,json,unittest,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];ROOT=CITY.parents[1]
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class FabricIntegration(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=load(HERE/'candidate.json');cls.old=load(HERE.parent/'r2/candidate.json')
 def test_hashes(self):
  for a in self.d['provenance']['input_packs']:self.assertEqual(sha(ROOT/a['path']),a['sha256'],a['name'])
  for k,a in self.d['common_assets'].items():
   with self.subTest(asset=k):self.assertEqual(sha(ROOT/a['master_path']),a['master_sha256']);self.assertEqual(sha(ROOT/a['render_path']),a['render_sha256'])
 def test_unique_rigid_poses(self):
  ids=[p['id'] for p in self.d['common_instances']];self.assertEqual(len(ids),len(set(ids)))
  for p in self.d['common_instances']:self.assertEqual(p['scale'],[1,1,1]);self.assertIn(p['asset_key'],self.d['common_assets'])
 def test_density_atomic_replacement_and_no_double_render(self):
  p=load(CITY/'assemblies/ordinary/registered/r1/resolved_placements.json');ids={q['id'] for q in self.d['common_instances']}
  self.assertFalse(ids&set(p['replaced_placement_ids']));self.assertEqual(len(p['component_placements']),45)
  self.assertEqual(sum(q['source_pack']=='ordinary_density' for q in self.d['common_instances']),16)
  for bid in p['replaced_placement_ids']:
   for suffix in ('',':support',':owned_foundation'):self.assertIn(bid+suffix,self.d['remove_proxy_ids'])
  self.assertTrue(set(p['superseded_old_path_ids'])<=set(self.d['access_overlay']['remove_path_ids']))
 def test_native_wall_replaces_every_old_box(self):
  o=load(CITY/'assemblies/fortifications/registered/placement_r01/supersession_overlay.json');self.assertEqual(len(o['remove_box_ids']),722);self.assertTrue(set(o['remove_box_ids'])<=set(self.d['remove_proxy_ids']))
 def test_quay_union_replaces_old_segments(self):
  p=load(CITY/'assemblies/landmarks/registered/port_r03_quay_unions/replacement_overlay.json');ids={q['id'] for q in self.d['common_instances']}
  self.assertFalse(ids&set(p['remove_placement_ids']));self.assertEqual(sum(q['source_pack']=='port' for q in self.d['common_instances']),39)
 def test_preserved_estates_landmarks_woodland(self):
  for kind in ('property','landmarks','woodland'):
   self.assertEqual([p for p in self.old['common_instances'] if p['source_pack']==kind],[p for p in self.d['common_instances'] if p['source_pack']==kind])
 def test_palette_cache_identity(self):
  keys={}
  for p in self.d['common_instances']:
   key=(p['asset_key'],p['palette_id']);value=json.dumps(p['palette_override'],sort_keys=True);self.assertEqual(keys.setdefault(key,value),value)
 def test_r07_water_and_ownership(self):
  c=load(CITY/'registered_topography/revisions/r07_native_interfaces/contract.json');self.assertEqual(len(c['water_surfaces']),6);self.assertEqual(len(c['water_support']['exterior_banks']),1199);self.assertEqual(len(c['ordinary_foundations']),616);self.assertEqual(self.d['floor_ownership_masks'],[])
 def test_market_customer_count(self):
  r=load(CITY/'assemblies/market/registered/r3_clusters/walkspace_report.json');self.assertEqual(r['passing'],104);self.assertEqual(sum(q['source_pack']=='market' for q in self.d['common_instances']),105)
if __name__=='__main__':unittest.main(verbosity=2)
