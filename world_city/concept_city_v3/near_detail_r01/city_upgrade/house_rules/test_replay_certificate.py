"""Independent replay ownership and preserved-core sampling contracts."""
import copy
import json
import unittest
import replay_certificate_qa as replay
import test_render_only as fixtures


class IndependentReplayContracts(unittest.TestCase):
    def test_owner_uses_solid_cell_side_of_normal_boundary(self):
        self.assertEqual(replay.quad_owner((0,1,0,0,60,0,60),60),(-1,0,0))
        self.assertEqual(replay.quad_owner((0,-1,0,0,60,0,60),60),(0,0,0))
        self.assertEqual(replay.quad_owner((1,1,60,-60,0,0,60),60),(0,0,-1))
        with self.assertRaises(replay.qa.QAError):replay.quad_owner((0,1,0,0,61,0,60),60)

    def test_selection_is_deterministic_unique_and_ignores_empty(self):
        chunks=[{'reference_owned_fine_cells':n} for n in (1,2,0,3,4,0,5,6)]
        selected=replay.choose_chunks(chunks,4)
        self.assertEqual(selected,[7,0,4,1]);self.assertEqual(len(selected),len(set(selected)))
        self.assertEqual(replay.choose_chunks([{'reference_owned_fine_cells':0}],4),[])

    def test_actual_preserved_unpruned_common_replay_and_tamper_rejection(self):
        T=fixtures.RenderOnlyContracts;T.setUpClass()
        try:
            report=replay.verify(T.ts)
            self.assertTrue(report['pass'],report)
            self.assertFalse(report['source_shapes_and_operations_pruned'])
            self.assertFalse(report['global_constraint_pass_inferred'])
            changed=copy.deepcopy(T.transient);i=replay.choose_chunks(changed['chunks'])[0]
            changed['chunks'][i]['full_fine_fingerprint']['count']+=1
            altered=T.d/'tampered_replay.stats.json';altered.write_text(json.dumps(changed))
            self.assertFalse(replay.verify(altered)['pass'])
        finally:T.tearDownClass()

if __name__=='__main__':unittest.main()
