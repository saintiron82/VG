"""Tiny, asset-independent regression tests for optional shared boundaries."""
import copy
import json
import math
from pathlib import Path
import unittest

try:
    from . import core, coordinate_planes as planes
except ImportError:
    import core
    import coordinate_planes as planes

ROOT = Path(__file__).resolve().parent


def fixture():
    return {'schema': core.SCHEMA, 'id': 'layer_fixture', 'revision': 1,
            'axes': {'up': '+Y', 'front': '+Z', 'right': '+X'}, 'grid_origin': [0, 0, 0],
            'materials': {'solid': '#999999', 'fill': '#1188aa'},
            'coordinate_planes': [
                {'id': 'surface', 'axis': 1, 'value': 1.45, 'snap': 'nearest'},
                {'id': 'interface', 'relative_to': 'surface', 'offset': -.08,
                 'minimum_offset_cells': 1, 'offset_quantization': 'ceil_cells'},
                {'id': 'bottom', 'relative_to': 'interface', 'offset': -.08, 'minimum_offset_cells': 1}],
            'components': [{'id': 'stack', 'parts': [{'id': 'p', 'pivot': [0, 0, 0]}], 'operations': [
                {'id': 'bottom', 'part': 'p', 'action': 'paint', 'material': 'solid', 'shape': {
                    'kind': 'box', 'min': [0, {'plane': 'bottom'}, 0], 'max': [.5, {'plane': 'interface'}, .3]}},
                {'id': 'top', 'part': 'p', 'action': 'paint', 'material': 'fill', 'shape': {
                    'kind': 'box', 'min': [0, {'plane': 'interface'}, 0], 'max': [.5, {'plane': 'surface'}, .3]}}]}],
            'instances': [{'id': 'i', 'component': 'stack'}],
            'constraints': [{'id': 'bottom_survives', 'kind': 'nonempty', 'selector': {'feature': 'bottom'}},
                            {'id': 'contact', 'kind': 'touch', 'a': {'feature': 'bottom'}, 'b': {'feature': 'top'}}]}


