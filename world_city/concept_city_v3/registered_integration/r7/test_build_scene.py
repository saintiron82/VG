import copy,unittest
from unittest.mock import patch
from . import build_scene as b
from ..r6.merge_patches import canonical_sha

UP=[[0.,0.,0.],[0.,0.,1.],[1.,0.,0.]]

class BuildTests(unittest.TestCase):
    def setUp(self):
        self.scene={'surfaces':{'ground':copy.deepcopy(UP),'water':[]},'boxes':[],
          'common_instances':[],'common_assets':{},'counts':{},
          'inspection_cameras':{'registered':{'position':[0,10,0]}},
          'collision_contracts':[{'id':'retained'}],
          'bridge_mechanism':{'asset_keys':[]},'materials':{'ground':'abc','water':'def'}}
        self.p={'id':'test','base_scene_sha256':b.BASE_SHA,'status':'producer_acceptance',
          'source_surface_hashes':{'ground':canonical_sha(UP)},
          'surface_edits':[{'material':'ground','triangle_index':0,'source_triangle_sha256':canonical_sha(UP),
              'replacement_triangles_xyz_m':[copy.deepcopy(UP)]}],
          'appended_surfaces':{},'removed_foundation_proxy_ids':[]}
        self.rows={'base':self.scene,'patch':self.p,'pack':{'assets':{},'placements':[]}}
        self.binding={'status':'sources_reviewed_ready_for_visual',
          'base_scene':{'path':'base','sha256':b.BASE_SHA},'producer_evidence':[],
          'patches':[{'path':'patch','sha256':'test'}],
          'packs':[{'path':'pack','sha256':'test','name':'empty_test'}],'limits':['fixture only']}
    def run_build(self):
        with patch.object(b,'verified',side_effect=lambda r:self.rows[r['path']]):
            return b.build(self.binding)
    def test_baseline_and_contracts_untouched(self):
        before=copy.deepcopy(self.scene);scene,p,g=self.run_build()
        self.assertEqual(self.scene,before)
        self.assertEqual(scene['collision_contracts'],before['collision_contracts'])
        self.assertEqual(scene['local_terrain_patch']['base_scene_sha256'],b.BASE_SHA)
        self.assertEqual(g['downward'],0)
    def test_source_reversal_rejected(self):
        self.p['surface_edits'][0]['replacement_triangles_xyz_m']=[[UP[0],UP[2],UP[1]]]
        with self.assertRaisesRegex(ValueError,'Downward'):self.run_build()
    def test_stale_source_rejected(self):
        self.p['source_surface_hashes']['ground']='bad'
        with self.assertRaisesRegex(ValueError,'Changed source'):self.run_build()
    def test_old_base_rejected(self):
        self.binding['base_scene']['sha256']='old'
        with self.assertRaisesRegex(ValueError,'R6 base'):self.run_build()
    def test_shared_index_rejected(self):
        self.binding['patches'].append({'path':'patch2','sha256':'test'})
        self.rows['patch2']=copy.deepcopy(self.p);self.rows['patch2']['id']='different_owner'
        with self.assertRaisesRegex(ValueError,'Overlapping source triangle'):self.run_build()
    def test_recolor_rejected(self):
        self.binding['new_materials']={'ground':'leaked recolor'}
        with self.assertRaisesRegex(ValueError,'recolor'):self.run_build()
    def test_registered_camera_overwrite_rejected(self):
        self.binding['review_cameras']={'registered':{'position':[0,0,0]}}
        with self.assertRaisesRegex(ValueError,'earlier camera'):self.run_build()
    def test_unreviewed_binding_rejected(self):
        self.binding['status']='working'
        with self.assertRaisesRegex(ValueError,'acceptance'):self.run_build()

if __name__=='__main__':unittest.main()
