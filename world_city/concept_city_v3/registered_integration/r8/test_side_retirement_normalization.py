import copy,unittest
from unittest.mock import patch
from . import normalize_side_retirements as n
from ..r6 import merge_patches as m
SOURCE=[[0.,0.,0.],[0.,2.,0.],[0.,0.,2.]]
SCENE={'surfaces':{'road':SOURCE}}
def row(tris):return dict(material='road',triangle_index=0,source_triangle_sha256=m.canonical_sha(SOURCE),replacement_triangles_xyz_m=tris)
def joint(tris):return dict(id='R8_JOINT_TEST_PUBLIC_BOUNDARY_CLOSURE',surface_edits=[row(tris)],source_references=[dict(path='physical',sha256='exact')],appended_surfaces={})
class Test(unittest.TestCase):
 def test_side_orientation_restored_without_movement(self):
  p=joint([[SOURCE[0],SOURCE[2],SOURCE[1]]]);before=copy.deepcopy(p);out,report=n.normalize(SCENE,[p]);self.assertEqual(p,before);self.assertEqual(out[0]['surface_edits'][0]['replacement_triangles_xyz_m'],[SOURCE]);self.assertEqual(len(report['side_orientation_flips']),1)
 def test_walking_top_cannot_be_delegated_as_side(self):
  scene={'surfaces':{'road':[[0.,0.,0.],[2.,0.,0.],[0.,0.,2.]]}}
  with self.assertRaisesRegex(ValueError,'walking top'):n.normalize(scene,[joint([])])
 def test_top_delegation_preserves_emission_and_binds_owner(self):
  p=dict(id='top',surface_edits=[row([SOURCE])],appended_surfaces={'road':[[0.,1.,0.],[0.,1.,1.],[1.,1.,0.]]});before=copy.deepcopy(p)
  with patch.dict(n.TOP_PHYSICAL_SOURCES,{'top':'dummy'}),patch.object(n,'ref',return_value=dict(path='physical',sha256='exact')):out,r=n.normalize(SCENE,[p,joint([])])
  self.assertEqual(out[0]['surface_edits'],[]);self.assertEqual(out[0]['appended_surfaces'],before['appended_surfaces']);self.assertEqual(out[0]['requires_patch_canonical_sha256'][out[1]['id']],m.canonical_sha(out[1]));self.assertEqual(p,before)
 def test_missing_exact_domain_rejected(self):
  p=dict(id='top',surface_edits=[row([SOURCE])],appended_surfaces={})
  with patch.dict(n.TOP_PHYSICAL_SOURCES,{'top':'dummy'}),patch.object(n,'ref',return_value=dict(path='physical',sha256='changed')):
   with self.assertRaisesRegex(ValueError,'physical-domain'):n.normalize(SCENE,[p,joint([])])
 def test_missing_joint_rejected(self):
  with self.assertRaisesRegex(ValueError,'Exactly one'):n.normalize(SCENE,[])
if __name__=='__main__':unittest.main()
