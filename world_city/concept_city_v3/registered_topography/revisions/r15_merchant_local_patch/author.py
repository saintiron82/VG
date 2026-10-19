"""Source-only R15 local merchant patch. This module cannot activate a scene.

The frozen R5 triangle arrays are the seam authority. R14 and all native packs
remain immutable. Only existing shared convex clipping is used here.
"""
from __future__ import annotations
import copy, hashlib, json, math
from collections import Counter
from functools import lru_cache
from pathlib import Path
from ..r14_precinct_merchant import author as base

HERE = Path(__file__).resolve().parent
CITY, ROOT, geo = base.CITY, base.ROOT, base.geo
REFERENCES = {
    'registered_topography/revisions/r14_precinct_merchant/author.py': 'd4fa282ff51698719a6726b64d0459b0f89860c9d44e298099f966c0441822c1',
    'registered_topography/revisions/r14_precinct_merchant/contract.json': 'ae8470ea3993e608100c7a7e8f4143d6162092f373d37cfa1099e843e55e4301',
    'assemblies/property/registered/merchant_fabric_r02/resolved_placements.json': 'fb365edf17a0f3f0c62ee1dc7d230a8bbbbda6403ed07d8b6bda118437ddd61d',
    'assemblies/property/registered/merchant_fabric_r02/terrain_handoff.json': '89fdac83930600c42a05d0f3921a9f00ff39c1cf5dca575691b4ba36e33d4c6a',
}
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
for path, expected in REFERENCES.items():
    if sha(CITY/path) != expected: raise ValueError('Changed R15 input: '+path)
PACK = json.loads((CITY/list(REFERENCES)[2]).read_bytes())
HANDOFF = json.loads((CITY/list(REFERENCES)[3]).read_bytes())
RETIRED = tuple(PACK['replaced_placement_ids'])
EXCLUDED = tuple(sorted(set(base.EXCLUDED) | set(RETIRED)))
MIN_AREA_M2 = 1e-10


def polygon(points):
    """Distance-weld zero-length edges, retaining all useful seam knots."""
    out = []
    for p in points:
        if not out or math.dist(p, out[-1]) > 1e-9: out.append(list(p))
    while len(out)>1 and math.dist(out[0],out[-1])<=1e-9: out.pop()
    return out if len(out)>=3 and geo.polygon_area(out)>MIN_AREA_M2 else None


def subtract(polys, masks):
    parts = list(polys)
    for mask in masks:
        new=[]
        for p in parts:
            q=polygon(geo.convex_intersection(p,mask))
            if q:
                new.extend(c for raw in geo.convex_difference(p,mask) if (c:=polygon(raw)))
            else: new.append(p)
        parts=new
        if not parts: break
    return parts


PLATFORMS = [dict(id=p['property_id']+':PLATFORM',property_id=p['property_id'],
    polygon_xz_m=p['platform_polygon_xz_m'],floor_y_m=p['finished_floor_y_m'],
    material='earth',material_partition_ref=p['property_id'],kind='level_platform')
    for p in HANDOFF['properties']]
GATES = [dict(copy.deepcopy(p['finite_gate_approach']),property_id=p['property_id'],
    material='stone',kind='candidate_gate_profile',accepted=False,
    boundary_authority='Actual frozen R5 road triangles; nine source anchors are proposals.')
    for p in HANDOFF['properties']]
NATIVE_HOLES = []
for group in PACK['ownership_masks']:
    for i,p in enumerate(group['terrain_exclusion_regions_xz_m']):
        NATIVE_HOLES.append(dict(id=group['owner_id']+':'+str(i),property_id=group['property_id'],
            polygon_xz_m=p,floor_y_m=group['floor_y_m'],
            bottom_y_m=group['floor_y_m']-group['foundation_embed_m'],
            render_land=False,render_sha256=group['render_sha256']))
NEW_MASKS = [r['polygon_xz_m'] for r in PLATFORMS+GATES]


