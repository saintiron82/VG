"""Default compatibility and exact bounded sampling against preserved common core."""
import copy
import importlib.util
import itertools
import json
import math
import unittest
from pathlib import Path
import adapter as a
import layered_compile as layer
from test_layered_compile import toy

P=Path(__file__).with_name('fixtures')/'common_core_before_cell_bounds.py'
spec=importlib.util.spec_from_file_location('original_common_before_bounds',P)
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)


def run(master,bounds=None):
    return a.core.compile_master(master,{'pitch':.05},cell_bounds=bounds,max_candidate_cells=100000,max_output_cells=100000)


def selected(rows,bounds):
    return [r for r in rows if all(bounds['min'][j]<=r[j]<bounds['max'][j] for j in range(3))]


class BoundedCommonContracts(unittest.TestCase):
    def test_snapshot_hash_is_original_approved_compiler(self):
        self.assertEqual(a.sha(P),'c4cc126554425211c7c670fefd0f97c22534ee5e489886354e0e00dd913f19e6')

    def variants(self):
        yield toy()
        m=toy();m['grid_origin']=[.013,-.071,.027];m['instances'][0]['transform']['translation']=[-.3,-.2,-.1];yield m
        for shape in [
            {'kind':'extrusion','polygon':[[-.3,-.2],[.2,.3],[.3,.3],[-.2,-.2]],'z_min':-.1,'z_max':.1},
            {'kind':'annulus','inner_radius':.1,'outer_radius':.25,'y_min':-.1,'y_max':.1},
            {'kind':'lathe','profile':[[0,0],[.2,0],[.1,.3],[0,.3]]},
            {'kind':'tube','points':[[-.2,0,0],[.2,.1,0]],'radius':.07}]:
            m=toy();m['components'][0]['operations'][0]['shape']=shape;yield m
        m=toy();c=math.sqrt(.5);m['instances'][0]['transform']={'translation':[-.1,0,.1],'basis':[[c,0,c],[0,1,0],[-c,0,c]]};yield m
        m=toy();ops=m['components'][0]['operations'];ops.append(a.box('cut',[.1,.1,-.1],[.3,.3,.5],action='cut'));ops.append(a.box('late',[.1,.1,.03],[.3,.3,.08],'glass'));yield m
        m=toy();m['instances'].append({'id':'second','component':'body','transform':{'translation':[.1,.1,.1]}})
        m['assembly_cuts']=[a.box('global_cut',[.1,-.1,.1],[.2,.6,.2],action='cut')];yield m

    def test_default_output_unchanged_except_honest_compiler_hash(self):
        for m in self.variants():
            before=original.compile_master(m,{'pitch':.05},max_candidate_cells=100000,max_output_cells=100000)
            after=run(m)
            self.assertEqual(before['cells'],after['cells']);self.assertEqual(before['materials'],after['materials']);self.assertEqual(before['payload_hash'],after['payload_hash'])
            before.pop('compiler_source_hash');after.pop('compiler_source_hash')
            self.assertEqual(json.dumps(before,sort_keys=True),json.dumps(after,sort_keys=True))
            self.assertNotIn('evaluation_scope',after)

    def test_bounds_equal_full_filter_all_shapes_transforms_and_operations(self):
        bounds_list=[{'min':[-4,-4,-4],'max':[4,4,4]},{'min':[0,0,0],'max':[2,5,9]},{'min':[-20,-20,-20],'max':[0,0,0]}]
        for m in self.variants():
            full=original.compile_master(m,{'pitch':.05},max_candidate_cells=100000,max_output_cells=100000)
            for b in bounds_list:
                result=run(m,b);self.assertEqual(result['cells'],selected(full['cells'],b))
                self.assertEqual(result['materials'],full['materials'])
                self.assertEqual(result['evaluation_scope'],{'kind':'cell_bounds',**b})
                self.assertFalse(result['global_constraints_evaluated']);self.assertIsNone(result['global_constraints_valid'])

    def test_multi_chunk_exact_union_no_overlap_or_missing_metadata(self):
        for m in self.variants():
            full=run(m);points={}
            for low in itertools.product(range(-8,12,4),repeat=3):
                b={'min':list(low),'max':[v+4 for v in low]}
                for row in run(m,b)['cells']:
                    self.assertNotIn(tuple(row[:3]),points);points[tuple(row[:3])]=row
            self.assertEqual([points[k] for k in sorted(points)],full['cells'])

    def test_bbox_pruning_keeps_original_shapes_and_shared_instances_fallback(self):
        b={'min':[-3,-3,-3],'max':[5,5,5]}
        for m in self.variants():
            source=layer.SpatialSource(m,.05,range_only=True)
            lo=[m.get('grid_origin',[0,0,0])[j]+b['min'][j]*.05 for j in range(3)]
            hi=[m.get('grid_origin',[0,0,0])[j]+b['max'][j]*.05 for j in range(3)]
            pruned=source.bounded_master(lo,hi)
            original_shapes={c['id']:{o['id']:o['shape'] for o in c['operations']} for c in m['components']}
            for c in pruned['components']:
                for op in c['operations']:self.assertEqual(op['shape'],original_shapes[c['id']][op['id']])
            self.assertEqual(run(pruned,b)['cells'],selected(run(m)['cells'],b))
            if source.shared_components:self.assertEqual(pruned['instances'],m['instances'])

    def test_large_original_shape_is_not_enumerated_outside_bounds(self):
        m=toy();m['components'][0]['operations'][0]['shape']={'kind':'box','min':[-1000,-1000,-1000],'max':[1000,1000,1000]}
        result=run(m,{'min':[-1,-1,-1],'max':[1,1,1]})
        self.assertEqual(len(result['cells']),8);self.assertEqual(result['candidate_cells'],8)

    def test_constraint_pass_is_explicitly_local_not_global(self):
        m=toy();m['components'][0]['operations'].append(a.box('island',[.8,0,0],[.9,.1,.1],'stone'))
        m['constraints']=[{'id':'joined','kind':'connected','selector':{}}]
        self.assertFalse(run(m)['valid'])
        scoped=run(m,{'min':[0,0,0],'max':[8,8,8]})
        self.assertTrue(scoped['valid']);self.assertEqual(scoped['valid_scope'],'cell_bounds_only')
        self.assertFalse(scoped['global_constraints_evaluated']);self.assertIsNone(scoped['constraints'][0]['global_pass'])

    def test_empty_region_check_samples_only_explicit_scope(self):
        m=toy();m['constraints']=[{'id':'air','kind':'empty_region','selector':{},'shape':{'kind':'box','min':[0,0,0],'max':[1,1,1]}}]
        scoped=run(m,{'min':[10,10,10],'max':[11,11,11]})
        self.assertTrue(scoped['constraints'][0]['pass']);self.assertEqual(scoped['constraints'][0]['sampled_region_cells'],1)
        self.assertEqual(scoped['constraints'][0]['blocked_cells'],0);self.assertIsNone(scoped['global_constraints_valid'])

    def test_empty_bounds_valid_and_invalid_bounds_rejected(self):
        self.assertEqual(run(toy(),{'min':[0,0,0],'max':[0,1,1]})['cells'],[])
        for b in ({}, {'min':[0,0,0],'max':[1,1]}, {'min':[False,0,0],'max':[1,1,1]}, {'min':[1,0,0],'max':[0,1,1]}, [[0,0,0],[1,1,1]], {'min':[.0,0,0],'max':[1,1,1]}):
            with self.assertRaises(a.core.InvalidMaster):run(toy(),b)

    def test_actual_hip_exact_edge_uses_original_polygon_without_crop(self):
        f=a.load(Path(__file__).with_name('fixtures')/'hip_trim_float_boundary.json');m=toy()
        m['instances']=[f['instance']];m['components'][0]['id']=f['instance']['component']
        m['components'][0]['operations']=[a.box('base',[-3,8,-7],[-2,9,-6],'stone'),f['operation']]
        key=f['failing_cell'];result=run(m,{'min':key,'max':[v+1 for v in key]})
        self.assertEqual(result['cells'],[])
        self.assertEqual(result['candidate_cells'],2)


if __name__=='__main__':unittest.main()
