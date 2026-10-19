"""Deterministic fictional v3 grade/water contract; no geometry compiler.

height_at is the excavated earth/bed proxy. road_height_at is the independent
cart-deck/approach datum and must be used for bridges. Flat landmark benches and
bounded grade slopes are analytic source data, not measurements from the image.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
CITY=HERE.parent
GRADE_LIMIT=.12
BASE_GROUND=1.0
SOURCE_PLAN_PATH=CITY/'source/plan.json'
SOURCE_PLAN_BYTES=SOURCE_PLAN_PATH.read_bytes() if SOURCE_PLAN_PATH.exists() else b'{}'
SOURCE_PLAN=json.loads(SOURCE_PLAN_BYTES)
SOURCE_PLAN_SHA256=hashlib.sha256(SOURCE_PLAN_BYTES).hexdigest()
SUPERSEDED_LANDMARK_PADS={'B_CASTLE_KEEP','B_CATHEDRAL','B_MONASTERY','B_TOWN_HALL','B_GRAIN_HALL',
    'B_CASTLE_TOWER_W','B_CASTLE_TOWER_E','B_CATHEDRAL_TOWER_W','B_CATHEDRAL_TOWER_E',
    'B_CATHEDRAL_CLOISTER','B_MONASTERY_CHAPEL','B_MONASTERY_SERVICE'}
BANK_GRADE=.08
# x0,z0,x1,z1; every rectangle defines a level bench and a continuous <=12% apron.
BENCHES=[
    ('castle',[-410,-335,-215,-175],24),
    ('cathedral',[155,-325,355,-175],14),
    ('reservoir_bank',[-60,-370,60,-300],18),
    ('spring_head',[15,-520,45,-495],26),
    ('noble_training',[-390,-100,-280,-80],16),
    ('noble_manors',[-375,-55,-145,-10],14),
    ('noble_lower_gardens',[-350,20,-170,40],12),
    ('market_civic',[-45,-60,160,110],4),
    ('monastery',[-390,80,-195,225],8),
    ('poor_craft',[180,85,420,220],2.5),
    ('port_loading',[-250,335,300,390],2.2),
]
CANAL_POINTS=[[-511.42857142857144,420],[-460,300],[-340,280],[-180,280],[-30,270],
              [130,260],[270,270],[350,310],[370,330],[390,345],[410,365],[455.29411764705884,420]]
CANAL_LEVELS=[1.9657142857142857,1.9,1.7,1.5,1.3,1.1,.8,.5,-.3,-.4,-1.2,-1.9011764705882355]
RESERVOIR_POLYGON=[[-48,-358],[48,-358],[48,-312],[-48,-312]]
WATER_SURFACES=[
    dict(id='MAIN_RIVER',polyline_xz_m=[[-580,465],[580,465]],width_m=90,
         levels_m=[2.24,-2.4],bed_depth_m=3,bank_offset_m=1.2,
         use='receiving_river_not_drinking_supply'),
    dict(id='SERVICE_CANAL',polyline_xz_m=CANAL_POINTS,width_m=6,
         levels_m=CANAL_LEVELS,bed_depth_m=.8,bank_offset_m=1.2,
         reserve_width_m=14,use='industrial_nonpotable',clip_bounds_xz_m=[-580,-520,580,420],
         transverse_height_api='water_height_at; first/last reaches match sloping river across full clipped shoreline'),
    dict(id='SPRING_FEEDER',polyline_xz_m=[[30,-510],[30,-440],[0,-370],[0,-358]],
         width_m=2,levels_m=[24,22,17,16],bed_depth_m=.6,bank_offset_m=.6,
         reserve_width_m=8,use='raw_spring_water_quality_unverified'),
    dict(id='NORTHERN_RESERVOIR',polygon_xz_m=RESERVOIR_POLYGON,water_y_m=16,
         bed_depth_m=2.4,bank_crest_y_m=18,use='settling_storage_raw_quality_unverified'),
]


def _finite(x,z):
    if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in (x,z)):
        raise ValueError('finite world XZ metres required')


def _rect_distance(x,z,r):
    return max(r[0]-x,0,x-r[2],r[1]-z,z-r[3])


def _inside(x,z,poly):
    sign=None
    for a,b in zip(poly,poly[1:]+poly[:1]):
        v=(b[0]-a[0])*(z-a[1])-(b[1]-a[1])*(x-a[0])
        if abs(v)<1e-9:continue
        s=v>0
        if sign is None:sign=s
        elif sign!=s:return False
    return True


def _project(x,z,a,b):
    dx,dz=b[0]-a[0],b[1]-a[1];den=dx*dx+dz*dz
    t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/den))
    return math.hypot(x-a[0]-t*dx,z-a[1]-t*dz),t


SEGMENTS=[]
for _w in WATER_SURFACES:
    if 'polyline_xz_m' not in _w:continue
    for _i,(_a,_b) in enumerate(zip(_w['polyline_xz_m'],_w['polyline_xz_m'][1:])):
        SEGMENTS.append((_w,_i,_a,_b,_w['levels_m'][_i],_w['levels_m'][_i+1]))


def river_water_y(x):
    """New authored 0.4% west-to-east river, not frozen r2's flat river."""
    _finite(x,0)
    return 2-.004*(x+520)


def bench_height_at(x,z):
    _finite(x,z)
    return max(BASE_GROUND,*(h-GRADE_LIMIT*_rect_distance(x,z,r) for _,r,h in BENCHES))


def dry_height_at(x,z):
    """Continuous earth/bank/deck support field, before finite water-bed cuts.

    Each planar bench apron is 0.12-Lipschitz. Each water-bank support cone has
    gradient <=sqrt(0.08²+longitudinal_water_grade²), always below 0.12 here.
    Their maximum preserves that bound. This field gives roads no cliff edges.
    """
    h=bench_height_at(x,z)
    for water,_,a,b,ya,yb in SEGMENTS:
        d,t=_project(x,z,a,b)
        candidate=ya+(yb-ya)*t+water['bank_offset_m']-BANK_GRADE*max(0,d-water['width_m']/2)
        h=max(h,candidate)
    # Source bridge heads are independent of canal bank crests. Continuous
    # earth cones provide visible approach support, not invisible ramps.
    for p,head in _bridge_supports():
        h=max(h,head+2.0-BANK_GRADE*math.dist([x,z],p))
    return h