def effective_record_after_retirement(x,z):
    """Read-only source screening, not the final frozen-triangle seam field."""
    record=base.owner_at(x,z)
    if base.R04.prior.is_excluded(record,EXCLUDED):
        record=base.R04.prior.owner_at(x,z,EXCLUDED)
        for i in sorted(base.INDEX.candidates([[x,z]])):
            candidate=base.OWNERS[i]
            if base.allowed(record,candidate) and geo.point_in_convex_polygon([x,z],candidate['polygon_xz_m'],1e-8):
                record=candidate;break
    return record


def effective_source_height(x,z):
    r=effective_record_after_retirement(x,z)
    return base.source_surface_height_at(r,x,z)


@lru_cache(maxsize=1)
def retired_owner_domains():
    """Disjoint actually exposed old body/door domains in the source hierarchy.

    This is only the finite removal ledger. R5 scene triangles and its native
    masks remain the final authority when a local scene patch is bound.
    """
    source=base.R04.prior.previous
    all_owners=source._source_owners(); result=[]
    for i,r in enumerate(all_owners):
        if not base.R04.prior.is_excluded(r,RETIRED): continue
        parts=[r['polygon_xz_m']]
        blockers=[all_owners[j]['polygon_xz_m'] for j in sorted(source._INDEX.candidates(parts[0])) if j<i]
        parts=subtract(parts,blockers)
        for j,p in enumerate(parts):
            result.append(dict(id='RETIRED:'+r['owner_id']+':'+str(j),
                old_owner_id=r['owner_id'],old_kind=r['kind'],polygon_xz_m=p,
                source_mass_id=r.get('source_mass_id'),old_record=r))
    return result


@lru_cache(maxsize=1)
def restoration_domains():
    """Exact retired domains outside new platforms/gates, with underlying owners."""
    result=[]
    for old in retired_owner_domains():
        for part in subtract([old['polygon_xz_m']],NEW_MASKS):
            xs,zs=zip(*part);bounds=[min(xs),min(zs),max(xs),max(zs)]
            for underlying in base.R04.prior._replacement_domains(part,bounds,EXCLUDED):
                p=polygon(underlying['polygon_xz_m'])
                if p:
                    result.append(dict(id='RESTORE:'+str(len(result)),polygon_xz_m=p,
                        retired_owner_id=old['old_owner_id'],retired_kind=old['old_kind'],
                        underlying_record=underlying,material_policy='Frozen adjacent material / exact base classifier',
                        height_policy='Restore legitimate source owner; bind boundary knots to frozen R5 triangles.',
                        accepted=False))
    return result


@lru_cache(maxsize=1)
def patch_masks():
    """Candidate replacement union; public collars will be added after R5 binding."""
    records=[dict(id=r['id'],polygon_xz_m=r['polygon_xz_m'],reason=r['kind']) for r in PLATFORMS+GATES]
    records += [dict(id=r['id'],polygon_xz_m=r['polygon_xz_m'],reason='retired_owner_restoration') for r in restoration_domains()]
    return records


@lru_cache(maxsize=1)
def mask_index():
    idx=geo._SpatialIndex(16)
    for i,r in enumerate(patch_masks()): idx.add(i,r['polygon_xz_m'])
    return idx


def affine_plane(triangle):
    a,b,c=triangle; dx1,dz1=b[0]-a[0],b[2]-a[2];dx2,dz2=c[0]-a[0],c[2]-a[2]
    det=dx1*dz2-dx2*dz1
    if abs(det)<=1e-14: raise ValueError('Vertical/degenerate triangle needs the side ledger.')
    gx=((b[1]-a[1])*dz2-(c[1]-a[1])*dz1)/det
    gz=(dx1*(c[1]-a[1])-dx2*(b[1]-a[1]))/det
    return gx,gz,a[1]-gx*a[0]-gz*a[2]


def plane_height(plane,x,z): return plane[0]*x+plane[1]*z+plane[2]


