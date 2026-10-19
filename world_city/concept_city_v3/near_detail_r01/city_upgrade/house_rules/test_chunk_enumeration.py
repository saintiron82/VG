"""Empty ownership pruning must preserve complete native occupancy and labels."""
import copy
import itertools
import unittest
import adapter as a
import layered_compile as layer
import chunk_enumeration as chunks
import test_bounded_common as fixtures


class PaintChunkEnumerationContracts(unittest.TestCase):
    def test_union_of_scheduled_chunks_equals_full_common_for_all_shape_variants(self):
        for master in fixtures.BoundedCommonContracts().variants():
            source=layer.SpatialSource(master,.05,range_only=True);origin=master.get('grid_origin',[0,0,0])
            plan=chunks.enumerate_paint_chunks(source,origin,4,a.core.EPS);rows={}
            for low in plan['owned_lows']:
                bounds={'min':low,'max':[x+4 for x in low]}
                result=a.core.compile_master(master,{'pitch':.05},cell_bounds=bounds,max_candidate_cells=100000,max_output_cells=100000)
                for row in result['cells']:
                    self.assertNotIn(tuple(row[:3]),rows);rows[tuple(row[:3])]=row
            expected=fixtures.run(master)['cells']
            self.assertEqual([rows[k] for k in sorted(rows)],expected)
            self.assertFalse(plan['sampling_predicates_changed'])

    def test_sparse_components_skip_empty_ownership_but_keep_negative_coordinates(self):
        master=fixtures.toy();master['instances'][0]['transform']={'translation':[-1.2,0,-1.2]}
        master['instances'].append({'id':'remote','component':'body','transform':{'translation':[1.2,0,1.2]}})
        source=layer.SpatialSource(master,.05,range_only=True);plan=chunks.enumerate_paint_chunks(source,[0,0,0],4,a.core.EPS)
        self.assertGreater(plan['proven_empty_chunks_skipped'],0)
        actual={tuple(v) for v in plan['owned_lows']}
        for row in fixtures.run(master)['cells']:self.assertIn(tuple(row[j]//4*4 for j in range(3)),actual)
        self.assertTrue(any(v[0]<0 for v in actual))

    def test_cut_only_domains_do_not_generate_paint_owners(self):
        master=fixtures.toy();source=layer.SpatialSource(master,.05,range_only=True)
        baseline=chunks.enumerate_paint_chunks(source,[0,0,0],4,a.core.EPS)
        master['components'][0]['operations'].append(a.box('remote_cut',[20,20,20],[21,21,21],action='cut'))
        updated=chunks.enumerate_paint_chunks(layer.SpatialSource(master,.05,range_only=True),[0,0,0],4,a.core.EPS)
        self.assertEqual(baseline,updated)

    def test_bounds_memory_guard_rejects_excessive_ownership(self):
        source=layer.SpatialSource(fixtures.toy(),.05,range_only=True)
        with self.assertRaises(ValueError):chunks.enumerate_paint_chunks(source,[0,0,0],1,a.core.EPS,max_chunks=1)

if __name__=='__main__':unittest.main()