def _segment_water_height(w,x,z,segment_index):
    a,b=w['polyline_xz_m'][segment_index:segment_index+2]
    d,t=_project(x,z,a,b);ya,yb=w['levels_m'][segment_index:segment_index+2]
    center=ya+(yb-ya)*t
    if w['id']=='SERVICE_CANAL' and segment_index in (0,len(CANAL_POINTS)-2):
        k=(1.9-river_water_y(-460))/120 if segment_index==0 else (-1.2-river_water_y(410))/55
        plane=river_water_y(x)+k*(420-z)
        weight=max(0,min(1,(z-300)/120)) if segment_index==0 else max(0,min(1,(z-365)/55))
        center+=weight*(plane-center)
    return center,d


def water_height_at(surface_id,x,z,segment_index=0):
    """Single-valued joined source surface, independent of segment ownership.

    Compact continuous blending only around nearby segment joins prevents two
    different heads at a bend. River mouths use exact transverse river grade
    along Z420. These are geometric source constraints, not hydraulic results.
    """
    w=next(w for w in WATER_SURFACES if w['id']==surface_id)
    if 'polygon_xz_m' in w:return w['water_y_m']
    radius=w['width_m']*2;weighted=[];nearest=None
    for i in range(len(w['polyline_xz_m'])-1):
        head,d=_segment_water_height(w,x,z,i)
        if nearest is None or d<nearest[0]:nearest=(d,head)
        if d<radius:
            weight=(1-(d/radius)**2)**2;weighted.append((head,weight))
    if not weighted:return nearest[1]
    return sum(h*w for h,w in weighted)/sum(w for _,w in weighted)

def water_samples_at(x,z):
    """All exact finite strip/polygon water domains owning this world point."""
    _finite(x,z);out=[]
    for domain in finite_water_domains():
        if _inside(x,z,domain['polygon_xz_m']):
            w=next(w for w in WATER_SURFACES if w['id']==domain['surface_id'])
            head=water_height_at(w['id'],x,z,domain.get('segment_index',0))
            out.append(dict(id=w['id'],segment=domain.get('segment_index'),water_y_m=head,
                            bed_y_m=head-w['bed_depth_m']))
    return out


def land_height_at(x,z):
    """Uncut land top with compound/body pads, stairs and real ledges applied.

    Use this at the OUTSIDE edge of a finite water-hole clip. It never returns a
    water bed merely because the point lies exactly on a shared shoreline.
    """
    h=dry_height_at(x,z)
    for compound in compound_pads():
        if any(_inside(x,z,p) for p in compound['owned_polygons_xz_m']):return compound['floor_y_m']
    nearby=_pads_near(x,z)
    for pad in nearby:
        if _inside(x,z,pad['body_polygon_xz_m']):return pad['floor_y_m']
    # Exterior approaches cannot displace the public cart road or its shoulders.
    if _road_clearance(x,z)<=0:return h
    for pad in nearby:
        y=_pad_approach_height(pad,x,z,h)
        if y is not None:return y
    stair=_stair_height_at(x,z)
    if stair is not None:return stair
    terrace=_terrace_height_at(x,z)
    return h if terrace is None else terrace


def height_at(x,z):
    """Excavated finite earth/bed proxy. Use land_height_at at clipped banks."""
    wet=water_samples_at(x,z)
    if wet:return min(dry_height_at(x,z),*(w['bed_y_m'] for w in wet))
    return land_height_at(x,z)


def road_height_at(road_id,x,z):
    """Cart-deck datum (+0.08 m surface separation), including water crossings.

    road_id is accepted for runtime compatibility; all streets share one
    continuous source datum. Bridge spans have independently owned support and
    collision, not earth filled across the water. Analytic grade <=12%.
    """
    return dry_height_at(x,z)+.08


def _polyline_samples(polyline,spacing=4):
    out=[]
    for a,b in zip(polyline,polyline[1:]):
        n=max(1,math.ceil(math.dist(a,b)/spacing))
        out += [[a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n] for i in range(n)]
    return out+[list(polyline[-1])] if polyline else []


def project_road(road):
    p=_polyline_samples(road['polyline_xz_m']);xyz=[[x,road_height_at(road['id'],x,z),z] for x,z in p]
    grades=[abs(b[1]-a[1])/math.hypot(b[0]-a[0],b[2]-a[2]) for a,b in zip(xyz,xyz[1:]) if a!=b]
    # The same continuous field governs the full width and shoulders, not just
    # centerline samples. Water-domain crossings explicitly switch to bridges.
    hits=sorted({w['id'] for x,z in p for w in water_samples_at(x,z)})
    return dict(id=road['id'],width_m=road['width_m'],profile_xyz_m=xyz,
        maximum_sampled_grade=max(grades,default=0),analytic_grade_limit=GRADE_LIMIT,
        water_domain_hits=hits,deck_offset_m=.08,shoulder_width_each_side_m=2,
        support='dry earth apron; bridge piers/abutments over water need separate source ownership',
        collision='uncompiled source only; no controller traversal claim')


