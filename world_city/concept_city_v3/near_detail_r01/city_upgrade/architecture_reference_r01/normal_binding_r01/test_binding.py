import unittest,copy
from bind_unchanged_groups import bind
class BindingTests(unittest.TestCase):
 def setUp(self):
  self.a={'schema':'riverstone.voxel.render.v1','materials':{'roof':[.7,.2,.1,1],'body':[.3,.4,.5,1]},'groups':[{'material':'body','quads':[[[0,0,0]]*4]},{'material':'roof','quads':[[[1,1,1],[1,1,2],[2,1,2],[2,1,1]]]}]}
  self.b=copy.deepcopy(self.a);self.s={'schema':'riverstone.roof.normal_split_sidecar.v1','render_sha256':'old','patches':[{'group_index':1,'quad_index':0}],'splits':[]}
 def call(self):return bind(self.a,self.b,self.s,'old','new','frozen')
 def test_equal(self):self.assertEqual(self.call()[0]['render_sha256'],'new');self.assertEqual(self.s['render_sha256'],'old')
 def test_unrelated_body_change(self):self.b['groups'][0]['quads']=[];self.assertEqual(len(self.call()[1]['groups_exact']),1)
 def test_group_reordered(self):self.b['groups'].reverse();self.assertRaises(ValueError,self.call)
 def test_quad_position(self):self.b['groups'][1]['quads'][0][0][0]+=1;self.assertRaises(ValueError,self.call)
 def test_quad_winding(self):self.b['groups'][1]['quads'][0].reverse();self.assertRaises(ValueError,self.call)
 def test_material(self):self.b['materials']['roof'][0]=.6;self.assertRaises(ValueError,self.call)
 def test_appended_material(self):self.b['materials']['measured_wood_0']=[.2,.1,0,1];self.assertEqual(list(self.call()[1]['appended_materials']),['measured_wood_0'])
 def test_original_body_color(self):self.b['materials']['body'][0]=.8;self.assertRaises(ValueError,self.call)
 def test_missing_old_palette(self):del self.b['materials']['body'];self.assertRaises(ValueError,self.call)
 def test_source_pin(self):self.s['render_sha256']='bad';self.assertRaises(ValueError,self.call)
 def test_missing_group(self):self.b['groups'].pop();self.assertRaises(ValueError,self.call)
 def test_wrong_schema(self):self.b['schema']='unknown';self.assertRaises(ValueError,self.call)
 def test_target_range(self):self.s['patches'][0]['quad_index']=5;self.assertRaises(ValueError,self.call)
 def test_empty_targets(self):self.s['patches']=[];self.assertRaises(ValueError,self.call)
if __name__=='__main__':unittest.main()
