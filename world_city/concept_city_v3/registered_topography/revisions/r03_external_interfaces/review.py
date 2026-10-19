"""Read-only cached evaluator of sealed r02, preserving float height semantics."""
import hashlib,json,math
from functools import lru_cache
from ..r02_assembly_overlay import author as prior
from world_city.runtime_city.checks import placement as geo
base=prior.previous.base
REGIONS=tuple(base.terrace_regions())
MAX_CACHE=262144

@lru_cache(maxsize=MAX_CACHE)
def dry_height_at(x,z):return base.dry_height_at(x,z)

@lru_cache(maxsize=MAX_CACHE)
def land_base_height_at(x,z):
    h=dry_height_at(x,z)
    for region in REGIONS:
        if region['id']=='NOBLE':continue
        poly=region['polygon_xz_m'];distance=0 if base._inside(x,z,poly) else min(base._project(x,z,p,q)[0] for p,q in zip(poly,poly[1:]+poly[:1]))
        h=max(h,region['floor_y_m']-.12*distance)
    return h

@lru_cache(maxsize=MAX_CACHE)
def owner_at(x,z):return prior.owner_at(x,z)
@lru_cache(maxsize=MAX_CACHE)
def wall_height_at(x,z):return base.wall_ground_height_at(x,z)[1]
@lru_cache(maxsize=MAX_CACHE)
def water_height_at(id,x,z,segment_index=0):return prior.water_height_at(id,x,z,segment_index)

def source_surface_height_at(record,x,z):
    kind=record['kind']
    if kind=='water_hole':return water_height_at(record['surface_id'],x,z,record.get('segment_index',0))
    if kind in ('road','road_shoulder'):return dry_height_at(x,z)
    if kind=='wall_footing':return wall_height_at(x,z)
    if kind=='door_approach':
        _,t=base._project(x,z,record['approach_start_xz_m'],record['approach_end_xz_m'])
        return (1-t)*record['floor_y_m']+t*dry_height_at(x,z)
    if 'floor_y_m' in record:return record['floor_y_m']
    return land_base_height_at(x,z)

def surface_height_at(record,x,z):
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

def surface_domains(bounds_xz_m,conform=True):return prior.surface_domains(bounds_xz_m,conform)
def road_height_at(id,x,z):return dry_height_at(x,z)
def path_height_at(id,x,z):return dry_height_at(x,z)
def finite_water_polygons():return prior.finite_water_polygons()
def water_samples_at(x,z):return prior.water_samples_at(x,z)
def river_water_y(x):return prior.river_water_y(x)
def land_height_at(x,z):
    p=owner_at(x,z)
    return base.land_height_at(x,z) if p['kind']=='water_hole' else source_surface_height_at(p,x,z)
def height_at(x,z):
    p=owner_at(x,z);y=source_surface_height_at(p,x,z)
    return y-p['bed_depth_m'] if p['kind']=='water_hole' else y
def building_floor_at(x,z):return land_height_at(x,z)

def _uniform_owner_proof(bounds,records):
    """Conservative exact polygon proof including a 0.1 mm exterior collar."""
    ids={r['owner_id'] for r in records}
    if len(ids)!=1:return False
    id=next(iter(ids));x0,z0,x1,z1=bounds;tile=prior.previous.rect([x0-.0001,z0-.0001,x1+.0001,z1+.0001])
    owners=prior.previous._source_owners();candidates=[owners[i] for i in sorted(prior.previous._INDEX.candidates(tile))]
    candidates=[p for p in candidates if not prior.is_excluded(p,prior.DEFAULT_EXCLUDED_SOURCE_IDS) and geo.positive_area_overlap(tile,p['polygon_xz_m'],0)]
    if id=='BASE_GROUND':return not candidates
    if not candidates:return False
    first=candidates[0]
    return first['owner_id']==id and geo.convex_polygon_contains(first['polygon_xz_m'],tile,0)

def retaining_interfaces(bounds_xz_m,records=None):
    records=records if records is not None else surface_domains(bounds_xz_m)
    if _uniform_owner_proof(bounds_xz_m,records):return []
    out=[];seen=set()
    for rec in records:
        p=rec['polygon_xz_m']
        for a,b in zip(p,p[1:]+p[:1]):
            length=math.dist(a,b)
            if length<1e-7:continue
            key=tuple(sorted((tuple(round(v,7) for v in a),tuple(round(v,7) for v in b))))
            if key in seen:continue
            seen.add(key);nx,nz=-(b[1]-a[1])/length*1e-5,(b[0]-a[0])/length*1e-5;m=[(a[k]+b[k])/2 for k in(0,1)]
            left=owner_at(m[0]+nx,m[1]+nz);right=owner_at(m[0]-nx,m[1]-nz)
            if left['owner_id']==right['owner_id'] or 'water_hole' in (left['kind'],right['kind']):continue
            left=dict(left,review_tile_bounds_xz_m=list(bounds_xz_m));right=dict(right,review_tile_bounds_xz_m=list(bounds_xz_m))
            ys=[[surface_height_at(r,*q) for q in(a,b)] for r in(left,right)]
            if max(abs(ys[0][i]-ys[1][i]) for i in(0,1))<1e-6:continue
            high=left if sum(ys[0])>=sum(ys[1]) else right
            out.append(dict(id='INTERFACE_'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:18],from_xz_m=a,to_xz_m=b,
                left_owner_id=left['owner_id'],right_owner_id=right['owner_id'],left_y_m=ys[0],right_y_m=ys[1],retaining_owner_id=high['owner_id'],
                vertices_xyz_m=[[a[0],ys[0][0],a[1]],[b[0],ys[0][1],b[1]],[b[0],ys[1][1],b[1]],[a[0],ys[1][0],a[1]]],thickness_m=.3,
                collision_semantics='intentional retaining barrier; no stair or walkability claim'))
    return out

def build_contract():
    c=prior.build_contract();c['review_evaluator']=dict(module='world_city.concept_city_v3.registered_topography.revisions.r03_external_interfaces.review',
        source_semantics='identical sealed r02 ownership and heights; immutable precomputed terrace polygons and bounded LRU caches only',
        max_cache_entries_per_function=MAX_CACHE,retaining_skip_rule='exact convex coverage proof over tile plus0.1mm collar; never skip merely because tile samples agree')
    return c
