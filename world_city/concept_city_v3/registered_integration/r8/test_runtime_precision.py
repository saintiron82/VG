import copy,unittest
from .runtime_precision import normalize_surfaces,zero_mask
class Test(unittest.TestCase):
 def test_exact_float32_collapse_only(self):
  flat=[[100.,2.,0.],[100.+1e-13,2.,0.],[101.,2.,1.]];s={'road':flat};old=copy.deepcopy(s);o,r,c,m=normalize_surfaces(s);self.assertEqual(o['road'],[]);self.assertEqual(len(r),1);self.assertEqual(s,old);self.assertEqual(m['road'],[])
 def test_tiny_representable_triangle_retained_without_threshold(self):
  f=[[0.,0.,0.],[0.,0.,1e-8],[1e-8,0.,0.]];o,r,_,m=normalize_surfaces({'road':f});self.assertEqual(o['road'],f);self.assertFalse(r);self.assertEqual(m['road'],[0])
 def test_every_nonzero_triangle_order_and_double_values_retained(self):
  a=[[1.,0.,1.],[1.,0.,2.],[2.,0.,1.]];b=[[100.,2.,0.],[100.+1e-13,2.,0.],[101.,2.,1.]];c=[[3.000000000001,0.,3.],[3.,0.,4.],[4.,0.,3.]]
  o,r,_,m=normalize_surfaces({'road':a+b+c});self.assertEqual(o['road'],a+c);self.assertEqual(m['road'],[0,2]);self.assertEqual(r[0]['source_triangle_index'],1)
 def test_nonfinite_is_error_not_removed(self):
  with self.assertRaisesRegex(ValueError,'Nonfinite'):zero_mask([[0.,0.,0.],[float('inf'),0.,1.],[1.,0.,0.]])
 def test_vertical_nonzero_faces_preserved(self):
  f=[[0.,0.,0.],[0.,1.,0.],[0.,0.,1.]];o,r,_,_=normalize_surfaces({'bank':f});self.assertEqual(o['bank'],f);self.assertFalse(r)
if __name__=='__main__':unittest.main()
