"""Small .05m compiler probes only: never compile a full house."""
import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import adapter as a
from voxel_character.common import core
MASTERS = a.ROOT/'world_city/runtime_city/generated/r2/masters'
PROBE_AUDIT = []
PRESETS = a.load(HERE/'presets.v1.json')
FIXTURES = {label:value['asset_key'] for label,value in PRESETS['verification_fixtures'].items()}


def clip_polygon(poly,axis,bound,keep_greater):
    out=[]
    for i,p in enumerate(poly):
        q=poly[i-1]
        pin=p[axis]>=bound if keep_greater else p[axis]<=bound
        qin=q[axis]>=bound if keep_greater else q[axis]<=bound
        if pin != qin:
            ratio=(bound-q[axis])/(p[axis]-q[axis])
            out.append([q[j]+ratio*(p[j]-q[j]) for j in range(2)])
        if pin:out.append(p)
    return out


def crop(op,lo,hi):
    op=copy.deepcopy(op)
    s=op['shape']
    if s['kind']=='box':
        s['min']=[max(v,b) for v,b in zip(s['min'],lo)]
        s['max']=[min(v,b) for v,b in zip(s['max'],hi)]
        return op if all(x<y-1e-10 for x,y in zip(s['min'],s['max'])) else None
    if s['kind']=='extrusion':
        s['z_min']=max(s['z_min'],lo[2]);s['z_max']=min(s['z_max'],hi[2])
        poly=s['polygon']
        for axis in (0,1):
            poly=clip_polygon(poly,axis,lo[axis],True)
            poly=clip_polygon(poly,axis,hi[axis],False)
        s['polygon']=poly
        return op if len(poly)>=3 and s['z_min']<s['z_max']-1e-10 else None
    raise AssertionError('Probe helper only accepts existing box/extrusion geometry')


