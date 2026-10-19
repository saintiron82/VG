"""Source-only extension integrity; does not launch physics or claim a scene pass."""
import hashlib,json,pathlib,sys,unittest
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H));import catalog
ROOT=catalog.ROOT
read=lambda p:json.loads(p.read_bytes())
class Next20Catalog(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.old=read(H/'route_catalog_ready_r04.json');cls.new=read(H/'route_catalog_61_ready_r05.json');cls.handoff=read(catalog.source(cls.new['sources']['ready_entries_next20']));cls.expanded=catalog.validate(cls.new)
 def test_immutable_372_predecessor(self):
  self.assertEqual(hashlib.sha256((H/'route_catalog_ready_r04.json').read_bytes()).hexdigest(),'88fb03035d971f379efa773cfad6c6f0677e7d9c172ba3e384608e17e6918de2')
  self.assertEqual(self.new['routes'][:len(self.old['routes'])],self.old['routes'])
 def test_expected_412_cases(self):
  self.assertEqual(len(self.expanded),412);self.assertEqual(len(self.new['routes'])-len(self.old['routes']),20)
 def test_all_exact_next20_source_vectors_preserved(self):
  lookup={r['id']:r for r in self.new['routes']}
  for r in self.handoff['entries']:
   self.assertEqual(lookup[r['id']]['points_xyz_m'],r['polyline_xyz_m']);self.assertEqual(lookup[r['id']]['inherited_public_steps'],r['inherited_public_steps']);self.assertTrue(lookup[r['id']]['bidirectional'])
 def test_three_explicit_public_steps_remain(self):
  self.assertEqual(sum(len(r['inherited_public_steps'])for r in self.handoff['entries']),3)
  for r in self.handoff['entries']:
   for step in r['inherited_public_steps']:
    p=step['point_xz_m'];self.assertIn([p[0],step['before_y_m'],p[1]],r['polyline_xyz_m']);self.assertIn([p[0],step['after_y_m'],p[1]],r['polyline_xyz_m'])
 def test_exact_activation_sources(self):
  self.assertEqual(len(self.new['activation_requirements']['native_packs']),5);self.assertEqual(len(self.new['activation_requirements']['appended_surface_patches']),3)
 def test_accepted_and_held_accounted(self):
  rows=self.new['coverage']['ordinary_entries'];self.assertEqual(sum(r['status']=='accepted'for r in rows),83);self.assertEqual(sum(r['status']=='held'for r in rows),17)
 def test_no_actual_replay_started(self):
  self.assertFalse((H/'prepared_runtime.json').exists());self.assertFalse((H/'evidence/public_network_replay.json').exists())
if __name__=='__main__':unittest.main(verbosity=2)
