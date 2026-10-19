import copy,unittest
from bind_winding import *
class WindingTests(unittest.TestCase):
 def fixture(self):
  d={'surfaces':{},'unchanged':'source'}
  for r in winding.contract()['cases']:d['surfaces'].setdefault(r['material'],[]).extend(copy.deepcopy(r['precise_source_vertices_xyz_m']))
  return d,winding.bind_scene(d,{'path':'fixture','sha256':'fixture'})
 def test_exact_ten(self):
  d,b=self.fixture();rows=validate_rows(d,b);self.assertEqual(len(rows),10);proof=surface_proof(d,rows);verify_output(d,proof)
 def test_reject_unknown_case(self):
  d,b=self.fixture();b['rows'][0]['case_id']='UNKNOWN'
  with self.assertRaises(AssertionError):validate_rows(d,b)
 def test_reject_moved_row(self):
  d,b=self.fixture();b['rows'][0]['runtime_after_vertices_xyz_m'][0][0]+=.001
  with self.assertRaises(AssertionError):validate_rows(d,b)
 def test_reject_extra_row(self):
  d,b=self.fixture();b['rows'].append(copy.deepcopy(b['rows'][0]))
  with self.assertRaises(AssertionError):validate_rows(d,b)
 def test_reject_ambiguous_source(self):
  d,b=self.fixture();r=winding.contract()['cases'][0];d['surfaces'][r['material']].extend(copy.deepcopy(r['precise_source_vertices_xyz_m']))
  with self.assertRaises(ValueError):validate_rows(d,b)
 def test_reject_unknown_output_edit(self):
  d,b=self.fixture();p=surface_proof(d,validate_rows(d,b));m=next(iter(d['surfaces']));d['surfaces'][m][0][0]+=.001
  with self.assertRaises(AssertionError):verify_output(d,p)
 def test_reject_non_surface_edit(self):
  d,b=self.fixture();p=surface_proof(d,validate_rows(d,b));d['unchanged']='wrong'
  with self.assertRaises(AssertionError):verify_output(d,p)
if __name__=='__main__':unittest.main()
