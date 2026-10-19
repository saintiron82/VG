"""Explain finite top holes from immutable legacy ownership, without filling them."""
import json, math, collections, time
from .height_field import HERE
from . import finite_geometry_r03 as g, public_domain
from ..r17_district_batches import author as a
from ..r14_precinct_merchant import author as old

def ref(p): return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def main():
 start=time.monotonic(); inp=HERE/'top_hole_classification_r02.json'; data=json.loads(inp.read_bytes())
 legacy=old.R04._owners(); ix=old.R04.INDEX; traffic=public_domain.records(); ti=a.geo._SpatialIndex(4)
 for i,r in enumerate(traffic):ti.add(i,r['polygon_xz_m'])
 north=a.CITY/'assemblies/waterworks/registered_bridge/north_approach_r03'; np=json.loads((north/'profile.json').read_bytes()); nm=json.loads((north/'ownership_review.json').read_bytes())['exact_native_footprint_masks_xz_m']; basis=np['bridge_frame']['basis']; trans=np['bridge_frame']['translation']
 rows=[]; summary=collections.defaultdict(lambda:dict(count=0,area_m2=0.))
 for source in data['rows']:
  masks=[]; strips=[]; pointowners=[]
  for p in source['hole_polygons_xz_m']:
   for i in ix.candidates(p):
    r=legacy[i]
    if r.get('render_land',True):continue
    q=g.clip(p,r['polygon_xz_m'])
    if q:masks.append(dict(owner_id=r['owner_id'],kind=r['kind'],property_id=r.get('property_id'),polygon_xz_m=q,area_m2=g.area(q),legacy_record=r))
   for i in ti.candidates(p):
    r=traffic[i];q=g.clip(p,r['polygon_xz_m'])
    if q:strips.append(dict(id=r['id'],road_id=r.get('road_id'),polygon_xz_m=q))
   # Returned record domains are retained, rather than treating the sample as
   # proof that the whole hole shares that owner.
   for v in p+[[math.fsum(v[0]for v in p)/len(p),math.fsum(v[1]for v in p)/len(p)]]:
    r=old.owner_at(*v);q=g.clip(p,r['polygon_xz_m'])
    if q:pointowners.append(dict(record=r,intersection_polygon_xz_m=q))
  bb=a.bounds([v for p in source['hole_polygons_xz_m']for v in p]); native=source['actual_native_and_contract_pieces']; ids=sorted({x['native_instance_id']for x in native if x.get('native_instance_id')})
  if bb[0]>90 and bb[1]>380: category='RETIRED_BRIDGE_MASK_PUBLIC_RESTORATION'
  elif bb[0]<-245 and bb[1]>-50 and bb[3]<-40: category='COMMON_CURRENT_TOP_OR_NATIVE_INTERFACE'
  elif any(x.startswith('E')and':registered_r1:'in x for x in ids):category='NOBLE_ATOMIC_REPLACEMENT_REQUIRED'
  elif any(x.get('property_id')in('E1','E2')for x in masks):category='E1_E2_LEGACY_PUBLIC_LANDING_NOTCH'
  elif source['source_hole_area_m2']<1e-6:category='NUMERICAL_FINITE_RESIDUAL_EXPLICIT_ACCOUNTING'
  else:category='UNCLASSIFIED_REQUIRES_REVIEW'
  legacy_union=g.union([x['polygon_xz_m']for x in masks]); legacy_missing=g.subtract(source['hole_polygons_xz_m'],legacy_union)
  out=dict(owner_id=source['owner_id'],category=category,area_m2=source['source_hole_area_m2'],polygons_xz_m=source['hole_polygons_xz_m'],plane_y_xz_m=source['candidate_plane_y_xz_m'],legacy_mask_pieces=masks,legacy_mask_uncovered_polygons_xz_m=legacy_missing,legacy_mask_uncovered_area_m2=math.fsum(g.area(p)for p in legacy_missing),legacy_effective_owner_intersections=pointowners,canonical_public_strips=strips,current_top_pieces=source['current_rendered_top_pieces'],current_native_and_contract_pieces=native,water_pieces=source['water_pieces'],authorized_cut_column_pieces=source['authorized_access_skin_cut_pieces'])
  if category=='RETIRED_BRIDGE_MASK_PUBLIC_RESTORATION':
   out['north_native_mask_overlap_m2']=math.fsum(g.area(g.clip(p,m))for p in source['hole_polygons_xz_m']for m in nm)
   out['bridge_local_polygons_xz_m']=[[[math.fsum(basis[i][k]*(v[0 if i==0 else 1]-trans[i])for i in(0,2))for k in(0,2)]for v in p]for p in source['hole_polygons_xz_m']]
   out['proposed_action']='Retire only this obsolete bridge-hole fraction; explicitly restore the already emitted finite R18 public plane. Actual native/water exclusion and support-side closure remain mandatory.'
  elif category=='E1_E2_LEGACY_PUBLIC_LANDING_NOTCH':out['proposed_action']='Bind to the atomic seven-entry full-notch replacement; do not restore its old private plane or equate the101 cap columns with the whole landing notch.'
  rows.append(out);summary[category]['count']+=1;summary[category]['area_m2']+=source['source_hole_area_m2']
 out=dict(schema='riverstone.r18.legacy_source_hole_ledger.v1',status='FINITE_CLASSIFICATION_AND_RESTORATION_PROPOSAL_NO_ACTIVATION',sources=[ref(inp),ref(a.CITY/'evidence/r8_district_r04/scene.json'),ref(HERE/'finite_field_candidate_r04_common.json'),ref(__import__('pathlib').Path(old.__file__)),ref(__import__('pathlib').Path(old.R04.__file__)),ref(north/'ownership_review.json')]+public_domain.source_refs(),code_sha256=a.sha(__file__),rows=rows,summary=dict(summary),seconds=time.monotonic()-start,limits=['Legacy masks explain an absent top but are not actual geometry.','Old native and collision intersections retain exact height differences.','No geometry, field, controller or accepted owner is modified.'])
 target=HERE/'top_hole_provenance_r03.json';target.write_text(json.dumps(out,separators=(',',':'))+'\n');print(json.dumps(dict(summary=out['summary'],seconds=out['seconds'],output=ref(target))))
if __name__=='__main__':main()
