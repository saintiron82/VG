"""Exact, bounded assembly ownership over sealed r02. No scene/compiler edits.

Use only when the named replacement assemblies and finite common-solid cuts are
also activated. Wet bridge and dock surfaces remain independent elevated layers.
"""
import hashlib,json,math
from pathlib import Path
from functools import lru_cache
from ..r03_external_interfaces import review,interfaces
from . import bridge,port_tie
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import clean
HERE=Path(__file__).resolve().parent
prior=review.prior;old=prior.previous;base=review.base;CITY=old.CITY
PROPERTY_PATH=CITY/'assemblies/property/registered/r1/repair_01/resolved_placements.json'
PROPERTY_SHA='aa8fd088eca6a1ba9a9012f7bd004132be1c84c74837e0def3ecfb6a341be152'
PORT_PATH=CITY/'assemblies/landmarks/registered/port_r01/resolved_placements.json'
MARKET_PATH=CITY/'assemblies/market/registered/resolved_placements.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
PROPERTY=json.loads(PROPERTY_PATH.read_bytes());PORT=json.loads(PORT_PATH.read_bytes());MARKET=json.loads(MARKET_PATH.read_bytes())
if sha(PROPERTY_PATH)!=PROPERTY_SHA:raise ValueError('Property repair pack changed')
for value in (PROPERTY['registered_source_sha256'],PORT['source_plan']['sha256'],MARKET['source_plan_sha256']):
    if value!=old.SOURCE_SHA:raise ValueError('Mixed source revisions')
EXCLUDED=tuple(sorted({'B_REG_0191','B_PORT_0'}|{s for r in PROPERTY['replacement_ledger'] for s in r['source_building_ids']}))
REPLACED_ROADS={'MARKET_PROCESSION'}
OWNERS=None;INDEX=None;HANDOFF_INDEX=geo._SpatialIndex(32);HANDOFFS=[]

def point_y(triangle,x,z):
    a,b,c=triangle;ux,uz=b[0]-a[0],b[2]-a[2];vx,vz=c[0]-a[0],c[2]-a[2];d=ux*vz-uz*vx
    if abs(d)<1e-12:raise ValueError('Degenerate profile triangle')
    u=((x-a[0])*vz-(z-a[2])*vx)/d;v=(ux*(z-a[2])-uz*(x-a[0]))/d
    return a[1]+u*(b[1]-a[1])+v*(c[1]-a[1])

def _owners():
    global OWNERS,INDEX
    if OWNERS is not None:return OWNERS
    out=[]
    def add(poly,**r):
        p=clean(poly)
        if p:out.append(dict(polygon_xz_m=p,material_hint='stone',**r))
    for r in old._source_owners():
        if prior.is_excluded(r,EXCLUDED) or r.get('road_id') in REPLACED_ROADS:continue
        out.append(dict(r))
    for road in MARKET['access_overlay']['replace_roads']:
        for i,p in enumerate(old.corridor(road['polyline_xz_m'],road['width_m'])):
            add(p,owner_id=road['id']+':R04:'+str(i),kind='replacement_road',road_id=road['id'],priority=8,render_land=True,floor_y_m=4.)
    for i,p in enumerate(port_tie.DOMAINS):
        add(p,owner_id='PORT_BRIDGE_TIE:R04:'+str(i),kind='port_tie',road_id='PORT_BRIDGE_TIE',priority=6,render_land=True)
    # Water owns the underlying ground partition. Bridge deck is independently
    # rendered above it; only its finite dry intersection suppresses dry ground.
    for r in bridge.dry_ground_replacement_domains():
        add(r['polygon_xz_m'],owner_id=r['owner_id'],kind='bridge_hole',priority=5,render_land=False)
    for f in interfaces.FLOORS:
        add(f['polygon_xz_m'],owner_id=f['id'],kind='common_floor_hole',priority=19,render_land=False,floor_y_m=f['floor_y_m'],support_bottom_y_m=f['support_bottom_y_m'])
    # Project each actual sampled upward face; broad logical plot polygons are
    # never terrain masks. Shared wall caps do not invent walkable ramps.
    for mask in PROPERTY['ownership_masks']:
        for i,f in enumerate(mask['compiled_upward_faces']):
            add(f['polygon_xz_m'],owner_id=mask['owner_id']+':face:'+str(i),kind='property_common_hole',priority=19,render_land=False,
                property_id=mask['property_id'],floor_y_m=f['y_m'],logical_floor_y_m=mask['floor_y_m'],surface_material=f['material'])
    for access in PROPERTY['external_access_surfaces']:
        for i,t in enumerate(access['triangulated_top_surface']):
            if t['kind']!='public_lane_threshold_landing':continue
            # This tiny explicit handoff owns the road-side terminal datum. Its
            # linear edge is shared verbatim, rather than resampling curved H.
            add([[v[0],v[2]] for v in t['vertices_xyz_m']],owner_id=access['id']+':handoff:'+str(i),kind='property_lane_handoff',
                priority=9,render_land=False,triangle_xyz_m=t['vertices_xyz_m'],property_id=access['property_id'])
    quay=[r['polygon_xz_m'] for r in old._source_owners() if r['kind']=='road' and r.get('road_id')=='PORT_QUAY']
    for f in PORT['owned_floors']:
        if f['datum']=='pier_top_plus2.2':continue
        add(f['polygon_xz_m'],owner_id=f['id'],kind='port_common_hole',priority=19,render_land=False,floor_y_m=f['floor_y_m'])
        for i,p in enumerate(quay):
            q=clean(geo.convex_intersection(f['polygon_xz_m'],p))
            if q:add(q,owner_id=f['id']+':same_level_quay:'+str(i),kind='port_common_hole',priority=9,render_land=False,floor_y_m=2.2,road_id='PORT_QUAY',travel_semantics='retained through same-level common apron')
    OWNERS=sorted(out,key=lambda r:r['priority']);INDEX=geo._SpatialIndex(32)
    for i,r in enumerate(OWNERS):
        INDEX.add(i,r['polygon_xz_m'])
        if r['kind']=='property_lane_handoff':
            HANDOFF_INDEX.add(len(HANDOFFS),r['polygon_xz_m']);HANDOFFS.append(r)
    return OWNERS

