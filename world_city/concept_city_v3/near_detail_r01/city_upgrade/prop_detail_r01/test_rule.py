from pathlib import Path
import copy,json,unittest
from lathe_stave_rule import apply
H=Path(__file__).resolve().parent
R=H.parent.parents[3]
class Rules(unittest.TestCase):
 def setUp(self):
  self.m=json.loads((R/'world_city/concept_city_v3/registered_integration/r9/port_market/masters/cargo_barrel.json').read_text());self.s=json.loads((H/'barrel_r01/rule.json').read_text())
 def test_deterministic(self): self.assertEqual(apply(self.m,self.s),apply(self.m,self.s))
 def test_source_immutable(self):
  old=copy.deepcopy(self.m);apply(self.m,self.s);self.assertEqual(self.m,old)
 def test_hoops_and_instances_unchanged(self):
  n,_=apply(self.m,self.s);self.assertEqual(n['components'][1:],self.m['components'][1:]);self.assertEqual(n['instances'],self.m['instances'])
 def test_profile_follows_changed_shape(self):
  m=copy.deepcopy(self.m);m['components'][0]['operations'][0]['shape']['profile'][2][0]=.42
  n,_=apply(m,self.s);a=apply(self.m,self.s)[0];self.assertNotEqual(n['components'][0]['operations'][1]['shape'],a['components'][0]['operations'][1]['shape'])
 def test_second_valid_lathe(self):
  m=copy.deepcopy(self.m);m['components'][0]['operations'][0]['shape']['profile']=[[0,0],[.4,0],[.5,.5],[.4,1.2],[0,1.2]]
  n,ops=apply(m,self.s);self.assertEqual(ops[0]['shape']['polygon'][0],[.375,0])
 def test_invalid_count(self):
  for v in [0,7,33,16.5]:
   s={**self.s,'stave_count':v}
   with self.assertRaises(AssertionError):apply(self.m,s)
 def test_invalid_depth(self):
  for v in [0,-.01,.2]:
   with self.assertRaises(AssertionError):apply(self.m,{**self.s,'groove_depth_m':v})
 def test_invalid_width(self):
  for v in [0,-.01,.2]:
   with self.assertRaises(AssertionError):apply(self.m,{**self.s,'groove_width_m':v})
 def test_invalid_spacing(self):
  for v in [0,.01,1]:
   with self.assertRaises(AssertionError):apply(self.m,{**self.s,'cap_board_spacing_m':v})
 def test_multiple_operations_reject(self):
  self.m['components'][0]['operations'].append(copy.deepcopy(self.m['components'][0]['operations'][0]))
  with self.assertRaises(AssertionError):apply(self.m,self.s)
 def test_transform_reject(self):
  self.m['components'][0]['operations'][0]['transform']={'translation':[1,0,0]}
  with self.assertRaises(AssertionError):apply(self.m,self.s)
 def test_nonwood_reject(self):
  self.m['components'][0]['operations'][0]['material']='stone'
  with self.assertRaises(AssertionError):apply(self.m,self.s)
 def test_nonmonotonic_reject(self):
  self.m['components'][0]['operations'][0]['shape']['profile'][2][1]=0
  with self.assertRaises(AssertionError):apply(self.m,self.s)
if __name__=='__main__':unittest.main()
