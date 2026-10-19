"""Schema guards, independent of pending R18 geometry or scene availability."""
import pathlib,sys,unittest,copy
H=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(H));import catalog

def fixture():
 r=dict(id='PUBLIC_TEST',case_class='public_corridor',points_xyz_m=[[0,0,0],[1,0,0]],source_road_ids=['TEST_ROAD'],test_scope='Synthetic catalog schema fixture only',provenance=[dict(path='unresolved_fixture',sha256='0'*64)],resolved_geometry_proof=dict(path='unresolved_fixture',sha256='0'*64),bidirectional=True)
 coverage={}
 for key,ids in[('public_roads',['TEST_ROAD']),('primary_network_goals',['GOAL']),('ordinary_entries',['ENTRY'])]:coverage['required_'+key+'_ids']=ids;coverage[key]=[dict(id=i,status='accepted',route_ids=['PUBLIC_TEST'])for i in ids]
 return dict(schema='riverstone.resolved_public_replay_catalog.r18.v1',status='READY_FOR_ACTUAL_SCENE_REPLAY',sources={},routes=[r],coverage=coverage)
class CatalogTests(unittest.TestCase):
 def test_bidirectional_expansion_preserves_geometry(self):
  d=fixture();r=catalog.validate(d,False);self.assertEqual(len(r),2);self.assertEqual(r[1]['points'],list(reversed(r[0]['points'])));self.assertEqual(d['routes'][0]['points_xyz_m'],[[0,0,0],[1,0,0]])
 def test_reject_unreleased_catalog(self):
  d=fixture();d['status']='CANDIDATE'
  with self.assertRaises(ValueError):catalog.validate(d,False)
 def test_reject_obsolete_unproved_axis(self):
  d=fixture();d['routes'][0].pop('resolved_geometry_proof')
  with self.assertRaises(ValueError):catalog.validate(d,False)
 def test_reject_path_escape_id(self):
  d=fixture();d['routes'][0]['id']='../outside'
  with self.assertRaises(ValueError):catalog.validate(d,False)
 def test_reject_missing_coverage(self):
  d=fixture();d['coverage']['ordinary_entries']=[]
  with self.assertRaises(ValueError):catalog.validate(d,False)
 def test_reject_unexplained_retired_owner(self):
  d=fixture();d['coverage']['ordinary_entries'][0]={'id':'ENTRY','status':'retired'}
  with self.assertRaises(ValueError):catalog.validate(d,False)
 def test_accept_explicit_held_owner(self):
  d=fixture();d['coverage']['ordinary_entries'][0]={'id':'ENTRY','status':'held','reason':'Not activated','source':{'path':'fixture','sha256':'0'*64}};self.assertEqual(len(catalog.validate(d,False)),2)
 def test_reject_positive_one_way_only(self):
  d=fixture();d['routes'][0]['bidirectional']=False
  with self.assertRaises(ValueError):catalog.validate(d,False)
 def test_reject_block_without_owner(self):
  d=fixture();d['routes'][0].update(case_class='blocked_native_negative',expected_failure='blocked')
  with self.assertRaises(ValueError):catalog.validate(d,False)
 def test_reject_ground_loss_without_datum(self):
  d=fixture();d['routes'][0].update(case_class='water_edge_negative',expected_failure='ground_lost')
  with self.assertRaises(ValueError):catalog.validate(d,False)
 def test_reject_duplicate_points(self):
  d=fixture();d['routes'][0]['points_xyz_m']=[[0,0,0],[0,0,0]]
  with self.assertRaises(ValueError):catalog.validate(d,False)
 def test_reject_invalid_actual_bridge_state(self):
  d=fixture();d['routes'][0]['bridge_state']='MADE_UP'
  with self.assertRaises(ValueError):catalog.validate(d,False)
 def test_grade_probe_requires_finite_owner(self):
  d=fixture();d['routes'][0].update(case_class='design_grade_probe',source_road_ids=[])
  with self.assertRaises(ValueError):catalog.validate(d,False)
 def test_grade_probe_accepts_explicit_finite_owner(self):
  d=fixture();d['routes'][0].update(case_class='design_grade_probe',source_road_ids=[],source_plane_owner_ids=['R18_FINITE:1:0'])
  self.assertEqual(len(catalog.validate(d,False)),2)
if __name__=='__main__':unittest.main(verbosity=2)
