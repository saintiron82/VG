import gzip,json,unittest
from pathlib import Path
import audit as a
class Areas(unittest.TestCase):
 def setUp(self):self.p=[[0,0],[2,0],[2,1],[0,1]]
 def test_empty(self):self.assertEqual(a.unoccluded(self.p,[]),2)
 def test_whole_mask(self):self.assertEqual(a.unoccluded(self.p,[[-1,-1,3,3]]),0)
 def test_half(self):self.assertEqual(a.unoccluded(self.p,[[0,0,1,1]]),1)
 def test_overlap_not_double_subtracted(self):self.assertEqual(a.unoccluded(self.p,[[0,0,1.5,1],[.5,0,2,1]]),0)
 def test_duplicate_not_double_subtracted(self):self.assertEqual(a.unoccluded(self.p,[[0,0,1,1],[0,0,1,1]]),1)
 def test_open_shutter_outside(self):self.assertEqual(a.unoccluded(self.p,[[2,0,2.5,1]]),2)
 def test_crossing_rectangle(self):self.assertEqual(a.unoccluded(self.p,[[-1,.25,3,.75]]),1)
 def test_gothic_triangle_clip(self):
  p=[[0,0],[2,0],[2,2],[1,3],[0,2]];self.assertEqual(a.area(p),5);self.assertAlmostEqual(a.unoccluded(p,[[.5,0,1.5,3]]),2.25)
 def test_negative_coordinates(self):
  p=[[-3,-2],[-1,-2],[-1,-1],[-3,-1]];self.assertEqual(a.unoccluded(p,[[-3,-2,-2,-1]]),1)
 def test_source_measurements_exact_arithmetic(self):
  rows=json.load(gzip.open(Path(a.HERE)/'window_measurements.json.gz','rt'))['windows'];r=next(x for x in rows if x['asset_key']=='registered_castle_stable');self.assertEqual(r['frame_inner_width_height_m'],[.76,.56]);self.assertAlmostEqual(r['after_frame_projected_area_m2'],.76*.56);r=next(x for x in rows if x['asset_key']=='working_r01_bank_joinery');self.assertAlmostEqual(r['after_frame_and_bars_area_m2'],(2.06-.24)*1.21)
 def test_source_totals(self):
  q=json.load(open(Path(a.HERE)/'audit.json'));self.assertEqual(q['asset_count'],72);self.assertEqual(sum(q['profile_window_counts'].values()),1694);self.assertEqual(sum(r['source_window_count'] for r in q['assets']),1694)
 def test_source_shutter_semantics(self):
  rows=json.load(gzip.open(Path(a.HERE)/'window_measurements.json.gz','rt'))['windows'];sh=[x for x in rows if x['shutter_state_geometry']!='absent'];self.assertEqual(len(sh),138);self.assertTrue(all(x['source_glass_exists'] and not x['open_unfilled_window_claimed'] and x['shutter_projected_overlap_m2']==0 for x in sh))
if __name__=='__main__':unittest.main()
