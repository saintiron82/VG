"""Explicit approximate spatial-preview LOD over r04 exact ownership.

Global2m edge interpolation in inactive ground, global.25m near active owners.
Neither collision nor source terrain is replaced by this review-only sampler.
"""
import math,json,hashlib
from pathlib import Path
from functools import lru_cache
from ..r04_assembly_ownership import author as prior
from world_city.runtime_city.checks import placement as geo
HERE=Path(__file__).resolve().parent
COARSE_PITCH=2.;DETAIL_PITCH=.25
INACTIVE_KINDS={'ground','terrace'}
COOWN_PATH=prior.CITY/'assemblies/landmarks/registered/port_r02_ownership/finite_coownership_addendum.json'
COOWN=json.loads(COOWN_PATH.read_bytes());COOWN_SHA=prior.sha(COOWN_PATH)
COOWN_REGIONS=COOWN['shared_regions'];COOWN_INDEX=geo._SpatialIndex(16)
for i,r in enumerate(COOWN_REGIONS):COOWN_INDEX.add(i,r['polygon_xz_m'])

def port_owner_at(x,z):
    for i in sorted(COOWN_INDEX.candidates([[x,z]])):
        r=COOWN_REGIONS[i]
        if geo.point_in_convex_polygon([x,z],r['polygon_xz_m'],1e-8):
            return dict(owner_id='PORT_QUAY_3_8:R05_SHARED:'+str(i),kind='port_common_hole',render_land=False,material_hint='none',floor_y_m=2.2,road_id='PORT_BRIDGE_TIE',travel_semantics='same-level common-apron ownership, original6m tie retained')
    return None

def apply_port_coownership(records):
    out=[]
    for r in records:
        if r['kind']!='port_tie':out.append(r);continue
        pieces=[r['polygon_xz_m']]
        for i in sorted(COOWN_INDEX.candidates(r['polygon_xz_m'])):
            new=[];mask=COOWN_REGIONS[i]['polygon_xz_m']
            for p in pieces:
                q=prior.clean(geo.convex_intersection(p,mask))
                if q:
                    out.append(dict(owner_id='PORT_QUAY_3_8:R05_SHARED:'+str(i),kind='port_common_hole',render_land=False,material_hint='none',floor_y_m=2.2,road_id='PORT_BRIDGE_TIE',polygon_xz_m=q,review_tile_bounds_xz_m=r['review_tile_bounds_xz_m']))
                    new.extend(q for cut in geo.convex_difference(p,mask) if(q:=prior.clean(cut)))
                else:new.append(p)
            pieces=new
        out.extend(dict(r,polygon_xz_m=p) for p in pieces)
    return out


def _edge_points(axis,fixed,lo,hi):return [[fixed,lo],[fixed,hi]] if axis=='z' else [[lo,fixed],[hi,fixed]]
@lru_cache(maxsize=131072)
def edge_pitch(axis,fixed,coarse_start):
    points=_edge_points(axis,fixed,coarse_start,coarse_start+COARSE_PITCH);owners=prior._owners()
    # Exact convex interval intersection; do not decide detail from sparse point
    # samples that could miss a narrow door or water strip.
    for i in prior.INDEX.candidates(points):
        r=owners[i]
        if r['kind'] in INACTIVE_KINDS:continue
        if prior.base._line_interval(points[0],points[1],r['polygon_xz_m']) is not None:return DETAIL_PITCH
    return COARSE_PITCH

def edge_knots(axis,fixed,lo,hi):
    out=[]
    for n in range(math.floor(lo/COARSE_PITCH),math.floor(hi/COARSE_PITCH)+1):
        start=n*COARSE_PITCH;p=edge_pitch(axis,fixed,start)
        for k in range(round(COARSE_PITCH/p)+1):
            v=start+k*p
            if lo-1e-8<=v<=hi+1e-8:out.append([fixed,v] if axis=='z' else [v,fixed])
    return out

def surface_domains(bounds_xz_m,conform=True):
    rs=apply_port_coownership(prior.surface_domains(bounds_xz_m,conform=False))
    if not conform:return rs
    x0,z0,x1,z1=bounds_xz_m;extra=[]
    for x in (x0,x1):extra+=edge_knots('z',x,z0,z1)
    for z in (z0,z1):extra+=edge_knots('x',z,x0,x1)
    return prior.old.conform_domains(rs,extra)