class CoordinatePlaneTests(unittest.TestCase):
    def test_shared_boundaries_at_two_pitches(self):
        for pitch in (.1, .2):
            with self.subTest(pitch=pitch):
                result = planes.compile_master(fixture(), {'pitch': pitch})
                self.assertTrue(result['valid'])
                self.assertGreater(sum(row[6] == 'bottom' for row in result['cells']), 0)

    def test_input_immutable_and_original_hash_retained(self):
        source = fixture(); original = copy.deepcopy(source)
        result = planes.compile_master(source, {'pitch': .1})
        self.assertEqual(source, original)
        self.assertEqual(result['master_hash'], core.digest(source))
        self.assertNotEqual(result['resolved_master_hash'], result['master_hash'])

    def test_ordinary_numeric_master_unchanged(self):
        source = json.loads((ROOT/'examples/wall_window.json').read_text())
        numeric, resolved = planes.resolve_master(source, {'pitch': .2})
        self.assertEqual(numeric, source)
        self.assertEqual(resolved, {})
        self.assertEqual(planes.compile_master(source, {'pitch': .2})['cells'],
                         core.compile_master(source, {'pitch': .2})['cells'])

    def test_nonzero_grid_origin_and_negative_ties(self):
        source = fixture(); source['grid_origin'][1] = .05
        source['coordinate_planes'][0]['value'] = -.2
        _, found = planes.resolve_master(source, {'pitch': .1})
        self.assertAlmostEqual(found['surface']['value'], -.15)

    def test_floor_and_ceil_snap(self):
        for mode, expected in [('floor', -.2), ('ceil', -.1), ('nearest', -.1)]:
            source = fixture(); source['coordinate_planes'][0].update(value=-.15, snap=mode)
            _, found = planes.resolve_master(source, {'pitch': .1})
            self.assertAlmostEqual(found['surface']['value'], expected)

    def test_reject_unknown_reference(self):
        source = fixture(); source['coordinate_planes'][1]['relative_to'] = 'missing'
        with self.assertRaisesRegex(core.InvalidMaster, 'unknown coordinate plane'):
            planes.resolve_master(source, {'pitch': .1})

    def test_reject_reference_cycle(self):
        source = fixture(); source['coordinate_planes'][1]['relative_to'] = 'bottom'
        with self.assertRaisesRegex(core.InvalidMaster, 'cycle'):
            planes.resolve_master(source, {'pitch': .1})

    def test_reject_nonfinite_and_bool(self):
        for value in [float('inf'), float('nan'), True]:
            source = fixture(); source['coordinate_planes'][0]['value'] = value
            with self.assertRaises(core.InvalidMaster):
                planes.resolve_master(source, {'pitch': .1})

    def test_reject_conflicting_axis(self):
        source = fixture(); source['coordinate_planes'][1]['axis'] = 2
        with self.assertRaisesRegex(core.InvalidMaster, 'axis mismatch'):
            planes.resolve_master(source, {'pitch': .1})

    def test_reject_unknown_fields_and_policies(self):
        for key, value in [('eval', 'os.exit()'), ('snap', 'python')]:
            source = fixture(); source['coordinate_planes'][0][key] = value
            with self.assertRaises(core.InvalidMaster):
                planes.resolve_master(source, {'pitch': .1})

    def test_reject_ambiguous_reference(self):
        source = fixture(); source['components'][0]['operations'][0]['shape']['min'][1]['extra'] = 1
        with self.assertRaisesRegex(core.InvalidMaster, 'only plane'):
            planes.resolve_master(source, {'pitch': .1})

    def test_reject_zero_direction(self):
        source = fixture(); source['coordinate_planes'][1]['offset'] = 0
        with self.assertRaisesRegex(core.InvalidMaster, 'no direction'):
            planes.resolve_master(source, {'pitch': .1})

    def test_declaration_reference_depth_and_traversal_budgets(self):
        for kwargs in [{'max_planes': 2}, {'max_references': 1}, {'max_depth': 1}, {'max_visited_nodes': 5}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(core.BudgetExceeded):
                planes.resolve_master(fixture(), {'pitch': .1}, **kwargs)

    def test_dependency_depth_rejected_even_with_shallow_shape(self):
        source = fixture()
        source['coordinate_planes'] = [{'id': str(i), 'axis': 1, 'relative_to': str(i+1), 'offset': .1}
                                       for i in range(10)] + [{'id': '10', 'axis': 1, 'value': 0}]
        with self.assertRaisesRegex(core.BudgetExceeded, 'dependency depth'):
            planes.resolve_master(source, {'pitch': .1}, max_depth=3)

    def test_dependency_budget_cannot_be_bypassed_by_cached_order(self):
        source = fixture()
        source['coordinate_planes'] = [{'id': '0', 'axis': 1, 'value': 0}] + [
            {'id': str(i), 'relative_to': str(i-1), 'offset': .1} for i in range(1, 10)]
        with self.assertRaisesRegex(core.BudgetExceeded, 'dependency depth'):
            planes.resolve_master(source, {'pitch': .1}, max_depth=3)

    def test_declared_dead_data_checked(self):
        source = fixture(); source['coordinate_planes'].append({'id': 'unused', 'axis': 1, 'value': float('nan')})
        with self.assertRaises(core.InvalidMaster):
            planes.resolve_master(source, {'pitch': .1})

    def test_tiny_nonzero_offset_still_rounds_outward(self):
        source = fixture()
        source['coordinate_planes'][1].update(offset=-1e-20, minimum_offset_cells=0)
        _, found = planes.resolve_master(source, {'pitch': .1})
        self.assertAlmostEqual(found['surface']['value']-found['interface']['value'], .1)

    def test_overflow_rejected(self):
        source = fixture(); source['coordinate_planes'][0]['value'] = 1e308
        with self.assertRaises(core.InvalidMaster):
            planes.resolve_master(source, {'pitch': 1e-300})


if __name__ == '__main__':
    unittest.main(verbosity=2)