def sample(master,component,lo,hi):
    """Geometric ROI clipping, then the unchanged production common compiler."""
    reduced={k:copy.deepcopy(v) for k,v in master.items() if k not in ('components','instances','constraints','assembly_cuts')}
    component=copy.deepcopy(component)
    component['operations']=[q for op in component['operations'] if (q:=crop(op,lo,hi))]
    reduced['components']=[component]
    inst=next(i for i in master['instances'] if i['component']==component['id'])
    reduced['instances']=[copy.deepcopy(inst)]
    if inst.get('parent'):raise AssertionError('Parented sample requires explicit ROI world resolution')
    reduced['constraints']=[];reduced['assembly_cuts']=[]
    compiled=core.compile_master(reduced,{'pitch':.05},max_candidate_cells=25000,max_output_cells=10000)
    assert compiled['valid']
    PROBE_AUDIT.append({'source_id':master['id'],'component':component['id'],'candidate_cells':compiled['candidate_cells'],'occupied_cells':len(compiled['cells']),'pitch_m':.05})
    return compiled


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules=a.load(HERE/PRESETS['rules'])
        cls.selectors=a.load(HERE/PRESETS['selectors'])
        cls.results={}
        cls.frozen_sha=a.sha(HERE.parents[1]/'source/house.r04.master.json')
        cls.source_sha={key:a.sha(MASTERS/(key+'.json')) for key in FIXTURES.values()}
        for label,key in FIXTURES.items():
            source=a.load(MASTERS/(key+'.json'))
            cls.results[label]=(source,*a.author(source,cls.rules,cls.selectors))

    def test_dimensions_instances_all_original_apertures_and_thresholds_preserved(self):
        for label,(source,out,provenance,report) in self.results.items():
            with self.subTest(label=label):
                for key,value in PRESETS['verification_fixtures'][label]['expected'].items():
                    self.assertEqual(source['metadata'][key],value)
                self.assertTrue(all(report['preservation']['checks'].values()))
                self.assertEqual(source['instances'],out['instances'])
                for key in ('body_bounds','entrance','width_m','depth_m','floors','row_units'):
                    self.assertEqual(source['metadata'][key],out['metadata'][key])
                self.assertEqual(report['counts']['door_leaves'],source['metadata']['row_units'])
                self.assertEqual(provenance['new_steps'],0)
                self.assertEqual(provenance['new_corbels'],0)
                for old,new in zip(source['components'],out['components']):
                    self.assertEqual([q for q in old['operations'] if q['action']=='cut'],
                                     [q for q in new['operations'] if q['action']=='cut' and '__near' not in q['id']])
                    for op in a.selected(old,'threshold',self.selectors):
                        self.assertEqual(op,next(q for q in new['operations'] if q['id']==op['id']))

    def test_roof_bounds_overlap_lips_and_final_course_geometry(self):
        for label,(source,out,_,report) in self.results.items():
            with self.subTest(label=label):
                self.assertTrue(report['preservation']['checks']['roof_horizontal_bounds_preserved'])
                for old in source['components']:
                    if a.component_role(old,self.selectors)!='roof':continue
                    new=next(c for c in out['components'] if c['id']==old['id'])
                    for plane in a.selected(old,'roof_plane',self.selectors):
                        x0,x1,y0,y1,_=a.roof_geometry(plane)
                        tiles=[o for o in new['operations'] if o['id'].startswith(plane['id']+'__near_tile_')]
                        self.assertGreater(len(tiles),1)
                        last=max(int(o['id'].split('_')[-2]) for o in tiles)
                        self.assertTrue(any(f'_tile_{last}_' in o['id'] for o in tiles))
                        expected_delta=self.rules['roof']['lip_height_m']
                        self.assertAlmostEqual(max(y-(y0+(y1-y0)*(x-x0)/(x1-x0)) for t in tiles for x,y in t['shape']['polygon']),expected_delta)
                        first=[o for o in tiles if '_tile_0_' in o['id']][0]
                        second=[o for o in tiles if '_tile_1_' in o['id']][0]
                        a0,b0=min(p[0] for p in first['shape']['polygon']),max(p[0] for p in first['shape']['polygon'])
                        a1,b1=min(p[0] for p in second['shape']['polygon']),max(p[0] for p in second['shape']['polygon'])
                        self.assertGreater(min(b0,b1)-max(a0,a1),0)

    def test_last_foundation_course_joint_survives_005m(self):
        for label,(_,out,_,_) in self.results.items():
            with self.subTest(label=label):
                c=next(c for c in out['components'] if a.component_role(c,self.selectors)=='foundation')
                body=a.selected(c,'foundation_body',self.selectors)[0]['shape']
                lo,hi=body['min'],body['max']
                n=math.ceil((hi[1]-lo[1])/self.rules['masonry']['course_height_m'])
                row=n-1;y=lo[1]+(row+.5)*(hi[1]-lo[1])/n
                offset=self.rules['masonry']['nominal_width_m']*.5 if row%2 else 0
                x=lo[0]-offset+3*self.rules['masonry']['nominal_width_m']
                compiled=sample(out,c,[x-.12,y-.04,lo[2]],[x+.12,y+.04,lo[2]+.125])
                cells=compiled['cells']
                # At the exterior voxel layer the vertical mortar gap is genuinely
                # empty; stone on both sides and recessed mortar behind survive.
                surface_z=math.floor(lo[2]/.05)
                exterior=[v for v in cells if v[2]==surface_z]
                self.assertTrue(any(f'__r{row}_' in v[6] for v in exterior))
                self.assertTrue(any(v[5]=='mortar' for v in cells))
                ix=math.floor(x/.05)
                self.assertFalse(any(v[0] in (ix-1,ix) for v in exterior))
                self.assertLess(compiled['candidate_cells'],25000)

    def test_roof_lateral_joint_is_real_at_005m(self):
        for label,(source,out,_,_) in self.results.items():
            with self.subTest(label=label):
                old=next(c for c in source['components'] if a.component_role(c,self.selectors)=='roof')
                c=next(c for c in out['components'] if c['id']==old['id'])
                plane=a.selected(old,'roof_plane',self.selectors)[0]
                x0,x1,y0,y1,_=a.roof_geometry(plane)
                n=math.ceil((x1-x0)/self.rules['roof']['tile_run_m'])
                x=x0+(x1-x0)/n/2
                y=y0+(y1-y0)*(x-x0)/(x1-x0)
                z=plane['shape']['z_min']+3*self.rules['roof']['tile_width_m']
                compiled=sample(out,c,[x-.026,y-.2,z-.12],[x+.026,y+.12,z+.12])
                placement=core.transform(next(i for i in out['instances'] if i['component']==c['id'])['transform'])
                tile_points=[];joint_points=[]
                for cell in compiled['cells']:
                    local=core.inverse(placement,[(cell[j]+.5)*.05 for j in range(3)])
                    if '__near_tile_' in cell[6]:tile_points.append(local)
                    if abs(local[2]-z)<self.rules['roof']['lateral_joint_m']/2-1e-7:joint_points.append((local,cell))
                self.assertTrue(tile_points)
                self.assertTrue(joint_points)
                self.assertTrue(all('__near_tile_' not in cell[6] for _,cell in joint_points))
                self.assertTrue(all(local[1]<y0+(y1-y0)*(local[0]-x0)/(x1-x0)-.09 for local,_ in joint_points))

    def test_window_glass_recess_and_aperture_void_sample(self):
        for label,(_,out,_,_) in self.results.items():
            with self.subTest(label=label):
                c=next(c for c in out['components'] if a.component_role(c,self.selectors)=='wall' and a.selected(c,'window_aperture',self.selectors))
                ap=a.selected(c,'window_aperture',self.selectors)[0]
                lo,hi=ap['shape']['min'],ap['shape']['max']
                # Interior quadrant safely beyond the original .22m frame.
                xm,ym=(lo[0]+hi[0])/2,(lo[1]+hi[1])/2
                name=ap['id'].removesuffix('_aperture')
                left=next(o for o in c['operations'] if o['id']==name+'_left')['shape']
                bottom=next(o for o in c['operations'] if o['id']==name+'_sill')['shape']
                x=(left['max'][0]+xm-self.rules['window']['mullion_width_m']/2)/2
                y=(bottom['max'][1]+ym-self.rules['window']['mullion_width_m']/2)/2
                compiled=sample(out,c,[x-.025,y-.025,-.25],[x+.025,y+.025,.10])
                glass=[v for v in compiled['cells'] if v[5]=='glass']
                self.assertTrue(glass)
                placement=core.transform(next(i for i in out['instances'] if i['component']==c['id'])['transform'])
                for v in compiled['cells']:
                    local=core.inverse(placement,[(v[j]+.5)*.05 for j in range(3)])
                    self.assertLess(local[2],-.14)

    def test_json_rules_are_executed_and_seed_is_deterministic(self):
        source=self.results['approved_reference'][0]
        out1,p1,_=a.author(source,self.rules,self.selectors)
        out2,p2,_=a.author(source,self.rules,self.selectors)
        self.assertEqual(core.digest(out1),core.digest(out2))
        rules=copy.deepcopy(self.rules);rules['roof']['tile_width_m']=.51
        changed,p3,_=a.author(source,rules,self.selectors)
        self.assertNotEqual(p1['counts']['roof_tiles'],p3['counts']['roof_tiles'])
        rules=copy.deepcopy(self.rules);rules['seed']+=1
        reseeded,_,_=a.author(source,rules,self.selectors)
        self.assertNotEqual(core.digest(out1),core.digest(reseeded))

    def test_semantic_selectors_not_component_or_operation_hardcoding(self):
        source=copy.deepcopy(self.results['approved_reference'][0])
        selectors=copy.deepcopy(self.selectors)
        for c in source['components']:
            if a.component_role(c,selectors)=='roof':
                previous=c['id'];c['id']='custom_'+previous
                for i in source['instances']:
                    if i['component']==previous:i['component']=c['id']
                for op in c['operations']:
                    if op['id'].startswith('roof_plane_'):op['id']=op['id'].replace('roof_plane_','sloped_skin_')
        selectors['surfaces']['roof_plane']['id_regex']='^sloped_skin_[0-9]+$'
        _,_,report=a.author(source,self.rules,selectors)
        self.assertEqual(report['counts']['roof_tiles'],self.results['approved_reference'][3]['counts']['roof_tiles'])

    def test_all_declared_roof_forms_use_original_rigid_transforms(self):
        from world_city.runtime_city.archetypes.ordinary_r2 import make_master
        for form in self.selectors['support']['roof_form']:
            with self.subTest(form=form):
                source=make_master({'asset_id':'synthetic_contract_'+form,'width_m':6,'depth_m':8,'floors':2,
                    'floor_height_m':2.8,'style':'old_timber','roof_form':form,'roof_pitch_degrees':42,
                    'assembly_class':'regular_house','construction_era':'rebuilt'})
                out,_,report=a.author(source,self.rules,self.selectors)
                self.assertEqual(out['instances'],source['instances'])
                self.assertTrue(report['preservation']['checks']['roof_horizontal_bounds_preserved'])
                self.assertGreater(report['counts']['roof_tiles'],0)

    def test_unsupported_roof_style_and_shape_rejected_without_fallback(self):
        base=self.results['approved_reference'][0]
        for key,value in [('roof_form','hip'),('roof_form','flat'),('style','institutional'),('style','invented_style')]:
            source=copy.deepcopy(base);source['metadata'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(a.UnsupportedSurface) as context:
                a.author(source,self.rules,self.selectors)
            self.assertEqual(context.exception.report['status'],'coverage_pending')
            self.assertFalse(context.exception.report['silent_fallback'])
        source=copy.deepcopy(base)
        c=next(c for c in source['components'] if a.component_role(c,self.selectors)=='roof')
        c['operations'][0]['shape']['polygon'].append([-1,7])
        with self.assertRaises(a.UnsupportedSurface):a.author(source,self.rules,self.selectors)

    def test_source_and_approved_r04_immutable(self):
        for source,_,p,_ in self.results.values():
            self.assertEqual(core.digest(source),p['source_canonical_sha256'])
        master=HERE.parents[1]/'source/house.r04.master.json'
        self.assertEqual(self.frozen_sha,a.sha(master))
        self.assertTrue(all(a.sha(MASTERS/(key+'.json'))==digest for key,digest in self.source_sha.items()))


if __name__=='__main__':
    unittest.main(verbosity=2)