def source_surface_height_at(r,x,z):return prior.source_surface_height_at(r,x,z)
def surface_height_at(r,x,z):
    if r['kind'] in ('property_lane_handoff','replacement_road','common_floor_hole','property_common_hole','port_common_hole','terrace','door_landing','building_body_hole'):
        return prior.surface_height_at(r,x,z)
    # Preserve the tiny property common/public triangle handoff verbatim.
    if r['kind']=='road':
        prior._owners()
        if any(geo.point_in_convex_polygon([x,z],prior.HANDOFFS[i]['polygon_xz_m'],1e-7) for i in prior.HANDOFF_INDEX.candidates([[x,z]])):
            return prior.surface_height_at(r,x,z)
    bounds=r.get('review_tile_bounds_xz_m')
    if bounds:
        x0,z0,x1,z1=bounds
        if abs(x-x0)<1e-7 or abs(x-x1)<1e-7:axis,fixed,value='z',x,z
        elif abs(z-z0)<1e-7 or abs(z-z1)<1e-7:axis,fixed,value='x',z,x
        else:return source_surface_height_at(r,x,z)
        start=math.floor(value/COARSE_PITCH+1e-9)*COARSE_PITCH;p=edge_pitch(axis,fixed,start)
        lo=math.floor(value/p+1e-8)*p;hi=lo+p;t=max(0,min(1,(value-lo)/p));a,b=_edge_points(axis,fixed,lo,hi)
        return (1-t)*source_surface_height_at(r,*a)+t*source_surface_height_at(r,*b)
    return source_surface_height_at(r,x,z)

def retaining_interfaces(bounds,records=None):
    # Re-evaluate the existing exact side polygons with this declared preview
    # profile, without modifying either source or previous evaluator.
    out=[]
    for r in prior.retaining_interfaces(bounds,records):
        a,b=r['from_xz_m'],r['to_xz_m'];m=[(a[k]+b[k])/2 for k in (0,1)];L=math.dist(a,b);n=[-(b[1]-a[1])/L*1e-5,(b[0]-a[0])/L*1e-5]
        owners=[prior.owner_at(*(m[k]+s*n[k] for k in (0,1))) for s in (1,-1)]
        ys=[[surface_height_at(dict(o,review_tile_bounds_xz_m=bounds),*p) for p in (a,b)] for o in owners]
        out.append(dict(r,left_y_m=ys[0],right_y_m=ys[1],vertices_xyz_m=[[a[0],ys[0][0],a[1]],[b[0],ys[0][1],b[1]],[b[0],ys[1][1],b[1]],[a[0],ys[1][0],a[1]]]))
    return out
def owner_at(x,z):
    r=prior.owner_at(x,z)
    return (port_owner_at(x,z) or r) if r['kind']=='port_tie' else r
land_height_at=prior.land_height_at;height_at=prior.height_at
road_height_at=prior.road_height_at;path_height_at=prior.path_height_at
finite_water_polygons=prior.finite_water_polygons;water_samples_at=prior.water_samples_at
water_height_at=prior.water_height_at;river_water_y=prior.river_water_y
ordinary_foundation_contracts=prior.ordinary_foundation_contracts

def build_contract():
    metadata=dict(schema='riverstone.registered_spatial_preview_lod.r05.v1',source_plan_sha256=prior.old.SOURCE_SHA,prior_author_sha256=prior.sha(prior.HERE/'author.py'),
        coarse_edge_pitch_m=COARSE_PITCH,active_edge_pitch_m=DETAIL_PITCH,world_grid_origin_xz_m=[0,0],
        detail_rule='Any exact active-owner intersection with a global2m edge interval promotes that whole interval to.25m; no sample-only feature detection.',
        height_rule='Linear edge interpolation at the chosen shared global pitch; actual convex ownership cuts and all returned boundary/T vertices retained.',
        coarse_ground_edge_error_bound_m=.12,coarse_bound_basis='Inactive ground base is max of <=12%-Lipschitz fields; a2m linear edge interpolant deviates by at most L*length/2=.12m. Flat terraces have zero error.',
        interior_mesh_rule='Bounded tile triangulation remains an explicit spatial proxy. See measured error ledger; this is not a collision replacement or byte-identical r02.',
        known_limit='Different height-owner discontinuities still need retaining sides; LOD does not heal grade-design failures.',
        status='candidate preview sampler; use measured metrics before whole-city export')

    c=prior.build_contract();c['preview_lod']=metadata
    c['port_coownership']=COOWN
    c['references'][str(COOWN_PATH.relative_to(prior.CITY))]=COOWN_SHA
    c['activation_requirements']=[s for s in c['activation_requirements'] if not s.startswith('Apply exact PORT_BRIDGE_TIE cut')]
    c['activation_requirements'].append('Port apron3_8 remains unchanged: exact158-piece proof certifies59.55628342446m² of same-level2.2m tie overlap. Its21finite shared masks suppress the duplicate tie surface and retain travel semantics. Use derived936 bridge cap.')
    c.setdefault('review_bounds_xz_m',[-580,-520,580,590])
    c['review_module']='world_city.concept_city_v3.registered_topography.revisions.r05_preview_lod.review'
    return c