def _water_graph():
    nodes=[];edges=[]
    def n(id,p,y,net,kind):
        nodes.append(dict(id=id,xz_m=p,head_y_m=y,network=net,kind=kind,quality='unverified'))
    def e(id,a,b,mode='gravity',**kw):
        edges.append(dict(id=id,source=a,target=b,mode=mode,**kw))
    n('SPRING',[30,-510],24,'raw_clean_source','authored_new_headwater')
    n('FEEDER',[30,-440],22,'raw_clean_source','contour_feeder')
    n('RESERVOIR_INLET',[0,-370],17,'raw_clean_source','settling_inlet')
    n('RESERVOIR',[0,-358],16,'raw_clean_source','open_settling_storage')
    n('COVERED_CISTERN',[68,-335],15.5,'protected_supply','covered_storage')
    for a,b in [('SPRING','FEEDER'),('FEEDER','RESERVOIR_INLET'),('RESERVOIR_INLET','RESERVOIR'),('RESERVOIR','COVERED_CISTERN')]:e(a+'_TO_'+b,a,b)
    for id,p,y in [('NOBLE_DRAW',[-220,-35],14.5),('CATHEDRAL_DRAW',[250,-230],14.5),
                   ('MARKET_DRAW',[20,40],4.6),('MONASTERY_DRAW',[-270,120],8.5)]:
        n(id,p,y,'protected_supply','closed_conduit_draw_point');e('SUPPLY_'+id,'COVERED_CISTERN',id,
            alignment='covered conduit source route still needs exact clearance and pressure controls')
    n('CASTLE_ROOF',[-300,-250],32,'protected_supply','roof_catchment')
    n('CASTLE_CISTERN',[-285,-245],22.8,'protected_supply','buried_local_storage')
    n('CASTLE_DRAW',[-280,-240],24.6,'protected_supply','bucket_lift_draw_point')
    e('CASTLE_RAIN','CASTLE_ROOF','CASTLE_CISTERN');e('CASTLE_LIFT','CASTLE_CISTERN','CASTLE_DRAW','manual_lift',energy_source='bucket_or_windlass')
    for i,(p,y) in enumerate(zip(CANAL_POINTS,CANAL_LEVELS)):
        n('CANAL_%02d'%i,p,y,'industrial_nonpotable','river_intake' if i==0 else 'river_outfall' if i==len(CANAL_POINTS)-1 else 'canal_control')
    for i in range(len(CANAL_POINTS)-1):
        e('CANAL_REACH_%02d'%i,'CANAL_%02d'%i,'CANAL_%02d'%(i+1),
          'wheel_head_drop' if i in (7,9) else 'gravity')
    for id,p,y in [('STORM_UP',[70,100],3.4),('STORM_MID',[230,185],2.2),('STORM_LOW',[330,230],1.1),('STORM_OUT',[480,445],-1.8)]:
        n(id,p,y,'storm','drain_invert')
    for a,b in [('STORM_UP','STORM_MID'),('STORM_MID','STORM_LOW'),('STORM_LOW','STORM_OUT'),('STORM_OUT','CANAL_11')]:
        e(a+'_TO_'+b,a,b,alignment='separate drain; culvert under service canal where crossing, not a potable connection')
    n('WASTE_VAULT',[310,180],1.0,'contained_waste','sealed_or_lined_storage_marker')
    n('WASTE_REMOVAL',[320,185],2.5,'contained_waste','manual_collection_no_designed_river_discharge')
    e('WASTE_REMOVE','WASTE_VAULT','WASTE_REMOVAL','manual_lift',energy_source='human_or_cart')
    index={n['id']:n for n in nodes};checks=[]
    for edge in edges:
        a,b=index[edge['source']],index[edge['target']];head=a['head_y_m']-b['head_y_m']
        if edge['mode']!='manual_lift' and head<=0:raise ValueError('non-downhill edge '+edge['id'])
        checks.append(dict(edge_id=edge['id'],head_drop_m=round(head,6),hydraulically_validated=False))
    return dict(nodes=nodes,edges=edges,checks=checks,
        design='fictional authored headwaters and a NEW 0.4% river profile; not the old flat river',
        protected_supply='closed distribution separate from service canal and storm/waste; quality unverified',
        castle_limit='reservoir +16 cannot gravity-feed castle +24; local roof cistern and powered lift retained',
        unresolved=['flow and drought yield','water quality','groundwater','reservoir/liner/embankment safety',
                    'pressure, capacity, erosion and sediment','flood stage/backwater','conduit and storm culvert alignments',
                    'wheel power and seasonal operation','offsite waste disposal'])


def _stairs():
    data=[('CASTLE_PEDESTRIAN',[[-300,-175],[-300,-100]]),
          ('NOBLE_UPPER_STEPS',[[-320,-80],[-320,-55]]),
          ('NOBLE_LOWER_STEPS',[[-250,-10],[-250,20]]),
          ('PORT_LANDING',[[0,390],[0,420]])]
    out=[]
    for id,p in data:
        top=dry_height_at(*p[0]);bottom=dry_height_at(*p[-1])
        if id=='PORT_LANDING':bottom=river_water_y(0)+.25
        rise=abs(top-bottom);count=max(1,math.ceil(rise/.15))
        out.append(dict(id=id,polyline_xz_m=p,endpoint_y_m=[top,bottom],width_m=2.4,
            nominal_max_riser_m=.15,number_of_risers=count,actual_riser_m=rise/count,
            tread_design_m=.30,remaining_run='landings/approach to fit endpoint distance',
            gameplay_not_historical_dimension=True,status='semantic source hook; not geometry or collision',
            road_exclusion='pedestrian shortcut only; continuous cart-grade earth route remains independent'))
    return out


