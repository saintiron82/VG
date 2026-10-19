import copy, unittest
from window_module_v1 import build_window_module
import revise_windows as base
M={'timber_light':'986e48','timber_dark':'493322','plaster':'ded7b8','glass':'314d55','iron':'353535'}
class WindowModule(unittest.TestCase):
 def build(self,*args,**kw):return build_window_module(*args,materials=M,**kw)
 def test_narrow_ordinary_wide_different_sizes(self):
  for w,h in [(1.15,1),(1.45,1.35),(2.5,1.65)]:
   x=self.build(w,h);self.assertEqual(x['dimensions']['aperture_m'],[w,h]);self.assertAlmostEqual(x['dimensions']['clear_frame_span_m'][0],w-.1)
 def test_styles_and_actual_depth(self):
  for style,recess,n in [('thin_wood_casement',.15,9),('plaster_trim_recessed_wood',.25,13)]:
   x=self.build(1.45,1.35,style);self.assertEqual(len(x['component']['operations']),n);self.assertAlmostEqual(x['component']['operations'][0]['shape']['max'][2],-recess)
 def test_no_shutters_closed_glass_not_passage(self):
  x=self.build(1.2,1);self.assertEqual(x['state_contract'],{'glazing':'closed','shutters':'absent','passage_open':False,'structural_members_included':False});self.assertFalse(any('shutter' in o['id'] for o in x['component']['operations']))
 def test_closed_shutters_have_exact_backing_coverage(self):
  x=self.build(1.2,1,state='shutters_closed');ops={o['id']:o for o in x['component']['operations']};self.assertEqual(ops['window_shutter_left']['shape']['min'],[-.6,0,.125]);self.assertEqual(ops['window_shutter_left']['shape']['max'],[0,1,.175]);self.assertEqual(ops['window_shutter_right']['shape']['min'],[0,0,.125]);self.assertEqual(x['dimensions']['projected_visible_glass_ratio'],0)
 def test_side_open_requires_measured_clearance(self):
  for clearance in [None,{'left':1}, {'left':.1,'right':1}]:
   with self.assertRaises(ValueError):self.build(1.2,1,state='glazed_closed_shutters_open',side_clearance=clearance)
  x=self.build(1.2,1,state='glazed_closed_shutters_open',side_clearance={'left':.7,'right':.7});self.assertEqual(x['state_contract']['shutters'],'side_open')
 def test_wall_cut_ownership_and_dimensions(self):
  x=self.build(1.2,1,module_id='GalleryWindow_03',wall_part_id='masonry',wall_depth_m=.45);cut=x['opening_cut'];self.assertEqual(cut['part'],'masonry');self.assertEqual(cut['selector'],{'part':'masonry'});self.assertAlmostEqual(cut['shape']['min'][2],-.475);self.assertEqual(x['component']['id'],'GalleryWindow_03');self.assertTrue(all(o['action']=='paint' for o in x['component']['operations']))
 def test_grain_axes_bind_final_material_and_id(self):
  for style in ['thin_wood_casement','plaster_trim_recessed_wood']:
   x=self.build(1.2,1,style,state='shutters_closed');ops={o['id']:o for o in x['component']['operations']}
   for a in x['grain_axes']:self.assertIn(a['operation_id'],ops);self.assertEqual(a['material'],ops[a['operation_id']]['material']);self.assertNotEqual(a['material'],'plaster');self.assertEqual(sum(v*v for v in a['grain_axis_component_local']),1)
   woods={o['id'] for o in ops.values() if o['material'] in ('timber_light','timber_dark')};self.assertEqual(woods,{a['operation_id'] for a in x['grain_axes']})
 def test_unknown_styles_states_fail(self):
  for kw in [{'style':'gothic'},{'state':'casement_open'},{'state':'open_void'}]:
   with self.assertRaises(ValueError):self.build(1.2,1,**kw)
 def test_invalid_dimensions_fail(self):
  for w,h in [(float('nan'),1),(float('inf'),1),(.2,1),(-1,1),(True,1)]:
   with self.assertRaises(ValueError):self.build(w,h)
  with self.assertRaises(ValueError):self.build(1.2,1,'plaster_trim_recessed_wood',wall_depth_m=.2)
 def test_caller_materials_unchanged_and_remap(self):
  before=copy.deepcopy(M);self.build(1.2,1);self.assertEqual(before,M)
  x=build_window_module(1.2,1,materials={'oak':'123456','pane':'789abc'},material_slots={'wood_light':'oak','glass':'pane'});self.assertEqual({o['material'] for o in x['component']['operations']},{'oak','pane'})
 def test_no_compiler_is_invoked(self):
  original=base.a.core.compile_master
  def reject(*args,**kw):raise AssertionError('sampling not allowed')
  base.a.core.compile_master=reject
  try:x=self.build(1.2,1);self.assertFalse(x['provenance']['compile_run'])
  finally:base.a.core.compile_master=original
 def test_deterministic_and_unique_ids(self):
  a=self.build(1.2,1,state='shutters_closed');b=self.build(1.2,1,state='shutters_closed');self.assertEqual(a,b);ids=[o['id'] for o in a['component']['operations']];self.assertEqual(len(ids),len(set(ids)))
if __name__=='__main__':unittest.main(verbosity=2)
