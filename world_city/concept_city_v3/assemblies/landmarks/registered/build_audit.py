"""Image/source audit and bounded source-cost inspection. Never samples a cell.

Existing common shape bounds and source factories are reused. The two tall
towers are isolated feasibility sources, not placed or reviewed city assets.
"""
from pathlib import Path
import copy
import hashlib
import itertools
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from voxel_character.common import coordinate_planes, core
from world_city.runtime_city.landmarks.author import _Author, make_master
from world_city.concept_city_v3.assemblies.landmarks.author import ROOFS, source_bounds
from world_city.concept_city_v3.registered_source.geometry import inside
from world_city.runtime_city.checks.placement import intersection_area,road_ribbon

HERE = Path(__file__).resolve().parent
LANDMARKS = HERE.parent
CONTROLS = ROOT/'world_city/concept_city_v3/image_registration/controls.json'
IMAGE = ROOT/'world_city/reference/revision_03/city_social_water_concept.png'
BASELINE = ROOT/'world_city/concept_city_v3/image_registration/evidence/current_matched_view/registered.png'


def ref(p):
    return {'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def write(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def camera_functions(controls):
    c=controls['camera_model'];s=c['scale_px_per_m'];yaw=math.radians(c['yaw_degrees']);e=math.radians(c['elevation_degrees']);cx,cy=c['offset_pixel_xy']
    def project(p):
        x,y,z=p
        return [cx+s*(math.cos(yaw)*x-math.sin(yaw)*z), cy+s*(math.sin(e)*math.sin(yaw)*x-math.cos(e)*y+math.sin(e)*math.cos(yaw)*z)]
    def inverse(p,y):
        u=(p[0]-cx)/s;v=(p[1]-cy+s*math.cos(e)*y)/(s*math.sin(e))
        return [math.cos(yaw)*u+math.sin(yaw)*v,y,-math.sin(yaw)*u+math.cos(yaw)*v]
    return project,inverse,s*math.cos(e),s*math.sin(e)


def bounds(points):
    return {'min':[min(p[j] for p in points) for j in range(len(points[0]))], 'max':[max(p[j] for p in points) for j in range(len(points[0]))]}


def corners(b):
    return list(itertools.product(*zip(b['min'],b['max'])))


def hull(points):
    pts=sorted(set(tuple(round(v,4) for v in p) for p in points))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lower=[];upper=[]
    for p in pts:
        while len(lower)>1 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper)>1 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
        upper.append(p)
    return lower[:-1]+upper[:-1]


def pose(local,origin,yaw):
    a=math.radians(yaw);c,s=math.cos(a),math.sin(a);x,y,z=local
    return [origin[0]+c*x+s*z,origin[1]+y,origin[2]-s*x+c*z]


def module(key,rect,height,role,source,**extra):
    x0,z0,x1,z1=rect
    return dict(id=key,semantic_role=role,local_bounds_m={'min':[x0,0,z0],'max':[x1,height,z1]},
                source_strategy=source,**extra)


def estimate_candidates(master,pitch):
    """Exactly the common sampler's AABB visits, including empty-region checks.

    This computes only integer range lengths. It does not call contains(),
    compile_master(), allocate occupancy cells, or export geometry.
    """
    m,_=coordinate_planes.resolve_master(master,{'pitch':pitch})
    comps,instances=core.validate_master(m,pitch);origin=m.get('grid_origin',[0,0,0]);poses={}
    def tr(k):
        if k not in poses:
            i=instances[k];t=core.transform(i.get('transform'))
            poses[k]=core.compose(tr(i['parent']),t) if i.get('parent') else t
        return poses[k]
    rows=[]
    def count(label,shape,transform,category):
        lo,hi=core.shape_bounds(core.prepare_shape(shape,pitch))
        pts=[core.apply(transform,p) for p in itertools.product(*zip(lo,hi))];b=bounds(pts)
        n=math.prod(max(0,math.ceil((hi-o)/pitch-core.EPS)-math.floor((lo-o)/pitch+core.EPS)) for lo,hi,o in zip(b['min'],b['max'],origin))
        rows.append({'id':label,'category':category,'candidate_cells':n})
    for key,i in instances.items():
        for op in comps[i['component']]['operations']:
            count(op['id'],op['shape'],core.compose(tr(key),core.transform(op.get('transform'))),op['action'])
    for op in m.get('assembly_cuts',[]):count(op['id'],op['shape'],core.transform(op.get('transform')),'assembly_cut')
    for op in m.get('constraints',[]):
        if op['kind']=='empty_region':count(op['id'],op['shape'],core.transform(op.get('transform')),'constraint_region')
    total=sum(r['candidate_cells'] for r in rows);paint=sum(r['candidate_cells'] for r in rows if r['category']=='paint')
    return {'pitch_m':pitch,'candidate_cells_exact_aabb_visits':total,'paint_candidate_upper_bound':paint,
            'cell_sampling_run':False,'measured_peak_memory_bytes':None,
            'planning_memory_envelope_mib_at_1536_bytes_per_paint_candidate':round(paint*1536/2**20,2),
            'memory_assumption':'Conservative planning allowance, not an RSS measurement or guaranteed bound. Occupancy layers, rows, mesh and Python overhead must be measured during a later isolated compile.',
            'largest_operations':sorted(rows,key=lambda r:r['candidate_cells'],reverse=True)[:5]}


