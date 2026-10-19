import unittest,json,copy
from .derive import HERE,ROOT,BASE,ny
from world_city.concept_city_v3.registered_integration.r8.runtime_contracts import append_collision_contracts
class Winding(unittest.TestCase):
 def test_exact_vertex_sets_and_negative_front(self):
  old=json.loads((BASE/'collision_contract.json').read_bytes());new=json.loads((HERE/'collision_contract.json').read_bytes());self.assertEqual(len(new['add_triangles_world_xyz_m']),74)
  for a,b in zip(old['add_triangles_world_xyz_m'],new['add_triangles_world_xyz_m']):self.assertEqual(sorted(map(tuple,a)),sorted(map(tuple,b)));self.assertGreater(ny(a),0);self.assertLess(ny(b),0)
 def test_adapter_rejects_original_direction(self):
  c=json.loads((HERE/'collision_contract.json').read_bytes());p=c['replacement_transform'];scene=dict(common_instances=[dict(id=c['native_placement_id'],asset_key='a',**p)],common_assets={'a':dict(render_sha256=c['native_source']['sha256'])})
  self.assertEqual(len(append_collision_contracts(scene,[c])['collision_contracts']),1);bad=copy.deepcopy(c);bad['add_triangles_world_xyz_m']=[[t[0],t[2],t[1]]for t in bad['add_triangles_world_xyz_m']]
  with self.assertRaisesRegex(ValueError,'winding'):append_collision_contracts(scene,[bad])
 def test_missing_convention_rejected(self):
  c=json.loads((HERE/'collision_contract.json').read_bytes());p=c['replacement_transform'];scene=dict(common_instances=[dict(id=c['native_placement_id'],asset_key='a',**p)],common_assets={'a':dict(render_sha256=c['native_source']['sha256'])});del c['triangle_convention']
  with self.assertRaisesRegex(ValueError,'explicit'):append_collision_contracts(scene,[c])
if __name__=='__main__':unittest.main()
