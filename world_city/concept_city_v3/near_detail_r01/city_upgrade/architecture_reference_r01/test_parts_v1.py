"""Small source-only positive/negative tests; none is an A production building."""
import copy,hashlib,json,sys,time,unittest
from pathlib import Path
from parts_v1 import AssemblyKit,unit_material,core,ROOT
import validate_assembly_v1 as v
from measurements_v1 import pixel_world,resolve_dimensions,validate_measurements

class Parts(unittest.TestCase):
 def test_deterministic_unit_palette(self):
  ids=['tile_%d_%d'%(r,t) for r in range(4) for t in range(12)];a={i:unit_material(i,'tile',['slate','slate_dark','slate_light'],411) for i in ids};b={i:unit_material(i,'tile',['slate','slate_dark','slate_light'],411) for i in reversed(ids)};self.assertEqual(a,b);self.assertEqual(len(set(a.values())),3)
 def test_more_than_three_tones_rejected(self):
  with self.assertRaises(ValueError):unit_material('x','tile',['a','b','c','d'],1)
 def test_duplicate_tones_rejected(self):
  with self.assertRaises(ValueError):unit_material('x','tile',['a','a'],1)
 def test_actual_perforation(self):
  a=AssemblyKit('synthetic_pierced_board');a.perforated_board('board',.3,1,.1,.12,.3,[0,0,0]);rows=v.world_records(a.master());self.assertFalse(v.point_labels(rows,[0,.5,0]));self.assertTrue(v.point_labels(rows,[.13,.5,0]));self.assertTrue(v.point_labels(rows,[0,.1,0]))
 def test_perforation_cannot_erase_board(self):
  with self.assertRaises(ValueError):AssemblyKit('x').perforated_board('board',.3,1,.1,.3,.3,[0,0,0])
 def test_brace_grain(self):
  a=AssemblyKit('x');a.brace('brace',0,0,1,1,.1,0,.1);self.assertAlmostEqual(a.grain_axes[0]['grain_axis_component_local'][0],2**-.5);self.assertTrue(v.point_labels(v.world_records(a.master()),[.5,.5,.05]))
 def test_window_same_pose_all_sides(self):
  for side in ('front','right','back','left'):
   a=AssemblyKit('test_'+side);wall=a.wall('wall',4,3,.35,[2,.5,-1],side);module=a.window(wall,'window',1.4,1.6,.5,.7,.35);m=a.master();rows=v.world_records(m);inst=next(i for i in m['instances'] if i['id']=='window');t=core.transform(inst['transform']);self.assertFalse('wall' in v.point_labels(rows,core.apply(t,[0,.4,-.1])));self.assertEqual(v.point_labels(rows,core.apply(t,[.3,.4,-.175]))['window']['material'],'glass');self.assertEqual(module['dimensions']['mullion_width_m'],.05)
 def test_window_does_not_cut_post(self):
  a=AssemblyKit('test');wall=a.wall('wall',4,3,.35,[0,0,0]);a.solid_box('post',[-.1,0,-.2],[.1,3,.1]);before=copy.deepcopy(a.components[-1]);a.window(wall,'window',1.4,1.6,0,.7,.35);self.assertEqual(a.components[1],before);self.assertIn('post',v.point_labels(v.world_records(a.master()),[0,1,-.1]))
 def test_open_shutters_require_clearance(self):
  a=AssemblyKit('test');wall=a.wall('wall',4,3,.35,[0,0,0])
  with self.assertRaises(ValueError):a.window(wall,'window',1.4,1.6,0,.7,.35,state='glazed_closed_shutters_open')
 def test_window_depth_too_shallow(self):
  a=AssemblyKit('test');wall=a.wall('wall',4,3,.1,[0,0,0])
  with self.assertRaises(ValueError):a.window(wall,'window',1.4,1.6,0,.7,.1)
 def test_deck_level_door_and_clear_route(self):
  a=AssemblyKit('test');wall=a.wall('wall',4,3,.35,[0,3.5,0]);a.open_doorway(wall,'door',1.2,2.25,0,0,.35,3.5);m=a.master();reservation={'min':[-.5,3.55,-.5],'max':[.5,5.5,.8]};self.assertTrue(v.empty_reservation(v.world_records(m),reservation)['clear'])
 def test_short_window_cannot_be_balcony_door(self):
  a=AssemblyKit('test');wall=a.wall('wall',4,3,.35,[0,3.5,0])
  with self.assertRaises(ValueError):a.open_doorway(wall,'door',1.2,1.5,0,.7,.35,3.5)
 def test_raised_door_bottom_rejected(self):
  a=AssemblyKit('test');wall=a.wall('wall',4,3,.35,[0,3.5,0])
  with self.assertRaises(ValueError):a.open_doorway(wall,'door',1.2,2.1,0,.3,.35,3.5)
 def test_later_paint_blocks_door(self):
  a=AssemblyKit('test');wall=a.wall('wall',4,3,.35,[0,0,0]);a.open_doorway(wall,'door',1.2,2.25,0,0,.35,0);a.paint(wall,'bad_glass',{'kind':'box','min':[-.6,0,-.2],'max':[.6,2.25,-.1]},'glass');self.assertFalse(v.empty_reservation(v.world_records(a.master()),{'min':[-.5,.05,-.5],'max':[.5,2,.5]})['clear'])
 def test_gallery_deck_no_gaps(self):
  a=AssemblyKit('test');d=a.gallery_deck('deck',-1,1,3.65,4.75,3.5,.2,[[-1,0],[0,1]]);self.assertAlmostEqual(d['depth_m'],1.1);self.assertTrue(v.point_labels(v.world_records(a.master()),[0,3.4,4]))
 def test_gallery_gap_rejected(self):
  with self.assertRaises(ValueError):AssemblyKit('x').gallery_deck('deck',-1,1,3.65,4.75,3.5,.2,[[-1,-.1],[.1,1]])
 def test_envelope_overhang_rejected(self):
  a=AssemblyKit('test');a.solid_box('beam',[0,0,0],[6.1,1,1]);r=v.validate(a.master(),{'envelope':{'min':[-6,0,-5],'max':[6,14,5]}});self.assertFalse(r['all_pass'])
 def test_source_support_contact(self):
  a=AssemblyKit('test');a.solid_box('post',[-.1,0,-.1],[.1,3.5,.1]);a.solid_box('beam',[-1,3.4,-.2],[1,3.6,.2]);r=v.validate(a.master(),{'envelope':{'min':[-6,0,-5],'max':[6,14,5]},'support_connections':[{'id':'joint','a':'post','b':'beam','contact_witnesses':[[0,3.45,0]]}]});self.assertTrue(r['all_pass'])
 def test_disconnected_support_rejected(self):
  a=AssemblyKit('test');a.solid_box('post',[-.1,0,-.1],[.1,3.2,.1]);a.solid_box('beam',[-1,3.4,-.2],[1,3.6,.2]);r=v.validate(a.master(),{'envelope':{'min':[-6,0,-5],'max':[6,14,5]},'support_connections':[{'id':'joint','a':'post','b':'beam','contact_witnesses':[[0,3.45,0]]}]});self.assertFalse(r['all_pass'])
 def test_gable_uses_measured_peak(self):
  a=AssemblyKit('test');a.roof_gable('roof',12,-5,5,9.5,13.5);r=v.validate(a.master(),{'envelope':{'min':[-6,0,-5],'max':[6,14,5]}});self.assertTrue(r['all_pass']);self.assertEqual(max(x['bounds']['max'][1] for x in v.world_records(a.master())),13.5)
 def test_raw_dimensions_rejected(self):
  with self.assertRaises(ValueError):resolve_dimensions(12,{'values':{}})
 def test_unmeasured_boundary_rejected(self):
  with self.assertRaises(ValueError):resolve_dimensions({'measurement':'x'},{'values':{'x':{'value_m':12,'provenance_kind':'planned_scale'}}},'pixel_measurement')
 def test_no_measurement_input_rejected(self):
  with self.assertRaises(ValueError):validate_measurements({},ROOT)
 def test_pixel_affine_no_hidden_scaling(self):
  view={'size_px':[1536,1024],'pixel_to_world_3x3':[[1/32,0,-8],[0,-1/32,15.5],[0,0,0]]};self.assertEqual(pixel_world(view,[64,496]),[-6,0,0]);self.assertEqual(pixel_world(view,[448,48]),[6,14,0])
 def test_side_clearance_reference_dictionary(self):
  values={'values':{'left':{'value_m':.8,'provenance_kind':'pixel_measurement'},'right':{'value_m':.9,'provenance_kind':'pixel_measurement'}}};self.assertEqual(resolve_dimensions({'left':{'measurement':'left'},'right':{'measurement':'right'}},values),{'left':.8,'right':.9})
 def test_production_emitter_requires_actual_measurements(self):
  from author_measured_v1 import build_source
  with self.assertRaises(ValueError):build_source({'schema':'riverstone.architecture.measured_recipe.v1'},{})
 def test_pixel_outside_rejected(self):
  with self.assertRaises(ValueError):pixel_world({'size_px':[12,12]},[13,1])

if __name__=='__main__':
 start=time.monotonic();suite=unittest.defaultTestLoader.loadTestsFromTestCase(Parts);result=unittest.TextTestRunner(verbosity=2).run(suite)
 out=Path(__file__).with_name('source_unit_tests.r01.json');out.write_text(json.dumps({'schema':'riverstone.architecture.source_unit_tests.v1','all_pass':result.wasSuccessful(),'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'seconds':time.monotonic()-start,'sampling_calls':0,'production_A_master_created':False,'proof_scope':'Synthetic source parts, reservations, preset pose and strict measurement refusal; actual six-view reconstruction pending.'},indent=2)+'\n');sys.exit(not result.wasSuccessful())
