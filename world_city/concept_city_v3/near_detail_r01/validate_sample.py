"""Reproducible lightweight contracts; deep occupancy audit remains independent evidence."""
from pathlib import Path
import hashlib,json,sys,unittest
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2];sys.path.insert(0,str(HERE))
import author_house

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
class Contract(unittest.TestCase):
 def test_master_reauthor_identity(self):
  self.assertEqual(author_house.build()[1],read(HERE/'source/house.r04.master.json'))
 def test_source_identity(self):
  m=read(HERE/'source/house.r04.master.json')['provenance']['near_detail']
  self.assertEqual(sha(ROOT/m['source_master']),m['source_sha256']);self.assertEqual(sha(ROOT/m['detailed_rule_reference']),m['detailed_sha256'])
 def test_render_matches_compilation(self):
  stats=read(HERE/'generated/house_near_r04.stats.json')
  self.assertEqual(sha(HERE/'preview/assets/house_after.render.json'),stats['files']['house_near_r04.render.json']['sha256'])
  self.assertEqual(stats['quads'],31928)
 def test_original_framework_unchanged(self):
  self.assertEqual(sha(HERE/'preview/RenderData.gd'),sha(ROOT/'world_city/concept_city_v3/playable_r01/RenderData.gd'))
  self.assertEqual(sha(HERE/'preview/character/runtime/LilyController.gd'),sha(ROOT/'voxel_character/lily_city/runtime/LilyController.gd'))
 def test_no_absolute_runtime_dependencies(self):
  for p in (HERE/'preview').rglob('*.gd'):
   if '.godot' not in p.parts:self.assertNotIn('/workspace/',p.read_text())
 def test_steps_visual_profile(self):
  ops=read(HERE/'source/entry_steps.master.json')['components'][0]['operations'];self.assertEqual(len(ops),3)
  for i,o in enumerate(ops):
   self.assertAlmostEqual(o['shape']['max'][1],.375-.125*i)
   self.assertAlmostEqual(o['shape']['max'][2],7+.3*(i+1))
  # Ramp is within a single visible riser of the authored stepped surface.
  for i in range(901):
   z=7+i*.001;ramp=.5*(7.9-z)/.9;visible=.375 if z<7.3 else .25 if z<7.6 else .125
   self.assertLessEqual(abs(ramp-visible),.1250001)
 def test_script_and_export_replay(self):
  a=read(HERE/'evidence/runtime/entry_r03.json');b=read(HERE/'evidence/runtime/exported_pack.json')
  for d in (a,b):self.assertTrue(d['controller_pass']);self.assertEqual(d['settled_ground_loss_frames'],0);self.assertGreater(d['entry_ascent']['feet_position_m'][1],.49);self.assertLess(d['entry_descent']['feet_position_m'][1],.01)
  for x,y in zip(a['player']['feet_position_m'],b['player']['feet_position_m']):self.assertAlmostEqual(x,y,places=6)
 def test_actual_gui(self):
  d=read(HERE/'evidence/runtime/exported_gui.json');keys=[e for e in d['events'] if e.get('event')=='gui_key']
  self.assertTrue(any(e['key']=='S' and e['player']['feet_position_m'][1]>.49 for e in keys))
  self.assertLess(d['player']['feet_position_m'][1],.01);self.assertGreater(d['player']['distance_walked_m'],9)
 def test_matched_camera_comparison(self):
  for view in ['overview','street','roof','stone']:
   a=read(HERE/'evidence/visual_r06'/f'{view}_before.json');b=read(HERE/'evidence/visual_r06'/f'{view}_after.json')
   self.assertEqual(a['camera_transform'],b['camera_transform']);self.assertEqual(a['lighting'],b['lighting'])
if __name__=='__main__':unittest.main(verbosity=2)
