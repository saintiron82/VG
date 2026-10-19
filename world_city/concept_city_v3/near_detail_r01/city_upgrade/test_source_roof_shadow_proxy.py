"""Finite cut exclusion guard; no runtime/catalog writes."""
import copy,json,unittest
from pathlib import Path
from build_source_roof_shadow_proxy import prove_unaffected_roof_operation
from facility_roofs.author_facility_roofs import instance_transforms,transformed_bounds,core
R=Path(__file__).resolve().parents[4]
class CutGuard(unittest.TestCase):
 def setUp(self):
  self.m=json.loads((R/'world_city/concept_city_v3/assemblies/landmarks/registered/assembly_r01/masters/registered_cathedral_north_cloister_range.json').read_text());self.c=next(c for c in self.m['components']if c['id']=='roof');self.op=self.c['operations'][0];self.t=instance_transforms(self.m)
 def test_actual_all_seven(self):
  proofs=[]
  for op in self.c['operations']:proofs+=prove_unaffected_roof_operation(self.m,self.c,op,self.t)
  self.assertEqual(len(proofs),7);self.assertTrue(all(p['roof_operation_aabb']['min'][1]-p['cut_aabb']['max'][1]>=11.4-1e-8 for p in proofs))
 def roof_bounds(self):
  ins=next(i for i in self.m['instances']if i['component']==self.c['id']);return transformed_bounds(self.op['shape'],core.compose(self.t[ins['id']],core.transform(self.op.get('transform'))))
 def test_intersection_rejected(self):
  b=self.roof_bounds();self.m['assembly_cuts'][0]['shape']={'kind':'box','min':b['min'],'max':b['max']}
  with self.assertRaises(AssertionError):prove_unaffected_roof_operation(self.m,self.c,self.op,self.t)
 def test_unsupported_epsilon_overlap_rejected(self):
  b=self.roof_bounds();lo=b['min'][:];hi=b['max'][:];lo[1]=b['min'][1]-1;hi[1]=b['min'][1]+1e-10;self.m['assembly_cuts'][0]['shape']={'kind':'box','min':lo,'max':hi}
  with self.assertRaises(AssertionError):prove_unaffected_roof_operation(self.m,self.c,self.op,self.t)
 def test_explicit_selector_exclusion(self):
  b=self.roof_bounds();self.m['assembly_cuts'][0]['shape']={'kind':'box','min':b['min'],'max':b['max']};self.m['assembly_cuts'][0]['selector']={'material':['not_a_roof_material']}
  self.assertTrue(all(p['exclusion']=='selector_excludes_roof_operation'for p in prove_unaffected_roof_operation(self.m,self.c,self.op,self.t)))
if __name__=='__main__':unittest.main()
