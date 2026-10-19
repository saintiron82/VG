import copy,unittest
from certify_results import certify
class CertificationTests(unittest.TestCase):
 def fixture(self):
  old={'cases':{'A':{'sha256':'a'},'B':{'sha256':'b'},'C':{'sha256':'c'}}};new=copy.deepcopy(old);new['cases']['B']['sha256']='d';rep={'cases':{'B':{'sha256':'d'}}};a=dict(settings={'fixed':60},engine_version={'version':'same'},errors=[],routes=[dict(id=k,pass_=True,status='reached',within_route_teleports=0)for k in old['cases']]);
  for r in a['routes']:r['pass']=r.pop('pass_')
  b=dict(settings=a['settings'].copy(),engine_version=a['engine_version'].copy(),errors=[],routes=[dict(id='B',**{'pass':True},status='reached',within_route_teleports=0)]);return old,new,rep,a,b
 def test_exact_reuse_and_replay(self):self.assertEqual(certify(*self.fixture())['passed'],3)
 def test_old_failure_stays_failed(self):
  q=self.fixture();q[3]['routes'][0]['pass']=False;r=certify(*q);self.assertEqual(r['failed'],1);self.assertTrue(r['cases'][0]['prior_failure_retained'])
 def test_missing_changed_case_rejected(self):
  q=self.fixture();q[2]['cases'].clear();q[4]['routes'].clear()
  with self.assertRaises(AssertionError):certify(*q)
 def test_wrong_replayed_input_rejected(self):
  q=self.fixture();q[2]['cases']['B']['sha256']='x'
  with self.assertRaises(AssertionError):certify(*q)
 def test_changed_settings_rejected(self):
  q=self.fixture();q[4]['settings']['fixed']=30
  with self.assertRaises(AssertionError):certify(*q)
 def test_changed_engine_rejected(self):
  q=self.fixture();q[4]['engine_version']['version']='other'
  with self.assertRaises(AssertionError):certify(*q)
 def test_duplicate_result_rejected(self):
  q=self.fixture();q[4]['routes'].append(copy.deepcopy(q[4]['routes'][0]))
  with self.assertRaises(AssertionError):certify(*q)
if __name__=='__main__':unittest.main()
