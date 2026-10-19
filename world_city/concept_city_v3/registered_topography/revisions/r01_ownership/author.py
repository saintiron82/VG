"""Registered r01: finite surface ownership for review and later common sources.

This is polygon clipping/height authoring, not a voxel mesher. Frozen r0 stays
unchanged. Each returned face has one height owner; never sample the composite
height function across a retained edge. Public road grades remain unchanged.
"""
from __future__ import annotations
import copy, hashlib, json, math
from functools import lru_cache
from pathlib import Path
from ... import author as base
from world_city.concept_city_v3.registered_source.geometry import triangulate
from world_city.concept_city_v3.review_geometry import clean
from world_city.runtime_city.checks import placement as geo
HERE=Path(__file__).resolve().parent
CITY=base.CITY
SOURCE_SHA='685592393dd5b3bffa189d497db8bff14ba4d893d5d81089a66427bd5a6b588c'
BASE_AUTHOR_SHA='c30ef5ad507b9704edc501f79363e64e4c8237626a1c7d89616ddb8cfbe3fec6'
BASE_CONTRACT_SHA='d481ba5351227de4f7d94aa5720931c7496642a3c5e8ac3bf35906ca5b00bf77'
ORDINARY_PATH=CITY/'assemblies/ordinary/registered/resolved_placements.json'
ORDINARY_SHA='3c877b51d78f827285d0109f108dc094c128e50429046fe6eaac1d706aa6027b'
ORDINARY=json.loads(ORDINARY_PATH.read_bytes())
REGION_ORDER=['CASTLE','E7','E6','E5','E4','E3','E2','E1','CLERGY','MARKET','MONASTERY','TRAIN','PORT','POOR','COMMON','NOBLE']
EPS=1e-7
_OWNERS=None;_INDEX=None;_AUDIT=None

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def snapshot_check():
    for path,expected in [(base.REGISTERED_PLAN_PATH,SOURCE_SHA),(base.HERE/'author.py',BASE_AUTHOR_SHA),(base.HERE/'contract.json',BASE_CONTRACT_SHA),(ORDINARY_PATH,ORDINARY_SHA)]:
        if sha(path)!=expected:raise ValueError('Snapshot mismatch: '+str(path))
    if ORDINARY['source_plan_sha256']!=SOURCE_SHA:raise ValueError('Ordinary source mismatch')

def rect(b):return [[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]]]
def centroid(poly):return [sum(p[k] for p in poly)/len(poly) for k in (0,1)]
def convex_parts(poly):
    p=clean(poly)
    if not p:return []
    if geo.is_convex_polygon(p):return [p]
    out=triangulate(p)
    if abs(sum(geo.polygon_area(q) for q in out)-geo.polygon_area(p))>1e-5:raise ValueError('Source polygon decomposition failed')
    return out

def circle(p,r):
    # Circumscribed polygon preserves the complete analytic protected corridor.
    # The only new inferred geometry is <=1 cm outward at rounded joins/caps.
    n=max(16,math.ceil(math.pi/math.acos(r/(r+.01))))
    rr=r/math.cos(math.pi/n)
    return [[p[0]+rr*math.cos(2*math.pi*i/n),p[1]+rr*math.sin(2*math.pi*i/n)] for i in range(n)]

def corridor(points,width):
    for a,b in zip(points,points[1:]):
        p=base._strip(a,b,width)
        if p:yield p
    for p in points:yield circle(p,width/2)

