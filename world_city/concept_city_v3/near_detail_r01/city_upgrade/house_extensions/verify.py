"""Bounded common-compiler ROI checks; never compiles a whole house or city."""
from __future__ import annotations
import copy
import io
import itertools
import json
import math
from pathlib import Path
import resource
import unittest
import extend as e
from layered_compile import SpatialSource

a=e.a;HERE=e.HERE
PROBES=[]
FIXTURES={'legacy':'ordinary_d4fcb5b21ffb18','institutional':'ordinary_r2_2b48237662aa54','hip':'ordinary_r2_2fb8f88976f56a','hip_rotated':'ordinary_r2_7ad67ff920484e','attached':'attached_native_row_52be8b0278a352'}


def sample(master,component,lo,hi,operation_transform=None,label='probe',preserve_cut_polygon=False):
    inst=next(i for i in master['instances'] if i['component']==component['id'])
    reduced={k:copy.deepcopy(v) for k,v in master.items() if k not in ('components','instances','constraints','assembly_cuts')}
    reduced.update(components=[copy.deepcopy(component)],instances=[copy.deepcopy(inst)],constraints=[],assembly_cuts=[])
    local_to_world=a.core.compose(a.core.transform(inst.get('transform')),a.core.transform(operation_transform))
    pts=[a.core.apply(local_to_world,p) for p in itertools.product(*zip(lo,hi))]
    low=[min(p[j] for p in pts) for j in range(3)];high=[max(p[j] for p in pts) for j in range(3)]
    roi=SpatialSource(reduced,.05).crop(low,high)
    if preserve_cut_polygon:
        originals={o['id']:o for o in component['operations']}
        for output_component in roi['components']:
            for op in output_component['operations']:
                if op['action']=='cut' and op['shape']['kind']=='extrusion':op['shape']['polygon']=copy.deepcopy(originals[op['id']]['shape']['polygon'])
    compiled=a.core.compile_master(roi,{'pitch':.05},max_candidate_cells=50000,max_output_cells=10000)
    assert compiled['valid']
    PROBES.append({'label':label,'source_id':master['id'],'component':component['id'],'candidate_cells':compiled['candidate_cells'],'occupied_cells':len(compiled['cells']),'pitch_m':.05,'world_roi':[low,high],'preserved_cut_polygon':preserve_cut_polygon})
    return compiled,local_to_world


def locals_in(compiled,transform):
    origin=compiled.get('grid_origin',[0,0,0])
    return [(a.core.inverse(transform,[origin[j]+(row[j]+.5)*.05 for j in range(3)]),row) for row in compiled['cells']]


class ExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config,cls.rules,cls.selectors=e.configuration()
        cls.catalog=e.load(HERE/'generated/active_catalog.json')
        cls.records={r['asset_key']:r for r in cls.catalog['assets']}
        cls.examples={}
        for label,key in FIXTURES.items():
            r=cls.records[key];cls.examples[label]=(e.load(a.ROOT/r['source_master_path']),e.load(a.ROOT/r['emitted_master_path']))

    def test_every_active_extension_source_and_artifact_hash_and_preservation(self):
        self.assertEqual(self.catalog['summary']['supported_assets'],26)
        self.assertEqual(self.catalog['index_sha256'],a.sha(a.ROOT/self.catalog['index_path']))
        for r in self.catalog['assets']:
            with self.subTest(asset=r['asset_key']):
                self.assertEqual(r['source_sha256'],a.sha(a.ROOT/r['source_master_path']))
                self.assertEqual(r['emitted_master_sha256'],a.sha(a.ROOT/r['emitted_master_path']))
                old=e.load(a.ROOT/r['source_master_path']);new=e.load(a.ROOT/r['emitted_master_path'])
                self.assertTrue(all(e.preservation(old,new,self.selectors).values()))
                a.core.validate_master(new,.05)
                if old['metadata'].get('native_modules'):
                    self.assertEqual(len(e.verify_native_sources(old,self.config)),old['metadata']['source_unit_count'])
                    self.assertIn('connected',[c['kind'] for c in new['constraints']])

    def test_material_roof_lateral_joint_is_geometric_all_families(self):
        for label,(old,new) in self.examples.items():
            with self.subTest(label=label):
                oc=next(c for c in old['components'] if a.component_role(c,self.selectors)=='roof')
                c=next(c for c in new['components'] if c['id']==oc['id']);plane=a.selected(oc,'roof_plane',self.selectors)[0]
                x0,x1,y0,y1,_=a.roof_geometry(plane);n=math.ceil((x1-x0)/self.rules['roof']['tile_run_m']);course=n//2
                x=x0+(course+.5)*(x1-x0)/n;y=y0+(y1-y0)*(x-x0)/(x1-x0)
                width=self.rules['roof']['tile_width_m'];base=plane['shape']['z_min']-(width*.5 if course%2 else 0)
                z=base+round(((plane['shape']['z_min']+plane['shape']['z_max'])/2-base)/width)*width
                out,t=sample(new,c,[x-.026,y-.19,z-.07],[x+.026,y+.13,z+.07],plane.get('transform'),label+'_tile_joint')
                points=locals_in(out,t)
                self.assertTrue(any('__near_tile_' in row[6] for _,row in points))
                joints=[(p,row) for p,row in points if abs(p[2]-z)<self.rules['roof']['lateral_joint_m']/2-1e-7]
                self.assertTrue(joints)
                self.assertTrue(all('__near_tile_' not in row[6] for _,row in joints))
                self.assertTrue(all(p[1]<y0+(y1-y0)*(p[0]-x0)/(x1-x0)-.09 for p,_ in joints))

    def test_institutional_masonry_recess_retains_backing(self):
        old,new=self.examples['institutional']
        c=next(c for c in new['components'] if c['id']=='wall_0_back')
        panel=a.selected(c,'wall_panel',self.selectors)[0]
        self.assertEqual(panel['material'],'mortar')
        strips=[o for o in c['operations'] if '__near_masonry_skin__near__r' in o['id']]
        self.assertTrue(strips)
        # Choose an actual stone's center, away from timber/posts and windows.
        stone=next(o for o in strips if .45<o['shape']['min'][1]<.8 and -2.9<o['shape']['min'][0] and o['shape']['max'][0]<-2.5)
        lo,hi=stone['shape']['min'],stone['shape']['max'];x=(lo[0]+hi[0])/2;y=(lo[1]+hi[1])/2
        out,t=sample(new,c,[x-.03,y-.025,-.4],[x+.03,y+.025,.08],label='institutional_backing')
        points=locals_in(out,t)
        self.assertTrue(any(p[2]<-.15 and row[5]=='mortar' for p,row in points))
        self.assertTrue(any(p[2]>.02 and row[5].startswith('stone') for p,row in points))
        # The joint directly at this stone's right edge has empty exterior and
        # mortar behind it, rather than a different-colored coplanar face.
        joint=hi[0]+self.rules['masonry']['joint_m']/2
        out,t=sample(new,c,[joint-.025,y-.025,-.12],[joint+.025,y+.025,.08],label='institutional_joint')
        points=locals_in(out,t)
        self.assertTrue(any(row[5]=='mortar' for _,row in points))
        self.assertFalse(any(p[2]>.02 for p,_ in points))

    def test_window_depth_all_families(self):
        for label,(_,new) in self.examples.items():
            c=next(c for c in new['components'] if a.component_role(c,self.selectors)=='wall' and a.selected(c,'window_aperture',self.selectors))
            ap=a.selected(c,'window_aperture',self.selectors)[0];lo,hi=ap['shape']['min'],ap['shape']['max'];name=ap['id'].removesuffix('_aperture')
            frame=next(o for o in c['operations'] if o['id']==name+'_left')['shape'];bottom=next(o for o in c['operations'] if o['id']==name+'_sill')['shape']
            x=(frame['max'][0]+(lo[0]+hi[0])/2-self.rules['window']['mullion_width_m']/2)/2
            y=(bottom['max'][1]+(lo[1]+hi[1])/2-self.rules['window']['mullion_width_m']/2)/2
            out,t=sample(new,c,[x-.025,y-.025,-.25],[x+.025,y+.025,.1],label=label+'_window_recess')
            points=locals_in(out,t);self.assertTrue(any(row[5]=='glass' for _,row in points))
            self.assertTrue(all(p[2]<-.14 for p,_ in points))

    def test_timber_face_recess_is_empty_above_retained_timber(self):
        for label in ('institutional','attached'):
            _,new=self.examples[label]
            c=next(c for c in new['components'] if c['id'].endswith('_back') and any(o['id'].endswith('__near_timber_recess') for o in c['operations']))
            cut=next(o for o in c['operations'] if o['id'].endswith('__near_timber_recess'))
            lo,hi=cut['shape']['min'],cut['shape']['max'];x=(lo[0]+hi[0])/2;y=(lo[1]+hi[1])/2
            out,t=sample(new,c,[x-.025,y-.025,lo[2]-.08],[x+.025,y+.025,hi[2]+.02],label=label+'_timber_recess')
            points=locals_in(out,t)
            self.assertTrue(points)
            self.assertTrue(any(row[5].startswith('timber') for _,row in points))
            self.assertFalse(any(a.core.contains(cut['shape'],p,epsilon=1e-10) for p,_ in points))

    def test_hip_trim_clips_new_tiles_in_both_operation_frames(self):
        old,new=self.examples['hip']
        for oc in [c for c in old['components'] if a.component_role(c,self.selectors)=='roof']:
            c=next(c for c in new['components'] if c['id']==oc['id']);plane=a.selected(oc,'roof_plane',self.selectors)[0]
            x0,x1,y0,y1,_=a.roof_geometry(plane);x=(x0+x1)/2;y=(y0+y1)/2
            if plane.get('transform'):
                # End plane's side boundary narrows to half the long run.
                z=(plane['shape']['z_max']-plane['shape']['z_min'])/4
            else:
                z=plane['shape']['z_min']+(x1-x0)/2
            lo=[x-.05,y-.25,z-.35];hi=[x+.05,y+.25,z+.35]
            out,t=sample(new,c,lo,hi,plane.get('transform'),c['id']+'_clipped',preserve_cut_polygon=True)
            unclipped=copy.deepcopy(c);unclipped['operations']=[o for o in c['operations'] if o['action']!='cut']
            before,_=sample(new,unclipped,lo,hi,plane.get('transform'),c['id']+'_unclipped_test_baseline')
            self.assertTrue(out['cells']);self.assertLess(len(out['cells']),len(before['cells']))
            inst=next(i for i in new['instances'] if i['component']==c['id']);instance_t=a.core.transform(inst['transform'])
            cuts=[o for o in oc['operations'] if o['action']=='cut']
            for row in out['cells']:
                world=[(row[j]+.5)*.05 for j in range(3)]
                self.assertFalse(any(a.core.contains(o['shape'],a.core.inverse(a.core.compose(instance_t,a.core.transform(o.get('transform'))),world),epsilon=.05*a.core.EPS) for o in cuts))

    def test_actual_ridge_caps_above_source_peak(self):
        for label in ('legacy','hip','attached'):
            old,new=self.examples[label]
            c=next(c for c in new['components'] if any('__near_ridge_cap_' in o['id'] for o in c['operations']))
            cap=next(o for o in c['operations'] if '__near_ridge_cap_' in o['id']);s=cap['shape'];x=(min(p[0] for p in s['polygon'])+max(p[0] for p in s['polygon']))/2
            y=max(p[1] for p in s['polygon']);z=(s['z_min']+s['z_max'])/2
            out,t=sample(new,c,[x-.06,y-.15,z-.04],[x+.06,y+.025,z+.04],cap.get('transform'),label+'_ridge_cap')
            self.assertTrue(any('__near_ridge_cap_' in row[6] for row in out['cells']))
            self.assertTrue(any(p[1]>y-self.config['ridge']['cap_rise_m'] for p,_ in locals_in(out,t)))

    def test_rule_changes_execute_and_output_is_deterministic(self):
        source=self.examples['legacy'][0]
        first,_,report=e.author(source)
        second,_,_=e.author(source)
        self.assertEqual(a.core.digest(first),a.core.digest(second))
        rules=copy.deepcopy(self.rules);rules['roof']['tile_width_m']=.47
        changed,_,changed_report=e.author(source,self.config,rules,self.selectors)
        self.assertNotEqual(report['counts']['roof_tiles'],changed_report['counts']['roof_tiles'])
        self.assertNotEqual(a.core.digest(first),a.core.digest(changed))
        config=copy.deepcopy(self.config);config['timber']['groove_depth_m']=.08
        changed,_,_=e.author(source,config,self.rules,self.selectors)
        old_cuts=[o for c in first['components'] for o in c['operations'] if o['id'].endswith('__near_timber_recess')]
        new_cuts=[o for c in changed['components'] for o in c['operations'] if o['id'].endswith('__near_timber_recess')]
        self.assertEqual(len(old_cuts),len(new_cuts));self.assertNotEqual(old_cuts,new_cuts)

    def test_contract_rejects_reordered_trim_and_tampered_native_source(self):
        source=copy.deepcopy(self.examples['hip'][0]);roof=next(c for c in source['components'] if a.component_role(c,self.selectors)=='roof')
        roof['operations']=roof['operations'][-1:]+roof['operations'][:-1]
        with self.assertRaises(a.UnsupportedSurface) as found:e.author(source)
        self.assertEqual(found.exception.report['reason'],'hip_trim_order_contract')
        source=copy.deepcopy(self.examples['hip'][0]);roof=next(c for c in source['components'] if a.component_role(c,self.selectors)=='roof')
        cut=next(o for o in roof['operations'] if o['action']=='cut');q=math.sqrt(.5)
        cut['transform']={'basis':[[q,0,-q],[0,1,0],[q,0,q]]}
        with self.assertRaises(a.UnsupportedSurface) as found:e.author(source)
        self.assertEqual(found.exception.report['reason'],'roof_operation_transform_contract')
        source=copy.deepcopy(self.examples['attached'][0]);source['components'][0]['operations'][0]['shape']['max'][0]+=.1
        with self.assertRaises(a.UnsupportedSurface) as found:e.author(source)
        self.assertEqual(found.exception.report['reason'],'native_component_equivalence_failed')


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ExtensionTests);stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    report={'schema':'riverstone.house_detail.extension_tests.v1','pass':result.wasSuccessful(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'extension_engine_sha256':a.sha(e.__file__),'compiler_sha256':a.sha(a.core.__file__),'config_sha256':a.sha(HERE/'extensions.v1.json'),
            'bounded_probes':PROBES,'max_candidate_cells':max((r['candidate_cells'] for r in PROBES),default=0),'full_master_compiles':0,
            'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'limitations':['ROI probes intentionally clear global constraints; full connected foundations are preserved for layered compiler validation.','No final city or visual approval.']}
    a.write(HERE/'generated/tests.report.json',report);(HERE/'generated/tests.log').write_text(stream.getvalue());print(stream.getvalue());print(json.dumps({k:v for k,v in report.items() if k!='bounded_probes'},indent=2));raise SystemExit(0 if result.wasSuccessful() else 1)
