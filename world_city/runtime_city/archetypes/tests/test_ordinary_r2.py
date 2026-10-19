"""Bounded R2 authoring, metric roof-pitch and common-compiler checks."""
import itertools
import json
import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'voxel_character/common'))
from core import compile_master,validate_master,prepare_shape,shape_bounds,transform,compose,apply
from render_data import make_render_data
from world_city.runtime_city.archetypes.ordinary_r2 import make_master,describe_spec,ASSEMBLY_CLASSES,ROOF_FORMS


def spec(**changes):
    result={'asset_id':'r2_specimen','width_m':8,'depth_m':10,'floors':2,
            'style':'old_timber','assembly_class':'regular_house','roof_form':'gable',
            'roof_pitch_degrees':42,'floor_height_m':3,'construction_era':'rebuilt'}
    result.update(changes)
    return result


class OrdinaryR2Tests(unittest.TestCase):
    def test_exact_pitch_and_reject_height_cap(self):
        d=describe_spec(spec(width_m=16,roof_pitch_degrees=52))
        self.assertAlmostEqual(d['roof_rise_m'],8*math.tan(math.radians(52)))
        self.assertAlmostEqual(d['height_m'],7+8*math.tan(math.radians(52)))
        with self.assertRaises(ValueError):make_master(spec(width_m=16,roof_pitch_degrees=52,height_m=9))
        self.assertEqual(make_master(spec(width_m=16,roof_pitch_degrees=52,height_m=d['height_m']))['metadata']['height_m'],d['height_m'])

    def test_run_for_each_roof(self):
        runs={'gable':4,'steep_gable':4,'hip':4,'shed':8,'twin_gable_z':2,'twin_gable_x':9.7/4}
        for roof,run in runs.items():
            m=make_master(spec(roof_form=roof))
            self.assertAlmostEqual(m['metadata']['roof_run_m'],run)
            self.assertAlmostEqual(m['metadata']['roof_rise_m'],run*math.tan(math.radians(42)))
        self.assertEqual(describe_spec(spec(roof_form='flat',roof_pitch_degrees=0))['roof_rise_m'],.5)

    def test_all_classes_have_distinct_source(self):
        sources=[]
        for kind in ASSEMBLY_CLASSES:
            m=make_master(spec(assembly_class=kind,floors=1 if kind=='stable' else 2))
            validate_master(m,.5)
            sources.append(json.dumps(m['components'],sort_keys=True))
        self.assertEqual(len(set(sources)),len(ASSEMBLY_CLASSES))

    def test_true_hip_planes_no_bright_bands(self):
        m=make_master(spec(roof_form='hip'))
        roof=[c for c in m['components'] if c['id'].startswith('roof')]
        self.assertEqual(len(roof),2)
        self.assertEqual(sum(op['action']=='paint' for c in roof for op in c['operations']),4)
        self.assertEqual(sum(op['action']=='cut' for c in roof for op in c['operations']),4)
        self.assertEqual({op['material'] for c in roof for op in c['operations'] if op['action']=='paint'},{'slate'})

    def test_low_detail_hints_and_material_family_do_not_change_source(self):
        base=make_master(spec())
        self.assertEqual(base,make_master(spec(lod='coarse',roof_material_family='clay_red')))
        self.assertEqual(base,make_master(spec(lod='detailed',roof_material_family='wood_brown')))

    def test_source_module_and_palette_unchanged(self):
        source=json.loads((ROOT/'voxel_character/common/assets/house/master.json').read_text())
        m=make_master(spec())
        self.assertEqual(m['materials'],source['materials'])
        rail=lambda x:next(c for c in x['components'] if c['id']=='eave_rail')
        self.assertEqual(rail(m),rail(source))

    def test_poor_row_multiple_real_closed_doors(self):
        m=make_master(spec(assembly_class='poor_row',width_m=12,attached_units=4))
        self.assertEqual(m['metadata']['row_units'],4)
        self.assertEqual(len(m['metadata']['entrance']['all_positions']),4)
        self.assertEqual(len([c for c in m['components'] if c['id'].startswith('wall_0_front_door_')]),4)
        self.assertAlmostEqual(m['metadata']['roof_run_m'],1.5)
        compiled=compile_master(m,{'pitch':.5})
        self.assertTrue(compiled['valid'])
        for i in range(4):
            self.assertTrue(any(row[3]==f'wall_0_front_door_{i}' and row[4]=='door' for row in compiled['cells']))

    def test_two_small_samples_both_pitches(self):
        for kind,roof,floors in [('stable','gable',1),('merchant_palazzo','hip',2)]:
            m=make_master(spec(assembly_class=kind,width_m=6,depth_m=8,floors=floors,roof_form=roof))
            for pitch in (.5,.25):
                with self.subTest(kind=kind,pitch=pitch):
                    c=compile_master(m,{'pitch':pitch})
                    self.assertTrue(c['valid'],c['constraints'])
                    r=make_render_data(c)
                    self.assertLess(c['candidate_cells'],200000)
                    self.assertLess(r['quad_count'],1500)
                    self.assertTrue(any(row[4]=='door' for row in c['cells']))
                    self.assertTrue(any(row[5]=='glass' for row in c['cells']))
                    env=m['metadata']['envelope']
                    for axis in range(3):
                        self.assertGreaterEqual(r['bounds']['min'][axis],env['min'][axis]-pitch/2-1e-7)
                        self.assertLessEqual(r['bounds']['max'][axis],env['max'][axis]+pitch/2+1e-7)

    def test_paint_envelopes_and_entrances(self):
        specs=[spec(assembly_class=kind,width_m=18 if kind=='older_stone_manor' else 16,
                    depth_m=18 if kind in ('older_stone_manor','merchant_palazzo') else 16,
                    floors=1 if kind=='stable' else 2,roof_form='hip' if kind in ('older_stone_manor','merchant_palazzo') else 'gable',
                    roof_pitch_degrees=50) for kind in ASSEMBLY_CLASSES]
        specs += [spec(width_m=4,depth_m=3.5,floors=1,roof_form=form,roof_pitch_degrees=0 if form=='flat' else 42) for form in ROOF_FORMS]
        for s in specs:
            m=make_master(s);cs={c['id']:c for c in m['components']};env=m['metadata']['envelope']
            for ins in m['instances']:
                for op in cs[ins['component']]['operations']:
                    if op['action']=='cut':continue
                    bounds=shape_bounds(prepare_shape(op['shape'],.5))
                    placement=compose(transform(ins.get('transform')),transform(op.get('transform')))
                    corners=[apply(placement,p) for p in itertools.product(*zip(*bounds))]
                    for axis in range(3):
                        context=(s['assembly_class'],s['roof_form'],ins['id'],op['id'],axis)
                        self.assertGreaterEqual(min(p[axis] for p in corners)+1e-7,env['min'][axis],context)
                        self.assertLessEqual(max(p[axis] for p in corners)-1e-7,env['max'][axis],context)
            for entry in m['metadata']['entrance']['all_positions']:
                self.assertTrue(all(lo<=value<=hi for value,lo,hi in zip(entry,env['min'],env['max'])))
                self.assertEqual(entry[1],.5)
            self.assertTrue(m['metadata']['entrance']['closed'])

    def test_era_is_real_geometry(self):
        for kind in ('regular_house','merchant_palazzo','timber_courtyard_house'):
            a=make_master(spec(assembly_class=kind,construction_era='crossing_fort'))
            b=make_master(spec(assembly_class=kind,construction_era='outer_infill'))
            self.assertNotEqual(a['components'],b['components'])

if __name__=='__main__':unittest.main()
