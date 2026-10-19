"""Bounded source/contract/common-compile tests, no GUI or full city sampling."""
from __future__ import annotations
import copy
import itertools
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from voxel_character.common import coordinate_planes, core, render_data
from world_city.runtime_city.parts.author import HERE, KINDS, approved_palette, file_ref, make_master

CANDIDATE_BUDGET = 120_000
OUTPUT_BUDGET = 40_000
MEASUREMENTS = []
REPEATS = []
COMMON_FILES = ['voxel_character/common/' + f for f in ('coordinate_planes.py','core.py','render_data.py')]


def compile_small(kind, pitch=None):
    source = make_master(kind)
    original = copy.deepcopy(source)
    pitch = pitch or source['extensions']['smoke_pitch_m']
    started = time.monotonic()
    result = coordinate_planes.compile_master(source, {'pitch':pitch},
        max_candidate_cells=CANDIDATE_BUDGET, max_output_cells=OUTPUT_BUDGET)
    assert source == original, 'Compiler changed the continuous master.'
    return source, result, time.monotonic() - started


class PartTests(unittest.TestCase):
    def test_sources_current_and_small(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                source = make_master(kind)
                stored = json.loads((HERE/'masters'/f'{kind}.json').read_text())
                self.assertEqual(source, stored)
                self.assertEqual(source['schema'], core.SCHEMA)
                self.assertLess(sum(len(c['operations']) for c in source['components']), 30)
                resolved, _ = coordinate_planes.resolve_master(source, {'pitch':.15})
                core.validate_master(resolved, .15)
                self.assertEqual(source['materials'], approved_palette())
                self.assertEqual(source['extensions']['status'], 'staged_prototype_needs_art_review')
                self.assertFalse(source['provenance']['new_engine'])
                self.assertIsNone(source['extensions']['city_placement'])
                self.assertIsNone(source['extensions']['terrain_placement'])

    def test_geometry_inside_local_envelope(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                source, _ = coordinate_planes.resolve_master(make_master(kind), {'pitch':.01})
                bounds = source['extensions']['local_bounds_m']
                for comp in source['components']:
                    for operation in comp['operations']:
                        if operation['action'] != 'paint': continue
                        shape = core.prepare_shape(operation['shape'], .01)
                        low, high = core.shape_bounds(shape)
                        placement = core.transform(operation.get('transform'))
                        for corner in itertools.product(*zip(low,high)):
                            xyz = core.apply(placement, corner)
                            for axis in range(3):
                                self.assertGreaterEqual(xyz[axis], bounds['min'][axis]-1e-8, (kind,operation['id'],xyz))
                                self.assertLessEqual(xyz[axis], bounds['max'][axis]+1e-8, (kind,operation['id'],xyz))

    def test_socket_support_clearance_animation_contracts(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                master = make_master(kind); ext = master['extensions']
                self.assertTrue(ext['sockets'])
                self.assertTrue(ext['supports'])
                self.assertTrue(ext['clearances'])
                self.assertEqual(len({s['id'] for s in ext['sockets']}), len(ext['sockets']))
                for s in ext['sockets']:
                    self.assertTrue(core.vector(s['position_m']))
                    self.assertTrue(core.vector(s['outward_normal']))
                for s in ext['supports']: core.prepare_shape(s['contact_region_m'], .1)
                components = {c['id']:c for c in master['components']}
                for hook in ext['animation_hooks']:
                    self.assertIn(hook['component'], components)
                    self.assertIn(hook['part'], [p['id'] for p in components[hook['component']]['parts']])
                    self.assertEqual(hook['status'], 'socket_and_pivot_contract_only_no_runtime_track')
                for clearance in ext['clearances']:
                    core.prepare_shape(clearance['region_m'], .1)
                    if clearance['source_empty_constraint']:
                        self.assertIn(clearance['id'], [c['id'] for c in master['constraints'] if c['kind']=='empty_region'])
                self.assertFalse(ext['lod']['source_geometry_changes_by_lod'])
                self.assertFalse(ext['lod']['output_cell_edits_allowed'])
                self.assertFalse(ext['lod']['collision_changes_by_lod'])

    def test_inventory_refs_coverage_and_states(self):
        inventory = json.loads((HERE/'inventory.json').read_text())
        entries = {e['id']:e for e in inventory['entries']}
        self.assertEqual(len(entries), len(inventory['entries']))
        self.assertEqual({k for k,v in entries.items() if v['status']=='staged_prototype'}, set(KINDS))
        required = ['timber_dock','multi_arch_bridge_vaults','bridge_pier','harbor_floodwall_and_water_stairs',
                    'sailing_river_boat_family','warehouse_buildings','cathedral_nave_transept','cathedral_twin_steeples',
                    'full_cloister_corners_and_court','castle_keep_courtyard','gatehouses','neighborhood_terrace_assemblies',
                    'grain_hall','market_stall_family','market_carts_and_handcarts','varied_roof_forms','dormer_family',
                    'chimneys','shopfronts','park_grove_trees','market_fountain']
        for key in required: self.assertIn(key, entries)
        for entry in entries.values():
            self.assertIn(entry['status'], ('existing_implemented','staged_prototype','needs_art_review'))
            self.assertTrue(entry['source_refs'])
            for ref in entry['source_refs']:
                self.assertEqual(file_ref(ref['path'])['sha256'], ref['sha256'])
                if 'json_pointer' in ref:
                    value=json.loads((ROOT/ref['path']).read_text())
                    for key in ref['json_pointer'].strip('/').split('/'): value=value[key]
            for dep in entry.get('depends_on_inventory_ids',[]): self.assertIn(dep, entries)
            self.assertFalse(entry['city_placement_changed'])
        self.assertEqual(inventory['process'].keys(), {'input','conditions','deliverables','completion_criteria'})
        self.assertEqual(len(entries), 75)
        self.assertFalse(inventory['water_system_policy']['low_river_gravity_uphill_claim'])
        for key in ('water_source_intake_headworks','water_reservoir_settling_pond','water_clean_cistern',
                    'water_covered_clean_conduit','water_millrace','water_sluice','water_weir','water_storm_drain',
                    'water_outfall','water_floodgate','water_well_drawpoint','water_canal_footbridge',
                    'water_protective_edge','military_training_ground','logistics_market_container',
                    'large_noble_compound_container','service_housing_container','poorer_row_quarter_container'):
            self.assertIn(key, entries)
            self.assertEqual(entries[key]['status'], 'needs_art_review')

    def test_stair_gameplay_dimensions_source_and_sample(self):
        master, result, _ = compile_small('park_terrace_stair')
        self.assertTrue(result['valid'], result['constraints'])
        ops=master['components'][0]['operations']
        steps=[op['shape'] for op in ops if op['id'].startswith('tread_')]
        self.assertEqual(len(steps), 6)
        previous=0
        for i, step in enumerate(steps):
            self.assertAlmostEqual(step['max'][1]-previous, .15)
            self.assertAlmostEqual(step['max'][2]-step['min'][2], .3)
            previous=step['max'][1]
            feature='tread_'+str(i+1)
            tops=[(row[1]+1)*result['pitch'] for row in result['cells'] if row[6]==feature]
            self.assertTrue(tops)
            self.assertAlmostEqual(max(tops), (i+1)*.15)
        self.assertIn(.2, master['extensions']['lod']['rejected_traversal_pitches_m'])
        self.assertTrue(any('not a historical assertion' in n for n in master['extensions']['design_notes']))

    def test_sequential_common_compile_and_render(self):
        before=[file_ref(p) for p in COMMON_FILES]
        for kind in KINDS:
            with self.subTest(kind=kind):
                source, result, elapsed = compile_small(kind)
                row={'kind':kind, 'pitch_m':result['pitch'], 'candidate_cells':result['candidate_cells'],
                     'output_cells':len(result['cells']), 'valid':result['valid'],
                     'master_hash':result['master_hash'], 'payload_hash':result['payload_hash'],
                     'compile_seconds':round(elapsed,4), 'constraints':result['constraints']}
                MEASUREMENTS.append(row)
                self.assertTrue(result['valid'], (kind,result['constraints']))
                self.assertLessEqual(result['candidate_cells'], CANDIDATE_BUDGET)
                self.assertLessEqual(len(result['cells']), OUTPUT_BUDGET)
                render=render_data.make_render_data(result)
                self.assertGreater(render['quad_count'], 0)
                row['render_quads']=render['quad_count']
                row['render_bounds']=render['bounds']
                row['render_payload_sha256']=core.digest(render)
                if kind in ('park_bench','pointed_arch_cloister_bay','park_terrace_stair'):
                    target=HERE/'evidence'/f'{kind}.smoke.render.json'
                    target.write_text(json.dumps(render,sort_keys=True,separators=(',',':'))+'\n')
                    row['render_artifact']=file_ref(str(target.relative_to(ROOT)))
                source_bounds=source['extensions']['local_bounds_m']
                for axis in range(3):
                    self.assertGreaterEqual(render['bounds']['min'][axis], source_bounds['min'][axis]-result['pitch']-1e-8)
                    self.assertLessEqual(render['bounds']['max'][axis], source_bounds['max'][axis]+result['pitch']+1e-8)
        self.assertEqual(before, [file_ref(p) for p in COMMON_FILES])

    def test_independent_recompile_two_pitches(self):
        # Two independently invoked direct source compiles, never copied cells.
        for pitch in (.15,.2):
            source, first, _=compile_small('park_bench',pitch)
            _, second, _=compile_small('park_bench',pitch)
            self.assertTrue(first['valid'], first['constraints'])
            self.assertTrue(second['valid'], second['constraints'])
            self.assertEqual(first['payload_hash'], second['payload_hash'])
            self.assertEqual(first['cells'], second['cells'])
            self.assertEqual(first['master_hash'], core.digest(source))
            REPEATS.append({'kind':'park_bench','pitch_m':pitch,'first_payload_hash':first['payload_hash'],
                            'second_payload_hash':second['payload_hash'],'identical':True,
                            'direct_from_same_master':True,'copied_output':False})


if __name__ == '__main__':
    HERE.joinpath('evidence').mkdir(exist_ok=True)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PartTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'status':'pass' if result.wasSuccessful() else 'fail',
            'scope':'source contracts and bounded sequential common smoke compile; no GUI, visual approval, full city compile, physics or animation execution',
            'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'test_source':file_ref('world_city/runtime_city/parts/test_parts.py'),
            'author_source':file_ref('world_city/runtime_city/parts/author.py'),
            'inventory':file_ref('world_city/runtime_city/parts/inventory.json'),
            'compiler_sources':[file_ref(p) for p in COMMON_FILES],
            'budgets':{'candidate_cells_per_compile':CANDIDATE_BUDGET,'output_cells_per_compile':OUTPUT_BUDGET},
            'compile_measurements':MEASUREMENTS,'independent_repeats':REPEATS,
            'visual_review':'not_run','runtime_physics':'not_run','animation_execution':'not_run','city_placement':'not_changed'}
    (HERE/'evidence'/'smoke_report.json').write_text(json.dumps(report,indent=2)+'\n')
    sys.exit(0 if result.wasSuccessful() else 1)
