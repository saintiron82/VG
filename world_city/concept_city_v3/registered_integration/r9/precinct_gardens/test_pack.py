"""Native-reference, ownership, support and reservation regression tests."""
import copy, hashlib, json, math, unittest
from author import *
class PlantingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.pack=load(HERE/'pack.json');cls.ledger=load(HERE/'placement_ledger.json');cls.world=World();cls.rows=cls.pack['add_instances']
 def test_base_identity_and_additive_schema(self):
  self.assertEqual(sha(BASE),BASE_SHA);self.assertEqual(self.pack['base_scene_sha256'],BASE_SHA)
  self.assertEqual(self.pack['schema'],'riverstone.city.visual_addendum.v1');self.assertEqual(self.pack['remove_instance_ids'],[])
  self.assertGreater(len(self.rows),25);self.assertLessEqual(len(self.rows),100)
 def test_exact_existing_native_asset_refs_and_no_scale(self):
  for k,a in self.pack['common_assets'].items():
   old=self.world.scene['common_assets'][k]
   for f in ['master_path','master_sha256','render_path','render_sha256','bounds']:self.assertEqual(a[f],old[f])
   self.assertEqual(sha(ROOT/a['master_path']),a['master_sha256']);self.assertEqual(sha(ROOT/a['render_path']),a['render_sha256'])
  for p in self.rows:self.assertEqual(p['scale'],[1,1,1]);self.assertTrue(all(math.isfinite(n)for n in p['position_m']+[p['yaw_rad']]))
 def test_unique_ids_and_no_base_replacements(self):
  ids=[p['id']for p in self.rows];base={p['id']for p in self.world.scene['common_instances']}
  self.assertEqual(len(ids),len(set(ids)));self.assertFalse(set(ids)&base)
 def test_full_canopies_are_within_named_owner(self):
  for p in self.rows:
   with self.subTest(id=p['id']):self.assertTrue(self.world.contained(ring(self.pack['common_assets'][p['asset_key']]['bounds'],p,.15),p['source_owner']))
 def test_public_routes_garden_paths_entrances_and_native_mesh_clear(self):
  self.assertEqual(len(self.world.routes),254);self.assertEqual(sum(2 if r.get('bidirectional')else 1 for r in self.world.routes),493)
  for p in self.rows:
   with self.subTest(id=p['id']):self.assertEqual(self.world.check(p,p['source_owner'])[0],[])
 def test_new_canopies_do_not_overlap(self):
  for i,p in enumerate(self.rows):
   for q in self.rows[:i]:self.assertFalse(overlap(ring(self.pack['common_assets'][p['asset_key']]['bounds'],p),ring(self.pack['common_assets'][q['asset_key']]['bounds'],q,.3)))
 def test_authored_finite_compositions_and_corrections(self):
  proposals_by_id={c['id']:c for c in proposals(self.world)}
  self.assertEqual(proposals(self.world),self.ledger['proposals'])
  for p in self.rows:
   c=proposals_by_id[p['id']];self.assertEqual(c['owner'],p['source_owner']);self.assertLessEqual(math.dist(c['desired_xz_m'],[p['position_m'][0],p['position_m'][2]]),c['maximum_local_fit_m']+1e-9)
  owners={p['source_owner']for p in self.rows};self.assertTrue(set('E'+str(i)for i in range(1,8))<=owners);self.assertTrue(any('MONASTERY'in o for o in owners));self.assertTrue(any('CLERGY'in o for o in owners))
 def test_rejects_deliberate_door_and_wrong_owner_mutations(self):
  p=copy.deepcopy(self.rows[0]);p['asset_key']=CYPRESS
  d=next(q for q in self.world.prop['actual_doors']if q['id'].startswith('E1:'))
  p['position_m']=d['door_xyz_m'];bad=self.world.check(p,'E1')[0];self.assertTrue(any(s.startswith('reservation:')for s in bad))
  p['position_m']=[0,16,0];bad=self.world.check(p,'E1')[0];self.assertIn('outside_owned_margin',bad);self.assertIn('native_root_support_unproven',bad)
if __name__=='__main__':unittest.main(verbosity=2)