def build_contract(roads=None):
    if roads is None:
        roads=SOURCE_PLAN.get('roads',[])
    profiles={r['id']:project_road(r) for r in roads if len(r.get('polyline_xz_m',[]))>=2}
    bank_bounds=[]
    for w,_,a,b,ya,yb in SEGMENTS:
        s=abs(yb-ya)/math.dist(a,b);bank_bounds.append(math.hypot(BANK_GRADE,s))
    quay_samples=[dict(x=x,quay_y_m=height_at(x,z),water_y_m=river_water_y(x),
                       freeboard_m=height_at(x,z)-river_water_y(x))
                   for x in range(-250,301,10) for z in (335,390)]
    return dict(schema='riverstone.concept_city_v3.terrain_water.v1',source_plan_sha256=SOURCE_PLAN_SHA256,status='authored_source_and_spatial_proxy_only',
        review_bounds_xz_m=[-580,-520,580,590],coordinate_system={'axes':'Y_up','units':'metres','grid_origin_m':[0,0,0]},
        height_api={'height_at':'excavated earth and water-bed proxy',
                    'dry_height_at':'continuous uncut bank/deck datum',
                    'road_height_at':'independent road/bridge deck, includes +0.08 m separation',
                    'path_height_at':'entrance pad landing then shared dry-deck datum; includes surface separation',
                    'river_water_y':'2 - 0.004 * (x + 520)'},
        benches=[dict(id=id,bounds_xz_m=r,host_y_m=h,apron_grade=GRADE_LIMIT) for id,r,h in BENCHES],
        terrain_formula='max(1, bench_height - .12 * rectangle_Linf_distance, bounded water-bank cones); finite water domains subtract beds afterwards',
        grade_proof={'dry_field_lipschitz_bound':max(GRADE_LIMIT,*bank_bounds),
            'maximum_water_bank_function_gradient':max(bank_bounds),
            'cart_limit':GRADE_LIMIT,'valid_for_full_road_width_and_shoulders':True,
            'exception':'finite water and bounded building-pad retaining edges are barriers; roads use independent decks',
            'sampled_proxy_is_not_physics_validation':True},
        water_surfaces=[dict(w,finite_domains=[d for d in finite_water_domains() if d['surface_id']==w['id']]) for w in WATER_SURFACES],
        water_domain_polygons=finite_water_domains(),water_graph=_water_graph(),
        shoreline={'river_z_bounds_m':[420,510],'channel_bed_depth_m':.8,'river_bed_depth_m':3,
            'reservoir_bed_y_m':13.6,'reservoir_bank_y_m':18,
            'finite_ownership':'exact finite rectangular strips clipped at river Z420 plus exact reservoir polygon; preserve holes in later common terrain',
            'overlap_rule':'bed is below every overlapping water surface at intake/outfall/joins'},
        port={'loading_bounds_xz_m':[-250,335,300,390],'loading_y_m':2.2,
            'minimum_normal_stage_freeboard_m':min(s['freeboard_m'] for s in quay_samples),
            'maximum_normal_stage_freeboard_m':max(s['freeboard_m'] for s in quay_samples),
            'normal_stage_only_not_flood_safety':True,'ship_api':'river_water_y(ship_x)',
            'landing_stairs':'separate local lowered steps; quay is not waterline'},
        road_profiles=profiles,pedestrian_stairs=_stairs(),neighborhood_stair_geometry=actual_stairs(),
        building_pads=building_pads(),compound_pads=compound_pads(),entrance_pad_summary=pad_summary(),
        superseded_landmark_pad_ids=sorted(SUPERSEDED_LANDMARK_PADS),
        neighborhood_terraces=terrace_contract(),
        bridge_support='source-plan bridge points get finite 8% earth approach cones up to water+2.0; deck adds .08',
        mill_hooks=[dict(id='MILL_01',center_xz_m=[360,320],forebay_y_m=.5,tailwater_y_m=-.3,gross_head_m=.8),
                    dict(id='MILL_02',center_xz_m=[400,355],forebay_y_m=-.4,tailwater_y_m=-1.2,gross_head_m=.8)],
        construction={'first_mesh':'finite 4 m spatial/grade proxy; water/liner risers and stairs are not exact common solids yet',
            'later_geometry':'existing common coordinate_planes/core/render_data only; no alternate voxel mesher',
            'layers':'large macro earth, medium support/retaining faces, sparse small surface caps at walk corridors and entries',
            'road_edge':'same continuous dry field under road width and two-metre shoulders; cut banks bridged, never centerline-only slope claim',
            'surface_separation_m':.08,'hidden_face_removal':'not implemented or claimed',
            'foundation':'rigid building at declared entrance datum with support down to minimum footprint grade; no floating corner acceptance',
            'collision':'controller traversal, stair step-up and bridge support tests still required'},
        evidence={'observed_in_concept_image':['separate noble/poor quarters','raised landmarks','northern basin','service canal and wheels','quays'],
            'authored_not_image_measurements':['all coordinates/elevations/slopes','water head','reservoir capacity','riser dimensions'],
            'historical_status':'fictional circa-1450 composition; hydraulic topology is a design proposal, not historical fact'},
        source_change={'old_city_modified':False,'frozen_r2_modified':False,'new_fictional_geography':True})



_PAD_CACHE=None
_PAD_INDEX=None
_PATH_INDEX={p['id']:p for p in SOURCE_PLAN.get('paths',[])}

def _station(polyline,distance):
    for a,b in zip(polyline,polyline[1:]):
        length=math.dist(a,b)
        if length<=1e-9:continue
        if distance<=length:
            t=distance/length
            return [a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])]
        distance-=length
    return list(polyline[-1])

def _strip(a,b,width):
    length=math.dist(a,b)
    if length<=1e-9:return []
    nx=-(b[1]-a[1])/length*width/2;nz=(b[0]-a[0])/length*width/2
    return [[a[0]+nx,a[1]+nz],[a[0]-nx,a[1]-nz],[b[0]-nx,b[1]-nz],[b[0]+nx,b[1]+nz]]

_ROAD_INDEX=None

def _road_clearance(x,z):
    """Signed distance outside finite public-road width plus 2 m shoulders."""
    global _ROAD_INDEX
    if _ROAD_INDEX is None:
        _ROAD_INDEX={}
        for road in SOURCE_PLAN.get('roads',[]):
            radius=road['width_m']/2+2
            for a,b in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:]):
                if math.dist(a,b)<1e-9:continue
                r=[min(a[0],b[0])-radius-1,min(a[1],b[1])-radius-1,
                   max(a[0],b[0])+radius+1,max(a[1],b[1])+radius+1]
                for ix in range(math.floor(r[0]/32),math.floor(r[2]/32)+1):
                    for iz in range(math.floor(r[1]/32),math.floor(r[3]/32)+1):
                        _ROAD_INDEX.setdefault((ix,iz),[]).append((a,b,radius))
    return min((_project(x,z,a,b)[0]-radius for a,b,radius in
                _ROAD_INDEX.get((math.floor(x/32),math.floor(z/32)),[])),default=1000.)


def _entry_weight(entry,x,z):
    line=entry['approach_polyline_xz_m'];length=entry['approach_length_m']
    if length<1e-9:return 0.
    a,b=line;distance,t=_project(x,z,a,b)
    # Outside the finite end planes there is no landing ownership.
    ux,uz=(b[0]-a[0])/length,(b[1]-a[1])/length
    along=(x-a[0])*ux+(z-a[1])*uz
    if along<0 or along>length:return 0.
    half=entry['width_m']/2;shoulder=.6
    side=max(0,min(1,(half+shoulder-distance)/shoulder))
    start=entry['level_threshold_length_m']
    longitudinal=max(0,min(1,(length-along)/max(1e-9,length-start)))
    road_priority=max(0,min(1,_road_clearance(x,z)/.6))
    return side*longitudinal*road_priority


def _pad_approach_height(pad,x,z,base):
    weights=[_entry_weight(e,x,z) for e in pad['entrance_ledger']
             if e.get('approach_polygon_xz_m') and _inside(x,z,e['approach_polygon_xz_m'])]
    weight=max(weights,default=0.)
    return base+weight*(pad['floor_y_m']-base) if weight>0 else None


