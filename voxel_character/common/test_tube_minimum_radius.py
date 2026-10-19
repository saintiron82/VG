"""Explicit existing tube thickness policy, with no global sampler change."""
import unittest
try:
    from . import core
except ImportError:
    import core


def sample(minimum, pitch, offset=0):
    return core.compile_master({
        'schema': core.SCHEMA, 'id': 'diagonal_tube_fixture', 'revision': 1,
        'axes': {'up': '+Y', 'front': '+Z', 'right': '+X'}, 'materials': {'m': '#ffffff'},
        'components': [{'id': 'c', 'parts': [{'id': 'p', 'pivot': [0, 0, 0]}], 'operations': [
            {'id': 'line', 'part': 'p', 'material': 'm', 'action': 'paint', 'shape': {
                'kind': 'tube', 'points': [[offset, offset, offset], [.6+offset, .6+offset, .6+offset]],
                'radius': .02, 'minimum_radius_cells': minimum}}]}],
        'instances': [{'id': 'i', 'component': 'c'}],
        'constraints': [{'id': 'line_is_six_connected', 'kind': 'connected', 'selector': {'feature': 'line'}}]
    }, {'pitch': pitch})


class TubeMinimumTests(unittest.TestCase):
    def test_three_quarter_cell_radius_can_disconnect_diagonal(self):
        self.assertFalse(sample(.75, .1)['valid'])

    def test_authored_one_cell_radius_connects_these_fixtures(self):
        for pitch in (.1, .2):
            for offset in (0, .013, -.017):
                with self.subTest(pitch=pitch, offset=offset):
                    result = sample(1, pitch, offset)
                    self.assertTrue(result['valid'])

    def test_policy_change_is_explicit_and_increases_occupied_cells(self):
        old, new = sample(.75, .1), sample(1, .1)
        self.assertGreater(len(new['cells']), len(old['cells']))
        self.assertNotEqual(old['master_hash'], new['master_hash'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
