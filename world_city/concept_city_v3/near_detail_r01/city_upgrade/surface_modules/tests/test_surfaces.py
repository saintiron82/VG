"""Geometry, origin, hole, collision and frozen-output regressions; no GUI."""
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import author_surfaces as a

class Surfaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules=json.loads((HERE/'inputs/surface_rules.v1.json').read_text())
        cls.manifest=json.loads((HERE/'generated/manifest.json').read_text())

    def spec(self):
        return copy.deepcopy(self.rules)

    def compile(self,spec,kind='paving',seed=41873):
        master,contract=a.author(spec,kind,seed)
        c=a.compile_master(master,{'pitch':spec['pitch_m']},max_candidate_cells=150000,max_output_cells=50000)
        mesh=a.make_render_data(c)
        a.validate_geometry(spec,c,mesh,contract)
        return master,c,mesh,contract

    def test_all_frozen_common_artifacts_and_reproducible_author(self):
        self.assertEqual(self.manifest['module_count'],12)
        for record in self.manifest['modules']:
            with self.subTest(module=record['id']):
                prefix=HERE/'generated'/record['id']
                for name,proof in record['files'].items():
                    content=(HERE/'generated'/name).read_bytes()
                    self.assertEqual(len(content),proof['bytes'])
                    self.assertEqual(hashlib.sha256(content).hexdigest(),proof['sha256'])
                master=json.loads(Path(str(prefix)+'.master.json').read_text())
                c=json.loads(gzip.decompress(Path(str(prefix)+'.compiled.json.gz').read_bytes()))
                mesh=json.loads(Path(str(prefix)+'.render.json').read_text())
                contract=json.loads(Path(str(prefix)+'.placement.json').read_text())
                self.assertEqual(a.author(self.rules,record['kind'],record['seed']),(master,contract))
                self.assertEqual(a.digest(master),record['master_hash'])
                self.assertEqual(a.digest(c['cells']),record['payload_hash'])
                self.assertEqual(a.digest(mesh),record['render_hash'])
                self.assertEqual(a.make_render_data(c),mesh)
                a.validate_geometry(self.rules,c,mesh,contract)

    def test_compiler_repeatability_and_rules_drive_geometry(self):
        spec=self.spec();before=copy.deepcopy(spec)
        m1,c1,r1,_=self.compile(spec,'rubble')
        m2,c2,r2,_=self.compile(spec,'rubble')
        self.assertEqual(m1,m2);self.assertEqual(c1,c2);self.assertEqual(r1,r2);self.assertEqual(spec,before)
        spec['geometry']['rubble']['stone_widths_m']=[.5]
        _,c3,r3,_=self.compile(spec,'rubble')
        self.assertNotEqual(c1['payload_hash'],c3['payload_hash'])
        self.assertNotEqual(r1['quad_count'],r3['quad_count'])

    def test_variants_are_distinct_bounded_and_small(self):
        for kind in a.KINDS:
            rows=[v for v in self.manifest['modules'] if v['kind']==kind]
            self.assertEqual(len({v['payload_hash'] for v in rows}),3)
            self.assertTrue(all(v['cells']<50000 and v['candidate_cells']<150000 and v['quads']<1000 for v in rows))
        self.assertLess(self.manifest['artifact_bytes'],20000000)

    def test_full_tile_edges_match_across_all_seed_variants(self):
        for kind in a.KINDS:
            profiles=[]
            for record in self.manifest['modules']:
                if record['kind'] != kind:continue
                c=json.loads(gzip.decompress((HERE/'generated'/(record['id']+'.compiled.json.gz')).read_bytes()))
                left={(v[1],v[2],v[5]) for v in c['cells'] if v[0]==0}
                right={(v[1],v[2],v[5]) for v in c['cells'] if v[0]==79}
                bottom={(v[0],v[2],v[5]) for v in c['cells'] if v[1]==0}
                top={(v[0],v[2],v[5]) for v in c['cells'] if v[1]==79}
                self.assertEqual(left,right);self.assertEqual(bottom,top)
                profiles.append((left,bottom))
            self.assertTrue(all(profile==profiles[0] for profile in profiles))

    def test_trim_and_holes_all_materials(self):
        spec=self.spec();spec['trim']={'width_m':.625,'height_m':.75,'offset_m':[.25,.125]}
        spec['holes']=[{'rect':[.125,.125,.375,.375]},{'rect':[.5,0,.625,.125]}]
        for kind in a.KINDS:
            with self.subTest(kind=kind):
                _,c,mesh,contract=self.compile(spec,kind)
                self.assertEqual(mesh['bounds']['max'][:2],[.625,.75])
                self.assertTrue(all(v['pass'] for v in c['constraints']))
                self.assertEqual(contract['trim']['offset_m'],[.25,.125])
                p=spec['pitch_m'];covered=set()
                for box in contract['collision']['reference_prisms']:
                    self.assertEqual(box['max'][2],0)
                    self.assertEqual(box['min'][2],-.1)
                    for x in range(round(box['min'][0]/p),round(box['max'][0]/p)):
                        for y in range(round(box['min'][1]/p),round(box['max'][1]/p)):
                            self.assertNotIn((x,y),covered);covered.add((x,y))
                visual_xy={tuple(row[:2]) for row in c['cells']}
                self.assertEqual(covered,visual_xy)
                expected=(.625*.75-.25*.25-.125*.125)/(p*p)
                self.assertEqual(len(covered),round(expected))

    def test_quarter_metre_edge_trim_grid_all_kinds(self):
        for width in (.25,.5,.75,1):
            for height in (.25,.5,.75,1):
                spec=self.spec();spec['trim']={'width_m':width,'height_m':height,'offset_m':[0,0]}
                for kind in a.KINDS:
                    with self.subTest(width=width,height=height,kind=kind):
                        _,_,mesh,_=self.compile(spec,kind)
                        self.assertEqual(mesh['bounds']['min'][:2],[0,0])
                        self.assertEqual(mesh['bounds']['max'][:2],[width,height])

    def test_visual_offset_covers_coarse_plane_with_correct_collision_error(self):
        maxima={'ashlar':.0625,'rubble':.0625,'planks':.05,'paving':.0375}
        for kind in a.KINDS:
            _,contract=a.author(self.rules,kind,41873)
            self.assertAlmostEqual(contract['visual_max_bounds']['min'][2]+.0375,0)
            self.assertAlmostEqual(contract['front_height_contract']['joint_top_z_m']+.0375,.0125)
            self.assertAlmostEqual(contract['visual_max_bounds']['max'][2]+.0375,maxima[kind])
        spec=self.spec()
        for kind in ('ashlar','rubble'):spec['geometry'][kind]['face_z_choices_m']=[0]
        spec['geometry']['planks']['nails']=False
        for kind in a.KINDS:
            _,_,mesh,_=self.compile(spec,kind)
            self.assertAlmostEqual(mesh['bounds']['max'][2]+.0375,.0375)

    def test_safe_catalog_recompiles_exactly_and_preserves_original(self):
        spec=json.loads((HERE/'inputs/safe_offset_rules.v1.json').read_text())
        manifest=json.loads((HERE/'generated_safe/manifest.json').read_text())
        self.assertEqual(manifest['module_count'],12)
        self.assertLess(manifest['artifact_bytes'],2000000)
        self.assertEqual(manifest['rules_hash'],a.digest(spec))
        edge_profiles={}
        for record in manifest['modules']:
            with self.subTest(module=record['id']):
                master,c,mesh,contract=self.compile(spec,record['kind'],record['seed'])
                self.assertEqual(a.digest(master),record['master_hash'])
                self.assertEqual(c['payload_hash'],record['payload_hash'])
                self.assertEqual(mesh,json.loads((HERE/'generated_safe'/(record['id']+'.render.json')).read_text()))
                self.assertEqual(contract,record['placement_contract'])
                self.assertAlmostEqual(mesh['bounds']['min'][2],-.0375,places=12)
                self.assertEqual(mesh['bounds']['max'][2],0)
                self.assertFalse(any(v[5]=='metal.iron' for v in c['cells']))
                for filename,proof in record['files'].items():
                    self.assertEqual(hashlib.sha256((HERE/'generated_safe'/filename).read_bytes()).hexdigest(),proof['sha256'])
                left={(v[1],v[2],v[5]) for v in c['cells'] if v[0]==0}
                right={(v[1],v[2],v[5]) for v in c['cells'] if v[0]==79}
                self.assertEqual(left,right)
                if record['kind'] in edge_profiles:self.assertEqual(left,edge_profiles[record['kind']])
                edge_profiles[record['kind']]=left
        self.assertEqual(len(list((HERE/'generated').glob('*.master.json'))),12)

    def test_exact_floor_height_and_collision_independence(self):
        _,c,mesh,contract=self.compile(self.rules)
        self.assertEqual(mesh['bounds']['max'][2],0)
        self.assertEqual(len(contract['collision']['reference_prisms']),1)
        self.assertFalse(contract['collision']['generate_from_render_mesh'])
        self.assertFalse(contract['collision']['create_module_colliders_automatically'])
        joint=[v for v in c['cells'] if v[4]=='joint']
        self.assertEqual(max(v[2]+1 for v in joint)*.0125,-.025)
        basis=contract['floor_basis_rows']
        self.assertTrue(a.validate_placement([-5,0,12],basis,grid_merge=True))
        self.assertEqual([sum(basis[i][j]*[0,0,1][j] for j in range(3)) for i in range(3)],[0,1,0])

    def test_optional_nails_are_real_occupancy(self):
        on=self.spec();off=self.spec();off['geometry']['planks']['nails']=False
        _,c1,mesh1,_=self.compile(on,'planks');_,c2,mesh2,_=self.compile(off,'planks')
        iron=[v for v in c1['cells'] if v[5]=='metal.iron']
        self.assertEqual(len(iron),40)
        self.assertFalse(any(v[5]=='metal.iron' for v in c2['cells']))
        self.assertEqual(mesh1['bounds']['max'][2],.0125);self.assertEqual(mesh2['bounds']['max'][2],0)

    def test_whole_piece_tones_and_muted_source_palette(self):
        house=json.loads((a.HERE.parents[1]/'source/house.r04.master.json').read_text())['materials']
        lane=json.loads((a.HERE.parents[1]/'lane/inputs/lane_rules.json').read_text())['materials']
        approved=set(house.values())|set(lane.values())
        self.assertTrue(set(self.rules['materials'].values())<=approved)
        for record in self.manifest['modules']:
            master=json.loads((HERE/'generated'/(record['id']+'.master.json')).read_text())
            by_stone={}
            for op in master['components'][0]['operations']:
                if op.get('part')=='stone':
                    stem=op['id'].rsplit('_',1)[0]
                    by_stone.setdefault(stem,set()).add(op['material'])
            self.assertTrue(all(len(colors)==1 for colors in by_stone.values()))

    def test_reject_negative_zero_nonfinite_and_unaligned_trim(self):
        for key,bad in [('width_m',-1),('height_m',0),('width_m',1.1),('width_m',.633),('height_m',float('inf'))]:
            spec=self.spec();spec['trim'][key]=bad
            with self.subTest(key=key,bad=bad),self.assertRaises(ValueError):a.author(spec,'ashlar',41873)
        for offset in ([-.0125,0],[.001,0],[.25,0]):
            spec=self.spec();spec['trim']['offset_m']=offset
            with self.subTest(offset=offset),self.assertRaises(ValueError):a.author(spec,'ashlar',41873)

    def test_reject_bad_hole_boundaries(self):
        for hole in ({'rect':[-.025,0,.1,.1]}, {'rect':[0,0,1.025,.1]}, {'rect':[0,0,0,.1]}, {'rect':[.01,.1,.2,.2]}, {'rect':[0,0,1,1]}, {'polygon':[[0,0],[.2,0],[0,.2]]}):
            spec=self.spec();spec['holes']=[hole]
            with self.subTest(hole=hole),self.assertRaises(ValueError):a.author(spec,'paving',41873)
        spec=self.spec();spec['holes']=[{'rect':[.1,.1,.3,.3]},{'rect':[.2,.2,.4,.4]}]
        with self.assertRaises(ValueError):a.author(spec,'paving',41873)

    def test_negative_world_positions_and_explicit_grid_alignment(self):
        identity=[[1,0,0],[0,1,0],[0,0,1]]
        self.assertTrue(a.validate_placement([-12.5,-2,3],identity,grid_merge=True))
        self.assertTrue(a.validate_placement([-12.501,0,3],identity,grid_merge=False))
        with self.assertRaises(ValueError):a.validate_placement([-12.501,0,3],identity,grid_merge=True)
        self.assertTrue(a.validate_placement([-12.501,0,3],identity,grid_origin=[-.001,0,0],grid_merge=True))
        with self.assertRaises(ValueError):a.validate_placement([0,0,0],[[-1,0,0],[0,1,0],[0,0,1]])
        with self.assertRaises(ValueError):a.validate_placement([0,0,0],[[2,0,0],[0,1,0],[0,0,1]])
        angle=.3;basis=[[math.cos(angle),0,math.sin(angle)],[0,1,0],[-math.sin(angle),0,math.cos(angle)]]
        self.assertTrue(a.validate_placement([-.1,2,3],basis))
        with self.assertRaises(ValueError):a.validate_placement([0,0,0],basis,grid_merge=True)

    def test_no_unapproved_fine_pitch_or_extrusion_budget(self):
        for field,bad in [('pitch_m',.025),('pitch_m',.001),('module_size_m',[100,100])]:
            spec=self.spec();spec[field]=bad
            with self.subTest(field=field,bad=bad),self.assertRaises(ValueError):a.author(spec,'ashlar',41873)
        spec=self.spec();spec['geometry']['rubble']['face_z_choices_m']=[.05]
        with self.assertRaises(ValueError):a.author(spec,'rubble',41873)
        spec=self.spec();spec['geometry']['paving']['face_z_choices_m']=[.0125]
        with self.assertRaises(ValueError):a.author(spec,'paving',41873)

    def test_original_dependency_hashes_unchanged(self):
        for name,sha in self.manifest['source_hashes'].items():
            self.assertEqual(hashlib.sha256((a.ROOT/name).read_bytes()).hexdigest(),sha)

if __name__=='__main__':
    unittest.main(verbosity=2)
