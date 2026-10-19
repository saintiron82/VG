import copy,json,pathlib,unittest
from bind_origins import transform,ROOT,sha,IMPLEMENTATION_SHA,origin
class BindingTests(unittest.TestCase):
 def fixture(self,triangles):
  return dict(assets={'S':dict(collision_format='actual_scene_triangles')},placements={'S':dict(id='S',asset_key='S',position_m=[0,0,0])},routes=[dict(id='r',points=[[64,16,-288],[66,16,-286]],placement_ids=['S'])]),dict(triangles=triangles,source_face_indices=[['road',i]for i in range(len(triangles))])
 def test_exact_world_and_indices(self):
  d,a=self.fixture([[[64.,16.,-288.],[66.,16.,-288.],[64.,16.,-286.]]]);before=copy.deepcopy(d);b,t,p=transform(d,'S',a);self.assertEqual(d,before);self.assertEqual(t,[64,16,-288]);self.assertEqual(b['source_face_indices'],a['source_face_indices']);self.assertEqual(p['removed_faces'],0);self.assertTrue(p['source_world_vertices_exact'])
 def test_reject_pretransformed(self):
  d,a=self.fixture([[[64.,16.,-288.],[66.,16.,-288.],[64.,16.,-286.]]]);d['placements']['S']['position_m']=[1,0,0]
  with self.assertRaises(AssertionError):transform(d,'S',a)
 def test_implementation_binding(self):self.assertEqual(sha(pathlib.Path(origin.__file__)),IMPLEMENTATION_SHA)
 def test_two_actual_shared_support_assets(self):
  p=ROOT/'world_city/concept_city_v3/traversal_r5/revisions/r06_r8_precinct/public_network_r18_runtime_r01/prepared_runtime.json';d=json.loads(p.read_bytes())
  for rid in ['CROSSING_MARKET_NORTH_LANE_1','NORTH_TWO_BRIDGE_INTERIOR_TURN_R03']:
   route=next(r for r in d['routes']if r['id']==rid);key=next(d['placements'][pid]['asset_key']for pid in route['placement_ids']if d['assets'][d['placements'][pid]['asset_key']].get('collision_format')=='actual_scene_triangles');asset=json.loads((ROOT/d['assets'][key]['render_path']).read_bytes());local,t,proof=transform(d,key,asset);self.assertEqual(t,[64,16,-288]);self.assertIsNone(proof['fallback_reason']);self.assertEqual(proof['applied_world_roundtrip_error_m'],0);self.assertEqual(len(local['triangles']),len(asset['triangles']))
if __name__=='__main__':unittest.main()