@lru_cache(maxsize=262144)
def owner_at(x,z):
    owners=_owners()
    for i in sorted(INDEX.candidates([[x,z]])):
        r=owners[i]
        if geo.point_in_convex_polygon([x,z],r['polygon_xz_m'],1e-8):return r
    return dict(owner_id='BASE_GROUND',kind='ground',priority=100,render_land=True,material_hint='inherit_district_or_plot')

def surface_domains(bounds_xz_m,conform=True):
    x0,z0,x1,z1=bounds_xz_m
    if max(x1-x0,z1-z0)>32.000001:raise ValueError('Query bounded tiles no larger than32m')
    owners=_owners();remaining=[old.rect(bounds_xz_m)];out=[]
    for i in sorted(INDEX.candidates(remaining[0])):
        r=owners[i];new=[]
        for p in remaining:
            if not geo.positive_area_overlap(p,r['polygon_xz_m'],0):new.append(p);continue
            q=clean(geo.convex_intersection(p,r['polygon_xz_m']))
            if q:out.append(dict(r,polygon_xz_m=q,review_tile_bounds_xz_m=list(bounds_xz_m)))
            new.extend(q for part in geo.convex_difference(p,r['polygon_xz_m']) if(q:=clean(part)))
        remaining=new
        if not remaining:break
    out.extend(dict(owner_id='BASE_GROUND',kind='ground',priority=100,render_land=True,material_hint='inherit_district_or_plot',polygon_xz_m=p,review_tile_bounds_xz_m=list(bounds_xz_m)) for p in remaining)
    if not conform:return out
    extra=[]
    for iz in range(math.ceil(z0*4),math.floor(z1*4)+1):extra.extend([[x0,iz/4],[x1,iz/4]])
    for ix in range(math.ceil(x0*4),math.floor(x1*4)+1):extra.extend([[ix/4,z0],[ix/4,z1]])
    return old.conform_domains(out,extra)

def source_surface_height_at(r,x,z):
    if r['kind']=='port_tie':return port_tie.height_at(x,z)
    if r['kind']=='bridge_hole':return port_tie.junction_height_at(x,z)
    if r['kind']=='property_lane_handoff':return point_y(r['triangle_xyz_m'],x,z)
    return review.source_surface_height_at(r,x,z)

def surface_height_at(r,x,z):
    # Exact rendered shared-edge interpolation: road triangles meeting a
    # common terminal face inherit its finite linear edge, including T knots.
    # This is a finite mesh handoff, not a claim the old analytic field changed.
    if r['kind']=='road':
        _owners()
        for i in sorted(HANDOFF_INDEX.candidates([[x,z]])):
            h=HANDOFFS[i]
            if geo.point_in_convex_polygon([x,z],h['polygon_xz_m'],1e-7):
                return point_y(h['triangle_xyz_m'],x,z)
    if r['kind'] in ('port_tie','bridge_hole','property_lane_handoff','replacement_road','common_floor_hole','property_common_hole','port_common_hole'):
        return source_surface_height_at(r,x,z)
    return review.surface_height_at(r,x,z)

def road_height_at(id,x,z):
    if id=='PORT_BRIDGE_TIE':return port_tie.height_at(x,z)
    if id=='MAIN_BRIDGE':return port_tie.junction_height_at(x,z)
    if id=='MARKET_PROCESSION':return 4.
    r=owner_at(x,z)
    if r['kind']=='property_lane_handoff':return source_surface_height_at(r,x,z)
    return review.road_height_at(id,x,z)
