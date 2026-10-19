"""Composition safety fixtures. They do not replace actual-scene/route checks."""
import copy,sys,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[4];sys.path.insert(0,str(R))
from world_city.concept_city_v3.registered_integration.r6.merge_patches import merge,canonical_sha,validate_against_scene
SHA='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
def fixture(pid='A',i=0):
 verts=[[0,0,0],[0,0,1],[1,0,0],[1,0,0],[0,0,1],[1,0,1]];t=verts[i*3:i*3+3]
 return {'id':pid,'schema':'riverstone.frozen_scene_patch.v1','status':'source_candidate','base_scene_sha256':SHA,'source_surface_hashes':{'road':canonical_sha(verts)},'surface_edits':[{'material':'road','triangle_index':i,'source_triangle_xyz_m':t,'source_triangle_sha256':canonical_sha(t),'replacement_triangles_xyz_m':[t]}],'appended_surfaces':{},'removed_foundation_proxy_ids':[]}, {'surfaces':{'road':verts},'boxes':[]}
class Composition(unittest.TestCase):
 def test_disjoint_faces(self):
  a,s=fixture();b,_=fixture('B',1);m=merge([a,b],SHA);self.assertEqual(len(m['surface_edits']),2);self.assertTrue(validate_against_scene(s,m))
 def test_duplicate_source_rejected(self):
  a,_=fixture();b,_=fixture('B');
  with self.assertRaises(ValueError):merge([a,b],SHA)
 def test_wrong_base_rejected(self):
  a,_=fixture();a['base_scene_sha256']='bad'
  with self.assertRaises(ValueError):merge([a],SHA)
 def test_changed_source_rejected(self):
  a,s=fixture();s['surfaces']['road'][0]=[0,1,0]
  with self.assertRaises(ValueError):validate_against_scene(s,merge([a],SHA))
 def test_input_preserved(self):
  a,_=fixture();before=copy.deepcopy(a);merge([a],SHA);self.assertEqual(a,before)
 def test_failed_producer_rejected(self):
  a,_=fixture();a['status']='FAIL_runtime'
  with self.assertRaises(ValueError):merge([a],SHA)
 def test_unknown_proxy_rejected(self):
  a,s=fixture();a['removed_foundation_proxy_ids']=['missing']
  with self.assertRaises(ValueError):validate_against_scene(s,merge([a],SHA))
if __name__=='__main__':unittest.main()