def clip_frozen_triangle(triangle, masks=None):
    """Retain outside pieces on the ORIGINAL plane. Never resample source H.

    The unchanged path returns the exact supplied object and original vertex
    order. Caller preserves untouched JSON records byte-for-byte/in order.
    """
    poly=[[p[0],p[2]] for p in triangle]
    if geo.polygon_area(poly)<=MIN_AREA_M2:
        return dict(unchanged=True,triangles_xyz_m=[triangle],requires_side_review=True)
    if masks is None:
        masks=[patch_masks()[i]['polygon_xz_m'] for i in sorted(mask_index().candidates(poly))]
    hits=[m for m in masks if polygon(geo.convex_intersection(poly,m))]
    if not hits: return dict(unchanged=True,triangles_xyz_m=[triangle],requires_side_review=False)
    parts=subtract([poly],hits);plane=affine_plane(triangle);out=[]
    original_sign=geo.signed_polygon_area(poly)
    for p in parts:
        if geo.signed_polygon_area(p)*original_sign<0:p=list(reversed(p))
        vertices=[[x,plane_height(plane,x,z),z] for x,z in p]
        for i in range(1,len(vertices)-1):out.append([vertices[0],vertices[i],vertices[i+1]])
    kept=sum(geo.polygon_area([[v[0],v[2]] for v in t]) for t in out)
    return dict(unchanged=False,triangles_xyz_m=out,requires_side_review=False,
        removed_projected_area_m2=geo.polygon_area(poly)-kept,source_plane_y_xz_m=list(plane))


def segment_mask_interval(a,b,mask):
    """Exact convex segment clipping for old vertical sides and road seams."""
    orient=1 if geo.signed_polygon_area(mask)>0 else -1;lo,hi=0.,1.
    for c,d in zip(mask,mask[1:]+mask[:1]):
        fa=orient*geo._cross(c,d,a);fb=orient*geo._cross(c,d,b);delta=fb-fa
        if abs(delta)<1e-14:
            if fa < -1e-10:return None
        else:
            t=-fa/delta
            if delta>0:lo=max(lo,t)
            else:hi=min(hi,t)
        if lo>hi+1e-12:return None
    return [max(0.,lo),min(1.,hi)] if hi-lo>1e-10 else None


def affected_side_intervals(a,b):
    hits=[]
    for i in sorted(mask_index().candidates([a,b])):
        r=patch_masks()[i];interval=segment_mask_interval(a,b,r['polygon_xz_m'])
        if interval:hits.append(dict(mask_id=r['id'],t_interval=interval))
    return hits


def support_requirements():
    out=[]
    for r in NATIVE_HOLES:
        p=r['polygon_xz_m'];points=p+[[sum(q[k] for q in p)/len(p) for k in (0,1)]]
        samples=[dict(point_xz_m=q,source_y_m=effective_source_height(*q)) for q in points]
        gap=max(0.,*(r['bottom_y_m']-s['source_y_m'] for s in samples))
        cut=max(0.,*(s['source_y_m']-r['floor_y_m'] for s in samples))
        out.append(dict(r,samples=samples,maximum_sampled_gap_below_plinth_m=gap,
            maximum_sampled_cut_above_floor_m=cut,required=gap>1e-7,
            design='Bounded buried common support only under exact native footprint; coarse support/fine skin split if needed.',
            status='Source obligation only; no support solid compiled.'))
    return out


def gate_risk_screen():
    out=[]
    for g in GATES:
        maximum_terminal=maximum_overlap=0.;ep=g['endpoint_profile'];road=g['road_id']
        for a,b in zip(ep,ep[1:]):
            for i in range(9):
                t=i/8;x,z=[(1-t)*a['point_xz_m'][k]+t*b['point_xz_m'][k] for k in (0,1)]
                y=(1-t)*a['y_m']+t*b['y_m']
                maximum_terminal=max(maximum_terminal,abs(y-base.road_height_at(road,x,z)))
        for r in g['public_coownership_proposals']:
            p=r['polygon_xz_m'];plane=affine_plane(r['height_profile_xyz_m'])
            for x,z in p+[[sum(q[k] for q in p)/len(p) for k in (0,1)]]:
                maximum_overlap=max(maximum_overlap,abs(plane_height(plane,x,z)-base.road_height_at(road,x,z)))
        out.append(dict(gate_id=g['id'],property_id=g['property_id'],road_id=road,
            source_triangle_max_grade=max(math.hypot(*affine_plane(t)[:2]) for t in g['height_evaluator']['triangles_xyz_m']),
            sampled_terminal_linear_vs_analytic_error_m=maximum_terminal,
            sampled_public_overlap_height_delta_m=maximum_overlap,
            needs_shared_public_transition=maximum_overlap>1e-6,
            final_frozen_triangle_seams=None,status='Await actual R5 triangle binding.'))
    return out