def land_height_at(x,z):
    r=owner_at(x,z)
    return base.land_height_at(x,z) if r['kind']=='water_hole' else source_surface_height_at(r,x,z)
def height_at(x,z):
    r=owner_at(x,z);y=source_surface_height_at(r,x,z)
    return y-r['bed_depth_m'] if r['kind']=='water_hole' else y
def ordinary_foundation_contracts():return prior.ordinary_foundation_contracts(EXCLUDED)
def finite_water_polygons():return review.finite_water_polygons()
def water_samples_at(x,z):return review.water_samples_at(x,z)
def water_height_at(id,x,z,segment_index=0):return review.water_height_at(id,x,z,segment_index)
def river_water_y(x):return review.river_water_y(x)
def path_height_at(id,x,z):return land_height_at(x,z)

def retaining_interfaces(bounds,records=None):
    records=records if records is not None else surface_domains(bounds);seen=set();out=[]
    for r in records:
        ring=r['polygon_xz_m']
        for a,b in zip(ring,ring[1:]+ring[:1]):
            L=math.dist(a,b)
            if L<1e-7:continue
            key=tuple(sorted(tuple(round(v,7) for v in p) for p in (a,b)))
            if key in seen:continue
            seen.add(key);m=[(a[k]+b[k])/2 for k in (0,1)];n=[-(b[1]-a[1])/L*1e-5,(b[0]-a[0])/L*1e-5]
            left=owner_at(*(m[k]+n[k] for k in (0,1)));right=owner_at(*(m[k]-n[k] for k in (0,1)))
            if left['owner_id']==right['owner_id'] or 'water_hole' in (left['kind'],right['kind']):continue
            # Compiled common assemblies own their own side faces. Do not add
            # duplicate retaining curtains up to wall caps or across wet decks.
            if any(o['kind'] in ('property_common_hole','property_lane_handoff','bridge_hole') for o in (left,right)):continue
            ys=[[surface_height_at(dict(o,review_tile_bounds_xz_m=bounds),*p) for p in (a,b)] for o in (left,right)]
            if max(abs(ys[0][i]-ys[1][i]) for i in (0,1))<1e-6:continue
            out.append(dict(id='R04_INTERFACE_'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:18],left_owner_id=left['owner_id'],right_owner_id=right['owner_id'],from_xz_m=a,to_xz_m=b,left_y_m=ys[0],right_y_m=ys[1],vertices_xyz_m=[[a[0],ys[0][0],a[1]],[b[0],ys[0][1],b[1]],[b[0],ys[1][1],b[1]],[a[0],ys[1][0],a[1]]],thickness_m=.3,collision_semantics='source cut/fill side; no traversal approval'))
    return out

def build_contract():
    _owners()
    return dict(schema='riverstone.registered_assembly_ownership.r04.v1',source_plan_sha256=old.SOURCE_SHA,author_sha256=sha(HERE/'author.py'),
        references={str(p.relative_to(CITY)):sha(p) for p in (PROPERTY_PATH,PORT_PATH,MARKET_PATH,HERE/'port_tie_contract.json',bridge.OVERLAY_PATH)},
        excluded_source_ids=list(EXCLUDED),removed_owner_kinds=['old body','old door','old support'],replaced_roads=MARKET['access_overlay']['replace_roads'],
        ordinary_foundations=ordinary_foundation_contracts(),property_terminal_handoffs=[r for r in OWNERS if r['kind']=='property_lane_handoff'],
        exact_property_face_count=sum(len(r['compiled_upward_faces']) for r in PROPERTY['ownership_masks']),port_floors=PORT['owned_floors'],
        property_external_access_profiles=PROPERTY['external_access_surfaces'],
        activation_requirements=['Use repaired property common pack and remove all29 source masses/old doors/supports together.',
            'Apply exact PORT_BRIDGE_TIE cut to common apron3_8; use the derived junction bridge cap rather than old291 cap.',
            'Use revised MARKET_PROCESSION bypass before placing the retained fountain/56stalls.',
            'No ground or water exclusion under elevated wet docks/bridge; independent upper surface geometry owns those decks.',
            'Property common upward-face union suppresses terrain only where actual sampled geometry exists; broad plot polygon never masks ground.',
            'Tiny property public-lane handoffs use declared piecewise-linear triangle profiles; native sampled ramp collisions remain a separate validation task.'],
        api=dict(partition='surface_domains(bounds,conform=True)',height='surface_height_at(record,x,z)',interfaces='retaining_interfaces(bounds,records)',road='road_height_at(id,x,z)'),
        status='bounded exact ownership contract; assembly adoption and interface/controller review still required')
if __name__=='__main__':
    c=build_contract();(HERE/'contract.json').write_text(json.dumps(c,indent=2)+'\n');print(json.dumps(dict(author_sha256=sha(HERE/'author.py'),contract_sha256=sha(HERE/'contract.json'),owners=len(OWNERS),excluded=len(EXCLUDED),foundations=len(c['ordinary_foundations']))))