def tower_source(name,width,height):
    spec={'asset_id':name,'kind':'wall_tower','width_m':width,'depth_m':width,'height_m':height}
    a=_Author(spec);a.tower('bell_tower',-width/2,width/2,-width/2,width/2,height,spire=True)
    for level in (.28,.46,.64):
        a.belt('stage_'+str(level),-width/2,width/2,-width/2,width/2,height*level,height*level+.5)
    for x in (-width*.21,width*.21):
        a.window('belfry_'+str(x),x,height*.57,width/2,width*.18,height*.12)
    # Authored metal finial, not a cell edit: the hollow cone alone loses its
    # last 1.5–2 m at 0.5 m sampling because no cell center reaches its apex.
    a.box('dressings','spire_finial',[-.3,height-2,-.3],[.3,height,.3],'iron')
    result=a.finish();result['materials'].update({k:v for k,v in ROOFS['slate_gray'].items() if k in result['materials']})
    result['provenance']['registered_adaptation_author']=ref(Path(__file__))
    result['extensions'].update(status='source_only_cost_feasibility_fixture',actual_scene_placement=False,
                                intended_use='One fictional bell tower. No stair, bell animation, internal access, structural or collision certification.',
                                body_top_m=height*.75,spire_top_m=height,
                                apex_detail='Continuous 0.6 m square, 2 m high iron finial preserves the chosen silhouette height at exterior pitch. No postcompile voxel edit.')
    return result