def building_pads():
    """Rigid body pad with correctly matched, bounded per-door approaches.

    Exterior source patches taper to the shared field at outer and side edges;
    public roads and their 2 m shoulders win. Tight frontage and secondary doors
    with insufficient ramp length remain explicit review exceptions.
    """
    global _PAD_CACHE,_PAD_INDEX
    if _PAD_CACHE is not None:return _PAD_CACHE
    _PAD_CACHE=[];_PAD_INDEX={}
    paths={}
    for path in SOURCE_PLAN.get('paths',[]):
        if path.get('owner_building_id'):paths.setdefault(path['owner_building_id'],[]).append(path)
    compounds={p['plot_id']:p for p in compound_pads()}
    for b in SOURCE_PLAN.get('buildings',[]):
        if b['id'] in SUPERSEDED_LANDMARK_PADS:continue
        footprint=b.get('footprint_xz_m');door=b.get('entrance_xz_m')
        if not footprint or not door:continue
        doors=[door]+[p for p in b.get('all_entrances_xz_m',[]) if math.dist(p,door)>1e-7]
        entries=[];candidates=paths.get(b['id'],[])
        for index,point in enumerate(doors):
            path=min(candidates,key=lambda p:math.dist(point,p['polyline_xz_m'][0])) if candidates else None
            mismatch=math.dist(point,path['polyline_xz_m'][0]) if path else None
            if mismatch is not None and mismatch>1e-5:path=None
            outer=_station(path['polyline_xz_m'],2) if path else list(point)
            length=math.dist(point,outer);width=max(2.4,path.get('width_m',1.8) if path else 2.4)
            interval=_line_inside_interval(point,outer,footprint) if length>1e-9 else None
            body_exit=length*interval[1] if interval and _inside(*point,footprint) else 0.
            level=min(max(.4,body_exit),max(0,length-.2))
            entries.append(dict(door_index=index,xz_m=point,path_id=path['id'] if path else None,
                path_start_error_m=mismatch if path else None,approach_polyline_xz_m=[point,outer],
                approach_length_m=length,landing_outer_xz_m=outer,width_m=width,
                level_threshold_length_m=level,
                approach_polygon_xz_m=_strip(point,outer,width+1.2),
                public_shoulder_clearance_at_door_m=_road_clearance(*point)))
        primary=entries[0];outer=primary['landing_outer_xz_m']
        floor=road_height_at(b.get('road_id',''),*(door if primary['public_shoulder_clearance_at_door_m']<.6 else outer))
        compound=compounds.get(b.get('plot_id'))
        if compound:floor=compound['floor_y_m']
        polygons=[footprint]+[e['approach_polygon_xz_m'] for e in entries if e['approach_polygon_xz_m']]
        natural=[dry_height_at(*p) for p in list(footprint)+[door,b['position_xz_m']]]
        for entry in entries:
            outer_y=road_height_at(b.get('road_id',''),*entry['landing_outer_xz_m'])
            run=max(0,entry['approach_length_m']-entry['level_threshold_length_m'])
            slope=abs(floor-outer_y)/max(1e-9,run)
            tight=entry['public_shoulder_clearance_at_door_m']<.6
            status=('compound_floor_owned' if compound else 'missing_exact_door_path' if not entry['path_id'] else
                    'tight_frontage_threshold_requires_review' if tight else
                    'requires_authored_steps_or_replan' if slope>.12+1e-8 else 'bounded_blended_source_approach_unverified')
            entry.update(threshold_y_m=floor,landing_y_m=floor,delta_m=0,outer_path_y_m=outer_y,
                minimum_centerline_ramp_grade=slope,routing_status=status,
                outer_edge_rule='exact shared field; lateral .6 m blend; public road and 2 m shoulder priority',
                collision_status='source height contract only; capsule and common solids not validated')
        pad=dict(id=b['id']+':PAD',building_id=b['id'],plot_id=b.get('plot_id'),floor_y_m=floor,
            owned_polygons_xz_m=polygons,body_polygon_xz_m=footprint,
            primary_entrance_xz_m=door,landing_outer_xz_m=outer,
            landing_length_m=primary['approach_length_m'],door_path_id=primary['path_id'],
            exterior_ownership='candidate transition domains only; public road/shoulder wins, then taper; not flat pad polygons',
            foundation_bottom_y_m=min(min(natural),floor)-.4,
            maximum_fill_m=max(0,floor-min(natural)),maximum_cut_m=max(0,max(natural)-floor),
            retaining_face_contract='closed body side/rear interfaces; exterior approach is bounded blend, not extended level slab',
            entrance_ledger=entries,
            geometry_status='exact source domains and proxy height only; retaining/foundation common solids not compiled')
        _PAD_CACHE.append(pad)
        xs=[p[0] for q in polygons for p in q];zs=[p[1] for q in polygons for p in q]
        for ix in range(math.floor(min(xs)/32),math.floor(max(xs)/32)+1):
            for iz in range(math.floor(min(zs)/32),math.floor(max(zs)/32)+1):
                _PAD_INDEX.setdefault((ix,iz),[]).append(pad)
    return _PAD_CACHE

def _pads_near(x,z):
    building_pads()
    return _PAD_INDEX.get((math.floor(x/32),math.floor(z/32)),[])

def path_height_at(path_id,x,z):
    """Finished path/transition datum; runtime adds no further display offset."""
    path=_PATH_INDEX.get(path_id)
    for compound in compound_pads():
        if path and path.get('owner_plot_id')==compound['plot_id'] and any(_inside(x,z,p) for p in compound['owned_polygons_xz_m']):
            return compound['floor_y_m']
    base=road_height_at(path.get('road_id','') if path else '',x,z)
    if path and path.get('owner_building_id'):
        for pad in _pads_near(x,z):
            if pad['building_id']!=path['owner_building_id']:continue
            if _inside(x,z,pad['body_polygon_xz_m']):return pad['floor_y_m']
            if _road_clearance(x,z)<=0:return base
            y=_pad_approach_height(pad,x,z,base)
            if y is not None:return y
    return base

def pad_summary():
    pads=building_pads();entries=[e for p in pads for e in p['entrance_ledger']]
    counts={}
    for e in entries:counts[e['routing_status']]=counts.get(e['routing_status'],0)+1
    return dict(pads=len(pads),source_primary_doors=len(pads),source_declared_doors=len(entries),
        primary_threshold_delta_max_m=0,maximum_approach_length_m=max((e['approach_length_m'] for e in entries),default=0),
        entrance_status_counts=counts,maximum_fill_m=max((p['maximum_fill_m'] for p in pads),default=0),
        maximum_cut_m=max((p['maximum_cut_m'] for p in pads),default=0),
        pads_over_2m_cut_or_fill=[p['building_id'] for p in pads if max(p['maximum_fill_m'],p['maximum_cut_m'])>2],
        scope='rigid body pads plus <=2 m per-declared-door blends; roads/shoulders protected; secondary/tight thresholds explicitly unverified')


