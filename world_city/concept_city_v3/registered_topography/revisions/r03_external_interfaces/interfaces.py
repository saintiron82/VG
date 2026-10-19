"""Finite external common-floor ownership and two-sided cut/fill interfaces.

Call per existing review tile; no citywide terrain generation is required.
Bridge profiles are bound separately only after their continuous join overlay seals.
"""
import hashlib,json,math
from pathlib import Path
from . import review
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import clean
HERE=Path(__file__).resolve().parent
LANDMARK_PATH=review.prior.previous.CITY/'assemblies/landmarks/registered/assembly_r01/sources_manifest.json'
MANIFEST=json.loads(LANDMARK_PATH.read_bytes())
FLOORS=MANIFEST['owned_floors']
FLOOR_GEOMETRY_SHA256=hashlib.sha256(json.dumps(FLOORS,sort_keys=True,separators=(',',':')).encode()).hexdigest()
INDEX=geo._SpatialIndex(32)
for i,f in enumerate(FLOORS):INDEX.add(i,f['polygon_xz_m'])

def floor_owner_at(x,z):
    # Actual public lanes and finite water keep precedence. The unoccupied
    # support shoulder is not a mandatory sidewalk and can be clipped by floors.
    ground=review.owner_at(x,z)
    if ground['kind'] in ('road','water_hole'):return ground
    for i in sorted(INDEX.candidates([[x,z]])):
        f=FLOORS[i]
        if geo.point_in_convex_polygon([x,z],f['polygon_xz_m'],1e-8):
            return dict(owner_id=f['id'],kind='common_floor_hole',render_land=False,floor_y_m=f['floor_y_m'],placement_id=f['placement_id'])
    return ground

def clip_floor_domains(bounds_xz_m,ground_records=None):
    records=ground_records if ground_records is not None else review.surface_domains(bounds_xz_m)
    candidate_ids=sorted(INDEX.candidates(review.prior.previous.rect(bounds_xz_m)))
    if not candidate_ids:return records
    out=[]
    for record in records:
        if record['kind'] in ('road','water_hole'):out.append(record);continue
        remaining=[record['polygon_xz_m']]
        for i in candidate_ids:
            floor=FLOORS[i];mask=floor['polygon_xz_m'];new=[]
            for p in remaining:
                if not geo.positive_area_overlap(p,mask,0):new.append(p);continue
                hit=clean(geo.convex_intersection(p,mask))
                if hit:out.append(dict(owner_id=floor['id'],kind='common_floor_hole',render_land=False,material_hint='none',
                    floor_y_m=floor['floor_y_m'],placement_id=floor['placement_id'],support_bottom_y_m=floor['support_bottom_y_m'],
                    polygon_xz_m=hit,review_tile_bounds_xz_m=list(bounds_xz_m)))
                new.extend(q for part in geo.convex_difference(p,mask) if(q:=clean(part)))
            remaining=new
            if not remaining:break
        out.extend(dict(record,polygon_xz_m=p) for p in remaining)
    return review.prior.previous.conform_domains(out)

def floor_interface_quads(bounds_xz_m,records=None):
    """Exact owner boundary faces for the same tile partition rendered above."""
    records=records if records is not None else clip_floor_domains(bounds_xz_m)
    out=[];seen=set()
    for record in records:
        if record['kind']!='common_floor_hole':continue
        ring=record['polygon_xz_m']
        for a,b in zip(ring,ring[1:]+ring[:1]):
            length=math.dist(a,b)
            if length<1e-7:continue
            key=tuple(sorted(tuple(round(v,7) for v in p) for p in(a,b)))
            if key in seen:continue
            seen.add(key);m=[(a[k]+b[k])/2 for k in(0,1)];nx,nz=-(b[1]-a[1])/length*1e-5,(b[0]-a[0])/length*1e-5
            left=floor_owner_at(m[0]+nx,m[1]+nz);right=floor_owner_at(m[0]-nx,m[1]-nz)
            if left['owner_id']==right['owner_id'] or 'water_hole' in (left['kind'],right['kind']):continue
            if 'common_floor_hole' not in (left['kind'],right['kind']):continue
            left=dict(left,review_tile_bounds_xz_m=list(bounds_xz_m));right=dict(right,review_tile_bounds_xz_m=list(bounds_xz_m))
            ys=[[review.surface_height_at(o,*p) for p in(a,b)] for o in(left,right)]
            if max(abs(ys[0][i]-ys[1][i]) for i in(0,1))<1e-6:continue
            out.append(dict(id='COMMON_FLOOR_INTERFACE_'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:18],
                left_owner_id=left['owner_id'],right_owner_id=right['owner_id'],from_xz_m=a,to_xz_m=b,left_y_m=ys[0],right_y_m=ys[1],
                vertices_xyz_m=[[a[0],ys[0][0],a[1]],[b[0],ys[0][1],b[1]],[b[0],ys[1][1],b[1]],[a[0],ys[1][0],a[1]]],
                thickness_m=.3,semantics='visible terrain cut or foundation fill side; collision not yet compiled'))
    return out

def build_contract():
    return dict(schema='riverstone.registered_external_floor_interfaces.v1',source_plan_sha256=review.prior.previous.SOURCE_SHA,
        prior_author_sha256=review.prior.previous.sha(review.prior.HERE/'author.py'),
        prior_contract_sha256=review.prior.previous.sha(review.prior.HERE/'contract.json'),
        floor_manifest_path=str(LANDMARK_PATH),floor_manifest_sha256=review.prior.previous.sha(LANDMARK_PATH),floor_geometry_sha256=FLOOR_GEOMETRY_SHA256,
        owned_floors=FLOORS,api=dict(partition='clip_floor_domains(bounds,ground_records=None)',interfaces='floor_interface_quads(bounds,records=None)',height='review.surface_height_at(record,x,z)'),
        rules=['Use the returned partition for terrain and matching cut-side geometry, rather than clipping one representation and sampling another.',
            'Common floors replace exact finite terrain top faces; actual road lanes and water retain precedence.',
            'Do not combine old retaining faces that run through a new common-floor hole. Filter them against owned floor domains or derive them from final partition.',
            'No whole-precinct flattening, display lift, bridge earth fill or frozen revision mutation.'])
