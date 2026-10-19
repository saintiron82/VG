"""Actual trim demand and exact same-seed crop invariance; no runtime edits."""
import copy
import itertools
import json
from pathlib import Path
import sys
import unittest
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import author_edge_trims as e

class EdgeTrims(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=e.read(e.HERE/'edge_catalog.v1.json');cls.demand=e.read(e.HERE/'edge_demand.v1.json')
        cls.safe=e.read(e.SURFACES/'inputs/safe_offset_rules.v1.json')

    def test_actual_206_asset_scan_replays_without_global_placement_expansion(self):
        self.assertEqual(e.scan(),self.demand)
        self.assertEqual(self.demand['candidate_assets'],206)
        self.assertEqual(self.demand['counts']['quarter_grid_vertical_rectangles'],34377)
        self.assertEqual(self.demand['required_kind_trim_count'],154)
        self.assertEqual(self.catalog['module_count'],462)
        self.assertFalse(self.demand['global_placement_data_expanded'])
        self.assertFalse(self.catalog['whole_city_coverage_pass'])

    def test_every_cached_trim_exactly_matches_original_full_seed_cells(self):
        full={}
        for kind in ('ashlar','planks'):
            for seed in self.safe['seeds']:
                master,_=e.common.author(self.safe,kind,seed)
                full[kind,seed]=e.common.compile_master(master,{'pitch':.0125},max_candidate_cells=150000,max_output_cells=50000)['cells']
        for record in self.catalog['modules']:
            with self.subTest(module=record['id']):
                spec=copy.deepcopy(self.safe);spec['trim']=record['trim'];spec['kinds']=[record['kind']]
                master,c,render,contract,_=e.compile_exact_crop(spec,record['kind'],record['seed'])
                self.assertEqual(master,e.read(e.HERE/record['master_file']))
                ox,oy=[round(v/.0125) for v in record['trim']['offset_m']]
                nx,ny=[round(record['trim'][k]/.0125) for k in ('width_m','height_m')]
                expected={(row[0]-ox,row[1]-oy,*row[2:]) for row in full[record['kind'],record['seed']] if ox<=row[0]<ox+nx and oy<=row[1]<oy+ny}
                self.assertEqual({(row[0]-ox,row[1]-oy,*row[2:]) for row in c['cells']},expected,'trim must crop the same full geometry/material/operation occupancy')
                self.assertEqual(c['master_hash'],record['master_hash']);self.assertEqual(c['payload_hash'],record['payload_hash'])
                self.assertEqual(e.common.payload(render),(e.HERE/record['render_file']).read_bytes())
                e.common.validate_geometry(spec,dict(c,grid_origin=[-ox*.0125,-oy*.0125,0]),render,contract)
                self.assertAlmostEqual(render['bounds']['min'][2]+.0375,0)
                self.assertAlmostEqual(render['bounds']['max'][2]+.0375,.0375)

    def test_bounded_compile_matches_complete_crop_master(self):
        choices=[self.catalog['modules'][i] for i in (0,55,141,278,350,461)]
        for record in choices:
            spec=copy.deepcopy(self.safe);spec['trim']=record['trim'];spec['kinds']=[record['kind']]
            master,bounded,_,_,_=e.compile_exact_crop(spec,record['kind'],record['seed'])
            complete=e.common.compile_master(master,{'pitch':.0125},max_candidate_cells=150000,max_output_cells=50000)
            self.assertEqual(bounded['cells'],complete['cells'])
            self.assertEqual(bounded['payload_hash'],complete['payload_hash'])
            self.assertEqual(bounded['valid_scope'],'cell_bounds_only')
            self.assertFalse(bounded['global_constraints_evaluated'])
            self.assertTrue(complete['valid'])

    def test_all_requested_patterns_have_exact_three_seed_lookup(self):
        by_id={m['id']:m for m in self.catalog['modules']}
        self.assertEqual(len(by_id),462)
        for request in self.demand['requirements']:
            ids=self.catalog['by_kind_trim'][request['kind']][request['trim_key']]
            self.assertEqual([by_id[i]['seed'] for i in ids],[41873,41879,41887])
            self.assertTrue(all(by_id[i]['trim']==request['trim'] for i in ids))
        for record in self.catalog['modules']:
            self.assertEqual(e.sha(e.HERE/record['render_file']),record['render_sha256'])
            self.assertEqual(record['sha256'],record['render_sha256'])
            self.assertFalse(record['collision_change'])

    def test_interval_demand_matches_explicit_small_grid_including_negative(self):
        for low in range(-9,9):
            for high in range(low+1,10):
                analytical=e.axis_patterns(low/4,high/4)
                observed={}
                for i in range(low//4,(high-1)//4+1):
                    a=max(low,i*4);b=min(high,(i+1)*4)
                    k=(a-i*4,b-a);observed[k]=observed.get(k,0)+1
                self.assertEqual(analytical,observed)
        self.assertEqual(sum(e.axis_patterns(-100000.25,100000.75).values()),200002)

    def test_rectangle_intersection_keeps_full_grid_anchor_and_offsets(self):
        rect=[-.75,.25,1.5,2.75]
        area=0
        for x in range(-2,3):
            for y in range(-1,4):
                patch=e.intersection_patch(rect,x,y)
                if patch is None:continue
                t=patch['trim'];ox,oy=t['offset_m'];w,h=t['width_m'],t['height_m']
                self.assertTrue(0<=ox<1 and 0<=oy<1 and ox+w<=1 and oy+h<=1)
                self.assertEqual(patch['grid_xy_m'],[x,y]);self.assertEqual(patch['local_translation_from_full_anchor_m'],[ox,oy,.0375])
                self.assertGreaterEqual(x+ox,rect[0]);self.assertGreaterEqual(y+oy,rect[1]);self.assertLessEqual(x+ox+w,rect[2]);self.assertLessEqual(y+oy+h,rect[3]);area+=w*h
        self.assertEqual(area,(rect[2]-rect[0])*(rect[3]-rect[1]))
        with self.assertRaises(ValueError):e.intersection_patch([0,0,.51,1],0,0)
        with self.assertRaises(ValueError):e.axis_patterns(0,-.5)
        with self.assertRaises(ValueError):e.intersection_patch(rect,-.5,0)

    def test_proper_source_axes_rectangle_and_unsupported_boundaries(self):
        for normal_axis,sign in itertools.product((0,2),(-1,1)):
            u=[sign,0,0] if normal_axis==2 else [0,0,-sign];v=[0,1,0];n=[0,0,0];n[normal_axis]=sign
            quad=[[u[i]*x+v[i]*y+n[i]*2 for i in range(3)] for x,y in [(-.5,0),(.75,0),(.75,1),(-.5,1)]]
            face,reason=e.rectangle(quad);self.assertIsNone(reason);self.assertEqual(face['normal'],n);self.assertEqual(face['u'],u)
            self.assertEqual(face['rect_uv_m'],[-.5,0,.75,1])
        self.assertEqual(e.rectangle([[0,0,0],[.51,0,0],[.51,1,0],[0,1,0]])[1],'nonquarter_boundary')
        self.assertEqual(e.rectangle([[0,0,0],[.125,0,0],[.125,1,0],[0,1,0]])[1],'smaller_than_quarter')
        self.assertEqual(e.rectangle([[0,0,0],[1,0,0],[.75,1,0],[0,1,0]])[1],'not_rectangle')

    def test_original_common_and_full_variants_preserved_and_budget(self):
        for path,digest in self.catalog['original_dependencies'].items():self.assertEqual(e.sha(e.ROOT/path),digest)
        self.assertEqual(len(e.read(e.SURFACES/'generated/manifest.json')['modules']),12)
        self.assertEqual(len(e.read(e.SURFACES/'generated_safe/manifest.json')['modules']),12)
        self.assertLess(sum(p.stat().st_size for p in e.HERE.rglob('*') if p.is_file()),15_000_000)
        self.assertFalse(any(p.suffix=='.bin' for p in e.HERE.rglob('*')))

if __name__=='__main__':unittest.main(verbosity=2)
