"""Dimension-authored landmark replacements for the v3 concept plan.

Composition only: existing standard source factories and rigid transforms are
reused. All sampling/meshing remains in unchanged common modules. Small staged
facilities retain their independently compiled 0.2 m sources. No city build.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from voxel_character.common import coordinate_planes, core, render_data
from world_city.runtime_city.landmarks.author import make_master as landmark
from world_city.runtime_city.archetypes.ordinary_r2 import make_master as ordinary
from world_city.runtime_city.infrastructure.author import make_master as infrastructure
from world_city.runtime_city.urban_fabric.author import make_master as fabric
from world_city.runtime_city.parts.author import Source, make_master as staged, extrusion

AUTHOR = 'world_city/concept_city_v3/assemblies/landmarks/author.py'
CONCEPT = 'world_city/reference/revision_03/city_social_water_concept.png'
PROMPT = 'world_city/reference/revision_03/prompt.txt'
ROOFS = json.loads((ROOT/'world_city/runtime_city/revisions/r2/city_history.r2.candidate.json').read_text())['roof_material_families']
CANDIDATE_CAP = 2_000_000
OUTPUT_CAP = 600_000


def ref(path):
    return {'path':str(path),'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest()}


def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')


def placement(position=(0,0,0), yaw=0):
    angle=math.radians(yaw); c,s=math.cos(angle),math.sin(angle)
    return {'translation':list(position),'basis':[[c,0,s],[0,1,0],[-s,0,c]]}


def source_bounds(master):
    numeric,_=coordinate_planes.resolve_master(master,{'pitch':.01})
    components={c['id']:c for c in numeric['components']}
    instances={i['id']:i for i in numeric['instances']}; resolved={}
    def pose(key):
        if key not in resolved:
            i=instances[key]; p=core.transform(i.get('transform'))
            resolved[key]=core.compose(pose(i['parent']),p) if i.get('parent') else p
        return resolved[key]
    vertices=[]
    for key,i in instances.items():
        for operation in components[i['component']]['operations']:
            if operation['action']!='paint':continue
            lo,hi=core.shape_bounds(core.prepare_shape(operation['shape'],.01))
            t=core.compose(pose(key),core.transform(operation.get('transform')))
            vertices.extend(core.apply(t,p) for p in itertools.product(*zip(lo,hi)))
    return {'min':[min(v[j] for v in vertices) for j in range(3)],
            'max':[max(v[j] for v in vertices) for j in range(3)]}


def lm(kind,w,d,h):
    return landmark({'asset_id':f'v3_{kind}_{w}_{d}_{h}','kind':kind,'width_m':w,'depth_m':d,'height_m':h})


def stable(w=24,d=12):
    return ordinary({'asset_id':f'v3_stable_{w}_{d}','assembly_class':'stable','style':'port',
                     'width_m':w,'depth_m':d,'floors':1,'floor_height_m':2.65,
                     'roof_form':'gable','roof_pitch_degrees':32,'construction_era':'early'})


def floor_master(w,d):
    # A bounded source surface, not a terrain generator or sampled mesh.
    a=Source('v3_floor',[-w/2,-.5,-d/2],[w/2,0,d/2])
    a.box('bearing_paving',[-w/2,-.5,-d/2],[w/2,0,d/2],'stone_dark')
    value=a.finish();value['id']=f'v3_paving_{w}_{d}'
    value['provenance']['adaptation_author']=ref(AUTHOR)
    return value


def flying_buttress():
    """Authored 12 m span / 20.4 m wall bearing, not a scaled mesh.

    Reuses the staged source grammar, with explicit longer arch and taller pier.
    Its wall end meets the 58 m cathedral's nave above the lower aisle roof.
    """
    a=Source('v3_upper_flying_buttress',[-6,0,-.65],[6,22,.65])
    a.box('footing',[4.7,0,-.65],[6,.4,.65],'stone_dark',component='pier')
    a.box('pier',[4.9,.4,-.5],[5.8,20.4,.5],'stone',component='pier')
    a.box('cap',[4.8,20.4,-.6],[5.9,20.8,.6],'stone_light',component='pier')
    a.box('finial',[5.1,20.8,-.35],[5.6,22,.35],'stone_light',component='pier')
    a.op('flying_arch',extrusion([[-6,20],[-3,19],[0,18.55],[5.1,18.4],
                                [5.1,19.05],[0,19.3],[-3,19.8],[-6,20.8]],-.35,.35),
         'stone_light',component='arch')
    a.socket('nave_wall',[-6,20.4,0],'nave_wall_bearing',(-1,0,0))
    a.socket('pier_foot',[5.35,0,0],'terrace_foundation')
    a.support('pier',[4.7,0,-.65],[6,.1,.65],'Level cathedral terrace.')
    a.support('nave',[-6,20,-.35],[-5.9,20.8,.35],'Cathedral nave wall X=±7.52 m, below clerestory.')
    a.clearance('under_arch',[-5.5,.1,-.3],[4.5,18.2,.3],'Aisle roof may occupy this volume in assembly.',False)
    a.constraints += [{'id':'arch_pier_contact','kind':'touch','a':{'component':'arch'},'b':{'component':'pier'}}]
    value=a.finish();value['id']='v3_cathedral_upper_flying_buttress'
    value['provenance']['adaptation_author']=ref(AUTHOR)
    value['provenance']['adaptation']='Explicit 12 m arch span, 20.4 m wall-bearing elevation, 22 m finial; no uniform object scaling.'
    return value


def dock_bent():
    a=Source('v3_dock_bent',[-3.5,-6.5,-.4],[3.5,-.5,.4])
    for x in (-3,3):a.box('pile_'+str(x),[x-.25,-6.5,-.25],[x+.25,-.5,.25],'timber_dark')
    a.box('crossbeam',[-3.5,-1,-.4],[3.5,-.5,.4],'timber')
    a.socket('deck',[0,-.5,0],'dock_underside')
    a.support('pile_tips',[-3.25,-6.5,-.25],[3.25,-6.4,.25],'World pile tips at −4.3 m embed below the current v3 river bed for all three placements; geotechnical bearing remains unverified.')
    value=a.finish();value['id']='v3_timber_dock_bent'
    value['provenance']['adaptation_author']=ref(AUTHOR)
    return value


def support_fill(name,lo,hi):
    a=Source(name,lo,hi);a.box('foundation_fill',lo,hi,'stone_dark')
    value=a.finish();value['id']=name;value['provenance']['adaptation_author']=ref(AUTHOR)
    return value


def quay_at_dock():
    value=copy.deepcopy(staged('quay_retaining_segment'))
    value['id']='v3_quay_dock_join'
    value['components']=[c for c in value['components'] if c['id']!='mooring']
    value['instances']=[i for i in value['instances'] if i['component']!='mooring']
    value['constraints']=[c for c in value['constraints'] if c['id']!='mooring_present']
    value['extensions']['sockets']=[v for v in value['extensions']['sockets'] if not v['id'].startswith('mooring_')]
    value['provenance']['adaptation_author']=ref(AUTHOR)
    value['provenance']['source_adaptations']=['Omit mooring posts from two central quay segments to preserve the 6 m dock access lane. Neighboring segments retain moorings.']
    return value


class Assembly:
    """Namespace and place common source data; never sample or alter output cells."""
    def __init__(self,name,anchor,height,reservation):
        self.name=name;self.anchor=anchor;self.height=height;self.reservation=reservation
        self.master={'schema':core.SCHEMA,'id':'concept_v3_'+name,'revision':1,
                     'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],
                     'materials':{},'coordinate_planes':[],'components':[],'instances':[],
                     'assembly_cuts':[],'constraints':[]}
        self.sources=[];self.details=[];self.access=[];self.supports=[];self.notes=[]

    def add(self,key,source,position=(0,0,0),yaw=0,roof='slate_gray',purpose=None):
        s=copy.deepcopy(source);t=placement(position,yaw);prefix=key+'__'
        def named(value):return [prefix+x for x in value] if isinstance(value,list) else prefix+value
        colors={**s['materials'],**{k:v for k,v in ROOFS[roof].items() if k in s['materials']}}
        material_map={k:'rgb_'+v.lstrip('#').lower() for k,v in colors.items()}
        self.master['materials'].update({material_map[k]:v for k,v in colors.items()})
        source_instances=[prefix+i['id'] for i in s['instances']]
        def selector(value,scope=False):
            out={}
            for k,v in value.items():
                if k in ('instance','component','feature'):out[k]=named(v)
                elif k=='material':out[k]=[material_map[x] for x in v] if isinstance(v,list) else material_map[v]
                else:out[k]=copy.deepcopy(v)
            if scope and 'instance' not in out:out['instance']=source_instances
            return out
        def planes(value):
            if isinstance(value,list):return [planes(v) for v in value]
            if isinstance(value,dict):return {k:(prefix+v if k=='plane' else planes(v)) for k,v in value.items()}
            return value
        for p in s.get('coordinate_planes',[]):
            p['id']=prefix+p['id']
            if 'relative_to' in p:p['relative_to']=prefix+p['relative_to']
            self.master['coordinate_planes'].append(p)
        for c in s['components']:
            c['id']=prefix+c['id']
            for op in c['operations']:
                op['id']=prefix+op['id'];op['shape']=planes(op['shape'])
                if 'material' in op:op['material']=material_map[op['material']]
                if 'selector' in op:op['selector']=selector(op['selector'])
            self.master['components'].append(c)
        for i in s['instances']:
            i['id']=prefix+i['id'];i['component']=prefix+i['component']
            if i.get('parent'):i['parent']=prefix+i['parent']
            else:i['transform']=core.compose(t,core.transform(i.get('transform')))
            self.master['instances'].append(i)
        for cut in s.get('assembly_cuts',[]):
            cut['id']=prefix+cut['id'];cut['shape']=planes(cut['shape'])
            cut['selector']=selector(cut.get('selector',{}),True)
            cut['transform']=core.compose(t,core.transform(cut.get('transform')))
            self.master['assembly_cuts'].append(cut)
        for con in s.get('constraints',[]):
            con['id']=prefix+con['id']
            for k in ('selector','a','b'):
                if k in con:con[k]=selector(con[k],True)
            if 'shape' in con:
                con['shape']=planes(con['shape'])
                con['transform']=core.compose(t,core.transform(con.get('transform')))
            self.master['constraints'].append(con)
        bounds=source_bounds(source)
        points=[core.apply(t,p) for p in itertools.product(*zip(bounds['min'],bounds['max']))]
        placed={'min':[min(p[j] for p in points) for j in range(3)],'max':[max(p[j] for p in points) for j in range(3)]}
        self.sources.append({'key':key,'source_id':source['id'],'source_revision':source['revision'],
                             'source_master_hash':core.digest(source),'placement':t,'placed_bounds_m':placed,
                             'roof_family':roof,'purpose':purpose,'source_provenance':source.get('provenance',{}),
                             'authored_dimensions':source.get('metadata',{}).get('spec',source.get('extensions',{}).get('dimensions_m',source.get('metadata',{}))),
                             'source_entrances':source.get('extensions',{}).get('entrances',source.get('metadata',{}).get('entrance'))})

    def detail(self,key,kind,position,yaw=0,datum='host_ground'):
        self.details.append({'id':key,'cache_key':kind,'position_local_m':list(position),'yaw_degrees':yaw,
                             'datum':datum,'requested_pitch_m':.2,'status':'static_candidate_runtime_motion_not_integrated'})

    def reserve(self,name,lo,hi,purpose):
        self.master['constraints'].append({'id':name,'kind':'empty_region','selector':{},
                                           'shape':{'kind':'box','min':lo,'max':hi}})
        self.access.append({'id':name,'clearance_box_local_m':{'min':lo,'max':hi},'purpose':purpose,
                            'fine_detail_overlap_test':'separate assembly contract test'})

    def finish(self):
        self.master['provenance']={'author':ref(AUTHOR),'concept':ref(CONCEPT),'prompt':ref(PROMPT),
                                  'source_rule':'Existing dimension-authored factories and staged continuous masters; rigid placement only, no scaled generic houses.',
                                  'design_status':'Fictional concept-derived design inference, not historical reconstruction.',
                                  'new_engine':False,'new_mesher':False}
        bounds=source_bounds(self.master)
        self.master['extensions']={'assembly_id':self.name,'status':'staged_common_assembly_pending_visual_review',
                                   'local_bounds_m':bounds,'source_assemblies':self.sources,'fine_details':self.details,
                                   'access_reservations':self.access,'support_contract':self.supports,
                                   'world_anchor_xz_m':self.anchor,'host_bench_y_m':self.height,
                                   'reservation_world_xz_m':self.reservation,
                                   'placement_policy':'Level host bench and external foundation required; this file does not modify terrain.',
                                   'visual_review':'not_run','collision_traversal':'not_run','animation':'not_integrated',
                                   'notes':self.notes,'whole_city_complete':False,
                                   'surface_ownership':'Main assembly owns its floor footprint. Integration must suppress underlying terrain top faces here, rather than add a display-height lift.'}
        return self.master


def tiles(a,key,bounds):
    x0,z0,x1,z1=bounds
    nx,nz=math.ceil((x1-x0)/24),math.ceil((z1-z0)/24)
    for ix in range(nx):
        for iz in range(nz):
            xa,xb=x0+(x1-x0)*ix/nx,x0+(x1-x0)*(ix+1)/nx
            za,zb=z0+(z1-z0)*iz/nz,z0+(z1-z0)*(iz+1)/nz
            a.add(f'{key}_{ix}_{iz}',floor_master(xb-xa,zb-za),[(xa+xb)/2,0,(za+zb)/2],purpose='Level bearing/paved surface')


def wall(a,key,center,length,height=3,yaw=0):
    n=math.ceil(length/24)
    for i in range(n):
        offset=-length/2+(i+.5)*length/n
        p=core.apply(placement(center,yaw),[offset,0,0])
        a.add(f'{key}_{i}',infrastructure({'kind':'wall_panel','width_m':length/n,'depth_m':1.5,'height_m':height,'battlements':False}),p,yaw,purpose='Enclosure wall; deliberately open at gate')


def build_sources():
    result={}
    a=Assembly('castle',[-300,-250],24,[-410,-335,-215,-175])
    tiles(a,'court',[-80,-70,80,72])
    a.add('keep',lm('castle_keep',90,64,34),[0,0,-25],roof='clay_red',purpose='Keep, open inner court, curtain and projecting towers')
    a.add('stable_west',stable(),[-58,-.5,35],90,'wood_brown','Purpose-authored livestock stable, closed entrance')
    a.add('stable_east',stable(),[58,-.5,35],-90,'wood_brown','Purpose-authored livestock stable, closed entrance')
    wall(a,'outer_west',[-79.25,0,0],140,3,90);wall(a,'outer_east',[79.25,0,0],140,3,90)
    wall(a,'outer_north',[0,0,-69.25],158.5)
    wall(a,'outer_front_west',[-44.5,0,65],71);wall(a,'outer_front_east',[44.5,0,65],71)
    a.add('south_gate',lm('gatehouse',18,14,16),[0,0,65],roof='clay_red')
    a.reserve('castle_main_access',[-3,.1,7.5],[3,3,72],'Clear axis from south gate to castle entry.')
    a.supports=[{'surface':'court','datum_local_y_m':0,'required_host':'Level +24 m castle bench; all foundations extend below this datum.'}]
    a.notes=['Stables use a −0.5 m foundation placement to align source 0.5 m thresholds with courtyard.',
             'Castle and gate shells are reused at authored dimensions; no interior rooms or wall-walk routes are claimed.']
    result[a.name]=a.finish()

    a=Assembly('cathedral',[250,-230],14,[155,-325,355,-175])
    tiles(a,'terrace',[-35,-68,88,50])
    a.add('nave',lm('cathedral',32,64,58),purpose='Nave, aisles, transept, front towers and stepped buttresses')
    for side in (-1,1):
        for i,z in enumerate((-20,8)):
            a.add(f'fly_{side}_{i}',flying_buttress(),[side*13.52,0,z],0 if side>0 else 180,
                  purpose='Upper nave abutment at X±7.52 m; outer pier bears on terrace')
    for i in range(7):a.detail(f'cloister_south_{i}','pointed_arch_cloister_bay',[42+i*4,0,24])
    for i in range(6):a.detail(f'cloister_east_{i}','pointed_arch_cloister_bay',[72,0,2+i*4],90)
    wall(a,'garden_north',[56,0,-12],32,1.8)
    a.reserve('cathedral_main_access',[-2.3,.1,29],[2.3,4.5,50],'West/front main entrance to south forecourt.')
    a.reserve('cathedral_cloister_access',[34,.1,27],[76,2.2,32],'Open south side of partial cloister.')
    a.supports=[{'surface':'terrace','datum_local_y_m':0,'required_host':'Level +14 m cathedral bench.'},
                {'feature':'flying_buttress','nave_bearing_y_m':20.4,'outer_pier_base_y_m':0,'structural_engineering':'not_performed'}]
    a.notes=['Four explicitly dimension-authored upper flying buttresses supplement existing stepped aisle supports.',
             'The L-shaped cloister is partial; complete corners/interior and garden planting remain open.']
    result[a.name]=a.finish()

    a=Assembly('monastery',[-270,120],8,[-390,80,-195,225])
    tiles(a,'terrace',[-72,-32,72,98])
    a.add('monastic_wings',lm('monastery',48,42,16),yaw=90,purpose='Three monastic wings and chapel opening toward east')
    for i in range(8):a.detail(f'cloister_north_{i}','pointed_arch_cloister_bay',[-10+i*4,0,-27])
    for i in range(5):a.detail(f'cloister_east_{i}','pointed_arch_cloister_bay',[32,0,-22+i*4],90)
    wall(a,'garden_west',[-55,0,65],60,2,90);wall(a,'garden_south',[-10,0,94],90,2)
    wall(a,'garden_east',[35,0,65],60,2,90);wall(a,'garden_north_left',[-29.5,0,36],51,2)
    wall(a,'garden_north_right',[19.5,0,36],31,2)
    for x in (-40,-10,20):
        for z in (52,78):a.add(f'garden_{x}_{z}',fabric({'kind':'garden_bed','width_m':10,'depth_m':10,'height_m':.8}),[x,0,z],purpose='Kitchen garden bed, not a cemetery')
    a.reserve('monastery_east_access',[21.5,.1,-3],[72,3.5,3],'East-facing cloister entry and exterior approach; connector bends to external gate at Z130.')
    a.reserve('monastery_garden_access',[-2,.1,24],[2,2.3,36.5],'Opening through garden enclosure.')
    a.supports=[{'surface':'terrace','datum_local_y_m':0,'required_host':'Level +8 m monastery bench.'}]
    a.notes=['Open front of existing monastery rotated east; garden enclosure is separate from roofed monastic wings.',
             'Hospital rooms, full enclosed cloister and functional growing simulation remain unbuilt.']
    result[a.name]=a.finish()

    a=Assembly('civic_grain',[20,40],4,[-30,-55,70,-10])
    tiles(a,'hall_forecourt',[-49,-94,50,-50])
    a.add('town_hall',lm('town_hall',46,24,24),[-20,0,-72],purpose='Purpose-authored civic hall with arcade and tower')
    a.add('grain_hall',lm('warehouse',28,28,13),[36,0,-72],roof='clay_red',purpose='Grain-storage hall adaptation from warehouse shell, with loading portal; not a generic house')
    a.reserve('town_hall_approach',[-21.4,.1,-64],[-18.6,2.8,-50],'Civic portal through front arcade to source reservation edge.')
    a.reserve('grain_hall_approach',[34.1,.1,-57.8],[37.9,3.8,-50],'Grain loading portal and cart approach.')
    a.supports=[{'surface':'hall_forecourt','datum_local_y_m':0,'required_host':'Level +4 m civic bench; main square Z≥0 belongs to plan, not this assembly.'}]
    a.notes=['Grain hall program reuses the warehouse architectural factory with distinct source ID and recorded dimensions.',
             'Silos, grain handling mechanisms, interior storage, scales and carts remain open; public market square is not filled by this assembly.']
    result[a.name]=a.finish()

    a=Assembly('port_cluster',[0,360],2.2,[-40,335,40,453])
    a.add('apron_foundation',support_fill('v3_apron_foundation',[-40,-1.2,-20],[40,-.5,59.2]),purpose='Bearing fill down to world Y1.0 beneath land apron only')
    a.add('quay_foundation',support_fill('v3_quay_foundation',[-40,-6.5,59.3],[40,-3,60.7]),purpose='Quay foundation tied to retaining mass and embedded in current river bed')
    tiles(a,'loading_yard',[-40,-20,40,59.2])
    a.add('warehouse_west',lm('warehouse',32,20,12),[-21,0,1],roof='clay_red')
    a.add('warehouse_east',lm('warehouse',32,20,12),[21,0,1],roof='clay_red')
    for i in range(20):a.add('quay_'+str(i),quay_at_dock() if i in (9,10) else staged('quay_retaining_segment'),[-38+i*4,0,60])
    a.add('dock',infrastructure({'kind':'dock','width_m':7,'length_m':32,'thickness_m':.5,'detail':True}),[0,0,76])
    for i,z in enumerate((68,84)):a.add('dock_bent_'+str(i),dock_bent(),[0,0,z])
    a.detail('crane','timber_harbor_crane',[-8,0,59.4])
    a.detail('barge','river_cargo_barge',[-8,0,62.5],90,'river_water')
    for i,x in enumerate((-26,-24,-22)):a.detail('cargo_'+str(i),'cargo_crate',[x,0,23])
    a.reserve('port_central_access',[-3,.1,12],[3,2.5,92],'Clear 6 m axis through post-free quay join to timber dock end.')
    a.reserve('west_loading_access',[-22.5,.1,11.2],[-19.5,3.5,20],'Warehouse west loading doorway.')
    a.reserve('east_loading_access',[19.5,.1,11.2],[22.5,3.5,20],'Warehouse east loading doorway.')
    a.supports=[{'surface':'loading_yard','datum_local_y_m':0,'required_host':'Local +2.2 m port bench; source apron foundation reaches world Y1.0 under land beyond the flat bench.'},
                {'feature':'dock_bents','pile_tip_local_y_m':-6.5,'required_host':'Pile tips world Y−4.3 lie below current candidate bed at all three axes; geotechnical bearing and final bathymetry remain unverified.'},
                {'feature':'barge','required_host':'Use river_water_y(world_x) for each placement, never quay terrain Y.'}]
    a.notes=['Repeat at three pier axes X=-180,0,180. Avoid bridge axis X120.',
             'Crane is above the quay; barge lies parallel to quay beside the pier. Hoist travel to the actual waterline is a required animation integration task.',
             'Quay/boat support is a geometric candidate, not hydraulic/structural certification.']
    result[a.name]=a.finish()
    return result



def detail_source(kind):
    value=copy.deepcopy(staged(kind))
    adjustments=[]
    if kind=='pointed_arch_cloister_bay':
        value['components']=[c for c in value['components'] if c['id']!='paving']
        value['instances']=[i for i in value['instances'] if i['component']!='paving']
        value['constraints']=[c for c in value['constraints'] if c['id']!='paving_present']
        adjustments.append('Standalone paving component omitted from this source variant: the main terrace owns floor and support. This avoids duplicate coplanar render surfaces.')
    if kind=='timber_harbor_crane':
        for c in value['components']:
            if c['id']=='base':c['operations']=[op for op in c['operations'] if op['id']!='stone_pad']
        adjustments.append('Standalone stone pad omitted from this source variant: the quay/main foundation owns bearing and surface; timber feet remain at local Y=0.')
    if adjustments:
        value['id']='v3_hosted_'+kind
        value['provenance']['adaptation_author']=ref(AUTHOR)
        value['provenance']['source_adaptations']=adjustments
        value['extensions']['local_bounds_m']=source_bounds(value)
        value['extensions']['host_surface_requirement']='Main assembly surface at local Y=0; this variant is not a standalone supported object.'
    return value


def build_manifest(sources):
    groups=[]
    for name,master in sources.items():
        ext=master['extensions'];replicas=[-180,0,180] if name=='port_cluster' else [ext['world_anchor_xz_m'][0]]
        for x in replicas:
            z=ext['world_anchor_xz_m'][1]
            groups.append({'id':name+(('_'+str(x)) if name=='port_cluster' else ''),'assembly_source':name,
                           'render_cache':f'cache/{name}.pitch_0.5.render.json',
                           'world_translation_m':[x,ext['host_bench_y_m'],z],
                           'fine_details':copy.deepcopy(ext['fine_details']),
                           'water_height_resolver':'world_city.concept_city_v3.topography.author.river_water_y' if name=='port_cluster' else None,
                           'status':'staged_static_replacement_not_integrated',
                           'replaces_source_building_ids':{'castle':['B_CASTLE_KEEP'],'cathedral':['B_CATHEDRAL'],
                             'monastery':['B_MONASTERY'],'civic_grain':['B_TOWN_HALL','B_GRAIN_HALL'],'port_cluster':[]}[name],
                           'source_plan_match':'source/plan.json reservation-based replacement; no scale applied to source proxy.'})
    return {'schema':'riverstone.city.landmark_assemblies.v1','revision':1,
            'status':'staged_common_sources_pending_art_and_terrain_integration',
            'concept':ref(CONCEPT),'prompt':ref(PROMPT),'author':ref(AUTHOR),
            'coordinate_system':{'up':'+Y','front':'+Z','right':'+X','unit':'m'},
            'process':{'input':'Approved concept v3, land-use reservations, candidate host datums and existing common source factories.',
                       'conditions':'No generic house scaling, no new engine/mesher, one continuous source per assembly, rigid placement and true openings. Keep main market square and bridge route clear.',
                       'deliverables':'Five authored landmark assembly sources, shared fine-part sources, cached common renders, footprint/access/support metadata and bounded validation.',
                       'completion_criteria':'Source references/footprints/clearances validate and common compile stays under budget. Visual, traversal, dynamics, hydraulics and live terrain integration remain pending.'},
            'compile_budget':{'candidate_cells_per_compile':CANDIDATE_CAP,'output_cells_per_compile':OUTPUT_CAP,'sequential_only':True,'main_pitch_m':.5,'fine_pitch_m':.2,'whole_city_compile':False,'gui_run':False},
            'assemblies':groups,
            'fine_cache_kinds':['pointed_arch_cloister_bay','timber_harbor_crane','river_cargo_barge','cargo_crate'],
            'source_masters':{name:ref(str((HERE/'masters'/f'{name}.json').relative_to(ROOT))) for name in sources},
            'limitations':['Staged replacement files only; no root scene file is modified.',
                           'Local host benches must cover each entire footprint; no unverified center-only terrain seating.',
                           'Closed stable doors, interiors, wall-walk, runtime animation and water mechanics remain outside this stage.']}


def author_all():
    sources=build_sources()
    for name,value in sources.items():write(HERE/'masters'/f'{name}.json',value)
    for kind in ('pointed_arch_cloister_bay','timber_harbor_crane','river_cargo_barge','cargo_crate'):
        write(HERE/'masters'/f'fine_{kind}.json',detail_source(kind))
    manifest=build_manifest(sources);write(HERE/'assemblies.json',manifest)
    return sources,manifest


if __name__=='__main__':
    sources,manifest=author_all()
    print(json.dumps({'main_assemblies':len(sources),'placements':len(manifest['assemblies']),
                      'source_bounds':{k:v['extensions']['local_bounds_m'] for k,v in sources.items()}}))
