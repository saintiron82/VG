"""Small schema fixtures for preservation of unaffected public owners."""
import copy,pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent));import emission_revision as e
def fixture():
 def row(i,x):return dict(id=i,source_triangle_index=x,polygon_xz_m=[[x,0],[x+1,0],[x,1]],plane_y_xz_m=[0,0,0],triangles_xyz_m=[[[x,0,0],[x+1,0,0],[x,0,1]]],source_gradient=0)
 a=row('A',0);b=row('B',2);c=row('B:REMAINDER',2);c['previous_owner_id']='B';c['polygon_xz_m'][1][0]=2.5;c['triangles_xyz_m'][0][1][0]=2.5
 old=dict(records=[a,b],report=dict(exceptions=[]));new=dict(records=[copy.deepcopy(a),c],report=dict(exceptions=[]));review=dict(changed=[dict(previous_owner_id='B',previous_owner_sha256=e.canonical_sha(b),previous_polygon_xz_m=b['polygon_xz_m'],plane_y_xz_m=b['plane_y_xz_m'],retained_record_ids=[c['id']])],unchanged_records=1,changed_previous_records=1,previous_grade_exception_records_unchanged=True,all_removals_inside_original_source_holes=True,nonhole_removals=[])
 return old,new,review
class EmissionRevisionTests(unittest.TestCase):
 def test_exact_bounded_revision(self):
  d=e.validate(*fixture());self.assertEqual(d['summary']['unchanged_owner_records'],1);self.assertEqual(d['summary']['retired_triangle_instances'],1)
 def test_reject_changed_unaffected_owner(self):
  a,b,c=fixture();b['records'][0]['source_gradient']=.1
  with self.assertRaises(AssertionError):e.validate(a,b,c)
 def test_reject_changed_retained_plane(self):
  a,b,c=fixture();b['records'][1]['plane_y_xz_m']=[0,0,1]
  with self.assertRaises(AssertionError):e.validate(a,b,c)
 def test_reject_unaccounted_owner(self):
  a,b,c=fixture();r=copy.deepcopy(b['records'][0]);r['id']='EXTRA';b['records'].append(r)
  with self.assertRaises(AssertionError):e.validate(a,b,c)
 def test_reject_wrong_previous_owner_hash(self):
  a,b,c=fixture();c['changed'][0]['previous_owner_sha256']='0'*64
  with self.assertRaises(AssertionError):e.validate(a,b,c)
 def test_reject_changed_grade_exceptions(self):
  a,b,c=fixture();b['report']['exceptions']=[dict(unreviewed=True)]
  with self.assertRaises(AssertionError):e.validate(a,b,c)
if __name__=='__main__':unittest.main(verbosity=2)