def build_contract():
    restoration=restoration_domains();support=support_requirements();risk=gate_risk_screen()
    area=Counter()
    for r in restoration:area[r['retired_kind']]+=geo.polygon_area(r['polygon_xz_m'])
    return dict(schema='riverstone.local_frozen_triangle_patch.v1',revision='r15_merchant_local_patch',
        status='SOURCE_ONLY_AWAIT_R5_SCENE_AND_FINITE_INTERFACE_ACCEPTANCE',active=False,
        source_plan_sha256=PACK['source_plan_sha256'],sources=REFERENCES,
        author_sha256=sha(__file__),base_scene=None,
        inheritance='Retain entire frozen R5 scene, water/beds/banks and unaffected triangle records. This is not a whole-city terrain module.',
        replacement_ledger=dict(retired_native_ids=list(RETIRED),
            retired_source_paths=PACK['superseded_source_path_ids'],retired_native_paths=PACK['superseded_native_access_ids'],
            new_runtime_group_ids=[r['id'] for r in PACK['placements']],render_components=False),
        platforms=PLATFORMS,native_holes=NATIVE_HOLES,gate_profiles=GATES,
        restoration_domains=restoration,retired_owner_domains=retired_owner_domains(),
        patch_masks=patch_masks(),support_requirements=support,gate_risk_screen=risk,
        material_source=dict(path=list(REFERENCES)[3],field='properties[].materials',extra_floor_planes=False),
        retained_lower_grounds=[dict(p['retained_lower_ground'],property_id=p['property_id']) for p in HANDOFF['properties']],
        retaining_edge_requirements=[e for p in HANDOFF['properties'] for e in p['retaining_edge_candidates']],
        affected_old_side_policy='Clip actual frozen side segments at patch boundaries; retain outside intervals and rebuild only changed intervals. Preserve wet/native sides.',
        frozen_scene_binding_requirements=['Exact scene SHA and triangle indices/materials.',
            'Every gate/outer seam split at actual intersected frozen triangle edges.',
            'One shared finite triangle field; measure full clipped-triangle grades, not just analytic H.',
            'Restore retired holes before surface coverage proof; keep native and wet owners protected.',
            'Untouched triangle records preserve exact values and ordering; no citywide resampling.'],
        summary=dict(platform_count=len(PLATFORMS),platform_area_m2=sum(geo.polygon_area(r['polygon_xz_m']) for r in PLATFORMS),
            native_hole_count=len(NATIVE_HOLES),retired_owner_domain_count=len(retired_owner_domains()),
            restoration_domain_count=len(restoration),restored_area_by_old_kind_m2=dict(area),
            gates_needing_public_transition=sum(r['needs_shared_public_transition'] for r in risk),
            native_support_region_count=sum(r['required'] for r in support)),
        limits=['Source screening does not approve support, public continuity or traversal.',
            'Candidate patch union excludes not-yet-designed public collars; final affected extent must expand explicitly.',
            'Projected masks do not authorize deletion of water, buildings or unrelated vertical faces.',
            'No heavy compile, whole-city export or activation has been run.'])

if __name__=='__main__':
    target=HERE/'source_contract.json'
    if target.exists():raise SystemExit('Use a new source-contract revision rather than overwrite evidence.')
    target.write_text(json.dumps(build_contract(),indent=2)+'\n')
    print(str(target),sha(target))
