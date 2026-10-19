import copy,random,unittest
import adapter as a
from semantic_selector_cache_v1 import SemanticSelectorCache,FIELDS
class Tests(unittest.TestCase):
 def setUp(self):
  self.mapping={'i0':'c0','i1':'c1'}
  self.cs=[{'id':'all','kind':'nonempty','selector':{}},{'id':'part','kind':'connected','selector':{'part':['wall','floor']}},{'id':'glass','kind':'nonempty','selector':{'material':'glass'}},{'id':'feature','kind':'nonempty','selector':{'feature':['opening','detail']}},{'id':'compound','kind':'connected','selector':{'instance':['i0'],'component':'c0','part':'wall','material':['wood','glass'],'feature':'detail'}}]
 def ref(self,row):
  key=(row[3],self.mapping[row[3]],row[4],row[5],row[6]);cell=dict(zip(FIELDS,key))
  return tuple((c['id'],c['kind']) for c in self.cs if a.core.selector_matches(c['selector'],cell))
 def test_random_exact_order_and_all_semantic_fields(self):
  rng=random.Random(41873);c=SemanticSelectorCache(self.cs,self.mapping,a.core.selector_matches)
  for _ in range(10000):
   r=[rng.randrange(-100,100),rng.randrange(-100,100),rng.randrange(-100,100),rng.choice(list(self.mapping)),rng.choice(['wall','floor','roof']),rng.choice(['wood','glass','stone']),rng.choice(['opening','detail',None])]
   self.assertEqual(c.match(r),self.ref(r))
  self.assertGreater(c.hits,9000)
 def test_coordinates_do_not_change_semantic_result(self):
  c=SemanticSelectorCache(self.cs,self.mapping,a.core.selector_matches);r=[0,0,0,'i0','wall','glass','detail'];x=c.match(r)
  self.assertEqual(c.match([-100,25,700,*r[3:]]),x);self.assertEqual(c.hits,1)
 def test_bounded_cache_and_reference_fallback_exact(self):
  for limit in (0,1,2):
   c=SemanticSelectorCache(self.cs,self.mapping,a.core.selector_matches,max_cached_keys=limit)
   for part in ('wall','floor','roof'):
    for material in ('wood','glass'):
     r=[0,0,0,'i0',part,material,None];self.assertEqual(c.match(r),self.ref(r))
   self.assertLessEqual(c.metrics()['cached_semantic_keys'],limit)
 def test_unhashable_semantic_value_uses_reference(self):
  c=SemanticSelectorCache(self.cs,self.mapping,a.core.selector_matches);r=[0,0,0,'i0','wall','glass',['detail']]
  self.assertEqual(c.match(r),self.ref(r));self.assertEqual(c.uncached,1)
 def test_snapshot_not_mutated_and_change_rejected(self):
  original=copy.deepcopy(self.cs);c=SemanticSelectorCache(self.cs,self.mapping,a.core.selector_matches);self.cs[1]['selector']['part'].append('roof')
  with self.assertRaises(ValueError):c.assert_source(self.cs,self.mapping)
  c.assert_source(original,self.mapping)
 def test_no_cache_sharing_between_sources(self):
  x=SemanticSelectorCache(self.cs,self.mapping,a.core.selector_matches);r=[0,0,0,'i0','wall','glass','detail'];before=x.match(r)
  changed=copy.deepcopy(self.cs);changed[2]['selector']={'material':'stone'};y=SemanticSelectorCache(changed,self.mapping,a.core.selector_matches)
  self.assertNotEqual(before,y.match(r));self.assertEqual(x.match(r),before)
 def test_invalid_contracts_rejected(self):
  for cs,n in [(self.cs,-1),(self.cs,True),(self.cs+self.cs[:1],10),([{'id':'x','kind':'other'}],10)]:
   with self.assertRaises(ValueError):SemanticSelectorCache(cs,self.mapping,a.core.selector_matches,max_cached_keys=n)
 def test_unknown_instance_rejected(self):
  c=SemanticSelectorCache(self.cs,self.mapping,a.core.selector_matches)
  with self.assertRaises(KeyError):c.match([0,0,0,'absent','wall','wood',None])
if __name__=='__main__':unittest.main()
