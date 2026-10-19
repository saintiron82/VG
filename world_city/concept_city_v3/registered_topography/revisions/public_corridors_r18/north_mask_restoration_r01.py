"""Bounded, unactivated earth restoration under obsolete north bridge masks."""
import json, math, time
from .height_field import HERE
from . import finite_geometry_r03 as g
from .revise_native_emission_r07 import fan, ref
from ..r17_district_batches import author as a
from ..r14_precinct_merchant import author as legacy

def main():
 start=time.monotonic();ep=HERE/'unknown_boundary_classification_r01.json';edges=json.loads(ep.read_bytes());target=[r for r in edges['rows']if r['category'].startswith('NORTH')and r['length_m']-r['native_projection_covered_length_m']>1e-7];wanted={r['legacy_midpoint_owner']['owner_id']for r in target};old=[r for r in legacy.R04._owners()if r['owner_id']in wanted];masks=g.union([r['polygon_xz_m']for r in old]);assert len(old)==len(wanted)
 sp=a.CITY/'evidence/r8_district_r04/scene.json';scene=json.loads(sp.read_bytes());index=a.TriangleIndex(scene,masks);current=[r['polygon_xz_m']for r in index.rows]
 north=a.CITY/'assemblies/waterworks/registered_bridge/north_approach_r03/ownership_review.json';native=json.loads(north.read_bytes())['exact_native_footprint_masks_xz_m'];wet=[r['polygon_xz_m']for r in scene['terrain_contract']['water_domain_polygons']]
 pp=HERE/'finite_field_candidate_r07_native_bound.json';pub=json.loads(pp.read_bytes());near=[r['polygon_xz_m']for r in pub['records']if any(a.intersects(a.bounds(r['polygon_xz_m']),a.bounds(p))for p in masks)];remaining=g.subtract(masks,native+wet+current+near)
 mp=HERE/'field_refinement_r01.json';mesh=json.loads(mp.read_bytes());owners=[];covered=[]
 for i,t in enumerate(mesh['triangles_xyz_m']):
  poly=[[v[0],v[2]]for v in t]
  if not any(a.intersects(a.bounds(poly),a.bounds(p))for p in remaining):continue
  plane=a.common.plane(t)
  for j,p in enumerate(remaining):
   q=g.clip(p,poly)
   if not q:continue
   covered.append(q);owners.append(dict(id='NORTH_RETIRED_MASK_EARTH:'+str(i)+':'+str(j),source_triangle_index=i,polygon_xz_m=q,plane_y_xz_m=plane,triangles_xyz_m=fan(q,plane),material='ground_earth',kind='obsolete_bridge_mask_earth_restoration',action='field',walking_semantics='outside canonical public traffic; finite supported earth only',source_triangle_xyz_m=t))
 uncovered=g.subtract(remaining,covered);uncovered_area=math.fsum(g.area(p)for p in uncovered);assert uncovered_area<1e-8,uncovered_area
 overlap_native=math.fsum(g.area(g.clip(r['polygon_xz_m'],p))for r in owners for p in native if a.intersects(a.bounds(r['polygon_xz_m']),a.bounds(p)));overlap_road=math.fsum(g.area(g.clip(r['polygon_xz_m'],p))for r in owners for p in near if a.intersects(a.bounds(r['polygon_xz_m']),a.bounds(p)))
 assert overlap_native<1e-8 and overlap_road<1e-8
 out=dict(schema='riverstone.r18.obsolete_native_mask_restoration.v1',status='FINITE_EARTH_RESTORATION_CANDIDATE_PENDING_PARENT_COMPOSITION_AND_SIDES',source_refs=[ref(ep),ref(sp),ref(pp),ref(mp),ref(north),ref(__import__('pathlib').Path(legacy.R04.__file__))],code_sha256=a.sha(__file__),obsolete_mask_records=old,source_unknown_edges=target,retired_mask_residual_polygons_xz_m=remaining,physical_earth_owners=owners,source_area_m2=math.fsum(g.area(p)for p in remaining),rendered_area_m2=math.fsum(g.area([[v[0],v[2]]for v in t])for r in owners for t in r['triangles_xyz_m']),uncovered_polygons_xz_m=uncovered,uncovered_area_m2=uncovered_area,overlap_with_native_masks_m2=overlap_native,overlap_with_current_public_m2=overlap_road,maximum_profile_grade=max((math.hypot(*r['plane_y_xz_m'][:2])for r in owners),default=0),seconds=time.monotonic()-start,policy='Only residual obsolete APPROACH_north_003/004 hole fractions outside all current terrain, accepted native footprint, water and public owners. Heights come from finite already-authored R18 source triangles; no extrapolated infinite plane or native-cap floor inference. New off-road earth requires parent side closure against actual surrounding ground.',activation=False)
 targetp=HERE/'north_mask_restoration_r01.json';targetp.write_text(json.dumps(out,separators=(',',':'))+'\n');print(json.dumps(dict(output=ref(targetp),summary={k:v for k,v in out.items()if k in('source_area_m2','rendered_area_m2','uncovered_area_m2','overlap_with_native_masks_m2','overlap_with_current_public_m2','maximum_profile_grade','seconds')},owner_count=len(owners))))
if __name__=='__main__':main()
