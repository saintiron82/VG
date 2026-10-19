import copy
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent))
import core
spec = importlib.util.spec_from_file_location('cell_pool_build', HERE/'build_render.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)


def fixture():
    master = {'schema':core.SCHEMA, 'id':'anonymous_sample', 'revision':1,
              'axes':{'up':'+Y','front':'+Z','right':'+X'},'materials':{'a':'#334455','b':'#11aacc'},
              'components':[{'id':'shared','parts':[{'id':'solid','pivot':[0,0,0]}],'operations':[
                  {'id':'under','part':'solid','action':'paint','material':'a','shape':{'kind':'box','min':[0,0,0],'max':[1,1,1]}},
                  {'id':'overlay','part':'solid','action':'paint','material':'b','shape':{'kind':'box','min':[0,.5,0],'max':[1,1,1]}}]}],
              'instances':[{'id':'first','component':'shared'}],
              'constraints':[{'id':'exists','kind':'nonempty','selector':{}}]}
    compiled = core.compile_master(master, {'pitch':.5})
    clip = {'schema':build.SCHEMA, 'source_id':master['id'], 'master_hash':core.digest(master),
            'duration':2., 'loop':True, 'update_hz':10, 'seed':0,
            'bounds':{'min':[-2,-2,-2],'max':[3,3,3]},
            'static_exclusions':[{'instance':'first','feature':'overlay'}],
            'pools':[{'id':'moving_ink','source':{'kind':'selected_cells','selector':{'instance':'first','feature':'overlay'}},
                      'cell_size':{'cells':1},'palette':['#112233','#ffeedd'],
                      'banded_color':{'axis':[0,1,0],'band_size':.5,'speed':.25,'step_rate':0,'cycle':2,'bright_bands':1,'base_index':0,'highlight_index':1}}]}
    return master, compiled, clip


class BuildTests(unittest.TestCase):
    def test_source_immutable_and_deterministic(self):
        master, compiled, clip = fixture(); before=copy.deepcopy((master, compiled, clip))
        a=build.make_render(master,compiled,clip);b=build.make_render(master,compiled,clip)
        self.assertEqual(a,b);self.assertEqual((master,compiled,clip),before)

    def test_hidden_static_source_survives_partition(self):
        master, compiled, clip=fixture()
        self.assertEqual(sum(r[6]=='under' for r in compiled['cells']),4)
        result=build.make_render(master,compiled,clip)
        self.assertEqual(result['cell_count'],8)
        self.assertEqual(len(result['cell_animation']['pools'][0]['positions']),4)
        self.assertFalse(result['provenance']['full_structure_rechecked_on_subset'])

    def test_changing_time_function_does_not_regenerate_geometry(self):
        master,compiled,clip=fixture();a=build.make_render(master,compiled,clip)
        clip['pools'][0]['banded_color']['speed']=.5;b=build.make_render(master,compiled,clip)
        self.assertEqual(a['groups'],b['groups']);self.assertEqual(a['payload_hash'],b['payload_hash'])
        self.assertNotEqual(a['cell_animation']['clip_hash'],b['cell_animation']['clip_hash'])

    def test_source_hash_and_invalid_compiled_rejected(self):
        master,compiled,clip=fixture();bad=copy.deepcopy(clip);bad['master_hash']='wrong'
        with self.assertRaises(core.InvalidMaster):build.make_render(master,compiled,bad)
        compiled['valid']=False
        with self.assertRaises(core.InvalidMaster):build.make_render(master,compiled,clip)

    def test_duplicate_selectors_and_unknown_selector_rejected(self):
        master,compiled,clip=fixture();clip['pools'].append(copy.deepcopy(clip['pools'][0]));clip['pools'][1]['id']='duplicate'
        with self.assertRaisesRegex(core.InvalidMaster,'overlap'):build.make_render(master,compiled,clip)
        master,compiled,clip=fixture();clip['static_exclusions'][0]['feature']='missing'
        with self.assertRaisesRegex(core.InvalidMaster,'matched no'):build.make_render(master,compiled,clip)

    def test_explicit_fixed_pool_static_occlusion(self):
        master,compiled,clip=fixture();clip['pools'][0]['occludes_static']=True
        result=build.make_render(master,compiled,clip)
        self.assertEqual(result['cell_count'],4)
        self.assertEqual(result['provenance']['static_cells_before_occlusion'],8)
        self.assertEqual(result['provenance']['static_cells_occluded_by_fixed_pools'],4)
        for change in [ {'threshold_visibility':{}}, {'ballistic':{}}, {'cell_size':{'cells':.9}}, {'source':{'kind':'members','members':[]}}, {'occludes_static':1} ]:
            bad=copy.deepcopy(clip);bad['pools'][0].update(change)
            with self.subTest(change=change),self.assertRaises(core.InvalidMaster):build.make_render(master,compiled,bad)

    def test_shared_component_partition_is_instance_specific(self):
        master,_,clip=fixture();master['instances'].append({'id':'second','component':'shared','transform':{'translation':[2,0,0]}})
        numeric=build.static_layer(master,clip['static_exclusions']);ops={i['id']:next(c for c in numeric['components'] if c['id']==i['component'])['operations'] for i in numeric['instances']}
        self.assertEqual([o['id'] for o in ops['first']],['under'])
        self.assertEqual([o['id'] for o in ops['second']],['under','overlay'])

    def test_component_cut_selectors_remain_scoped(self):
        master,_,clip=fixture();master['components'][0]['operations'].append({'id':'notch','part':'solid','action':'cut','selector':{'component':'shared'},'shape':{'kind':'box','min':[0,0,0],'max':[.5,.5,.5]}})
        static=build.static_layer(master,clip['static_exclusions'])
        self.assertEqual(static['components'][0]['operations'][-1]['selector']['component'],['static_cell_layer_0'])
        compiled=core.compile_master(static,{'pitch':.5});self.assertEqual(len(compiled['cells']),7)

    def test_lattice_sorted_and_budgeted(self):
        source={'origin':[0,0,0],'axis':[0,1,0],'length':.8,'radius':.11,'minimum_radius_cells':.75}
        points=build.lattice_positions(source,.1,[0,0,0],10000)
        self.assertEqual(len(points),32)
        self.assertEqual([p[1] for p in points],sorted(p[1] for p in points))
        with self.assertRaises(core.BudgetExceeded):build.lattice_positions(source,.01,[0,0,0],10)

    def test_threshold_piecewise_keys_and_step_clock(self):
        master,compiled,clip=fixture();r=build.make_render(master,compiled,clip);a=r['cell_animation'];pool=a['pools'][0]
        pool.pop('banded_color');pool['positions']=[[0,.25,0],[0,.75,0]];pool['color_indices']=[0,0]
        pool['threshold_visibility']={'axis':[0,1,0],'keys':[[0,.3],[1,1],[2,.3]],'interpolation':'linear'}
        build.validate_animation(a)
        self.assertEqual(build.evaluate(a,0)['pools'][0]['visible_count'],1)
        self.assertEqual(build.evaluate(a,1)['pools'][0]['visible_count'],2)
        self.assertEqual(build.evaluate(a,.19)['evaluation_time'],.1)
        self.assertEqual(build.evaluate(a,2)['pools'],build.evaluate(a,0)['pools'])
        self.assertEqual(build.evaluate(a,2-1e-12)['pools'],build.evaluate(a,0)['pools'])
        self.assertEqual(build.evaluate(a,4-1e-12)['evaluation_time'],0)

    def test_all_tick_boundaries_multiple_loops_and_large_seek(self):
        master,compiled,clip=fixture();a=build.make_render(master,compiled,clip)['cell_animation']
        for cycle in [-3,-1,0,1,2,10,1000000]:
            for tick in range(20):
                exact=cycle*2+tick/10
                for delta,expected in [(-1e-6,(tick-1)%20),(0,tick),(1e-6,tick)]:
                    with self.subTest(cycle=cycle,tick=tick,delta=delta):
                        self.assertAlmostEqual(build.evaluate(a,exact+delta)['evaluation_time'],expected/10)
            for delta in [-1e-12,0,1e-12]:
                self.assertEqual(build.evaluate(a,cycle*2+delta)['evaluation_time'],0)
        a['loop']=False
        self.assertEqual(build.evaluate(a,1000000)['evaluation_time'],2)

    def test_ballistic_member_identity_and_quantization(self):
        master,compiled,clip=fixture();r=build.make_render(master,compiled,clip);a=r['cell_animation'];pool=a['pools'][0]
        pool.pop('banded_color');pool['positions']=[[0,0,0],[0,0,0]];pool['color_indices']=[0,1]
        pool['ballistic']={'period':1.,'acceleration':[0,-2,0],'up_axis':[0,1,0],'minimum_up_offset':0,
                           'velocities':[[1,1,0],[0,1,1]],'phases':[0,.5],'lifetimes':[.4,.4],
                           'quantize':{'pitch':.1,'origin':[0,0,0]}}
        build.validate_animation(a)
        state=build.evaluate(a,.6)['pools'][0]
        self.assertEqual(state['member_ids'],[1]);self.assertEqual(state['color_indices'],[1])
        self.assertEqual(state['visible_count'],1)
        for point in state['positions']:
            for v in point:self.assertAlmostEqual(v/.1-.5,round(v/.1-.5))

    def test_relative_capped_lifetime_boundary(self):
        master,compiled,clip=fixture();a=build.make_render(master,compiled,clip)['cell_animation']
        pool=a['pools'][0];pool.pop('banded_color');pool['positions']=[[0,0,0]];pool['color_indices']=[0]
        pool['ballistic']={'period':2.,'acceleration':[0,0,0],'up_axis':[0,1,0],'minimum_up_offset':0,
                           'velocities':[[0,0,0]],'phases':[0],'lifetimes':[.54]}
        # Shift member phase while t=0 to address exact ages without the authored frame clock.
        for age,count in [(.54-2e-8,1),(.54,0),(.54+2e-8,0)]:
            pool['ballistic']['phases'][0]=-age
            self.assertEqual(build.evaluate(a,0)['pools'][0]['visible_count'],count)
        pool['ballistic']['lifetimes'][0]=1e-12
        for age,count in [(0,1),(.5e-12,1),(1e-12,0)]:
            pool['ballistic']['phases'][0]=-age
            self.assertEqual(build.evaluate(a,0)['pools'][0]['visible_count'],count)

    def test_reject_bad_function_inputs(self):
        master,compiled,clip=fixture();a=build.make_render(master,compiled,clip)['cell_animation']
        for field,value in [('duration',0),('duration',float('nan')),('seed',1),('update_hz',.13),('loop',1)]:
            bad=copy.deepcopy(a);bad[field]=value
            with self.subTest(field=field),self.assertRaises(core.InvalidMaster):build.validate_animation(bad)
        bad=copy.deepcopy(a);bad['pools'][0]['banded_color']['cycle']=0
        with self.assertRaises(core.InvalidMaster):build.validate_animation(bad)
        with self.assertRaises(core.BudgetExceeded):build.validate_animation(a,max_instances=1)

    def test_function_update_requires_no_oracle(self):
        master,compiled,clip=fixture();r=build.make_render(master,compiled,clip)
        self.assertNotIn('states',r['cell_animation']);self.assertNotIn('frames',r['cell_animation'])
        self.assertNotEqual(build.evaluate(r['cell_animation'],0)['pools'],build.evaluate(r['cell_animation'],1)['pools'])

    def test_foreign_asset_names_are_not_interpreted(self):
        text=(HERE/'build_render.py').read_text().lower()
        self.assertNotIn('fountain',text);self.assertNotIn('house',text);self.assertNotIn('eval(',text)

    def test_explicit_member_plane_and_size(self):
        planes={'surface':{'axis':1,'value':2.1}}
        self.assertEqual(build.resolve_position([0,{'plane':'surface'},0],planes),[0,2.1,0])
        self.assertEqual(build.cell_size({'world':.065,'minimum_cells':.55,'maximum_cells':1},.1),.065)
        with self.assertRaises(core.InvalidMaster):build.resolve_position([{'plane':'surface'},0,0],planes)


if __name__=='__main__':unittest.main(verbosity=2)
