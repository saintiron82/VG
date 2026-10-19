import copy,math,tempfile,unittest
from input_contract import *
class InputContractTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=H);self.path=Path(self.temp.name)/'fixture.master.json'
  self.master={'id':'fixture','components':[{'id':'roof','parts':[{'id':'solid','pivot':[0,0,0]}],'operations':[{'id':'roof_plane','part':'solid','action':'paint','material':'slate','shape':{'kind':'extrusion','polygon':[[0,1.7],[2,2.7],[2,3],[0,2]],'z_min':0,'z_max':4}}]}],'instances':[{'id':'roof','component':'roof'}],'assembly_cuts':[]}
 def tearDown(self):self.temp.cleanup()
 def inspect(self):
  write(self.path,self.master);s={'master_path':str(self.path.relative_to(R)),'master_sha256':sha(self.path),'render_path':'fixture.render.json','render_sha256':'unused'}
  mapping={**s,'pitch_m':.5,'palette_id_counts':{},'slots':{'slate':{'operation_role_counts':{'roof_covering':1}}}}
  return inspect('fixture',mapping,s,self.master)
 def cut(self,low,high,selector=None):
  c={'id':'cut','action':'cut','shape':{'kind':'box','min':low,'max':high}}
  if selector:c['selector']=selector
  self.master['assembly_cuts'].append(c)
 def test_basic(self):self.assertEqual(self.inspect()['status'],'SUPPORTED_INPUT_UNBUILT')
 def test_disjoint_cut(self):
  self.cut([20,20,20],[21,21,21]);r=self.inspect();self.assertEqual(r['status'],'SUPPORTED_INPUT_UNBUILT');self.assertEqual(len(r['cut_exclusion_proofs']),1)
 def test_selector_excluded_cut(self):
  self.cut([0,0,0],[3,4,5],{'component':'other'});r=self.inspect();self.assertEqual(r['status'],'SUPPORTED_INPUT_UNBUILT');self.assertEqual(r['cut_exclusion_proofs'][0]['exclusion'],'selector_excludes_roof_operation')
 def test_relevant_cut(self):
  self.cut([0,0,0],[3,4,5]);r=self.inspect();self.assertEqual(r['status'],'UNSUPPORTED');self.assertIn('ROOF_INTERSECTING_OR_SELECTOR_RELEVANT_CUT',r['reason_codes'])
 def test_nonroof_shared_material(self):
  self.master['components'][0]['operations'].append({'id':'nonroof_cap','part':'solid','action':'paint','material':'slate','shape':{'kind':'box','min':[5,0,0],'max':[6,1,1]}})
  r=self.inspect();self.assertEqual(r['status'],'UNSUPPORTED');self.assertIn('WHOLE_MATERIAL_GROUP_OWNERSHIP_UNPROVEN',r['reason_codes'])
 def test_curved_shape(self):
  self.master['components'][0]['operations'][0]['shape']={'kind':'lathe','profile':[[1,0],[1,1],[0,2]]}
  r=self.inspect();self.assertEqual(r['status'],'UNSUPPORTED');self.assertIn('UNSUPPORTED_ROOF_SHAPE_OR_THICKNESS',r['reason_codes'])
 def test_nonorthonormal_basis(self):
  self.master['instances'][0]['transform']={'basis':[[2,0,0],[0,1,0],[0,0,1]]}
  r=self.inspect();self.assertEqual(r['status'],'UNSUPPORTED');self.assertIn('UNSUPPORTED_TRANSFORM_OR_INVALID_SOURCE',r['reason_codes'])
 def test_arbitrary_rigid_rotation(self):
  t=math.radians(37);self.master['instances'][0]['transform']={'basis':[[math.cos(t),0,math.sin(t)],[0,1,0],[-math.sin(t),0,math.cos(t)]],'translation':[2,5,9]}
  r=self.inspect();self.assertEqual(r['status'],'SUPPORTED_INPUT_UNBUILT');self.assertEqual(r['non_axis_aligned_rigid_roof_operations'],1)
  solids=[surface.solid(x)for x in r['canonical_solids']];regions,_=surface.regions(solids);_,q=surface.quads(regions);a=surface.audit_boundary(q,solids)
  self.assertEqual(a['open_or_nonmanifold_edge_segments'],0);self.assertEqual(a['normal_probe_errors'],0)
 def test_pitch_dependent_minimum(self):
  self.master['components'][0]['operations'][0]['shape']['minimum_cells']=20
  r=self.inspect();self.assertEqual(r['status'],'UNSUPPORTED');self.assertIn('PITCH_DEPENDENT_MINIMUM_SHAPE_UNSUPPORTED',r['reason_codes'])
 def test_edge_only_contact_rejected_by_geometry(self):
  records=[{'id':str(i),'shape':{'kind':'box','min':low,'max':high},'material':'a','priority':i}for i,(low,high)in enumerate([([0,0,0],[1,1,1]),([1,1,0],[2,2,1])])]
  solids=[surface.solid(x)for x in records];regions,_=surface.regions(solids);_,q=surface.quads(regions);a=surface.audit_boundary(q,solids)
  self.assertGreater(a['open_or_nonmanifold_edge_segments'],0)
if __name__=='__main__':unittest.main()
