"""Compare bounded streaming connectivity against actual common constraint results."""
import copy
import itertools
import gzip
import json
import tempfile
from pathlib import Path
import unittest
from connected_constraints import ConnectedAccumulator
import layered_compile as layer
import test_layered_compile as fixtures


class ConnectedConstraintContracts(unittest.TestCase):
    def assert_matches_common(self,master,edge=4):
        master=copy.deepcopy(master)
        master['constraints']=[{'id':'connection','kind':'connected','selector':{}}]
        full=layer.a.core.compile_master(master,{'pitch':.05})
        lo=[min(r[j] for r in full['cells']) if full['cells'] else 0 for j in range(3)]
        hi=[max(r[j]+1 for r in full['cells']) if full['cells'] else 1 for j in range(3)]
        state=ConnectedAccumulator()
        starts=[range(lo[j]//edge*edge,hi[j],edge) for j in range(3)]
        for low in itertools.product(*starts):
            high=[v+edge for v in low]
            points=[tuple(r[:3]) for r in full['cells'] if layer.owned(r[:3],low,high)]
            state.add_chunk(points,low,high)
        actual=state.result();expected=full['constraints'][0]
        for key in ('pass','occupied_cells','unreached_cells'):self.assertEqual(actual[key],expected[key])
        self.assertFalse(actual['whole_building_cell_union_created'])
        return actual

    def master(self,boxes):
        return {'schema':'riverstone.voxel.master.v1','id':'connected_fixture','revision':1,
                'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':{'stone':'aaaaaa'},
                'components':[{'id':'c','parts':[{'id':'foundation','pivot':[0,0,0]}],'operations':[{'id':'box'+str(i),'action':'paint','part':'foundation','material':'stone','feature':'body',
                'shape':{'kind':'box','min':lo,'max':hi}} for i,(lo,hi) in enumerate(boxes)]}],
                'instances':[{'id':'i','component':'c'}]}

    def test_cross_chunk_connected_matches_common(self):
        result=self.assert_matches_common(self.master([([-.3,-.1,-.1],[.35,.1,.1])]))
        self.assertTrue(result['pass']);self.assertGreater(result['retained_boundary_cells'],0)

    def test_gap_fails_and_exact_unreached_count_matches_common(self):
        result=self.assert_matches_common(self.master([([-.3,0,0],[-.1,.1,.1]),([0,0,0],[.4,.1,.1])]))
        self.assertFalse(result['pass']);self.assertEqual(result['unreached_cells'],32)

    def test_corner_contact_is_not_six_neighbor_connected(self):
        result=self.assert_matches_common(self.master([([0,0,0],[.1,.1,.1]),([.1,.1,.1],[.2,.2,.2])]),edge=2)
        self.assertFalse(result['pass']);self.assertEqual(result['unreached_cells'],8)

    def test_gzip_catalog_and_connected_compiler_integration(self):
        with tempfile.TemporaryDirectory(dir=layer.HERE) as directory:
            d=Path(directory);master=self.master([([-.2,0,0],[.3,.1,.1])]);master['constraints']=[{'id':'joined','kind':'connected','selector':{}}]
            source=d/'original.json';source.write_text(json.dumps(master))
            authored=d/'authored.master.json.gz'
            with gzip.open(authored,'wt') as f:json.dump(master,f)
            catalog=d/'catalog.json';catalog.write_text(json.dumps({'assets':[{'asset_key':'toy','source_master_path':str(source.relative_to(layer.a.ROOT)),
                'source_sha256':layer.a.sha(source),'emitted_master_path':str(authored.relative_to(layer.a.ROOT)),'emitted_master_sha256':layer.a.sha(authored)}]}))
            rules=layer.a.load(layer.HERE/'layer_rules.v1.json');rules['chunk_edge_fine_cells']=4
            rule_path=d/'rules.json';rule_path.write_text(json.dumps(rules))
            stats=layer.run('toy',d/'output',rule_path,catalog)
            self.assertTrue(stats['constraints'][0]['pass'])
            render_path=layer.a.ROOT/stats['files']['.render.json']['path']
            self.assertEqual(render_path.suffix,'.gz');self.assertEqual(render_path.read_bytes()[4:8],b'\0'*4)
            self.assertEqual(json.load(gzip.open(render_path,'rt'))['schema'],'riverstone.voxel.render.v1')
            expected=layer.a.core.compile_master(master,{'pitch':.05})['constraints'][0]
            for key in ('pass','occupied_cells','unreached_cells'):self.assertEqual(stats['constraints'][0][key],expected[key])

    def test_empty_selected_set_fails(self):
        self.assertFalse(ConnectedAccumulator().result()['pass'])

    def test_boundary_budget_and_overlapping_owner_rejected(self):
        with self.assertRaises(ValueError):ConnectedAccumulator(1).add_chunk([(0,0,0),(1,0,0)],[0,0,0],[2,2,2])
        state=ConnectedAccumulator();state.add_chunk([(0,0,0)],[0,0,0],[2,2,2])
        with self.assertRaises(ValueError):state.add_chunk([(0,0,0)],[0,0,0],[2,2,2])


if __name__=='__main__':unittest.main()