def main():
    controls=json.loads(CONTROLS.read_text());project,inverse,vertical_px,depth_px=camera_functions(controls)
    poly={p['id']:[[q[0],q[2]] for q in p['world_xyz_m']] for p in controls['polygons']}
    anchors={a['id']:a for a in controls['anchors']}
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in list((LANDMARKS/'masters').glob('*.json'))+list((LANDMARKS/'cache').glob('*.json'))}
    measurements=[
      {'id':'cathedral_bell_tower','tip_px':[1120,84],'base_px':[1120,263],'base_uncertainty_px':7,'tip_uncertainty_px':3,'observed':'One dominant slender bell tower beside the nave front/side. No equally tall companion is visible.','inferred':'The partly occluded shaft foot is vertically below the spire, not the precinct anchor.','proposed_height_m':128},
      {'id':'cathedral_nave_front_ridge','tip_px':[1114,211],'base_px':[1114,263],'base_uncertainty_px':5,'tip_uncertainty_px':3,'observed':'Main nave roof is much lower than the bell tower.','inferred':'Same-XZ ground beneath ridge is partly hidden by frontage.','proposed_height_m':40},
      {'id':'monastery_bell_tower','tip_px':[244,385],'base_px':[244,500],'base_uncertainty_px':7,'tip_uncertainty_px':4,'observed':'A distinct bell tower rises behind/left of the long church.','inferred':'Base is hidden by the church roof and adjoining wings.','proposed_height_m':84},
      {'id':'monastery_nave_front_ridge','tip_px':[315,518],'base_px':[315,560],'base_uncertainty_px':4,'tip_uncertainty_px':3,'observed':'Long gray gabled church above lower red-roofed convent ranges.','inferred':'Front ridge foot estimated at the church threshold plane.','proposed_height_m':30},
      {'id':'castle_front_left_tower','tip_px':[251,115],'base_px':[251,198],'base_uncertainty_px':8,'tip_uncertainty_px':4,'observed':'Red-roofed projecting tower on the front-left of the inner court.','inferred':'Terrace/plinth contribution is uncertain; do not attribute all visible retaining height to the tower.','proposed_height_m':56},
      {'id':'civic_bell_tower','tip_px':[946,332],'base_px':[946,432],'base_uncertainty_px':5,'tip_uncertainty_px':4,'observed':'A narrow tower rises over the north market arcade.','inferred':'Civic function and hidden tower footprint are assigned design roles.','proposed_height_m':72},
    ]
    for m in measurements:
        rise=m['base_px'][1]-m['tip_px'][1];unc=m['base_uncertainty_px']+m['tip_uncertainty_px']
        m.update(rise_px=rise,literal_height_if_same_xz_m=round(rise/vertical_px,3),height_interval_m=[round((rise-unc)/vertical_px,3),round((rise+unc)/vertical_px,3)],
                 proposed_rise_px=round(m['proposed_height_m']*vertical_px,3),vertical_fit_residual_px=round(rise-m['proposed_height_m']*vertical_px,3),status='manual_image_observation_with_explicit_foot_inference_not_survey')
    axes=[]
    for key,a,b in [('cathedral_nave',[1067,169],[1114,211]),('monastery_nave',[256,478],[316,518]),('civic_long_roof',[875,403],[935,389])]:
        p,q=inverse(a,0),inverse(b,0);dx,dz=q[0]-p[0],q[2]-p[2]
        axes.append({'id':key,'ridge_endpoints_px':[a,b],'same_height_assumption':True,'world_plan_run_m':round(math.hypot(dx,dz),3),
                     'yaw_from_positive_z_degrees':round(math.degrees(math.atan2(dx,dz)),3),'uncertainty_degrees':8,
                     'note':'A roof-ridge run is depth/footprint evidence. Its image rise is not building height; hidden ridge ends can shorten the observed length.'})
    cached=[]
    keymap={'castle':'castle','cathedral':'cathedral','monastery':'monastery','civic_grain':'market','port_cluster':'port_west'}
    principal={'castle':['keep','stable_west','stable_east','south_gate'],'cathedral':['nave'],'monastery':['monastic_wings'],'civic_grain':['town_hall','grain_hall'],'port_cluster':['warehouse_west','warehouse_east']}
    for name,key in keymap.items():
        master=json.loads((LANDMARKS/'masters'/f'{name}.json').read_text());cache=json.loads((LANDMARKS/'cache'/f'{name}.pitch_0.5.render.json').read_text())
        old=anchors[key]['current_world_xyz_m'];target=anchors[key]['inferred_target_world_xyz_m']
        verts=[v for g in cache['groups'] for q in g['quads'] for v in q]
        proj={}
        for label,origin in [('original',old),('anchor_translation_only',target)]:
            pts=[project([v[j]+origin[j] for j in range(3)]) for v in verts]
            proj[label]={'screen_bounds_px':bounds(pts),'convex_envelope_px':hull(pts),'warning':'Convex outer envelope spans empty courtyards and does not imply filled geometry.'}
        sources=[s for s in master['extensions']['source_assemblies'] if s['key'] in principal[name]]
        cached.append({'id':name,'master':ref(LANDMARKS/'masters'/f'{name}.json'),'cache':ref(LANDMARKS/'cache'/f'{name}.pitch_0.5.render.json'),
                       'actual_cache_bounds_m':cache['bounds'],'projected_cache':proj,
                       'principal_source_groups':[{'key':s['key'],'bounds_m':s['placed_bounds_m'],'source_id':s['source_id']} for s in sources],
                       'independent_cached_semantic_parts':False,'reason':'Main cache groups are materials, after compositing. Internal interfaces are absent; do not split its final quads to invent reusable pieces.'})
    # Frames use actual semantic control candidates; image district anchors stay separate.
    groups=[
      {'id':'castle_registered','precinct':'CASTLE','image_anchor_id':'castle','origin_control_px':[310,174],'origin_meaning':'inner courtyard floor center; separate from the [310,210] precinct control','ground_y_m':24,'yaw_degrees':-18,
       'modules':[
        module('west_residence',[-48,-42,-27,32],34,'roofed_castle_wing','New purpose-authored stone hall using existing shell/roof writer',roof='clay_red',eave_m=24),
        module('rear_residence',[-27,-50,30,-30],38,'roofed_castle_wing','New dimension-authored rear hall derived from castle rear_keep families',roof='clay_red',eave_m=27),
        module('east_service_wing',[30,-28,46,35],28,'roofed_castle_wing','New stone/timber service range source',roof='clay_red',eave_m=19),
        module('front_gate_wing',[-20,34,32,48],25,'gate_wing','Existing gatehouse opening grammar plus long asymmetric roofed wing',roof='clay_red',opening_local_xz_m=[0,48],clear_width_m=6,clear_height_m=5),
        module('rear_square_tower',[9,-31,23,-17],64,'hip_roof_tower','Existing hollow tower shell; new red pyramidal roof source',roof='clay_red',body_top_m=53),
        module('front_left_tower',[-42,12,-28,26],56,'hip_roof_tower','Existing hollow tower shell; new red pyramidal roof source',roof='clay_red',body_top_m=46),
        module('east_tower',[40,17,52,29],43,'hip_roof_tower','Existing hollow tower shell; new red pyramidal roof source',roof='clay_red',body_top_m=35),
        module('rear_left_tower',[-51,-47,-39,-35],46,'hip_roof_tower','Existing hollow tower shell; new red pyramidal roof source',roof='clay_red',body_top_m=38)],
       'clear_court_local_xz_m':[-26,-14,28,30],'access_local_polyline_xz_m':[[0,10],[0,48],[0,58]],'external_access_status':'requires registered roads and terrain; old R_CASTLE audit is not transferred',
       'retained_modules':['common gate opening grammar','stable factory as a separate exercise-ground assembly','wall panels and local retaining modules'],
       'omitted_old_composition':['symmetric four-crenellated-tower keep cache','160×142 m rectangular blanket paving','separate monumental outer gate competing with the inner castle']},
      {'id':'cathedral_registered','precinct':'CLERGY','image_anchor_id':'cathedral','origin_control_px':[1112,262],'origin_meaning':'candidate main nave front threshold','ground_y_m':14,'yaw_degrees':32.3,
       'modules':[
        module('nave_aisles_transept',[-17,-88,17,0],40,'church_body','New tower-free cathedral source using nave/aisle/transept/window/buttress families',roof='slate_gray',nave_eave_m=28.06,aisle_eave_m=14.33,aisle_ridge_m=19.10,main_portal_clear_m=[5,6]),
        module('single_bell_tower',[-2.394,-2.489,9.606,9.511],128,'bell_tower','registered/masters/cathedral_bell_tower_128m.json',roof='slate_gray',body_top_m=96),
        module('north_cloister_range',[30,-74,102,-62],24,'roofed_cloister_range','New institutional shell/roof range, independent source with gallery sockets',roof='slate_gray',eave_m=16),
        module('east_cloister_range',[90,-62,102,6],22,'roofed_cloister_range','Same common range family, perpendicular assembly placement',roof='slate_gray',eave_m=15),
        module('south_cloister_walk',[30,-2,90,6],10,'covered_arcade','Repeat existing 4 m pointed arch bays, add independently authored roof gallery',roof='slate_gray'),
        module('west_cloister_walk',[26,-62,34,-2],10,'covered_arcade','Repeat common 4 m bays; explicit corner join source required',roof='slate_gray')],
       'clear_court_local_xz_m':[34,-62,90,-2],'access_local_polyline_xz_m':[[-6,-3],[-6,0],[-6,12]],'external_access_status':'New nave front portal shifts to local X−6 m to keep the single front/side tower clear. Candidate threshold requires registered approach ramp; no terrain height changed',
       'retained_modules':['approved stone and gray roof palette','nave/aisles/transept sources','pointed arch bay caches','service lodge source as separate optional range'],
       'omitted_old_composition':['paired front spires','low sparse L-shaped cloister as the complete precinct','wide full-rectangle floor under cemetery/landscape']},
      {'id':'monastery_registered','precinct':'MONASTERY','image_anchor_id':'monastery','origin_control_px':[320,558],'origin_meaning':'candidate long church front threshold','ground_y_m':8,'yaw_degrees':40.2,
       'modules':[
        module('monastic_church',[-12,-68,12,0],30,'church_body','Tower-free church source, independently dimensioned body and roof',roof='slate_gray',nave_eave_m=22.39,main_portal_clear_m=[3,4]),
        module('rear_side_bell_tower',[-.234,-85.766,10.766,-74.766],84,'bell_tower','registered/masters/monastery_bell_tower_84m.json',roof='slate_gray',body_top_m=63),
        module('rear_chapel_connection',[-8,-81,12,-62],22,'monastic_chapel_connector','New bounded rear vestibule joins church and independently pinned bell tower',roof='slate_gray',eave_m=15),
        module('north_convent_range',[22,-76,84,-62],18,'monastic_residential_range','Recompose monastery wing shell/roof grammar at authored dimensions',roof='clay_red',eave_m=12),
        module('east_convent_range',[70,-62,84,8],18,'monastic_residential_range','Purpose-authored convent wing with service sockets',roof='clay_red',eave_m=12),
        module('front_refectory',[22,-6,70,8],17,'refectory','Purpose-authored stone range; no enlarged generic house',roof='clay_red',eave_m=11),
        module('west_arcade',[-48,6,10,14],8,'covered_arcade','Repeat independent cloister bays with low roof source',roof='slate_gray')],
       'clear_court_local_xz_m':[24,-60,68,-8],'access_local_polyline_xz_m':[[0,-3],[0,0],[0,20]],'external_access_status':'registered street link required; former east-only monastery link is superseded design evidence',
       'retained_modules':['garden bed sources','pointed arch bay caches','monastic wing shell grammar','enclosure wall modules'],
       'omitted_old_composition':['16 m chapel as the whole church silhouette','one large flat rectangular garden platform']},
      {'id':'civic_registered','precinct':None,'avoid_precinct':'MARKET','image_anchor_id':'market','origin_control_px':[895,440],'origin_meaning':'northwest market hall arcade threshold; market anchor remains the fountain/square','ground_y_m':4,'yaw_degrees':24.3,
       'modules':[
        module('north_market_hall',[-21,-22,21,0],25,'civic_arcaded_hall','Existing town_hall shell/arcade/roof families, independent tower dimensions',roof='clay_red',eave_m=16),
        module('civic_tower',[-4.5,-4.5,4.5,4.5],72,'bell_tower','Same hollow tower source family, 9 m square; separate independent cache',roof='slate_gray',body_top_m=54,image_ground_control_px=[946,432])],
       'access_local_polyline_xz_m':[[0,-2],[0,0],[0,8]],'external_access_status':'front arcade must meet open square edge after registration',
       'retained_modules':['town hall nine-bay arcade grammar','grain warehouse architecture as separate long market hall','fountain and stall sources'],
       'separate_grain_hall':{'origin_control_px':[800,451],'width_m':46,'depth_m':30,'ridge_height_m':28,'eave_m':18,'yaw_degrees':24.3,'roof':'slate_gray','source_strategy':'Purpose-authored arcaded grain hall using warehouse shell plus civic arcade; separate front threshold frame','status':'held_not_in_proxy_handoff','blocker':'Proposed footprint crosses inferred CIVIC_WEST_APPROACH. Preserve road; exact hall fit unresolved.'},
       'composition_note':'Hall reduced to42×22 m and moved to pixel[895,440] to remain west of MARKET_NORTH. Tower independently pinned to[946,432] east of the road. Do not bridge the public street with a solid linking wing.',
       'omitted_old_composition':['market point as the center of an arbitrary hall floor','two small side-by-side halls as the entire civic skyline']},
    ]
    for g in groups:
        g['world_origin_xyz_m']=[round(v,4) for v in inverse(g['origin_control_px'],g['ground_y_m'])]
        g['registered_district_anchor_xyz_m']=anchors[g['image_anchor_id']]['inferred_target_world_xyz_m']
        g['frame_contract']='Local +Z is church/hall front. world = origin + Y-yaw(local); no scale. Image district point is not the module origin.'
        g['source_status']='adaptation_design_only_except_two_isolated_tower_feasibility_sources';g['compiled_cache']=False;g['actual_placed']=False
        footprint_pts=[]
        for m in g['modules']:
            if m.get('image_ground_control_px'):
                target=inverse(m['image_ground_control_px'],g['ground_y_m']);dx,dz=target[0]-g['world_origin_xyz_m'][0],target[2]-g['world_origin_xyz_m'][2]
                angle=math.radians(g['yaw_degrees']);x,z=math.cos(angle)*dx-math.sin(angle)*dz,math.sin(angle)*dx+math.cos(angle)*dz
                b=m['local_bounds_m'];hw=(b['max'][0]-b['min'][0])/2;hd=(b['max'][2]-b['min'][2])/2
                b['min'][0],b['max'][0],b['min'][2],b['max'][2]=x-hw,x+hw,z-hd,z+hd
            pts=[pose(p,g['world_origin_xyz_m'],g['yaw_degrees']) for p in corners(m['local_bounds_m'])]
            m['world_bounds_m']=bounds(pts);m['projected_envelope_px']=hull([project(p) for p in pts]);footprint_pts.extend([[p[0],p[2]] for p in pts])
            b=m['local_bounds_m'];ring=[[b['min'][0],0,b['min'][2]],[b['max'][0],0,b['min'][2]],[b['max'][0],0,b['max'][2]],[b['min'][0],0,b['max'][2]]]
            samples=[]
            for p,q in zip(ring,ring[1:]+ring[:1]):
                n=max(1,math.ceil(math.dist(p,q)/.25))
                samples.extend(pose([p[j]+(q[j]-p[j])*i/n for j in range(3)],g['world_origin_xyz_m'],g['yaw_degrees']) for i in range(n+1))
            if g['precinct']:
                m['precinct_fit']={'method':'all footprint edges sampled at ≤0.25 m; not a terrain or collision test','samples':len(samples),'outside_samples':sum(not inside([p[0],p[2]],poly[g['precinct']]) for p in samples)}
            else:m['market_overlap_edge_samples']=sum(inside([p[0],p[2]],poly[g['avoid_precinct']]) for p in samples)
        g['component_footprint_world_bounds_xz_m']=bounds(footprint_pts)
    registered_plan_path=ROOT/'world_city/concept_city_v3/registered_source/plan.json'
    registered_plan=json.loads(registered_plan_path.read_text());road_checks=[]
    for g in groups:
        for m in g['modules']:
            b=m['local_bounds_m'];ring=[[b['min'][0],0,b['min'][2]],[b['max'][0],0,b['min'][2]],[b['max'][0],0,b['max'][2]],[b['min'][0],0,b['max'][2]]]
            p=[pose(v,g['world_origin_xyz_m'],g['yaw_degrees']) for v in ring];p=[[v[0],v[2]] for v in p]
            for r in registered_plan['roads']:
                for i,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
                    overlap=intersection_area(p,road_ribbon(a,b,r['width_m']))
                    if overlap>1e-5:road_checks.append({'group':g['id'],'module':m['id'],'road_id':r['id'],'segment':i,'intersection_area_m2':overlap})
    port={'id':'port_registered','source_status':'adaptation_design_only','compiled_cache':False,'actual_placed':False,
          'observed':['Long low red-roofed sheds run along a curved shore frontage.','Three main loading piers and one dominant timber crane are visible.','Several cargo and sailing boats have different hull/rig sizes.'],
          'inferred':['Exact pier count of three is also specified by prompt; smaller incidental platforms are not classified as equal piers.','Boat dimensions and crane joint geometry need a new source design; isolated perspective pixels do not certify their length or height.'],
          'quay_control_id':'PORT_QUAY','quay_trace_height_conflict':'controls road trace uses Y4 while PORT polygon uses Y2.2; registered terrain owner must resolve. No override applied.',
          'assembly_policy':'Split old 80×112 m monolithic cluster. Follow each shore tangent with independent long sheds/quay runs; piers point along local water-facing normal.',
          'modules':[{'id':'long_warehouse','dimensions_xzy_m':[48,12,10],'eave_m':6.5,'ridge_axis':'+X','door_face':'+Z','door_width_m':4,'roof':'clay_red','reuse':'new warehouse shell/roof variant, preserving current factory; long-axis roof and multiple water-facing loading bays'},
                     {'id':'quay_segment','dimensions_xzy_m':[4,1.6,3.5],'reuse':'existing common retaining segment; select no-post join at pier openings'},
                     {'id':'pier','dimensions_xzy_m':[7,26,.5],'reuse':'existing dimension-authored dock factory and separate bents; new bed support per pier'},
                     {'id':'harbor_crane','footprint_xz_m':[16,12],'mast_height_m':18,'boom_reach_m':22,'max_height_m':26,'reuse':'new dimension-authored timber crane variant; 3.9 m source is too small for focal silhouette; moving-part sockets retained'},
                     {'id':'cargo_barge','hull_length_m':18,'beam_m':4.5,'reuse':'new source hull stations and deck sections; current 8 m cache retained for small lighter'},
                     {'id':'sailing_barge','hull_length_m':24,'beam_m':5.5,'mast_height_above_water_m':17,'reuse':'missing sail/rigging source; author new bounded family without scaling current cache'}],
          'support_gate':'Current old river field and old flat quay assumptions cannot certify newly traced shoreline placements. Recompute dry bank, water level, bed and freeboard after registered hydrology freezes.',
          'bridge_note':'Existing bridge_datum_discrepancy.json remains active; no deck or approach value changed.'}
    estimates=[]
    for name,w,h in [('cathedral_bell_tower_128m',12,128),('monastery_bell_tower_84m',11,84)]:
        src=tower_source(name,w,h);write(HERE/'masters'/f'{name}.json',src)
        estimates.append({'id':name,'source':ref(HERE/'masters'/f'{name}.json'),'source_bytes':(HERE/'masters'/f'{name}.json').stat().st_size,
                          'source_bounds_m':source_bounds(src),'requests':[estimate_candidates(src,p) for p in (.5,.25)]})
    # Verify the estimator against every previously compiled frozen main source.
    report=json.loads((LANDMARKS/'evidence/compile_report.json').read_text());checks=[]
    for r in report['requests']:
        if r['id'].startswith('fine_'):continue
        src=json.loads((LANDMARKS/'masters'/f"{r['id']}.json").read_text());est=estimate_candidates(src,r['pitch_m'])
        checks.append({'id':r['id'],'estimate':est['candidate_cells_exact_aabb_visits'],'recorded_compile':r['candidate_cells'],'pass':est['candidate_cells_exact_aabb_visits']==r['candidate_cells']})
    after={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in before}
    audit={'schema':'riverstone.city.registered_landmark_shape_audit.v1','status':'source_design_and_projection_review_no_compile_no_placement',
           'inputs':[ref(IMAGE),ref(CONTROLS),ref(BASELINE)],'pixel_inspection':True,
           'measurement_contract':{'vertical_px_per_m':vertical_px,'camera_depth_px_per_m':depth_px,'image_is_calibrated_survey':False,'controls_anchor_rms_px':controls['anchor_rms_px'],
             'limits':['Manual points carry explicit ±pixel uncertainty. Hidden feet and non-single-camera image perspective prevent exact metric reconstruction.','Precinct controls include occluded/interpolated boundaries; passing a fit is not proof of real ground clearance.','Matched baseline is source proxy geometry, not the frozen common assemblies integrated into scene. Actual cache projections are computed separately here.']},
           'vertical_measurements':measurements,'roof_axes':axes,'frozen_cache_projection':cached,
           'mismatch_summary':{'castle':'Current central rear keep, symmetric crenellated towers and broad bare court miss asymmetric red-roofed residential wings and tall roofed towers.',
             'cathedral':'Actual existing nave ridge 38.86 m is close to the 40 m proposal. The 27.26 m number is wall height. Twin 58 m spires, axis alignment and sparse low cloister are the large shape errors.',
             'monastery':'Frozen 48×42 m three-wing/chapel group tops out at 16 m and has no tower. Image requires a long independent church and a bell tower, with connected roofed ranges.',
             'civic':'Market control is the open square/fountain, not the hall origin. North hall, its tall narrow tower, west grain hall and other frontage blocks are separately visible.',
             'port':'Three identical large rectangular clusters miss the narrow curved frontage, long shore-parallel roofs and focal large crane/boat family.'},
           'proposed_groups':groups,'port_adaptation':port,'feasibility_sources':estimates,
           'cost_estimator_checks':checks,'sealed_source_cache_hashes_unchanged':before==after,
           'registered_road_footprint_check':{'plan':ref(registered_plan_path),'method':'Component footprint vs each registered rectangular road ribbon using existing common placement intersection. Does not certify capsule caps, entrances, terrain seating or detailed mesh.', 'conflicts':road_checks},
           'compile_policy':{'compile_run':False,'approved_current_candidate_cap':2000000,'next_compile':'Only independent approved modules after fit review. Cache at local yaw0, apply rigid group yaw at placement, and avoid baking rotations into candidate AABBs.',
             'suggested_isolated_tower_pitch_m':.5,'suggested_isolated_tower_output_cell_cap':300000,'memory_gate':'Measure RSS on the first isolated compile; keep sequential, abort before any unapproved budget expansion.'},
           'process':{'input':'Approved revision_03 pixels, manual registration controls, matched proxy baseline, sealed common sources and actual cached exterior vertices.',
             'conditions':'Preserve masters/caches and both city plans. Separate observation, hidden-foot inference and authored metric choices. No new engine, cell sampling, whole-city compile or scene placement.',
             'deliverables':'Five-family silhouette audit, semantic component plan and local frames, projected old-cache/new-envelope comparison, two standard source-only tall-tower feasibility fixtures and exact AABB resource estimates.',
             'completion_criteria':'Input hashes verified; all frozen main candidate estimates reproduce recorded counts; precinct edge samples reported; projected height residuals and unresolved supports/access stay explicit. Compilation, actual integration and visual review remain gated.'}}
    write(HERE/'concept_shape_audit.json',audit)
    write(HERE/'adaptation_plan.json',{'schema':'riverstone.city.registered_landmark_adaptation_plan.v1','status':audit['status'],'apply_allowed':False,'groups':groups,'port':port,'source_audit':ref(HERE/'concept_shape_audit.json')})
    write(HERE/'evidence/cost_and_fit_checks.json',{'estimator_checks':checks,'tower_estimates':estimates,'sealed_sources_unchanged':before==after,
      'precinct_fit':{g['id']:{m['id']:m.get('precinct_fit',{'market_overlap_edge_samples':m.get('market_overlap_edge_samples')}) for m in g['modules']} for g in groups},'cell_sampling_run':False})
    # Vector projection comparison uses actual cache vertices, not a new render engine.
    import base64
    img=base64.b64encode(IMAGE.read_bytes()).decode()
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1536" height="1024" viewBox="0 0 1536 1024"><image width="1536" height="1024" href="data:image/png;base64,{img}"/><style>text{{font-family:DejaVu Sans;font-size:13px;paint-order:stroke;stroke:#111;stroke-width:3px}}</style>']
    for c in cached:
        pts=c['projected_cache']['anchor_translation_only']['convex_envelope_px'];ss=' '.join(f'{x:.2f},{y:.2f}' for x,y in pts)
        svg.append(f'<polygon points="{ss}" fill="none" stroke="#ff40a0" stroke-width="2" stroke-dasharray="7 4"/>')
    for g in groups:
        for m in g['modules']:
            ss=' '.join(f'{x:.2f},{y:.2f}' for x,y in m['projected_envelope_px']);svg.append(f'<polygon points="{ss}" fill="#28ffcf" fill-opacity=".035" stroke="#28ffcf" stroke-width="1.2"/>')
        x,y=g['origin_control_px'];svg.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#28ffcf"/><text x="{x+7}" y="{y+12}" fill="#28ffcf">{g["id"]}</text>')
    for m in measurements:
        x,y=m['tip_px'];bx,by=m['base_px'];svg.append(f'<path d="M{x},{y} L{bx},{by}" stroke="#fff45b" stroke-width="2"/><circle cx="{x}" cy="{y}" r="3" fill="#fff45b"/>')
    svg.append('<rect x="10" y="980" width="1130" height="32" fill="#111" fill-opacity=".8"/><text x="20" y="1002" fill="white">Magenta: old cache envelope after anchor-only translation. Mint: proposed component envelopes. Yellow: same-footprint height measurements. No city placement.</text></svg>')
    (HERE/'projected_silhouette_comparison.svg').write_text(''.join(svg))
    print(json.dumps({'sealed_sources_unchanged':before==after,'estimator_checks':checks,'towers':[{ 'id':e['id'],'costs':[(r['pitch_m'],r['candidate_cells_exact_aabb_visits']) for r in e['requests']]} for e in estimates],
                      'fit_failures':[(g['id'],m['id'],m['precinct_fit']['outside_samples']) for g in groups for m in g['modules'] if m.get('precinct_fit',{}).get('outside_samples',0)]},indent=2))


if __name__=='__main__':main()
