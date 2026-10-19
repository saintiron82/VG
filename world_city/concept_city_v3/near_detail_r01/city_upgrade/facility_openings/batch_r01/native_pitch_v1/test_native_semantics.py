import unittest
import verify_native_semantics as v

class Semantics(unittest.TestCase):
    def setUp(self):
        self.box={'min':[0,0,0],'max':[1,1,1]}
        self.q=v.a.rect_quad([0,0,1,1],2,[0,1],.5,1)
    def test_identical(self):
        a=v.domain_faces([('stone',self.q)],self.box);self.assertEqual(v.difference_area(a,a),0)
    def test_removed(self):
        self.assertEqual(v.difference_area(v.domain_faces([('stone',self.q)],self.box),{}),1)
    def test_material_changed(self):
        a=v.domain_faces([('stone',self.q)],self.box);b=v.domain_faces([('iron',self.q)],self.box);self.assertEqual(v.difference_area(a,b),1)
    def test_reversed(self):
        a=v.domain_faces([('stone',self.q)],self.box);b=v.domain_faces([('stone',list(reversed(self.q)))],self.box);self.assertEqual(v.difference_area(a,b),1)
    def test_fragmentation_equal(self):
        a=v.domain_faces([('stone',self.q)],self.box);b=v.domain_faces([('stone',v.a.rect_quad(r,2,[0,1],.5,1)) for r in [[0,0,.5,1],[.5,0,1,1]]],self.box);self.assertEqual(v.difference_area(a,b)+v.difference_area(b,a),0)
    def test_clip(self):
        b={'min':[.2,.3,0],'max':[.8,.7,1]};self.assertAlmostEqual(v.difference_area(v.domain_faces([('stone',self.q)],b),{}),.24)
    def test_open_constraint_18(self):
        s={'constraints':[{'id':'bay','kind':'empty_region','selector':{},'shape':{'kind':'box',**self.box}}]};self.assertEqual(len(v.empty_constraint_probes(s,[])),18)
    def test_closed_constraint_rejected(self):
        s={'constraints':[{'id':'bay','kind':'empty_region','selector':{},'shape':{'kind':'box',**self.box}}]}
        with self.assertRaises(AssertionError):v.empty_constraint_probes(s,[('stone',self.q)])
    def test_touch_disjoint(self):
        self.assertFalse(v.overlap(self.box,{'min':[1,0,0],'max':[2,1,1]}))
    def test_intrusion(self):
        self.assertTrue(v.overlap(self.box,{'min':[.99,0,0],'max':[2,1,1]}))

if __name__=='__main__':unittest.main()
