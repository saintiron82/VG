from pathlib import Path
import copy,json,os,sys,tempfile,unittest
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/'tools'))
from presets import read,make_preset,cohort,geometry_combinations,geometry_signature,appearance_module,digest,generate,report,validate_rules,CONTRACT_PATH,RULES_PATH
from compatibility import validate_derived

class PresetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared=appearance_module();cls.base=cls.shared.load_sources();cls.contract=read(CONTRACT_PATH);cls.rules=read(RULES_PATH)

    def test_01_repeat_exact(self):
        self.assertEqual(make_preset('41029','stable_person'),make_preset('41029','stable_person'))

    def test_02_append_and_order_do_not_change_people(self):
        small=cohort(7,['a','b']);large=cohort(7,['b','c','a'])
        self.assertEqual({p['id']:p for p in small},{p['id']:p for p in large if p['id'] in ['a','b']})

    def test_03_seed_changes_appearance(self):
        a,b=make_preset(1,'same_id'),make_preset(2,'same_id')
        self.assertNotEqual(a['palette'],b['palette']);self.assertEqual(a['id'],b['id'])

    def test_04_100_data_records_cover_choices(self):
        people=cohort('41029',[f'person_{i:04}' for i in range(100)]);result=report(people)
        self.assertEqual(result['unique_full_appearances'],100)
        for key,rule in [('body_frame','body_frames'),('face','faces'),('hair_style','hair_styles'),('outfit','outfits')]:
            self.assertEqual(set(result['coverage'][key]),set(self.rules[rule]))
        for key in result['palette_coverage']:self.assertEqual(set(result['palette_coverage'][key]),set(self.rules[key]))
        for p in people:
            self.assertEqual(set(p['palette']),set(self.contract['palette_slots']));self.shared.validate_preset(p)

    def test_05_no_behavior_or_demographic_assignment(self):
        p=make_preset(1,'person')
        self.assertFalse({'role','job','class','gender','schedule','dialogue','shop','household'}&set(p))

    def test_06_all_216_geometry_combinations_and_clips(self):
        matrix=list(geometry_combinations());self.assertEqual(len(matrix),216)
        self.assertEqual(len({geometry_signature(p) for p in matrix}),216)
        for p in matrix:
            with self.subTest(id=p['id']):
                sources=self.shared.derive_sources(p,self.base)
                result=validate_derived(p,sources,self.base)
                self.assertEqual(result['status'],'pass');self.assertGreaterEqual(result['parts'],25)

    def test_07_derivation_never_mutates_canonical(self):
        before=copy.deepcopy(self.base)
        self.shared.derive_sources(make_preset(2,'person'),self.base)
        self.assertEqual(self.base,before)

    def test_08_palette_only_reuses_geometry_and_motion(self):
        a=make_preset(4,'person');b=copy.deepcopy(a);b['palette']['teal_wool']='ff0000'
        x,y=self.shared.derive_sources(a),self.shared.derive_sources(b)
        for key in ['components','instances','constraints']:self.assertEqual(x['master.json'][key],y['master.json'][key])
        self.assertEqual(x['rig.json']['parts'],y['rig.json']['parts'])
        self.assertEqual(x['walk.json']['tracks'],y['walk.json']['tracks'])
        self.assertNotEqual(x['master.json']['materials'],y['master.json']['materials'])

    def test_09_negative_presets_fail_closed(self):
        original=make_preset(1,'person')
        bad=[{'body_frame':'child'},{'face':'unsupported'},{'outfit':'plate_armour'},{'hair_style':'bald'},
             {'palette':{'skin':'pink'}},{'palette':{'unrecognized':'ffffff'}},{'accessories':{'cape':1}},
             {'accessories':{'wings':True}},{'family':'another_rig'},{'schema':'unknown'},{'id':'../escape'}]
        for patch in bad:
            with self.subTest(patch=patch),self.assertRaises(ValueError):self.shared.validate_preset({**original,**patch})

    def test_10_invalid_ids_and_duplicates_rejected(self):
        for id in ['../escape','','PERSON','a/b','a'*65]:
            with self.assertRaises(ValueError):make_preset(1,id)
        with self.assertRaises(ValueError):cohort(1,['same','same'])

    def test_11_corrupt_rig_and_socket_rejected(self):
        p=make_preset(9,'person');good=self.shared.derive_sources(p)
        for change in ['socket','cycle','pivot','channel']:
            x=copy.deepcopy(good)
            if change=='socket':x['rig.json']['sockets']['head_look']['part']='missing'
            if change=='cycle':x['rig.json']['parts'][0]['parent']='head'
            if change=='pivot':x['rig.json']['parts'][0]['pivot_m'][0]+=1
            if change=='channel':x['rig.json']['motion_channels']['blink'].append('head')
            with self.subTest(change=change),self.assertRaises(ValueError):validate_derived(p,x,self.base)

    def test_12_stale_sidecars_and_removed_target_rejected(self):
        p=make_preset(9,'person');good=self.shared.derive_sources(p)
        x=copy.deepcopy(good);x['walk.json']['master_hash']='0'*64
        with self.assertRaises(ValueError):validate_derived(p,x,self.base)
        x=copy.deepcopy(good);x['walk.json']['tracks'][0]['selector']['part']='missing'
        with self.assertRaises(ValueError):validate_derived(p,x,self.base)

    def test_13_source_contract_drift_rejected(self):
        rules=copy.deepcopy(self.rules);rules['body_frames'].append('child')
        with self.assertRaises(ValueError):validate_rules(rules,self.contract)

    def test_14_palette_shade_order(self):
        luma=lambda h:sum(v*int(h[i:i+2],16) for i,v in [(0,.2126),(2,.7152),(4,.0722)])
        for p in cohort(1,[f'p_{i}' for i in range(100)]):
            c=p['palette']
            for low,base,high in [('skin_shadow','skin','skin_light'),('silver_shadow','silver','silver_light'),('teal_shadow','teal_wool','teal_light'),('leather_dark','leather','leather_light')]:
                self.assertLess(luma(c[low]),luma(c[base]));self.assertLess(luma(c[base]),luma(c[high]))

    def test_15_new_output_only_and_deterministic_files(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a',Path(d)/'b';generate(a,41029,6);generate(b,41029,6)
            self.assertEqual({p.name:p.read_bytes() for p in a.iterdir()},{p.name:p.read_bytes() for p in b.iterdir()})
            with self.assertRaises(FileExistsError):generate(a,41029,6)

    def test_16_relative_collection_path_verifies(self):
        from verify import verify
        with tempfile.TemporaryDirectory() as d:
            collection=Path(d)/'collection';generate(collection,41029,2)
            # Public API accepts a relative input path even outside this package.
            relative=Path(os.path.relpath(collection,Path.cwd()))
            output=Path(d)/'verification.json'
            # External collections retain their absolute location in the audit.
            result=verify(relative,output,False)
            self.assertEqual(result['source_matrix_passed'],216)
            self.assertEqual(result['review_common_compilations'],[])

    def test_17_changed_collection_is_rejected(self):
        from verify import verify
        with tempfile.TemporaryDirectory() as d:
            collection=Path(d)/'collection';generate(collection,41029,2)
            (collection/'review_00.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'Artifact drift'):
                verify(collection,Path(d)/'verification.json',False)

if __name__=='__main__':unittest.main(verbosity=2)
