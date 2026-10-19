"""Bounded terrain/deck integration for the hash-bound continuous bridge overlay.

A source surface contract only. Existing common bridge geometry is compiled by
its assembly owner; this module never builds or fills an earth bridge over water.
"""
import bisect,hashlib,json,math
from pathlib import Path
from . import review
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import clean
from world_city.concept_city_v3.assemblies.waterworks.registered_bridge.compile_bridge import deck_y
HERE=Path(__file__).resolve().parent
OVERLAY_PATH=review.prior.previous.CITY/'assemblies/waterworks/registered_bridge/continuous_deck_overlay.json'
OVERLAY_SHA='90305493e619b1610e58fe61deee34652dd4a0e273c979403fb2cab070e04928'
DATA=json.loads(OVERLAY_PATH.read_bytes())
if hashlib.sha256(OVERLAY_PATH.read_bytes()).hexdigest()!=OVERLAY_SHA:raise ValueError('Continuous bridge overlay hash changed')
if DATA['source_plan']['sha256']!=review.prior.previous.SOURCE_SHA:raise ValueError('Bridge/source mismatch')
REGIONS=DATA['regions'];PROFILE_X=[p[0] for p in DATA['profile_x_y_m']]
INDEX=geo._SpatialIndex(32)
for i,r in enumerate(REGIONS):INDEX.add(i,r['polygon_xz_m'])

def _transform(t,p):return [sum(t['basis'][i][j]*[p[0],0,p[1]][j] for j in range(3))+t['translation'][i] for i in (0,2)]
def bridge_surface_height_at(record,x,z):return deck_y(DATA,x,z)

def bridge_surface_domains(bounds_xz_m=None,split_profile=True):
    """Independent elevated surfaces, split at every true height-profile kink."""
    ids=range(len(REGIONS)) if bounds_xz_m is None else sorted(INDEX.candidates(review.prior.previous.rect(bounds_xz_m)))
    out=[]
    for i in ids:
        r=REGIONS[i];poly=r['polygon_xz_m']
        if bounds_xz_m is not None:poly=clean(geo.convex_intersection(poly,review.prior.previous.rect(bounds_xz_m)))
        if not poly:continue
        pieces=[poly]
        if split_profile:
            local=[_transform(DATA['world_to_bridge'],p) for p in poly];xs=[p[0] for p in local];zs=[p[1] for p in local]
            cuts=[min(xs)]+[v for v in PROFILE_X if min(xs)+1e-9<v<max(xs)-1e-9]+[max(xs)];pieces=[]
            for lo,hi in zip(cuts,cuts[1:]):
                q=clean(geo.convex_intersection(local,review.prior.previous.rect([lo,min(zs)-1,hi,max(zs)+1])))
                if q:pieces.append([_transform(DATA['bridge_to_world'],p) for p in q])
        for j,p in enumerate(pieces):
            out.append(dict(owner_id='MAIN_BRIDGE:'+r['id']+':profile:'+str(j),source_region_id=r['id'],
                ownership_kind=r['ownership_kind'],polygon_xz_m=p,render_surface=True,
                vertex_y_m=[deck_y(DATA,*q) for q in p],height_api='bridge_surface_height_at(record,x,z)',
                ground_policy='independent elevated surface; only dry underlying top-face replacement, water and bed remain'))
    return out

def dry_ground_replacement_domains(bounds_xz_m=None):
    """Finite dry-only masks. Never subtract these from water or bed geometry."""
    out=[];wet=review.finite_water_polygons()
    for r in bridge_surface_domains(bounds_xz_m,split_profile=False):
        pieces=[r['polygon_xz_m']]
        for w in wet:
            if not review.base._overlap(review.base._bounds(r['polygon_xz_m']),review.base._bounds(w['polygon_xz_m'])):continue
            pieces=[q for p in pieces for part in geo.convex_difference(p,w['polygon_xz_m']) if(q:=clean(part))]
        for p in pieces:out.append(dict(owner_id=r['owner_id'],ownership_kind=r['ownership_kind'],polygon_xz_m=p,
            replacement='old MAIN_BRIDGE road face and dry support ground only',water_bed_preserved=True))
    return out