def _source_owners():
    global _OWNERS,_INDEX,_AUDIT
    if _OWNERS is not None:return _OWNERS
    snapshot_check();_OWNERS=[];_INDEX=geo._SpatialIndex(32)
    _AUDIT=dict(ordinary_body_count=len(ORDINARY['placements']),door_count=len(ORDINARY['access_proposals']),body_public_or_water_conflicts=[],landing_public_or_water_conflicts=[])
    def add(id,kind,poly,priority,**kw):
        for i,p in enumerate(convex_parts(poly)):
            _OWNERS.append(dict(owner_id=id,kind=kind,material_hint={'road':'road','road_shoulder':'ground','door_landing':'alley','door_approach':'alley','wall_footing':'ground','terrace':'inherit_district_or_plot','water_hole':'water','building_body_hole':'none'}.get(kind,'ground'),polygon_xz_m=p,priority=priority,render_land=kind not in ('water_hole','building_body_hole'),**kw))
    for w in base.finite_water_polygons():
        add(w['surface_id'],'water_hole',w['polygon_xz_m'],0,surface_id=w['surface_id'],segment_index=w.get('segment_index',0),bed_depth_m=w['bed_depth_m'])
    # Same shared continuous H on every road and its full 2 m shoulders.
    for r in base.REGISTERED_PLAN['roads']:
        for p in corridor(r['polyline_xz_m'],r['width_m']):add(r['id'],'road',p,10,road_id=r['id'])
        for p in corridor(r['polyline_xz_m'],r['width_m']+4):add(r['id']+':SHOULDER','road_shoulder',p,35,road_id=r['id'])
    for p in ORDINARY['placements']:
        add(p['id']+':BODY','building_body_hole',p['actual_body_footprint_xz_m'],20,
            floor_y_m=p['pad_floor_y_m'],source_mass_id=p['source_mass_id'],asset_origin_y_m=p['position_m'][1],
            support_top_y_m=p['pad_floor_y_m']-.05,
            support_bottom_y_m=min(q[1] for q in p['foundation_support']['support_samples_xyz_m'])-.25)
    for a in ORDINARY['access_proposals']:
        floor=a['pad_floor_y_m'];points=a['complete_proposed_connection_xz_m'];stub=a['cached_threshold_stub_xz_m']
        # Exact existing stub and first reserved approach, not an invented porch.
        add(a['id']+':STUB','door_landing',base._strip(*stub,a['width_m']),30,floor_y_m=floor,door_id=a['id'])
        reserved=a['reserved_connection_polygons_xz_m']
        if reserved:add(a['id']+':LANDING','door_landing',reserved[0],30,floor_y_m=floor,door_id=a['id'])
        for i,poly in enumerate(reserved[1:]):
            add(a['id']+':APPROACH','door_approach',poly,31,door_id=a['id'],floor_y_m=floor,
                approach_start_xz_m=points[1],approach_end_xz_m=points[-1],
                status='finite graded source proposal; independent full-width traversal unresolved')
    wall=base.registered_wall()['polygon_xz_m']
    for p in corridor(wall+[wall[0]],4):add('WALL_FOOTING','wall_footing',p,40)
    regions={r['id']:r for r in base.terrace_regions()}
    for i,id in enumerate(REGION_ORDER):
        r=regions[id]
        add(id,'terrace',r['polygon_xz_m'],50+i,floor_y_m=r['floor_y_m'],registration_control_id=id)
    _OWNERS.sort(key=lambda r:(r['priority'],r['owner_id']))
    for i,p in enumerate(_OWNERS):_INDEX.add(i,p['polygon_xz_m'])
    return _OWNERS

def owner_at(x,z):
    owners=_source_owners();q=[x,z]
    for i in sorted(_INDEX.candidates([q])):
        p=owners[i]
        if geo.point_in_convex_polygon(q,p['polygon_xz_m'],1e-8):return p
    return dict(owner_id='BASE_GROUND',kind='ground',priority=100,render_land=True)

def source_surface_height_at(record,x,z):
    """Evaluate the record's side of an interface, including at its boundary."""
    kind=record['kind']
    if kind=='water_hole':return base.water_height_at(record['surface_id'],x,z,record.get('segment_index',0))
    if kind in ('road','road_shoulder'):return base.road_height_at(record['road_id'],x,z)
    if kind=='wall_footing':return base.wall_ground_height_at(x,z)[1]
    if kind=='door_approach':
        _,t=base._project(x,z,record['approach_start_xz_m'],record['approach_end_xz_m'])
        return (1-t)*record['floor_y_m']+t*base.dry_height_at(x,z)
    if 'floor_y_m' in record:return record['floor_y_m']
    return base.land_base_height_at(x,z)

