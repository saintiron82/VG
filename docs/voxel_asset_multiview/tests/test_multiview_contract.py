from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
from fixture_factory import build, sha, write_json
from render_data import make_render_data
spec = importlib.util.spec_from_file_location('multiview_contract', REPO/'voxel_character/common/validation/multiview_contract.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='multiview-contract-')
        self.root = Path(self.tmp.name)
        self.c = build(self.root)
    def tearDown(self):
        self.tmp.cleanup()
    def result(self):
        return v.validate_contract(self.c, self.root)
    def fails(self, code):
        result = self.result()
        self.assertFalse(result['technical_contract_pass'])
        self.assertIn(code,[x['code'] for x in result['errors']],result)
        self.assertFalse(result['automatic_art_acceptance'])
        self.assertFalse(result['asset_complete'])
    def change(self, key, fn):
        path = self.root/self.c['artifacts'][key]['path']
        data = json.loads(path.read_text())
        fn(data)
        write_json(path,data)
        self.c['artifacts'][key]['sha256'] = sha(path)
        return data
    def changed_cells(self, fn):
        compiled=self.change('compiled',fn)
        compiled=self.change('compiled',lambda d:d.update(payload_hash=v.digest(d['cells'])))
        mesh=make_render_data(compiled)
        path=self.root/self.c['artifacts']['render_mesh']['path']
        write_json(path,mesh)
        self.c['artifacts']['render_mesh']['sha256']=sha(path)
    def test_valid_tiny_fixture_never_art_acceptance(self):
        result = self.result()
        self.assertTrue(result['technical_contract_pass'],result)
        self.assertEqual(result['visual_review_status'],'pending')
        self.assertFalse(result['automatic_art_acceptance'])
        self.assertFalse(result['asset_complete'])
        self.assertFalse(result['coverage_claim_allowed'])
        self.assertEqual(result['diagnostics']['reference_alignment']['observed_views'],[])
        self.assertEqual(result['diagnostics']['common_geometry']['cell_count'],64)
    def test_missing_back_reference(self):
        self.c['references'].pop()
        self.fails('reference_views')
    def test_inferred_is_not_observed(self):
        self.c['references'][0]['origin'] = 'observed'
        self.fails('artifact_kind')
    def test_inference_missing_original(self):
        self.c['references'][0]['source_refs'] = []
        self.fails('inference_sources')
    def test_bad_hash(self):
        self.c['artifacts']['master']['sha256'] = '0'*64
        self.fails('artifact_hash_mismatch')
    def test_missing_file(self):
        self.c['artifacts']['master']['path'] = 'absent.json'
        self.fails('artifact_missing')
    def test_path_escape(self):
        self.c['artifacts']['master']['path'] = '../escape.json'
        self.fails('artifact_path')
    def test_calibration_conflict(self):
        self.change('alignment_side',lambda d:d.update(unresolved_conflicts=['face turned toward camera']))
        self.fails('alignment_unresolved')
    def test_reference_yaw_not_profile(self):
        self.change('alignment_side',lambda d:d.update(yaw_deg=70))
        self.fails('reference_orientation')
    def test_reference_scale_disagreement(self):
        self.change('alignment_side',lambda d:d.update(pixels_per_m=60,footline_px=76))
        self.fails('reference_alignment')
    def test_wrong_camera_scale(self):
        self.change('record_compiled_mesh_side',lambda d:d['camera'].update(vertical_span_m=1.6))
        self.fails('render_alignment')
    def test_autofit_forbidden(self):
        self.change('record_compiled_mesh_side',lambda d:d['camera'].update(scale_source='fit_model_bounds'))
        self.fails('render_auto_fit')
    def test_missing_compiled_back(self):
        self.c['model_renders'] = [r for r in self.c['model_renders'] if not(r['stage']=='compiled_mesh' and r['view']=='back')]
        self.fails('render_views')
    def test_missing_authored_volume_views(self):
        self.c['model_renders'] = [r for r in self.c['model_renders'] if r['stage']=='compiled_mesh']
        self.fails('render_views')
    def test_reference_image_as_model_render(self):
        row = self.c['model_renders'][0]
        old = self.c['artifacts'][row['image']]
        ref = self.c['artifacts']['ref_front']
        old.update(path=ref['path'],sha256=ref['sha256'])
        self.fails('reference_as_render')
    def test_zero_section_depth(self):
        self.change('profile',lambda d:d['parts'][0]['sections'][1].update(depth_m=0))
        self.fails('section_volume')
    def test_section_gap(self):
        self.change('profile',lambda d:d['parts'][0].update(max_station_step_m=.2))
        self.fails('section_continuity')
    def test_curve_gap(self):
        def mutate(d):
            d['parts']=[{'id':'hair','source_pointer':'/parts/0','representation':'curve_sweep',
                        'points_m':[[0,0,0],[0,.1,.1],[0,2,.2]],'radii_m':[.05]*3,'max_sample_step_m':.3}]
        self.change('profile',mutate)
        self.fails('curve_continuity')
    def test_missing_source_geometry_pointer(self):
        self.change('profile',lambda d:d['parts'][0].update(source_pointer='/does_not_exist'))
        self.fails('volume_source_pointer')
    def test_payload_hash(self):
        self.change('compiled',lambda d:d.update(payload_hash='0'*64))
        self.fails('payload_binding')
    def test_single_depth_layer_is_not_complex_volume(self):
        self.changed_cells(lambda d:d.update(cells=[r for r in d['cells'] if r[2]==0]))
        self.fails('single_depth_layer')
    def test_disconnected_part_needs_disposition(self):
        self.changed_cells(lambda d:d['cells'][0].__setitem__(0,20))
        self.fails('continuity_unreviewed')
    def test_duplicate_cell_rejected(self):
        self.change('compiled',lambda d:d['cells'].append(d['cells'][0]))
        self.change('compiled',lambda d:d.update(payload_hash=v.digest(d['cells'])))
        self.fails('duplicate_cell')
    def test_bad_mesh_count(self):
        self.change('render_mesh',lambda d:d.update(quad_count=99))
        self.fails('mesh_quad_count')
    def test_inward_mesh_normal(self):
        self.change('render_mesh',lambda d:d['groups'][0]['quads'][0].reverse())
        self.fails('mesh_boundary')
    def test_mesh_missing_occupied_surface(self):
        self.change('render_mesh',lambda d:d['groups'][0]['quads'].pop())
        self.change('render_mesh',lambda d:d.update(quad_count=d['quad_count']-1))
        self.fails('mesh_missing_faces')
    def test_duplicate_mesh_face(self):
        self.change('render_mesh',lambda d:d['groups'][0]['quads'].append(d['groups'][0]['quads'][0]))
        self.change('render_mesh',lambda d:d.update(quad_count=d['quad_count']+1))
        self.fails('mesh_boundary')
    def test_wrong_master(self):
        self.change('master',lambda d:d.update(revision=2))
        self.fails('master_binding')
    def test_bounded_compile_no_global_pass(self):
        self.change('compiled',lambda d:d.update(valid_scope='cell_bounds_only',global_constraints_evaluated=False))
        self.fails('scoped_compile')
    def test_fake_coverage_claim(self):
        self.c['claims']['coverage_pass'] = True
        self.fails('automatic_quality_claim')
    def test_numeric_completion_claim(self):
        self.c['claims']['numeric_quality_pass'] = True
        self.fails('automatic_quality_claim')
    def test_unbacked_visual_acceptance(self):
        self.c['visual_review']={'status':'recorded_accepted','record':'does_not_exist'}
        self.fails('artifact_reference')
    def test_unreviewed_source_volume_cannot_satisfy_pipeline(self):
        self.change('source_review',lambda d:d.update(decision='pending'))
        self.fails('precompile_review_pending')
    def test_wrong_source_to_master_binding(self):
        self.change('lowering',lambda d:d.update(master_sha256='0'*64))
        self.fails('lowering_binding')
    def test_png_header_without_pixels_is_not_render_evidence(self):
        key=self.c['model_renders'][0]['image']
        path=self.root/self.c['artifacts'][key]['path']
        path.write_bytes(path.read_bytes()[:24])
        self.c['artifacts'][key]['sha256']=sha(path)
        self.change(self.c['model_renders'][0]['record'],lambda d:d.update(image_sha256=sha(path)))
        self.fails('render_image_format')
    def test_recorded_human_review_still_not_automatic_art_pass(self):
        data={'status':'recorded_accepted','reviewer':'SYNTHETIC_TEST_RECORD',
              'findings':['Fixture-only reviewer record, not actual asset approval.'],
              'basis':'direct_multiview_image_review',
              'reviewed_image_sha256':[self.c['artifacts'][r['image']]['sha256'] for r in self.c['model_renders']]}
        path=self.root/'visual_review.json';write_json(path,data)
        self.c['artifacts']['review']={'path':'visual_review.json','sha256':sha(path),'kind':'visual_review'}
        self.c['visual_review']={'status':'recorded_accepted','record':'review'}
        result=self.result()
        self.assertTrue(result['technical_contract_pass'],result)
        self.assertFalse(result['automatic_art_acceptance'])
        self.assertFalse(result['asset_complete'])
    def test_dimensional_exception_preserves_simple_parts(self):
        self.c['asset_class']='standard_component'
        self.c['references']=[]
        self.c.pop('volume')
        self.c['model_renders']=[r for r in self.c['model_renders'] if r['stage']=='compiled_mesh']
        result=self.result()
        self.assertTrue(result['technical_contract_pass'],result)
        self.assertNotIn('reference_alignment',result['gates'])
    def test_malformed_contract_fail_closed(self):
        self.assertFalse(v.validate_contract([],self.root)['technical_contract_pass'])
    def test_nonfinite_json(self):
        path=self.root/'nonfinite.json';path.write_text('{"x":NaN}')
        with self.assertRaises(v.ContractError):v.read_json(path)

if __name__=='__main__':unittest.main()