def endpoint_audit():
    road=next(r for r in review.base.REGISTERED_PLAN['roads'] if r['id']=='MAIN_BRIDGE');points=road['polyline_xz_m'];rows=[]
    for side,idx,other in [('north',0,1),('south',-1,-2)]:
        p=points[idx];q=points[other];dx,dz=p[0]-q[0],p[1]-q[1];length=math.hypot(dx,dz);nx,nz=-dz/length,dx/length
        samples=[]
        for j in range(29):
            offset=-road['width_m']/2+road['width_m']*j/28;x,z=p[0]+offset*nx,p[1]+offset*nz
            deck=deck_y(DATA,x,z);source=review.road_height_at('MAIN_BRIDGE',x,z)
            samples.append(dict(xz_m=[x,z],deck_y_m=deck,source_y_m=source,delta_m=deck-source))
        rows.append(dict(endpoint=side,source_width_m=road['width_m'],samples=samples,max_abs_delta_m=max(abs(s['delta_m']) for s in samples)))
    return dict(rows=rows,all_fixed_centerline_datums_preserved=all(abs(deck_y(DATA,*p['world_xz_m'])-p['finished_y_m'])<1e-10 for p in DATA['fixed_endpoints']),
        rule='Source approach is7m at gate/endpoints;8m cart lane applies to14m bridge deck, not silently to the narrower inherited approach.',
        threshold='Report full-width residuals; do not infer traversal from centerline anchors alone.')

def approach_interface_quads():
    """Dry approach skirts only; elevated wet deck retains open undercroft."""
    regions=bridge_surface_domains(split_profile=True);out=[];seen=set()
    for r in regions:
        if r['ownership_kind']!='dry_approach':continue
        ring=r['polygon_xz_m']
        for a,b in zip(ring,ring[1:]+ring[:1]):
            length=math.dist(a,b)
            if length<1e-7:continue
            key=tuple(sorted(tuple(round(v,7) for v in p) for p in(a,b)))
            if key in seen:continue
            seen.add(key);m=[(a[k]+b[k])/2 for k in(0,1)];normal=[-(b[1]-a[1])/length*1e-5,(b[0]-a[0])/length*1e-5]
            neighbors=[]
            for sign in[-1,1]:
                q=[m[k]+sign*normal[k] for k in(0,1)]
                inside=any(geo.point_in_convex_polygon(q,REGIONS[i]['polygon_xz_m'],1e-8) for i in INDEX.candidates([q]))
                if not inside:neighbors.append(q)
            if len(neighbors)!=1:continue
            outside=review.owner_at(*neighbors[0])
            if outside['kind']=='water_hole':continue
            upper=[deck_y(DATA,*p) for p in(a,b)];ground=[review.source_surface_height_at(outside,*p) for p in(a,b)]
            if max(abs(upper[i]-ground[i]) for i in(0,1))<1e-6:continue
            out.append(dict(id='BRIDGE_APPROACH_INTERFACE_'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:18],
                from_xz_m=a,to_xz_m=b,deck_y_m=upper,outside_y_m=ground,outside_owner_id=outside['owner_id'],
                vertices_xyz_m=[[a[0],upper[0],a[1]],[b[0],upper[1],b[1]],[b[0],ground[1],b[1]],[a[0],ground[0],a[1]]],
                public_lane_interface=outside['kind']=='road',
                status='source skirt; a flagged public-lane seam requires finite transition review rather than a blocking wall'))
    return out

def build_contract():
    return dict(schema='riverstone.registered_bridge_terrain_interfaces.v1',source_plan_sha256=review.prior.previous.SOURCE_SHA,
        continuous_overlay_path=str(OVERLAY_PATH),continuous_overlay_sha256=OVERLAY_SHA,
        original_candidate_sha256=DATA['candidate']['sha256'],
        source_regions=REGIONS,world_to_bridge=DATA['world_to_bridge'],profile_x_y_m=DATA['profile_x_y_m'],fixed_endpoints=DATA['fixed_endpoints'],
        api=dict(surfaces='bridge_surface_domains(bounds=None,split_profile=True)',height='bridge_surface_height_at(record,x,z)',dry_masks='dry_ground_replacement_domains(bounds=None)',approach_sides='approach_interface_quads()'),
        endpoint_audit=endpoint_audit(),maximum_profile_grade=DATA['maximum_profile_grade'],
        ownership=['Replace old MAIN_BRIDGE road/deck faces only inside the exact finite union.',
            'Terrain top masks are dry-only; retain every river water and bed polygon underneath elevated spans.',
            'Profile-kink splits are mandatory if triangulating a cheap preview; corners alone flatten camber.',
            'Dry approaches may own former unoccupied shoulders; other public lanes need explicit endpoint reconciliation.',
            'Keep open wet undercroft; do not extrude deck ownership to the river bed. Native piers/abutments are independent solids.'])

if __name__=='__main__':
    c=build_contract();(HERE/'bridge_contract.json').write_text(json.dumps(c,indent=2)+'\n')
    masks=dry_ground_replacement_domains();faces=approach_interface_quads()
    (HERE/'bridge_dry_interfaces.json').write_text(json.dumps(dict(dry_ground_replacement_domains=masks,approach_interface_quads=faces),indent=2)+'\n')
    print(json.dumps(dict(source_regions=len(REGIONS),dry_masks=len(masks),approach_sides=len(faces),endpoint_max_deltas_m=[r['max_abs_delta_m'] for r in c['endpoint_audit']['rows']])))