def surface_height_at(record,x,z):
    """Owner-specific height, with a shared 0.25 m linear tile-edge profile.

    Convex subtraction can introduce harmless extra collinear boundary vertices.
    Both tiles interpolate the SAME world-anchored edge profile at those vertices,
    so different subdivisions cannot create vertical T-junction cracks. Interior
    points still evaluate the analytic owner. This is a declared review sampling
    rule; the final common grid uses its own common coordinate planes.
    """
    bounds=record.get('review_tile_bounds_xz_m')
    if bounds and record['kind'] not in ('terrace','door_landing','building_body_hole'):
        x0,z0,x1,z1=bounds
        if abs(x-x0)<1e-7 or abs(x-x1)<1e-7:
            lo=math.floor(z*4+1e-8)/4;hi=lo+.25;t=max(0,min(1,(z-lo)/.25))
            return (1-t)*source_surface_height_at(record,x,lo)+t*source_surface_height_at(record,x,hi)
        if abs(z-z0)<1e-7 or abs(z-z1)<1e-7:
            lo=math.floor(x*4+1e-8)/4;hi=lo+.25;t=max(0,min(1,(x-lo)/.25))
            return (1-t)*source_surface_height_at(record,lo,z)+t*source_surface_height_at(record,hi,z)
    return source_surface_height_at(record,x,z)

def land_height_at(x,z):
    p=owner_at(x,z)
    if p['kind']=='water_hole':return base.land_height_at(x,z)
    return surface_height_at(p,x,z)

def height_at(x,z):
    p=owner_at(x,z)
    h=surface_height_at(p,x,z)
    return h-p['bed_depth_m'] if p['kind']=='water_hole' else h

def road_height_at(id,x,z):return base.road_height_at(id,x,z)
def path_height_at(id,x,z):return base.path_height_at(id,x,z)
def water_height_at(id,x,z,segment_index=0):return base.water_height_at(id,x,z,segment_index)
def water_samples_at(x,z):return base.water_samples_at(x,z)
def finite_water_polygons():return base.finite_water_polygons()
def river_water_y(x):return base.river_water_y(x)
def building_floor_at(x,z):return land_height_at(x,z)

def _edge_points(a,b,points):
    dx,dz=b[0]-a[0],b[1]-a[1];ll=dx*dx+dz*dz
    if ll<1e-16:return [a]
    found={0.:a,1.:b}
    for q in points:
        t=((q[0]-a[0])*dx+(q[1]-a[1])*dz)/ll
        if 1e-8<t<1-1e-8 and abs(dx*(q[1]-a[1])-dz*(q[0]-a[0]))<1e-7*math.sqrt(ll):found[round(t,10)]=q
    return [found[t] for t in sorted(found)]

def conform_domains(records,extra_points=()):
    """Insert every shared T vertex, keeping polygon pieces convex."""
    points=[q for p in records for q in p['polygon_xz_m']]+list(extra_points)
    for p in records:
        ring=p['polygon_xz_m'];out=[]
        for a,b in zip(ring,ring[1:]+ring[:1]):out.extend(_edge_points(a,b,points)[:-1])
        p['polygon_xz_m']=out
    return records

def surface_domains(bounds_xz_m,conform=True):
    """Complete disjoint finite owner partition for a <=32 m review tile.

    Holes are explicit records. Skip render_land=False, then render the separate
    water/asset surface. Clip further assembly floor masks before triangulation.
    Owner polygons include global tile-edge crossing points for consistent seams.
    """
    x0,z0,x1,z1=bounds_xz_m
    if not(0<x1-x0<=32 and 0<z1-z0<=32):raise ValueError('Ownership queries must be positive and <=32 m on each axis')
    tile=rect(bounds_xz_m);remaining=[tile];out=[];owners=_source_owners();extra=[]
    for i in sorted(_INDEX.candidates(tile)):
        owner=owners[i];mask=clean(geo.convex_intersection(tile,owner['polygon_xz_m']))
        # Include raw boundary intersections even when this owner has no area here.
        raw=geo.convex_intersection(tile,owner['polygon_xz_m']);extra.extend(raw)
        if not mask:continue
        new=[]
        for p in remaining:
            if not geo.positive_area_overlap(p,mask,0):new.append(p);continue
            intersection=clean(geo.convex_intersection(p,mask))
            if intersection:
                r={k:v for k,v in owner.items() if k!='polygon_xz_m'};r['polygon_xz_m']=intersection;out.append(r)
            new.extend(q for part in geo.convex_difference(p,mask) if(q:=clean(part)))
        remaining=new
    out.extend(dict(owner_id='BASE_GROUND',kind='ground',priority=100,render_land=True,material_hint='inherit_district_or_plot',polygon_xz_m=p) for p in remaining)
    # Every integer world metre on tile edges is a stable shared sample, regardless
    # of which neighboring tile is queried first. Source crossing points above
    # handle narrow roads, pad corners and water strips.
    for iz in range(math.ceil(z0*4),math.floor(z1*4)+1):extra.extend([[x0,iz/4],[x1,iz/4]])
    for ix in range(math.ceil(x0*4),math.floor(x1*4)+1):extra.extend([[ix/4,z0],[ix/4,z1]])
    for r in out:r['review_tile_bounds_xz_m']=list(bounds_xz_m)
    return conform_domains(out,extra) if conform else out

