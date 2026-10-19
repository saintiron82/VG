"""Explicit source-ID exclusion overlay over sealed registered r01 ownership.

No runtime monkeypatching: r01 owners and files remain untouched. Removed body,
actual-door and support owners reveal the next legitimate underlying owner.
External common-floor masks are still consumed by the parent integration layer.
"""
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
from ..r01_ownership import author as previous
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import clean
HERE=Path(__file__).resolve().parent
DEFAULT_EXCLUDED_SOURCE_IDS=('B_REG_0191',)
PREVIOUS_AUTHOR_SHA='5dbdf08a9b5bc39778e412f9599c122c12e1b2abd2428eddc97851cb8bb9f46d'
PREVIOUS_CONTRACT_SHA='6e3d745a8bf685eaf35f0cc15bf8dfe4fb7b1ce71de850004e736f21b8721685'


def snapshot_check():
    previous.snapshot_check()
    if previous.sha(previous.HERE/'author.py')!=PREVIOUS_AUTHOR_SHA:raise ValueError('Sealed r01 author changed')
    if previous.sha(previous.HERE/'contract.json')!=PREVIOUS_CONTRACT_SHA:raise ValueError('Sealed r01 contract changed')


def is_excluded(record,excluded_source_ids):
    source=record.get('source_mass_id');owner=record.get('owner_id','');door=record.get('door_id','')
    return any(source==id or owner==id or owner.startswith(id+':') or door.startswith(id+':') for id in excluded_source_ids)


def owner_at(x,z,excluded_source_ids=DEFAULT_EXCLUDED_SOURCE_IDS):
    owners=previous._source_owners()
    for i in sorted(previous._INDEX.candidates([[x,z]])):
        p=owners[i]
        if is_excluded(p,excluded_source_ids):continue
        if geo.point_in_convex_polygon([x,z],p['polygon_xz_m'],1e-8):return p
    return dict(owner_id='BASE_GROUND',kind='ground',priority=100,render_land=True,material_hint='inherit_district_or_plot')


def _replacement_domains(polygon,bounds,excluded):
    """Repartition just the removed finite polygon, not the whole city."""
    owners=previous._source_owners();remaining=[polygon];out=[]
    for i in sorted(previous._INDEX.candidates(polygon)):
        owner=owners[i]
        if is_excluded(owner,excluded):continue
        mask=clean(geo.convex_intersection(polygon,owner['polygon_xz_m']))
        if not mask:continue
        new=[]
        for p in remaining:
            if not geo.positive_area_overlap(p,mask,0):new.append(p);continue
            intersection=clean(geo.convex_intersection(p,mask))
            if intersection:
                r={k:v for k,v in owner.items() if k!='polygon_xz_m'};r.update(polygon_xz_m=intersection,review_tile_bounds_xz_m=list(bounds));out.append(r)
            new.extend(q for part in geo.convex_difference(p,mask) if(q:=clean(part)))
        remaining=new
        if not remaining:break
    out.extend(dict(owner_id='BASE_GROUND',kind='ground',priority=100,render_land=True,material_hint='inherit_district_or_plot',polygon_xz_m=p,review_tile_bounds_xz_m=list(bounds)) for p in remaining)
    return out


def surface_domains(bounds_xz_m,conform=True,excluded_source_ids=DEFAULT_EXCLUDED_SOURCE_IDS):
    out=[]
    for r in previous.surface_domains(bounds_xz_m,conform=False):
        if is_excluded(r,excluded_source_ids):out.extend(_replacement_domains(r['polygon_xz_m'],bounds_xz_m,excluded_source_ids))
        else:out.append(r)
    extra=[];x0,z0,x1,z1=bounds_xz_m
    for iz in range(math.ceil(z0*4),math.floor(z1*4)+1):extra.extend([[x0,iz/4],[x1,iz/4]])
    for ix in range(math.ceil(x0*4),math.floor(x1*4)+1):extra.extend([[ix/4,z0],[ix/4,z1]])
    for r in out:r['excluded_source_ids']=list(excluded_source_ids)
    return previous.conform_domains(out,extra) if conform else out


def source_surface_height_at(record,x,z):return previous.source_surface_height_at(record,x,z)
def surface_height_at(record,x,z):return previous.surface_height_at(record,x,z)
def road_height_at(id,x,z):return previous.road_height_at(id,x,z)
def path_height_at(id,x,z):return previous.path_height_at(id,x,z)
def water_height_at(id,x,z,segment_index=0):return previous.water_height_at(id,x,z,segment_index)
def finite_water_polygons():return previous.finite_water_polygons()
def water_samples_at(x,z):return previous.water_samples_at(x,z)
def river_water_y(x):return previous.river_water_y(x)
def land_height_at(x,z,excluded_source_ids=DEFAULT_EXCLUDED_SOURCE_IDS):
    p=owner_at(x,z,excluded_source_ids)
    return previous.base.land_height_at(x,z) if p['kind']=='water_hole' else source_surface_height_at(p,x,z)
