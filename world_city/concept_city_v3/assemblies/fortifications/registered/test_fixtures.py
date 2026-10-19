import json,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];sys.path.insert(0,str(ROOT))
from voxel_character.common import core,coordinate_planes
from author_fixtures import ref
class FixtureTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.r=json.loads((HERE/'fixture_manifest.json').read_text())
 def test_hashes_and_caps(self):
  self.assertEqual(self.r['status'],'pass');self.assertEqual(len(self.r['sources']),10)
  for r in self.r['sources']:
   self.assertEqual(ref(ROOT/r['source']['path']),r['source']);self.assertEqual(ref(ROOT/r['cache']['path']),r['cache']);self.assertLess(r['candidate_cells'],2000000)
   s=json.loads((ROOT/r['source']['path']).read_text());c=json.loads((ROOT/r['cache']['path']).read_text());self.assertEqual(core.digest(s),c['master_hash'])
 def test_both_gate_jambs_reach_ground(self):
  for r in self.r['sources']:
   if '_gate_header' not in r['id']:continue
   s=json.loads((ROOT/r['source']['path']).read_text());c=coordinate_planes.compile_master(s,{'pitch':.5},max_candidate_cells=100000,max_output_cells=50000);low=[row for row in c['cells'] if -.5<(row[1]+.5)*.5<1]
   self.assertTrue(any(row[0]<0 for row in low));self.assertTrue(any(row[0]>=0 for row in low));self.assertEqual(c['payload_hash'],json.loads((ROOT/r['cache']['path']).read_text())['payload_hash'])
   clear=s['extensions']['design_dimensions_m']['clear_width'];blocked=[row for row in c['cells'] if abs((row[0]+.5)*.5)<clear/2 and .1<(row[1]+.5)*.5<3.5];self.assertEqual(blocked,[])
 def test_no_extra_gates_or_placement(self):
  self.assertEqual(self.r['placements'],[]);p=json.loads((ROOT/self.r['source_plan']['path']).read_text());self.assertEqual(len(p['gates']),2);self.assertFalse(self.r['actual_scene_loaded'])
 def test_tower_roof_sampling_error_declared(self):
  for r in self.r['sources']:
   if 'fort_tower' in r['id']:
    target=int(r['id'].split('x')[-1]);self.assertLessEqual(abs(r['bounds']['max'][1]-target),.5)
 def test_footings_have_symmetric_four_metre_bearing(self):
  for r in self.r['sources']:
   if 'fort_footing' in r['id']:self.assertEqual([r['bounds']['min'][2],r['bounds']['max'][2]],[-2,2])
if __name__=='__main__':unittest.main(verbosity=2)
