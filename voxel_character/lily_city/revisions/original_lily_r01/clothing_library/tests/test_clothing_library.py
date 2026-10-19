from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('validate_clothing',ROOT/'validate_clothing.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

class ClothingLibraryTests(unittest.TestCase):
    def test_all_sources_and_outfits_are_valid(self):
        self.assertEqual(v.validate_library(),[])
    def test_requested_silhouette_families_exist(self):
        ids={m['id'] for m in v.read_json('catalog.json')['modules']}
        self.assertTrue({'female_dress','female_blouse','female_skirt','female_workwear','male_tunic','male_vest','male_coat','male_workwear','child_tunic','child_dress','child_trousers'} <= ids)
    def test_complete_outfits_compose_without_mutating_modules(self):
        for outfit in v.read_json('outfit_examples.json')['outfits']:
            with self.subTest(outfit=outfit['id']):
                result=v.compose_outfit(outfit['modules'],outfit['age_frame'])
                self.assertTrue(result['ops'])
                self.assertEqual(len({op['id'] for op in result['ops']}),len(result['ops']))
                self.assertTrue(result['frame_transform_required'])
                before=v.load_module(outfit['modules'][0])
                result['ops'][0]['material']='mutated_for_test'
                self.assertEqual(before,v.load_module(outfit['modules'][0]))
    def test_slots_can_be_changed_without_palette_change(self):
        outfit=deepcopy(v.read_json('outfit_examples.json')['outfits'][0])
        a=v.compose_outfit(outfit['modules'],outfit['age_frame'])
        outfit['modules'][outfit['modules'].index('sleeves_long')]='sleeves_puffed'
        b=v.compose_outfit(outfit['modules'],outfit['age_frame'])
        arm=lambda c: [op['shape'] for op in c['ops'] if 'arm_' in op['part']]
        self.assertNotEqual(arm(a),arm(b))
    def test_frame_mismatch_is_rejected(self):
        outfit=v.read_json('outfit_examples.json')['outfits'][0]
        self.assertTrue(any('does not allow' in e for e in v.validate_outfit(outfit['modules'],'child')))
    def test_slot_conflict_is_rejected(self):
        outfit=v.read_json('outfit_examples.json')['outfits'][0]
        self.assertTrue(any('occupied by both' in e for e in v.validate_outfit(outfit['modules']+['female_blouse'],outfit['age_frame'])))
    def test_missing_required_slots_are_rejected(self):
        self.assertTrue(any('Missing required slot' in e for e in v.validate_outfit(['female_dress'],'adult_female')))
    def test_wrong_coat_sleeves_are_rejected(self):
        outfit=deepcopy(next(o for o in v.read_json('outfit_examples.json')['outfits'] if o['id']=='male_coat'))
        outfit['modules'][outfit['modules'].index('sleeves_coat')]='sleeves_long'
        self.assertTrue(any('requires one of' in e for e in v.validate_outfit(outfit['modules'],outfit['age_frame'])))
    def test_solid_leg_blocking_skirt_is_rejected(self):
        m=deepcopy(v.load_module('female_dress'))
        s=next(op for op in m['ops'] if op['part']=='skirt_left')['shape']
        s['z_min']=-.2;s['z_max']=.2
        self.assertTrue(any('blocks the leg' in e for e in v.validate_module(m)))
    def test_vest_is_really_sleeveless_and_open(self):
        m=v.load_module('male_vest')
        self.assertTrue(all('arm' not in op['part'] for op in m['ops']))
        fronts=[op for op in m['ops'] if '__open_front_' in op['id']]
        self.assertEqual(len(fronts),2)
        for op in fronts:
            xs=[p[0] for p in op['shape']['polygon']]
            self.assertTrue(max(xs)<0 or min(xs)>0)
    def test_child_patterns_are_not_scaled_adult_copies(self):
        child=v.load_module('child_dress');adult=v.load_module('female_dress')
        self.assertNotEqual([op['shape'] for op in child['ops']],[op['shape'] for op in adult['ops']])
        self.assertIn('high_waist',child['presentation_tags'])
        self.assertTrue(all('lacing' not in op['id'] for op in child['ops']))
        self.assertTrue(child['frame_transform_required'])
    def test_preserves_original_bones_and_canonical_palette(self):
        rules=v.read_json('validation_rules.json')
        for m in v.read_json('catalog.json')['modules']:
            module=v.load_module(m['id'])
            for op in module['ops']:
                self.assertIn(op['part'],rules['allowed_parts'])
                self.assertNotIn(op['material'],['skin','skin_light','skin_shadow'])
                self.assertFalse(op['part'].startswith('costume_'))
    def test_pants_and_skirts_cover_the_original_skin_pelvis(self):
        required=v.read_json('validation_rules.json')['pelvis_coverage']['required_for']
        for ident in required:
            with self.subTest(module=ident):
                m=v.load_module(ident)
                front=[op for op in m['ops'] if '_pelvis_front' in op['id']]
                rear=[op for op in m['ops'] if '_pelvis_rear' in op['id']]
                self.assertTrue(front and rear)
                for op in front+rear:
                    self.assertEqual(op['part'],'pelvis')
                    s=op['shape']
                    self.assertLessEqual(s['min'][1],.825)
                    self.assertGreaterEqual(s['max'][1],1.05)
                    self.assertLessEqual(s['min'][0],-.16)
                    self.assertGreaterEqual(s['max'][0],.16)
                    self.assertLessEqual(s['max'][2]-s['min'][2],.035)
                    self.assertGreaterEqual(s['min'][1],.80)
    def test_missing_modesty_underlap_is_rejected(self):
        m=deepcopy(v.load_module('female_dress'))
        m['ops']=[op for op in m['ops'] if '_pelvis_front' not in op['id']]
        self.assertTrue(any('pelvis coverage' in error for error in v.validate_module(m)))
    def test_long_skirt_hem_flare_is_hollow_and_deeper_than_waist(self):
        for ident,hem_depth in [('female_dress',.32),('female_skirt',.32),('male_coat',.29)]:
            with self.subTest(module=ident):
                ops=[op for op in v.load_module(ident)['ops'] if '_front_left_band_' in op['id']]
                self.assertGreater(len(ops),10)
                low=min(ops,key=lambda op:min(y for x,y in op['shape']['polygon']))
                high=max(ops,key=lambda op:max(y for x,y in op['shape']['polygon']))
                self.assertAlmostEqual((low['shape']['z_min']+low['shape']['z_max'])/2,hem_depth,places=3)
                self.assertGreater(low['shape']['z_min'],high['shape']['z_min'])
                for op in ops:
                    shape=op['shape'];ys=[y for x,y in shape['polygon']]
                    self.assertLessEqual(max(ys)-min(ys),.035001)
                    self.assertLessEqual(shape['z_max']-shape['z_min'],.036001)
                    self.assertEqual(op['part'],'skirt_left')
    def test_child_dress_retains_existing_nonflared_pattern(self):
        self.assertTrue(all('_band_' not in op['id'] for op in v.load_module('child_dress')['ops']))
    def test_generation_is_byte_reproducible(self):
        files=sorted(ROOT.glob('*.json'))+sorted((ROOT/'modules').glob('*.json'))
        before={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        subprocess.run([sys.executable,str(ROOT/'generate_clothing.py')],check=True,capture_output=True)
        after={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        self.assertEqual(before,after)

if __name__=='__main__': unittest.main()
