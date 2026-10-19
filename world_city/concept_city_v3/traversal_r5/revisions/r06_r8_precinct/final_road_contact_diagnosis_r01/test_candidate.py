import copy
import unittest
import numpy as np
from .diagnose import HERE, ROOT, BASE, load, ref, geometry
from .compose_candidate import apply, case_payload
from world_city.concept_city_v3.registered_integration.r8.collision_local_origin import zero_count


class Candidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = load(BASE / 'public_network_final_runtime_r01/prepared_runtime.json')
        cls.candidate = load(HERE / 'candidate_r02/prepared_runtime.json')
        cls.recipe = load(HERE / 'candidate_r02/collision_recipe.json')
        cls.composed = load(HERE / 'composed_candidate_r01/prepared_all481.json')

    def test_source_bindings(self):
        for operation in self.recipe['operations']:
            for key in ['input', 'output', 'retained_output', 'translated_output']:
                if key in operation:
                    source = operation[key]
                    self.assertEqual(ref(ROOT / source['path']), source)

    def test_controller_loader_and_settings(self):
        self.assertEqual((HERE / 'Traversal.gd').read_bytes(), (ROOT / 'world_city/concept_city_v3/traversal_r5/Traversal.gd').read_bytes())
        self.assertEqual((HERE / 'RenderData.gd').read_bytes(), (ROOT / 'voxel_character/common/preview/RenderData.gd').read_bytes())
        self.assertEqual((HERE / 'project.godot').read_bytes(), (BASE / 'ordinary61_diagnostic_r01/project.godot').read_bytes())

    def test_b003_exact_translation(self):
        operation = self.recipe['operations'][0]
        original = load(ROOT / operation['input']['path'])
        candidate = load(ROOT / operation['output']['path'])
        origin = operation['origin_xyz_m']
        reconstructed = [[[v[i] + origin[i] for i in range(3)] for v in t] for t in candidate['triangles']]
        self.assertEqual(original['triangles'], reconstructed)
        self.assertEqual(original['source_face_indices'], candidate['source_face_indices'])
        self.assertEqual(zero_count(candidate['triangles']), 0)

    def test_east_exact_partition(self):
        operation = self.recipe['operations'][1]
        original = load(ROOT / operation['input']['path'])
        retained = load(ROOT / operation['retained_output']['path'])
        shifted = load(ROOT / operation['translated_output']['path'])
        selected = operation['selected_input_indices']
        remaining = operation['retained_input_indices']
        self.assertEqual(sorted(selected + remaining), list(range(len(original['triangles']))))
        self.assertEqual(set(selected) & set(remaining), set())
        self.assertEqual(retained['triangles'], [original['triangles'][i] for i in remaining])
        origin = operation['origin_xyz_m']
        reconstructed = [[[v[i] + origin[i] for i in range(3)] for v in t] for t in shifted['triangles']]
        self.assertEqual(reconstructed, [original['triangles'][i] for i in selected])
        self.assertEqual(zero_count(shifted['triangles']), 0)

    def test_civic_bounded_single_vertex(self):
        operation = self.recipe['operations'][2]
        original = load(ROOT / operation['input']['path'])
        candidate = load(ROOT / operation['output']['path'])
        differences = [(i, j, k) for i, (a, b) in enumerate(zip(original['triangles'], candidate['triangles']))
                       for j in range(3) for k in range(3) if a[j][k] != b[j][k]]
        self.assertEqual(differences, [(operation['collider_face_index'], 1, 1)])
        self.assertLess(operation['max_visible_source_deviation_m'], .008386)
        self.assertEqual(original['source_face_indices'], candidate['source_face_indices'])
        self.assertEqual(zero_count(candidate['triangles']), 0)

    def test_all_route_geometry_and_criteria_unchanged(self):
        originals = {r['id']: r for r in self.original['routes']}
        for route in self.composed['routes']:
            old = originals[route['id']]
            self.assertEqual({k: v for k, v in route.items() if k != 'placement_ids'},
                             {k: v for k, v in old.items() if k != 'placement_ids'})

    def test_only_six_road_case_inputs_change(self):
        originals = {r['id']: r for r in self.original['routes']}
        changed = [r['id'] for r in self.candidate['routes']
                   if case_payload(self.candidate, r) != case_payload(self.original, originals[r['id']])]
        self.assertEqual(len(changed), 6)
        self.assertTrue(all(not r.startswith('NEGATIVE_') for r in changed))

    def test_disjoint_recipe_reproduction(self):
        radial = load(BASE / 'east_radial_shared_frame_r03/prepared_all_candidate.json')
        self.assertEqual(apply(radial), self.composed)

    def test_conflicting_asset_rejected(self):
        radial = load(BASE / 'east_radial_shared_frame_r03/prepared_all_candidate.json')
        radial['assets']['SCENE:PUBLIC_NETWORK:ROAD:CIVIC_WEST_APPROACH']['render_sha256'] = 'unexpected'
        with self.assertRaises(ValueError):
            apply(radial)

    def test_original_failures_preserved(self):
        original = load(HERE / 'evidence/original_final481/replay.json')
        self.assertEqual([r['pass'] for r in original['routes']], [False, False])
        b003 = load(HERE / 'evidence/original_b003_c003/replay.json')
        self.assertFalse(b003['routes'][0]['pass'])

    def test_eight_case_actual_candidate(self):
        result = load(HERE / 'evidence/bounded_candidate_r02/replay.json')
        self.assertEqual(result['summary']['passed'], 8)
        self.assertEqual(result['summary']['cases'], 8)
        for row in result['routes']:
            if row['id'].startswith('NEGATIVE_'):
                continue
            self.assertEqual(row['ground_ray_miss_frames'], 0)
            self.assertEqual(row['not_on_floor_frames'], 0)

    def test_composed_29_actual_cases(self):
        result = load(HERE / 'evidence/composed_29/replay.json')
        self.assertEqual(result['summary']['passed'], 29)
        self.assertEqual(result['summary']['cases'], 29)
        for row in result['routes']:
            if not row['id'].startswith('NEGATIVE_'):
                self.assertEqual(row['ground_ray_miss_frames'], 0)
                self.assertEqual(row['not_on_floor_frames'], 0)
                self.assertEqual(row['obstacle_contact_ids'], {})

    def test_453_identical_inputs(self):
        review = load(HERE / 'composed_candidate_r01/composition_review.json')
        self.assertEqual(len(review['changed_case_ids']), 28)
        self.assertEqual(len(review['identical_case_ids']), 453)


if __name__ == '__main__':
    unittest.main()
