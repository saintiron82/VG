"""Low-memory, deterministic point fixtures. No compiler/common imports or sampling."""
import copy
import itertools
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkpoint_store as checkpoint
from connected_constraints import ConnectedAccumulator
from connected_frontier_v4 import ConnectedFrontierV4, FrontierError, plan_digest


SEMANTICS = ('pass', 'occupied_cells', 'unreached_cells', 'connected_components',
             'peak_local_selected_cells', 'whole_building_cell_union_created')


def fixture_truth(points):
    remaining = set(points)
    total = len(remaining)
    first_size = 0
    count = 0
    while remaining:
        start = min(remaining)
        remaining.remove(start)
        stack = [start]
        size = 0
        while stack:
            point = stack.pop()
            size += 1
            for neighbor in ConnectedAccumulator.neighbors(point):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        if count == 0:
            first_size = size
        count += 1
    return {'pass': bool(total) and first_size == total, 'occupied_cells': total,
            'unreached_cells': total - first_size, 'connected_components': count}


class FrontierContracts(unittest.TestCase):
    def make(self, lows, edge=3, maximum=500000):
        return ConnectedFrontierV4(lows, edge, expected_plan_sha256=plan_digest(lows, edge),
                                   max_boundary_cells=maximum)

    def assert_state_exact(self, expected, frontier):
        actual = frontier._accumulator
        # This is stronger than final booleans: every DSU node and size is kept.
        for key in ('parents', 'sizes', 'total', 'first_point', 'first_node', 'peak_local_cells'):
            self.assertEqual(getattr(expected, key), getattr(actual, key), key)
        self.assertTrue(set(actual.boundary) <= set(expected.boundary))
        for point, node in actual.boundary.items():
            self.assertEqual(node, expected.boundary[point])
            owner = frontier._owner(point)
            self.assertIn(owner, frontier.completed_lows)
            self.assertTrue(frontier._touches_pending(point, owner))
        # Independent literal six-neighbor rule, not the implementation's face helper.
        wanted = {p: node for p, node in expected.boundary.items()
                  if any(frontier._owner(q) != frontier._owner(p) and
                         frontier._owner(q) in frontier._pending
                         for q in ConnectedAccumulator.neighbors(p))}
        self.assertEqual(actual.boundary, wanted)

    def compare_fixture(self, lows, edge, chunks, order, resume_at=None):
        original = ConnectedAccumulator()
        frontier = self.make(lows, edge)
        completed = []
        for index, low in enumerate(order):
            points = chunks.get(low, [])
            high = tuple(n + edge for n in low)
            original.add_chunk(points, low, high)
            frontier.add_chunk(points, low, high)
            completed.append(low)
            self.assert_state_exact(original, frontier)
            if resume_at == index:
                unchanged = checkpoint.serialize_connected(original)
                adopted = ConnectedFrontierV4.from_accumulator(
                    original, lows, edge, completed, expected_plan_sha256=plan_digest(lows, edge))
                self.assertEqual(checkpoint.serialize_connected(original), unchanged)
                self.assert_state_exact(original, adopted)
                self.assertEqual(adopted.snapshot(), frontier.snapshot())
                frontier = adopted
            # Exercise checkpoint serialization and native v4 resume at every boundary.
            record = frontier.snapshot()
            checkpoint._record({'frontier': record})
            frontier = ConnectedFrontierV4.restore(record, lows, edge, completed,
                                                   expected_plan_sha256=plan_digest(lows, edge))
            self.assert_state_exact(original, frontier)
            if index + 1 < len(lows):
                with self.assertRaisesRegex(FrontierError, 'Incomplete ownership coverage'):
                    frontier.result()
                # Both legacy result() and progress() path-compress DSU roots.
                # Keep diagnostic calls symmetric for the exact array check.
                original.result()
                self.assertNotIn('pass', frontier.progress())
        expected, actual = original.result(), frontier.result()
        for key in SEMANTICS:
            self.assertEqual(expected[key], actual[key], key)
        truth = fixture_truth(itertools.chain.from_iterable(chunks.values()))
        for key, value in truth.items():
            self.assertEqual(actual[key], value, key)
        self.assertEqual(actual['retained_boundary_cells'], 0)
        return frontier

    def test_200_random_arbitrary_order_negative_and_sparse_plans(self):
        for seed in range(200):
            rng = random.Random(seed)
            edge = 1 + seed % 5
            lattice = list(itertools.product(range(-2, 2), range(-1, 2), range(-1, 1)))
            lows = [tuple(n * edge for n in p) for p in lattice if rng.random() < .75]
            chunks = {}
            for low in lows:
                density = rng.choice((0, .05, .3, .7, 1.))
                chunks[low] = [tuple(low[j] + delta[j] for j in range(3))
                               for delta in itertools.product(range(edge), repeat=3)
                               if rng.random() < density]
            order = list(lows)
            rng.shuffle(order)
            with self.subTest(seed=seed, edge=edge):
                self.compare_fixture(lows, edge, chunks, order, rng.randrange(len(order)))

    def test_all_six_faces_and_negative_coordinates(self):
        lows = [(0, 0, 0), (-2, 0, 0), (2, 0, 0), (0, -2, 0),
                (0, 2, 0), (0, 0, -2), (0, 0, 2)]
        chunks = {low: [tuple(low[j] + d[j] for j in range(3))
                        for d in itertools.product(range(2), repeat=3)] for low in lows}
        for order in (lows, list(reversed(lows)), lows[1::2] + lows[::2]):
            self.assertTrue(self.compare_fixture(lows, 2, chunks, order, 2).result()['pass'])

    def test_edge_one_opposite_neighbors_both_retained(self):
        lows = [(-1, 0, 0), (0, 0, 0), (1, 0, 0)]
        state = self.make(lows, 1)
        state.add_chunk([(0, 0, 0)], (0, 0, 0))
        state.add_chunk([(-1, 0, 0)], (-1, 0, 0))
        self.assertIn((0, 0, 0), state._accumulator.boundary)
        state.add_chunk([(1, 0, 0)], (1, 0, 0))
        self.assertTrue(state.result()['pass'])

    def test_closed_interior_and_boundary_components_never_disappear(self):
        lows = [(-6, 0, 0), (0, 0, 0), (3, 0, 0), (12, 0, 0)]
        chunks = {lows[0]: [(-5, 1, 1)], lows[1]: [(2, 1, 1)],
                  lows[2]: [(3, 1, 1)], lows[3]: [(12, 0, 0)]}
        state = self.compare_fixture(lows, 3, chunks, [lows[3], lows[1], lows[0], lows[2]], 2)
        result = state.result()
        self.assertEqual(result['connected_components'], 3)
        self.assertEqual(result['unreached_cells'], 3)
        self.assertEqual(len(state._accumulator.parents), 4)

    def test_late_bridge_and_corner_only_contact(self):
        lows = [(-2, 0, 0), (0, 0, 0), (2, 0, 0)]
        chunks = {low: [(low[0], 0, 0), (low[0] + 1, 0, 0)] for low in lows}
        self.assertTrue(self.compare_fixture(lows, 2, chunks, [lows[2], lows[0], lows[1]], 1).result()['pass'])
        lows = [(0, 0, 0), (2, 2, 2)]
        chunks = {lows[0]: [(1, 1, 1)], lows[1]: [(2, 2, 2)]}
        self.assertFalse(self.compare_fixture(lows, 2, chunks, lows, 0).result()['pass'])

    def test_all_empty_and_empty_schedule(self):
        self.assertFalse(self.make([], 2).result()['pass'])
        lows = [(-2, 0, 0), (0, 0, 0)]
        self.assertFalse(self.compare_fixture(lows, 2, {}, lows, 0).result()['pass'])

    def test_missing_empty_chunk_keeps_global_result_pending(self):
        lows = [(0, 0, 0), (3, 0, 0)]
        state = self.make(lows)
        state.add_chunk([(1, 1, 1)], lows[0])
        self.assertTrue(state.progress()['selected_prefix_connected'])
        with self.assertRaises(FrontierError):
            state.result()
        state.add_chunk([], lows[1])
        self.assertTrue(state.result()['pass'])

    def test_duplicate_and_missing_plan_and_changed_edge_rejected(self):
        lows = [(0, 0, 0), (3, 0, 0)]
        digest = plan_digest(lows, 3)
        for wrong in (lows + [lows[0]], lows[:-1], lows + [(6, 0, 0)], [(1, 0, 0)]):
            with self.subTest(wrong=wrong), self.assertRaises(FrontierError):
                ConnectedFrontierV4(wrong, 3, expected_plan_sha256=digest)
        with self.assertRaises(FrontierError):
            ConnectedFrontierV4(lows, 1, expected_plan_sha256=digest)
        self.assertEqual(plan_digest(lows, 3), plan_digest(list(reversed(lows)), 3))

    def test_bad_additions_are_rejected_without_mutation_even_empty_duplicates(self):
        state = self.make([(0, 0, 0), (3, 0, 0)])
        state.add_chunk([], (0, 0, 0))
        before = state.snapshot()
        for points, lo, hi in (([], (0, 0, 0), None), ([], (6, 0, 0), None),
                               ([(2, 0, 0)], (3, 0, 0), None),
                               ([(3, 0, 0)], (3, 0, 0), (5, 3, 3)),
                               ([(3., 0, 0)], (3, 0, 0), None)):
            with self.subTest(points=points, lo=lo, hi=hi), self.assertRaises(FrontierError):
                state.add_chunk(points, lo, hi)
            self.assertEqual(state.snapshot(), before)

    def test_duplicate_points_preserve_original_set_semantics_and_input(self):
        lows = [(0, 0, 0)]
        points = [[0, 0, 0], [0, 0, 0], [1, 0, 0]]
        before = copy.deepcopy(points)
        state = self.make(lows, 2)
        state.add_chunk(points, lows[0])
        self.assertEqual(points, before)
        self.assertEqual(state.result()['occupied_cells'], 2)

    def test_budget_failure_is_atomic_and_unexpected_failure_is_poisoned(self):
        state = self.make([(0, 0, 0)], 2, maximum=1)
        before = state.snapshot()
        with self.assertRaises(FrontierError):
            state.add_chunk([(0, 0, 0), (1, 0, 0)], (0, 0, 0))
        self.assertEqual(state.snapshot(), before)
        with mock.patch.object(state._accumulator, 'add_chunk', side_effect=RuntimeError('interrupted')):
            with self.assertRaises(RuntimeError):
                state.add_chunk([], (0, 0, 0))
        for action in (state.snapshot, state.result, state.progress):
            with self.assertRaisesRegex(FrontierError, 'last committed snapshot'):
                action()

    def test_legacy_import_rejects_wrong_completed_ownership(self):
        lows = [(0, 0, 0), (3, 0, 0)]
        original = ConnectedAccumulator()
        original.add_chunk([(2, 1, 1)], lows[0], (3, 3, 3))
        for completed in ([], [lows[0], lows[0]], [lows[1]], [(6, 0, 0)]):
            with self.subTest(completed=completed), self.assertRaises(FrontierError):
                ConnectedFrontierV4.from_accumulator(original, lows, 3, completed,
                                                     expected_plan_sha256=plan_digest(lows, 3))

    def test_snapshot_rejects_wrong_plan_coverage_schema_and_bad_projection(self):
        lows = [(0, 0, 0), (3, 0, 0), (6, 0, 0)]
        state = self.make(lows)
        state.add_chunk([], lows[0])
        state.add_chunk([(3, 0, 0), (4, 0, 0), (5, 0, 0)], lows[1])
        record = state.snapshot()
        changes = [('schema', 'unknown'), ('edge', True), ('owned_lows', [list(lows[0])]),
                   ('completed_lows', [list(lows[1])]),
                   ('completed_lows', [list(lows[0]), list(lows[1]), list(lows[1])]),
                   ('plan_sha256', '0' * 64), ('retired_boundary_cells', -1)]
        for key, value in changes:
            changed = copy.deepcopy(record)
            changed[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(FrontierError):
                ConnectedFrontierV4.restore(changed, lows, 3, lows[:2],
                                             expected_plan_sha256=plan_digest(lows, 3))
        with self.assertRaises(FrontierError):
            ConnectedFrontierV4.restore(record, lows, 3, [lows[1]],
                                         expected_plan_sha256=plan_digest(lows, 3))
        changed = copy.deepcopy(record)
        changed['connected']['sizes'][0] += 1
        with self.assertRaises(checkpoint.CheckpointError):
            ConnectedFrontierV4.restore(changed, lows, 3, lows[:2],
                                         expected_plan_sha256=plan_digest(lows, 3))

    def test_existing_store_roundtrip_continue_without_store_changes(self):
        lows = [(0, 0, 0), (3, 0, 0), (6, 0, 0)]
        order = list(reversed(lows))
        state = self.make(lows)
        identity = {'plan_sha256': plan_digest(lows, 3), 'frontier_schema': 'v4'}
        with tempfile.TemporaryDirectory(prefix='frontier-v4-') as directory:
            for sequence, low in enumerate(order):
                store = checkpoint.Store(Path(directory) / 'test-store', identity)
                if sequence:
                    state = ConnectedFrontierV4.restore(
                        store.load_state()['frontier'], lows, 3, order[:sequence],
                        expected_plan_sha256=identity['plan_sha256'])
                state.add_chunk([(low[0] + i, 0, 0) for i in range(3)], low)
                store.append(sequence, {'owner': list(low)}, {'frontier': state.snapshot()})
            restored = checkpoint.Store(Path(directory) / 'test-store', identity)
            state = ConnectedFrontierV4.restore(restored.load_state()['frontier'], lows, 3, order,
                                                 expected_plan_sha256=identity['plan_sha256'])
            self.assertTrue(state.result()['pass'])
            self.assertEqual(state.result()['occupied_cells'], 9)
            self.assertEqual(len(list(restored.load_records())), 3)

    def test_separate_metadata_keeps_existing_connected_field_compatible(self):
        lows = [(0, 0, 0), (3, 0, 0)]
        state = self.make(lows)
        state.add_chunk([(2, 0, 0)], lows[0])
        saved = {'connected': {'constraint_id': checkpoint.serialize_connected(state.accumulator)},
                 'frontier_state': {'constraint_id': state.metadata()}}
        checkpoint._record(saved)
        self.assertEqual(saved['connected']['constraint_id']['schema'], checkpoint.CONNECTED_SCHEMA)
        self.assertNotIn('connected', saved['frontier_state']['constraint_id'])
        resumed = ConnectedFrontierV4.restore_projection(
            saved['connected']['constraint_id'], saved['frontier_state']['constraint_id'],
            lows, 3, lows[:1], expected_plan_sha256=plan_digest(lows, 3))
        resumed.add_chunk([(3, 0, 0)], lows[1])
        self.assertTrue(resumed.result()['pass'])


if __name__ == '__main__':
    unittest.main()