def retaining_interfaces(bounds_xz_m,records=None):
    """Explicit riser quads at real owner changes; no walls across road centers.

    Stable interface IDs allow duplicate removal when neighboring tile results
    share a boundary. Water edges are owned by water_support instead.
    """
    records=records if records is not None else surface_domains(bounds_xz_m)
    out=[];seen=set()
    for rec in records:
        p=rec['polygon_xz_m']
        for a,b in zip(p,p[1:]+p[:1]):
            length=math.dist(a,b)
            if length<1e-7:continue
            key=tuple(sorted((tuple(round(v,7) for v in a),tuple(round(v,7) for v in b))))
            if key in seen:continue
            seen.add(key);nx,nz=-(b[1]-a[1])/length*1e-5,(b[0]-a[0])/length*1e-5
            m=[(a[k]+b[k])/2 for k in (0,1)]
            left=owner_at(m[0]+nx,m[1]+nz);right=owner_at(m[0]-nx,m[1]-nz)
            if left['owner_id']==right['owner_id'] or 'water_hole' in (left['kind'],right['kind']):continue
            left=dict(left,review_tile_bounds_xz_m=list(bounds_xz_m));right=dict(right,review_tile_bounds_xz_m=list(bounds_xz_m))
            ys=[[surface_height_at(r,*q) for q in (a,b)] for r in (left,right)]
            if max(abs(ys[0][i]-ys[1][i]) for i in(0,1))<1e-6:continue
            ident=hashlib.sha256(json.dumps(key).encode()).hexdigest()[:18]
            high=left if sum(ys[0])>=sum(ys[1]) else right
            out.append(dict(id='INTERFACE_'+ident,from_xz_m=a,to_xz_m=b,
                left_owner_id=left['owner_id'],right_owner_id=right['owner_id'],
                left_y_m=ys[0],right_y_m=ys[1],retaining_owner_id=high['owner_id'],
                vertices_xyz_m=[[a[0],ys[0][0],a[1]],[b[0],ys[0][1],b[1]],[b[0],ys[1][1],b[1]],[a[0],ys[1][0],a[1]]],
                thickness_m=.3,collision_semantics='intentional retaining barrier; no stair or walkability claim'))
    return out

def ordinary_foundation_contracts():
    """Source support boxes under actual body footprints, with no asset raising."""
    return [dict(source_mass_id=p['source_mass_id'],polygon_xz_m=p['actual_body_footprint_xz_m'],
        floor_y_m=p['pad_floor_y_m'],asset_origin_y_m=p['position_m'][1],
        top_y_m=p['pad_floor_y_m']-.05,bottom_y_m=min(p['pad_floor_y_m']-.55,*[q[1]-.25 for q in p['foundation_support']['support_samples_xyz_m']]),
        terrain_cut_rule='remove exact body surface and terrain intrusion above floor; side cut retained explicitly',
        common_status='finite source solid, not yet common-compiled') for p in ORDINARY['placements']]

def gate_audit():
    path=CITY/'assemblies/property/registered/generated/gate_proposals.json';data=json.loads(path.read_bytes())
    if data['registered_source_sha256']!=SOURCE_SHA:raise ValueError('Gate snapshot mismatch')
    out=[]
    for prop in data['records']:
        for g in prop['gates']:
            pts=[g['center_xz_m'],g['outside_point_xz_m'],g['external_source_link_xz_m']]
            length=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]));road=base.road_height_at(g['external_road_id'],*pts[-1]);floor=prop['floor_y_m']
            out.append(dict(property_id=prop['property_id'],gate_id=g['id'],floor_y_m=floor,road_y_m=road,
                source_link_length_m=length,minimum_ramp_grade=abs(road-floor)/length,
                gate_existing_surface_y_m=base.land_height_at(*pts[0]),
                status='requires_explicit_full_width_link_and_ownership_audit' if abs(road-floor)>1e-6 else 'datum_matches; finite gate ownership still required'))
    return dict(proposal_sha256=sha(path),source_plan_sha256=SOURCE_SHA,records=out,
        acceptance='No gate promoted; best-case average grade is not a full-width collision proof')

