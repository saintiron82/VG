import copy
import json
from pathlib import Path
import tempfile
import unittest
import adapter as a
import layered_compile_v3_r02 as engine
from bounded_surface_export_v1 import make_bounded_render_data
from voxel_character.common.render_data import make_render_data


def source(with_window=True):
    ops=[{'id':'body','action':'paint','part':'wall','material':'stone','shape':{'kind':'box','min':[0,0,0],'max':[1,.1,.1]}}]
    if with_window:ops.append({'id':'window','action':'paint','part':'wall','material':'glass','shape':{'kind':'box','min':[.8,0,0],'max':[1,.1,.1]}})
    return {'schema':'riverstone.voxel.master.v1','id':'bounded_window_scope','revision':1,
        'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],
        'materials':{'stone':'aaaaaa','glass':'aabbcc'},
        'components':[{'id':'wall','parts':[{'id':'wall','pivot':[0,0,0]}],'operations':ops}],
        'instances':[{'id':'house','component':'wall'}],
        'constraints':[{'id':'window_exists','kind':'nonempty','selector':{'material':'glass'},'minimum_cells':1}]}


class BoundedSurfaceScope(unittest.TestCase):
    def compiled(self):
        return a.core.compile_master(source(),{'pitch':.05},cell_bounds={'min':[0,0,0],'max':[4,2,2]})
    def test_local_missing_window_keeps_exact_geometry_and_original_false_result(self):
        result=self.compiled();before=copy.deepcopy(result)
        self.assertFalse(result['valid']);self.assertFalse(result['constraints'][0]['pass'])
        plain=source();plain['constraints']=[]
        reference=a.core.compile_master(plain,{'pitch':.05},cell_bounds={'min':[0,0,0],'max':[4,2,2]})
        actual=make_bounded_render_data(result);expected=make_render_data(reference)
        self.assertEqual(actual['groups'],expected['groups']);self.assertEqual(result,before)
        self.assertFalse(actual['provenance']['global_constraints_inferred'])
    def test_unbounded_invalid_global_result_is_rejected(self):
        result=a.core.compile_master(source(False),{'pitch':.05});self.assertFalse(result['valid'])
        with self.assertRaises(ValueError):make_bounded_render_data(result)
    def test_mutated_payload_and_invalid_scope_are_rejected(self):
        result=self.compiled();result['cells'][0][0]+=1
        with self.assertRaises(ValueError):make_bounded_render_data(result)
        result=self.compiled();result['global_constraints_evaluated']=True
        with self.assertRaises(ValueError):make_bounded_render_data(result)
    def run_global(self,with_window):
        with tempfile.TemporaryDirectory(dir=engine.HERE) as directory:
            d=Path(directory);m=source(with_window);p=d/'source.json';p.write_text(json.dumps(m))
            c=d/'catalog.json';c.write_text(json.dumps({'assets':[{'asset_key':'scope_fixture','source_master_path':str(p.relative_to(a.ROOT)),
                'source_sha256':a.sha(p),'emitted_master_path':str(p.relative_to(a.ROOT)),'emitted_master_sha256':a.sha(p)}]}))
            out=d/'output';rules=a.load(engine.HERE/'layer_rules.v1.json');rules['chunk_edge_fine_cells']=4
            rules['shared_output_reservation']={'book_path':str((d/'book.json').relative_to(a.ROOT)),
                'retained_roots':[str(out.relative_to(a.ROOT)),str((engine.HERE/'replay_code').relative_to(a.ROOT))],
                'limit_bytes':10000000,'asset_cap_bytes':1000000,'min_free_disk_bytes':1073741824}
            rp=d/'rules.json';rp.write_text(json.dumps(rules))
            if with_window:
                result=engine.run('scope_fixture',out,rp,c,render_only=True)
                self.assertEqual(result['reference_full_fine_cells'],80);self.assertTrue(result['constraints'][0]['pass'])
                self.assertEqual(result['constraints'][0]['occupied_fine_reference_cells'],16)
            else:
                with self.assertRaises(a.UnsupportedSurface):engine.run('scope_fixture',out,rp,c,render_only=True)
                report=a.load(out/'scope_fixture.layered.blocked.json')
                self.assertEqual(report['reason'],'layer_global_constraints_failed')
                self.assertFalse((out/'scope_fixture.layered.stats.json').exists())
                self.assertFalse((out/'scope_fixture.layered.render.json.gz').exists())
                self.assertEqual(report['completed_chunks'],5)
                a.write(engine.HERE/'generated/v3_scope_failclosed_fixture.r01.json',{'source':m,'blocked_report':report,
                    'global_missing_window_rejected':True,'no_final_render_or_pass_stats':True,'all_planned_chunks':5})
    def test_global_window_in_later_chunk_passes_only_after_aggregation(self):self.run_global(True)
    def test_global_missing_window_never_publishes_pass_or_render(self):self.run_global(False)

if __name__=='__main__':unittest.main()