def height_at(x,z,excluded_source_ids=DEFAULT_EXCLUDED_SOURCE_IDS):
    p=owner_at(x,z,excluded_source_ids);y=source_surface_height_at(p,x,z)
    return y-p['bed_depth_m'] if p['kind']=='water_hole' else y
def building_floor_at(x,z):return land_height_at(x,z)


def retaining_interfaces(bounds_xz_m,records=None,excluded_source_ids=DEFAULT_EXCLUDED_SOURCE_IDS):
    records=records if records is not None else surface_domains(bounds_xz_m,excluded_source_ids=excluded_source_ids)
    if records:excluded_source_ids=records[0].get('excluded_source_ids',excluded_source_ids)
    out=[];seen=set()
    for rec in records:
        p=rec['polygon_xz_m']
        for a,b in zip(p,p[1:]+p[:1]):
            length=math.dist(a,b)
            if length<1e-7:continue
            key=tuple(sorted((tuple(round(v,7) for v in a),tuple(round(v,7) for v in b))))
            if key in seen:continue
            seen.add(key);nx,nz=-(b[1]-a[1])/length*1e-5,(b[0]-a[0])/length*1e-5;m=[(a[k]+b[k])/2 for k in(0,1)]
            left=owner_at(m[0]+nx,m[1]+nz,excluded_source_ids);right=owner_at(m[0]-nx,m[1]-nz,excluded_source_ids)
            if left['owner_id']==right['owner_id'] or 'water_hole' in (left['kind'],right['kind']):continue
            left=dict(left,review_tile_bounds_xz_m=list(bounds_xz_m));right=dict(right,review_tile_bounds_xz_m=list(bounds_xz_m))
            ys=[[surface_height_at(r,*q) for q in(a,b)] for r in(left,right)]
            if max(abs(ys[0][i]-ys[1][i]) for i in(0,1))<1e-6:continue
            high=left if sum(ys[0])>=sum(ys[1]) else right
            out.append(dict(id='INTERFACE_'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:18],
                from_xz_m=a,to_xz_m=b,left_owner_id=left['owner_id'],right_owner_id=right['owner_id'],
                left_y_m=ys[0],right_y_m=ys[1],retaining_owner_id=high['owner_id'],
                vertices_xyz_m=[[a[0],ys[0][0],a[1]],[b[0],ys[0][1],b[1]],[b[0],ys[1][1],b[1]],[a[0],ys[1][0],a[1]]],
                thickness_m=.3,collision_semantics='intentional retaining barrier; no stair or walkability claim'))
    return out


def ordinary_foundation_contracts(excluded_source_ids=DEFAULT_EXCLUDED_SOURCE_IDS):
    return [r for r in previous.ordinary_foundation_contracts() if r['source_mass_id'] not in excluded_source_ids]


def build_contract(excluded_source_ids=DEFAULT_EXCLUDED_SOURCE_IDS):
    snapshot_check();c=previous.build_contract();c.update(schema='riverstone.registered_terrain.r02_assembly_overlay.v1',revision='r02_assembly_overlay',
        previous_author_sha256=PREVIOUS_AUTHOR_SHA,previous_contract_sha256=PREVIOUS_CONTRACT_SHA,
        ordinary_foundations=ordinary_foundation_contracts(excluded_source_ids),
        exclusion_ledger=[dict(source_mass_id=id,removed_owner_kinds=['building_body_hole','door_landing','door_approach','foundation_support'],
            reason='explicit parent-authorized civic common assembly supersession',
            replacement_rule='reveal underlying registered terrain first; exact civic floor mask replaces it in parent assembly integration',
            instance_path_rule='parent also removes ordinary instance, source mass and source-centered path') for id in excluded_source_ids])
    c['exact_surface_ownership'].update(module='world_city.concept_city_v3.registered_topography.revisions.r02_assembly_overlay.author',
        excluded_source_ids=list(excluded_source_ids),configuration='surface_domains(...,excluded_source_ids=...), owner_at(...,excluded_source_ids=...) and build_contract(excluded_source_ids=...) use the same explicit list')
    return c


def main():
    c=build_contract();(HERE/'contract.json').write_text(json.dumps(c,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(source_plan_sha256=c['source_plan_sha256'],author_sha256=previous.sha(HERE/'author.py'),contract_sha256=previous.sha(HERE/'contract.json'),excluded_source_ids=list(DEFAULT_EXCLUDED_SOURCE_IDS),remaining_foundations=len(c['ordinary_foundations']))))
if __name__=='__main__':main()
