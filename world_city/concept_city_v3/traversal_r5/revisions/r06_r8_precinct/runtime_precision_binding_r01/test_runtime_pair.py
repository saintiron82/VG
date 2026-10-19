import copy,unittest
import numpy as np
from runtime_pair import canonical,source_proof,verify_runtime

def fixture():
 tri=[[0.,0.,0.],[1.,0.,0.],[0.,0.,1.]];dead=[[100.,0.,0.],[100.+1e-8,0.,0.],[101.,0.,1.]];source=dict(surfaces={'road':tri+dead},counts={'terrain_triangles':2,'native':1},common_instances=[{'id':'native'}],collision_contracts=[{'id':'unchanged'}]);q=np.asarray(dead,dtype=np.float32);runtime=copy.deepcopy(source);runtime['surfaces']['road']=tri;runtime['counts'].update(terrain_triangles=1,authored_terrain_triangles=2)
 ledger=dict(schema='riverstone.runtime_precision.exact_float32_zero_area.v1',retained_double_vertices_and_order_unchanged=True,non_surface_fields_unchanged_except_terrain_count_metadata=True,collision_contracts_unchanged=True,source_preserved=True,removed_triangle_count=1,removals=[dict(material='road',source_triangle_index=1,source_triangle_xyz_m=dead,source_triangle_sha256=canonical(dead),runtime_float32_vertices_xyz_m=q.tolist(),runtime_float32_cross_xyz=np.cross(q[1]-q[0],q[2]-q[0]).tolist())],material_summary={'road':dict(source_triangles=2,removed_zero_area=1,retained_triangles=1,source_array_sha256=canonical(tri+dead),runtime_array_sha256=canonical(tri))})
 return source,runtime,ledger,{'road':[0]}

class RuntimePairTests(unittest.TestCase):
 def test_exact_candidate(self):
  s,r,l,m=fixture();self.assertTrue(verify_runtime(r,source_proof(s,l,m)))
 def test_retained_nonzero_cannot_be_removed(self):
  s,r,l,m=fixture();m['road']=[]
  with self.assertRaisesRegex(ValueError,'every nonzero'):source_proof(s,l,m)
 def test_collapsed_face_cannot_be_retained(self):
  s,r,l,m=fixture();m['road']=[0,1]
  with self.assertRaisesRegex(ValueError,'every nonzero'):source_proof(s,l,m)
 def test_retained_vertices_are_exact(self):
  s,r,l,m=fixture();p=source_proof(s,l,m);r['surfaces']['road'][0][1]=1e-12
  with self.assertRaisesRegex(ValueError,'retained triangles'):verify_runtime(r,p)
 def test_native_fields_are_exact(self):
  s,r,l,m=fixture();p=source_proof(s,l,m);r['common_instances'][0]['id']='changed'
  with self.assertRaisesRegex(ValueError,'native geometry'):verify_runtime(r,p)
 def test_only_declared_count_metadata_changes(self):
  s,r,l,m=fixture();p=source_proof(s,l,m);r['counts']['native']=2
  with self.assertRaisesRegex(ValueError,'metadata'):verify_runtime(r,p)
 def test_removal_hash_is_exact(self):
  s,r,l,m=fixture();l['removals'][0]['source_triangle_sha256']='invalid'
  with self.assertRaisesRegex(ValueError,'retired source'):source_proof(s,l,m)
 def test_duplicate_removal_rejected(self):
  s,r,l,m=fixture();l['removals']*=2
  with self.assertRaisesRegex(ValueError,'Duplicate removal'):source_proof(s,l,m)
 def test_source_nonfinite_rejected(self):
  s,r,l,m=fixture();s['surfaces']['road'][0][0]=float('inf')
  with self.assertRaisesRegex(ValueError,'Nonfinite'):source_proof(s,l,m)
 def test_other_material_rejected(self):
  s,r,l,m=fixture();p=source_proof(s,l,m);r['surfaces']['water']=[]
  with self.assertRaisesRegex(ValueError,'inventory'):verify_runtime(r,p)

if __name__=='__main__':unittest.main()
