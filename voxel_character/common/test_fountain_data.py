"""Read-only source and checked-output tests; no full asset recompilation or GUI."""
import hashlib
import json
from pathlib import Path
import unittest

try:
    from . import core, coordinate_planes
except ImportError:
    import core
    import coordinate_planes

COMMON = Path(__file__).resolve().parent
PROJECT = COMMON.parent.parent
DATA = COMMON/'assets/fountain'


class FountainCommonDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((PROJECT/'voxel_character/master/fountain_master.json').read_text())
        cls.master = json.loads((DATA/'master.json').read_text())
        cls.compiled = json.loads((DATA/'compiled_pitch_0.1.json').read_text())
        cls.coarse = json.loads((DATA/'compiled_pitch_0.2.json').read_text())

    def test_all_source_operations_accounted_for(self):
        self.assertEqual(set(self.master['extensions']['source_feature_groups']),
                         {o['id'] for o in self.source['operations']})
        operations = self.master['components'][0]['operations']
        self.assertEqual(len(operations), 62)
        self.assertEqual({o['shape']['kind'] for o in operations}, {'lathe', 'annulus', 'box', 'tube'})
        self.assertEqual(len(self.master['coordinate_planes']), 20)

    def test_continuous_profiles_retained(self):
        operations = {o['id']: o for o in self.master['components'][0]['operations']}
        for source in self.source['operations']:
            if source['kind'] == 'lathe_y':
                self.assertEqual(operations[source['id']]['shape']['profile'], source['profile'])
            elif source['kind'] == 'radial_bezier_tubes':
                for feature in self.master['extensions']['source_feature_groups'][source['id']]:
                    shape = operations[feature]['shape']
                    self.assertEqual(len(shape['points']), 65)
                    self.assertEqual(shape['radius'], source['radius'])
                    self.assertEqual(shape['minimum_radius_cells'], .75 if source['id'] == 'top_jet' else 1)

    def test_animation_and_collision_contracts_are_preserved_not_claimed_executed(self):
        extension = self.master['extensions']
        for key in ('animation', 'voxel_state_animation', 'preferred_animation', 'invariants', 'sockets'):
            self.assertEqual(extension[key], self.source[key])
            self.assertEqual(self.compiled['extensions'][key], self.source[key])
        self.assertFalse(extension['animation_support']['runtime_evaluated'])
        self.assertFalse(extension['invariants']['collision_changes_with_lod'])
        self.assertEqual(self.master['components'][0]['parts'], self.source['parts'])

    def test_eight_outlets_and_anchors_link_to_data(self):
        extension = self.master['extensions']
        self.assertEqual(len(extension['functional_openings']), 8)
        self.assertEqual(len(extension['functional_anchors']), 8)
        ids = {o['id'] for o in self.master['components'][0]['operations']}
        for opening in extension['functional_openings']:
            self.assertTrue(set(opening['features'].values()) <= ids)
            self.assertIn(opening['flow_feature'], ids)
            self.assertGreaterEqual(opening['minimum_gap_cells'], 2)
        for anchor in extension['functional_anchors']:
            self.assertIn(anchor['flow_feature'], ids)
            self.assertIn(anchor['receiving_surface'], ids)
        splash = extension['voxel_state_animation']['splash']
        self.assertEqual(len(extension['functional_anchors'])*len(splash['trajectories']), 48)
        self.assertGreaterEqual(splash['pool_limit'], 48)

    def test_numeric_master_resolves_for_both_requests(self):
        for pitch in (.1, .2):
            numeric, _ = coordinate_planes.resolve_master(self.master, {'pitch': pitch})
            core.validate_master(numeric, pitch)

    def test_supported_pitch_checks_and_full_repeat_match(self):
        self.assertTrue(self.compiled['valid'])
        self.assertEqual(len(self.compiled['constraints']), 107)
        self.assertTrue(all(c['pass'] for c in self.compiled['constraints']))
        self.assertEqual(len(self.compiled['cells']), 10992)
        self.assertEqual(self.compiled, json.loads((DATA/'repeat_pitch_0.1.json').read_text()))

    def test_coarse_failure_retained_without_false_success(self):
        self.assertFalse(self.coarse['valid'])
        self.assertEqual([c['id'] for c in self.coarse['constraints'] if not c['pass']], ['masonry_connected'])
        self.assertEqual(self.coarse, json.loads((DATA/'repeat_pitch_0.2.json').read_text()))

    def test_exact_source_and_compiler_lineage(self):
        for item in self.master['provenance']['source_files']:
            self.assertEqual(hashlib.sha256((PROJECT/item['path']).read_bytes()).hexdigest(), item['sha256'])
        self.assertEqual(core.digest(self.master), self.compiled['master_hash'])
        self.assertEqual(core.digest(self.compiled['cells']), self.compiled['payload_hash'])
        self.assertEqual(hashlib.sha256((COMMON/'core.py').read_bytes()).hexdigest(), self.compiled['compiler_source_hash'])
        self.assertEqual(hashlib.sha256((COMMON/'coordinate_planes.py').read_bytes()).hexdigest(), self.compiled['preprocessor']['source_hash'])

    def test_no_fountain_or_house_dispatch_in_shared_code(self):
        for path in [COMMON/'core.py', COMMON/'coordinate_planes.py']:
            text = path.read_text().lower()
            self.assertNotIn('fountain', text)
            self.assertNotIn('house', text)
            self.assertNotIn('eval(', text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