# Real 2--4 m neighborhood ledges, with roads, shoulders, entries and bodies
# removed from their ownership. These do not quantize the public-road datum.
TERRACES=[
    dict(id='NOBLE_UPPER_LEDGE',bounds_xz_m=[-390,-80,-280,-55],top_y_m=16),
    dict(id='NOBLE_MIDDLE_LEDGE',bounds_xz_m=[-350,-10,-170,20],top_y_m=14),
    dict(id='NOBLE_LOWER_LEDGE',bounds_xz_m=[-350,40,-195,72],top_y_m=12),
]
_TERRACE_CACHE=None

def _rect_poly(r):return [[r[0],r[1]],[r[2],r[1]],[r[2],r[3]],[r[0],r[3]]]

def _bounds(poly):return [min(p[0] for p in poly),min(p[1] for p in poly),max(p[0] for p in poly),max(p[1] for p in poly)]

def _overlap(a,b):return min(a[2],b[2])>=max(a[0],b[0]) and min(a[3],b[3])>=max(a[1],b[1])

def _terrace_data():
    global _TERRACE_CACHE
    if _TERRACE_CACHE is not None:return _TERRACE_CACHE
    protected=[]
    for p in SOURCE_PLAN.get('roads',[])+SOURCE_PLAN.get('paths',[]):
        width=p['width_m']+4 # two metres owned dry shoulder on each side
        line=p['polyline_xz_m']
        for a,b in zip(line,line[1:]):
            q=_strip(a,b,width)
            if q:protected.append(dict(owner=p['id'],polygon_xz_m=q))
        for x,z in line:
            protected.append(dict(owner=p['id'],polygon_xz_m=_rect_poly([x-width/2,z-width/2,x+width/2,z+width/2])))
    for pad in building_pads()+compound_pads():
        for p in pad['owned_polygons_xz_m']:
            b=_bounds(p);b=[b[0]-1,b[1]-1,b[2]+1,b[3]+1]
            protected.append(dict(owner=pad['id'],polygon_xz_m=_rect_poly(b)))
    _TERRACE_CACHE=[]
    for t in TERRACES:
        q=dict(t);q['polygon_xz_m']=_rect_poly(t['bounds_xz_m'])
        q['exclusions']=[p for p in protected if _overlap(t['bounds_xz_m'],_bounds(p['polygon_xz_m']))]
        _TERRACE_CACHE.append(q)
    return _TERRACE_CACHE

def _terrace_height_at(x,z):
    for t in _terrace_data():
        if _inside(x,z,t['polygon_xz_m']) and not any(_inside(x,z,p['polygon_xz_m']) for p in t['exclusions']):
            return t['top_y_m']
    return None

def _line_inside_interval(a,b,poly):
    # Exact convex source interval clipping, not a voxel or triangle mesher.
    lo,hi=0.,1.
    area=sum(p[0]*q[1]-p[1]*q[0] for p,q in zip(poly,poly[1:]+poly[:1]))
    sign=1 if area>=0 else -1
    for p,q in zip(poly,poly[1:]+poly[:1]):
        f0=sign*((q[0]-p[0])*(a[1]-p[1])-(q[1]-p[1])*(a[0]-p[0]))
        f1=sign*((q[0]-p[0])*(b[1]-p[1])-(q[1]-p[1])*(b[0]-p[0]))
        delta=f1-f0
        if abs(delta)<1e-10:
            if f0<0:return None
            continue
        crossing=-f0/delta
        if delta>0:lo=max(lo,crossing)
        else:hi=min(hi,crossing)
        if hi<lo:return None
    return [max(0,lo),min(1,hi)] if hi>=0 and lo<=1 else None

def _subtract_intervals(interval,holes):
    pieces=[interval]
    for lo,hi in sorted(holes):
        nextp=[]
        for a,b in pieces:
            if hi<=a+1e-9 or lo>=b-1e-9:nextp.append([a,b]);continue
            if lo>a+1e-9:nextp.append([a,min(lo,b)])
            if hi<b-1e-9:nextp.append([max(hi,a),b])
        pieces=nextp
    return pieces

def terrace_contract():
    out=[]
    for t in _terrace_data():
        walls=[];outer=t['polygon_xz_m'];holes=[p['polygon_xz_m'] for p in t['exclusions']]
        stair_holes=[s['owned_polygon_xz_m'] for s in actual_stairs() if s.get('terrace_id')==t['id']]
        holes+=stair_holes
        boundaries=[('outer',outer,None)]+[('exclusion',p,i) for i,p in enumerate(holes)]
        for kind,poly,index in boundaries:
            for a,b in zip(poly,poly[1:]+poly[:1]):
                allowed=_line_inside_interval(a,b,outer)
                if allowed is None:continue
                cut=[v for i,p in enumerate(holes) if i!=index and (v:=_line_inside_interval(a,b,p)) is not None]
                for lo,hi in _subtract_intervals(allowed,cut):
                    length=math.dist(a,b)*(hi-lo);n=max(1,math.ceil(length/2))
                    for j in range(n):
                        p=[a[k]+(b[k]-a[k])*(lo+(hi-lo)*j/n) for k in (0,1)]
                        q=[a[k]+(b[k]-a[k])*(lo+(hi-lo)*(j+1)/n) for k in (0,1)]
                        bottom=[dry_height_at(*p),dry_height_at(*q)];top=t['top_y_m']
                        if max(top-y for y in bottom)<.12:continue
                        walls.append(dict(from_xz_m=p,to_xz_m=q,top_y_m=top,bottom_y_m=bottom,
                            thickness_m=.4,boundary_kind=kind,
                            quad_xyz_m=[[p[0],bottom[0],p[1]],[q[0],bottom[1],q[1]],
                                        [q[0],top,q[1]],[p[0],top,p[1]]]))
        record={k:v for k,v in t.items() if k!='bounds_xz_m'}
        record['stair_openings_xz_m']=stair_holes
        record.update(ground_operation='replace dry source height by top_y_m in outer polygon minus exact exclusions',
            retaining_segments=walls,maximum_retaining_height_m=max((w['top_y_m']-min(w['bottom_y_m']) for w in walls),default=0),
            source_resolution='exact outer/exclusion domains; 2m retaining-quad segments are a render proxy, not common final solids',
            road_contract='all roads/paths plus 2m each side excluded; road_height_at unchanged',
            stair_contract='pedestrian stair geometry may replace a bounded outer-edge opening only after clearance selection')
        out.append(record)
    return out


