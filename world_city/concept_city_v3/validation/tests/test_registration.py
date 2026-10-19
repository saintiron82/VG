import copy,json,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from check_registration import check,project_xyz,engine_project

class RegistrationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.data=json.loads((Path(__file__).resolve().parents[2]/'image_registration/controls.json').read_text())
 def test_declared_transform_round_trip(self):self.assertEqual(check(self.data)['status'],'pass')
 def test_engine_camera_is_independently_consistent(self):
  for p in [[0,0,0],[100,20,-40],[-23,7,421]]:self.assertLess(math.dist(project_xyz(self.data['camera_model'],p),engine_project(self.data['matched_engine_camera'],p)),.001)
 def test_height_change_without_registration_is_detected(self):
  data=copy.deepcopy(self.data);data['roads'][0]['world_xyz_m'][0][1]+=1;self.assertEqual(check(data)['status'],'fail')
 def test_wrong_engine_camera_is_detected(self):
  data=copy.deepcopy(self.data);data['matched_engine_camera']['target_m'][0]+=3;self.assertEqual(check(data)['status'],'fail')
 def test_missing_correspondence_is_detected(self):
  data=copy.deepcopy(self.data);data['estates'][0]['world_xyz_m'].pop();self.assertEqual(check(data)['status'],'fail')
 def test_wrong_uv_is_detected(self):
  data=copy.deepcopy(self.data);data['water'][0]['trace_normalized_uv'][0][0]+=.01;self.assertEqual(check(data)['status'],'fail')
 def test_stale_anchor_metric_is_detected(self):
  data=copy.deepcopy(self.data);data['anchor_rms_px']=0;self.assertEqual(check(data)['status'],'fail')

if __name__=='__main__':unittest.main()