def build_contract():
    snapshot_check();c=json.loads((base.HERE/'contract.json').read_bytes())
    graph=c['water_graph'];last='EAST_CHANNEL_VISIBLE:'+str(len(base.WATER_BY_ID['EAST_CHANNEL_VISIBLE']['polyline_xz_m'])-1)
    graph['edges'].append(dict(source=last,target='RIVER_OUTFALL',mode='gravity',role='explicit missing receiving-network link; same physical terminus'))
    c.update(schema='riverstone.registered_terrain.r01_exact_ownership.v1',revision='r01_ownership',
        base_author_sha256=BASE_AUTHOR_SHA,base_contract_sha256=BASE_CONTRACT_SHA,ordinary_pack_sha256=ORDINARY_SHA,
        status='bounded render-ready source polygons; no common compile or traversal approval',
        exact_surface_ownership=dict(module='world_city.concept_city_v3.registered_topography.revisions.r01_ownership.author',api='surface_domains(bounds_xz_m)',maximum_query_span_m=32,
            height_api='surface_height_at(record,x,z)',interface_api='retaining_interfaces(bounds_xz_m,records=None)',
            precedence=['finite water hole','actual travel lane','actual ordinary body hole','actual door landing','reserved approach','unoccupied 2m shoulder support','wall footing','ordered exact terraces','continuous regional support'],
            render_rule='skip render_land=false; triangulate each convex piece at its own height API; never resample composite land_height_at on both sides',
            road_layer_rule='road pieces replace the same terrain surface; omit duplicate zero-offset road ribbons',
            assembly_floor_rule='further exact common floor masks replace their terrain tops; floor ownership is never a display lift',
            finite_corridor_join_tolerance_m=.01,cap_policy='circumscribed polygon; original analytic protected width is entirely preserved',
            seam_rule='conform_domains inserts internal shared T vertices; tile edges use a global 0.25m linear owner profile, so extra collinear subdivision vertices have identical interpolated height on both sides',
            geometry_backend='existing placement convex_intersection/convex_difference and registered_source polygon triangulation'),
        ordinary_foundations=ordinary_foundation_contracts(),gate_audit=gate_audit(),
        neighborhood_terraces=[],
        ownership_limits=['Wall vertex 4 intersects a public shoulder away from declared gate; road priority retained, wall support/route opening requires explicit review.',
            'Actual traffic lanes and water win over bodies/landings; unoccupied 2m shoulder support is clipped by actual body/entrance domains, not an invented mandatory sidewalk.',
            'Reserved approach surfaces can be steeper than 12%; no stair is invented and no cart/capsule pass is claimed.',
            'Old sampled retaining proxies are disabled; consume exact retaining_interfaces instead.'],
        voxel_stage_plan=dict(global_grid_origin_m=[0,0,0],macro_pitch_m=2,macro_chunk_size_m=32,medium_support_pitch_m=.5,
            fine_pitch_m=.1,fine_shell_depth_m=.2,buried_support_overlap_m=.2,
            promotion='only owned roads, shoulders, entry landings and explicit stair/retaining patches; no citywide fine fill',
            common_backend='coordinate_planes/core/render_data only',
            collision='continuous source-owned road proxy separate from intentional discrete risers',
            compile_status='not started; count owned square metres and candidate cells before allocation'))
    return c

def main():
    c=build_contract();(HERE/'contract.json').write_text(json.dumps(c,indent=2,sort_keys=True)+'\n')
    (HERE/'gate_audit.json').write_text(json.dumps(c['gate_audit'],indent=2)+'\n')
    print(json.dumps(dict(source_plan_sha256=SOURCE_SHA,contract_sha256=sha(HERE/'contract.json'),ordinary_pack_sha256=ORDINARY_SHA)))
if __name__=='__main__':main()