_ACTUAL_STAIR_CACHE=None

def actual_stairs():
    global _ACTUAL_STAIR_CACHE
    if _ACTUAL_STAIR_CACHE is not None:return _ACTUAL_STAIR_CACHE
    _ACTUAL_STAIR_CACHE=[]
    for t in _terrace_data():
        x0,z0,x1,end=t['bounds_xz_m'];selected=None
        for x in range(math.ceil(x0+6),math.floor(x1-6),2):
            top=t['top_y_m'];bottom=dry_height_at(x,end)
            rise=top-bottom
            if not 1.8<=rise<=4.0:continue
            count=math.ceil(rise/.15);run=count*.3;start=end-run
            poly=_rect_poly([x-1.2,start,x+1.2,end])
            # A conservative source check: no road/path/body exclusion may
            # overlap the bounded stair's axis-aligned domain.
            if any(_overlap(_bounds(poly),_bounds(p['polygon_xz_m'])) for p in t['exclusions']):continue
            selected=(x,top,bottom,count,start,end,poly);break
        if selected is None:
            _ACTUAL_STAIR_CACHE.append(dict(id=t['id']+':STAIR',status='no_clear_source_slot_found'))
            continue
        x,top,bottom,count,start,end,poly=selected;rise=(top-bottom)/count
        treads=[];risers=[]
        for i in range(count):
            z=start+i*.3;y=top-(i+1)*rise
            tread=dict(index=i,polygon_xz_m=_rect_poly([x-1.2,z,x+1.2,z+.3]),
                       top_y_m=y,bottom_y_m=min(y,dry_height_at(x,z))-.2,
                       common_shape='bounded rectangular solid through existing common compiler')
            treads.append(tread)
            risers.append(dict(index=i,from_xz_m=[x-1.2,z],to_xz_m=[x+1.2,z],
                               bottom_y_m=y,top_y_m=y+rise,rise_m=rise))
        _ACTUAL_STAIR_CACHE.append(dict(id=t['id']+':STAIR',terrace_id=t['id'],status='source_geometry_ready_uncompiled',
            owned_polygon_xz_m=poly,width_m=2.4,run_m=count*.3,top_y_m=top,bottom_y_m=bottom,
            step_count=count,step_rise_m=rise,step_tread_m=.3,treads=treads,risers=risers,
            collision='actual 0.15m-or-less stair risers; controller step-up NOT yet validated; do not replace with invisible ramp',
            terrain_operation='replace terrace top by discrete tread heights inside exact stair polygon',
            retaining_operation='remove this opening from terrace wall ownership'))
    return _ACTUAL_STAIR_CACHE

def _stair_height_at(x,z):
    for stair in actual_stairs():
        poly=stair.get('owned_polygon_xz_m')
        if poly and _inside(x,z,poly):
            start=poly[0][1];index=min(stair['step_count']-1,max(0,math.floor((z-start)/.3)))
            return stair['treads'][index]['top_y_m']
    return None


_WATER_DOMAIN_CACHE=None

def _clip_source_poly(poly,axis,bound,keep_less):
    if not poly:return []
    result=[];prev=poly[-1];pv=(bound-prev[axis]) if keep_less else (prev[axis]-bound)
    for cur in poly:
        cv=(bound-cur[axis]) if keep_less else (cur[axis]-bound)
        if (pv>=-1e-10)!=(cv>=-1e-10):
            t=pv/(pv-cv);result.append([prev[k]+t*(cur[k]-prev[k]) for k in (0,1)])
        if cv>=-1e-10:result.append(list(cur))
        prev,pv=cur,cv
    return result

def finite_water_domains():
    """Disjoint finite source polygons, including owned bends and bank clips.

    Uses the existing independent source polygon-difference helper. It does not
    create voxels or replace the common mesh compiler.
    """
    global _WATER_DOMAIN_CACHE
    if _WATER_DOMAIN_CACHE is not None:return _WATER_DOMAIN_CACHE
    from world_city.runtime_city.checks.placement import convex_difference, polygon_area, positive_area_overlap
    _WATER_DOMAIN_CACHE=[]
    def convex_hull(points):
        pts=sorted(set(tuple(p) for p in points))
        def half(ps):
            out=[]
            for p in ps:
                while len(out)>1 and (out[-1][0]-out[-2][0])*(p[1]-out[-2][1])-(out[-1][1]-out[-2][1])*(p[0]-out[-2][0])<=0:out.pop()
                out.append(p)
            return out
        return [list(p) for p in half(pts)[:-1]+half(reversed(pts))[:-1]]
    for w in WATER_SURFACES:
        if 'polygon_xz_m' in w:
            _WATER_DOMAIN_CACHE.append(dict(surface_id=w['id'],polygon_xz_m=w['polygon_xz_m'],
                vertex_y_m=[w['water_y_m']]*len(w['polygon_xz_m']),water_y_m=w['water_y_m']))
            continue
        raw=[];owned=[];strips=[]
        for i,(aa,bb) in enumerate(zip(w['polyline_xz_m'],w['polyline_xz_m'][1:])):
            a,b=list(aa),list(bb);length=math.dist(a,b);ux,uz=(b[0]-a[0])/length,(b[1]-a[1])/length
            if w['id']=='SERVICE_CANAL' and i==0:a=[a[0]-ux*8,a[1]-uz*8]
            if w['id']=='SERVICE_CANAL' and i==len(CANAL_POINTS)-2:b=[b[0]+ux*8,b[1]+uz*8]
            poly=_strip(a,b,w['width_m']);strips.append(poly);raw.append((i,'reach',poly))
        for i in range(len(strips)-1):
            poly=convex_hull(strips[i][2:]+strips[i+1][:2])
            if polygon_area(poly)>1e-8:raw.append((i,'bend_join',poly))
        for i,kind,poly in raw:
            clip=w.get('clip_bounds_xz_m')
            if clip:
                for axis,bound,less in [(0,clip[0],False),(1,clip[1],False),(0,clip[2],True),(1,clip[3],True)]:
                    poly=_clip_source_poly(poly,axis,bound,less)
            pieces=[poly] if polygon_area(poly)>1e-8 else []
            for previous in owned:
                if not pieces:break
                pieces=[part for p in pieces for part in (convex_difference(p,previous) if _overlap(_bounds(p),_bounds(previous)) and positive_area_overlap(p,previous,1e-8) else [p]) if polygon_area(part)>1e-8]
            for poly in pieces:
                owned.append(poly)
                _WATER_DOMAIN_CACHE.append(dict(surface_id=w['id'],segment_index=i,part_kind=kind,
                    polygon_xz_m=poly,vertex_y_m=[water_height_at(w['id'],*p,i) for p in poly],
                    interior_height_api='water_height_at(surface_id,x,z,segment_index)',
                    ownership='disjoint source reach/join pieces clipped before receiver; no overlapping same-surface faces'))
    return _WATER_DOMAIN_CACHE


