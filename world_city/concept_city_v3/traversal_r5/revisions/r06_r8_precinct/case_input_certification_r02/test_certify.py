import copy,unittest
from certify import certify
class Certification(unittest.TestCase):
 def case(self,h='a'):return dict(sha256=h)
 def fixture(self,h='a',passed=True):return dict(name='old',input=dict(cases={'A':self.case(h)}),prepared_sha256='p',report=dict(prepared_sha256='p',errors=[],engine_version='4.6.3',settings={'fps':60},routes=[dict(id='A',pass_=passed,within_route_teleports=0)]))
 def fixed(self,*a,**k):
  r=self.fixture(*a,**k);r['report']['routes'][0]['pass']=r['report']['routes'][0].pop('pass_');return r
 def test_identical(self):self.assertEqual(certify(dict(cases={'A':self.case()}),[self.fixed()])['passed'],1)
 def test_unknown_input(self):
  with self.assertRaises(AssertionError):certify(dict(cases={'A':self.case('b')}),[self.fixed()])
 def test_old_failure(self):self.assertEqual(certify(dict(cases={'A':self.case()}),[self.fixed(passed=False)])['failed'],1)
 def test_changed_input_replay(self):self.assertEqual(certify(dict(cases={'A':self.case('b')}),[self.fixed(passed=False),self.fixed('b')])['passed'],1)
 def test_conflicting_outcome(self):
  with self.assertRaises(AssertionError):certify(dict(cases={'A':self.case()}),[self.fixed(),self.fixed(passed=False)])
 def test_settings_reject(self):
  r=self.fixed();r['report']['settings']['fps']=30
  with self.assertRaises(AssertionError):certify(dict(cases={'A':self.case()}),[self.fixed(),r])
 def test_duplicate_case_reject(self):
  r=self.fixed();r['report']['routes']*=2
  with self.assertRaises(AssertionError):certify(dict(cases={'A':self.case()}),[r])
if __name__=='__main__':unittest.main()