_COMPOUND_CACHE=None

def compound_pads():
    """One level gate datum for each retained noble estate, with finite ownership."""
    global _COMPOUND_CACHE
    if _COMPOUND_CACHE is not None:return _COMPOUND_CACHE
    _COMPOUND_CACHE=[]
    for plot in SOURCE_PLAN.get('plots',[]):
        if plot.get('property_type')!='noble_estate':continue
        gate=plot['gate_position_xz_m'];connection=plot['gate_connection_xz_m']
        outer=_station([gate,connection],2);floor=road_height_at(plot['road_id'],*outer)
        polygon=plot['polygon_xz_m'];landing=_strip(gate,outer,3.4)
        yaw=plot.get('yaw_rad',0);origin=plot['origin_xz_m']
        def world(local):
            xx,zz=local;return [origin[0]+xx*math.cos(yaw)+zz*math.sin(yaw),origin[1]-xx*math.sin(yaw)+zz*math.cos(yaw)]
        service=world([-21,31]);service_outer=world([-21,33])
        apron=[world(p) for p in [[-22.7,31],[1.7,31],[1.7,33],[-22.7,33]]]
        owned=[polygon]+([landing] if landing else [])+[apron]
        b=_bounds(polygon);samples=[gate]+polygon
        for x in range(math.ceil(b[0]),math.floor(b[2])+1,2):
            for z in range(math.ceil(b[1]),math.floor(b[3])+1,2):
                if _inside(x,z,polygon):samples.append([x,z])
        levels=[dry_height_at(*p) for p in samples]
        walls=[]
        for a,c in zip(polygon,polygon[1:]+polygon[:1]):
            run=math.dist(a,c);n=max(1,math.ceil(run/2))
            for i in range(n):
                p=[a[k]+(c[k]-a[k])*i/n for k in (0,1)]
                q=[a[k]+(c[k]-a[k])*(i+1)/n for k in (0,1)]
                mid=[(p[k]+q[k])/2 for k in (0,1)]
                if min(math.dist(mid,gate),math.dist(mid,service))<2.5:continue
                ground=[dry_height_at(*p),dry_height_at(*q)]
                if max(abs(y-floor) for y in ground)<.12:continue
                walls.append(dict(from_xz_m=p,to_xz_m=q,pad_y_m=floor,source_ground_y_m=ground,
                    top_y_m=max(floor,*ground),bottom_y_m=min(floor,*ground),thickness_m=.5,
                    side='rear_or_side_except_explicit_gate_opening',
                    tier_count_for_4m_max=max(1,math.ceil(max(abs(y-floor) for y in ground)/4))))
        _COMPOUND_CACHE.append(dict(id=plot['id']+':COMPOUND_PAD',plot_id=plot['id'],
            floor_y_m=floor,gate_xz_m=gate,gate_landing_outer_xz_m=outer,
            owned_polygons_xz_m=owned,source_plot_polygon_xz_m=polygon,
            local_floor_ownership='entire compound paving/garden/courtyard and all local building bases use this single datum',
            maximum_fill_m=max(0,floor-min(levels)),maximum_cut_m=max(0,max(levels)-floor),
            foundation_bottom_y_m=min(floor,min(levels))-.4,
            retaining_segments=walls,gate_delta_m=0,
            gate_ledger=[dict(id='main',xz_m=gate,threshold_y_m=floor,landing_y_m=floor,delta_m=0),dict(id='service',xz_m=service,threshold_y_m=floor,landing_y_m=floor,delta_m=0)],
            service_gate_path_xz_m=[service,service_outer,outer],service_gate_path_y_m=[floor,floor,floor],
            gate_path_contract='level first2m landing; continue path_height_at to source road at <=12%',
            retaining_tier_policy='walls exceeding4m require stepped structural treatment; source tier count is not engineered geometry',
            geometry_status='finite source pad + proxy top; common compound owns visible floor, ground must be masked under it'))
    return _COMPOUND_CACHE


def finite_water_polygons():
    return finite_water_domains()


_BRIDGE_SUPPORT_CACHE=None

def _bridge_supports():
    global _BRIDGE_SUPPORT_CACHE
    if _BRIDGE_SUPPORT_CACHE is None:
        _BRIDGE_SUPPORT_CACHE=[]
        for bridge in SOURCE_PLAN.get('bridges',[]):
            p=bridge.get('position_xz_m')
            if p and 'water_level_m' in bridge:
                exact=water_samples_at(*p)
                head=max((v['water_y_m'] for v in exact),default=bridge['water_level_m'])
                _BRIDGE_SUPPORT_CACHE.append((p,head))
    return _BRIDGE_SUPPORT_CACHE

def main():
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');args=p.parse_args()
    c=build_contract()
    if args.write:
        if hashlib.sha256(SOURCE_PLAN_PATH.read_bytes()).hexdigest()!=SOURCE_PLAN_SHA256:
            raise RuntimeError('Source plan changed during generation; retry in a fresh process after source freeze')
        (HERE/'contract.json').write_text(json.dumps(c,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'benches':len(BENCHES),'road_profiles':len(c['road_profiles']),
        'water_nodes':len(c['water_graph']['nodes']),'water_edges':len(c['water_graph']['edges']),
        'port':c['port'],'grade_proof':c['grade_proof']},indent=2))
if __name__=='__main__':main()
