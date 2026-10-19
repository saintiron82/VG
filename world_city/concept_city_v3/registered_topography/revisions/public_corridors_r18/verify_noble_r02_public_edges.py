import json,math,time,hashlib
from pathlib import Path
from .height_field import HERE
from . import finite_geometry_r03 as g
from .revise_native_emission_r07 import ref,read_bound
from ..r17_district_batches import author as a

def clipline(A,B,p):
 p=g.normalize_mask(p)
 if len(p)<3 or g.area(p)<=g.MIN_AREA:return None
 sign=1 if g.signed_area(p)>0 else -1;lo=0.;hi=1.
 for u,v in zip(p,p[1:]+p[:1]):
  da=sign*g.cross(u,v,A);db=sign*g.cross(u,v,B)
  if da<0 and db<0:return None
  if da<0:lo=max(lo,da/(da-db))
  elif db<0:hi=min(hi,da/(da-db))
  if hi<=lo:return None
 return[lo,hi]
def main():
 start=time.monotonic();src=HERE/'finite_field_candidate_r07_native_bound.json';public=read_bound(src,'d807f13a82e2639e1e9c7ff37ce8750b60d783b80cee9205fe1ffe8344239683')['records'];ix=a.geo._SpatialIndex(4)
 for i,r in enumerate(public):ix.add(i,r['polygon_xz_m'])
 capownerpath=HERE/'public_top_r03_native_bound/physical_owners.json';capdata=json.loads(capownerpath.read_bytes());capowners=[r for r in capdata['owners']if r.get('kind')=='nonwalking_private_cap_remainder'];edgeowners=public+capowners;edgeindex=a.geo._SpatialIndex(4)
 for i,r in enumerate(edgeowners):edgeindex.add(i,r['polygon_xz_m'])
 root=a.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_entry_batch_r02';ep=root/'unknown_perimeter_classification.json';edges=json.loads(ep.read_bytes())['rows'];results=[]
 for e in edges:
  if not e['approved_public_column_or_landing_indexes']:continue
  A,B=e['edge_xz_m'];parts=[]
  for i in edgeindex.candidates([A,B]):
   r=edgeowners[i];seg=clipline(A,B,r['polygon_xz_m'])
   if seg:
    pts=[[A[k]+t*(B[k]-A[k])for k in(0,1)]for t in seg];parts.append(dict(owner_id=r['id'],kind=r.get('kind','public_R18'),interval=seg,plane_y_xz_m=r['plane_y_xz_m'],xyz_m=[[p[0],a.common.height(r['plane_y_xz_m'],p),p[1]]for p in pts]))
  union=[]
  for l,h in sorted(x['interval']for x in parts):
   if union and l<=union[-1][1]+1e-12:union[-1][1]=max(union[-1][1],h)
   else:union.append([l,h])
  missing=[];t=0
  for l,h in union:
   if l>t:missing.append([t,l])
   t=max(t,h)
  if t<1:missing.append([t,1])
  results.append(dict(**e,public_segments=parts,uncovered_intervals=missing,uncovered_length_m=math.dist(A,B)*math.fsum(h-l for l,h in missing)))
 audit=json.loads((root/'physical_profile_audit.json').read_bytes());nativehits=[];maxround=0.;classareas={};refs=[ref(src),ref(ep),ref(root/'physical_profile_audit.json'),ref(capownerpath)]
 for own in audit['owners']:
  phys=a.ROOT/own['physical_top']['path'];pd=json.loads(phys.read_bytes());refs.append(ref(phys))
  for kind,records in [('actual_native',own['actual_native_upward_faces']),('physical',pd['top_pieces']),('collar',own['collar_pieces'])]:
   for j,r in enumerate(records):
    for i in ix.candidates(r['polygon_xz_m']):
     q=g.clip(r['polygon_xz_m'],public[i]['polygon_xz_m']);ar=g.area(q)
     if ar:
      classareas[kind]=classareas.get(kind,0)+ar
      if ar>1e-9:nativehits.append(dict(estate=own['owner_id'],kind=kind,record_index=j,public_owner_id=public[i]['id'],polygon_xz_m=q,area_m2=ar))
      else:maxround=max(maxround,ar)
 review=json.loads((HERE/'noble_r02_public_rebind_review.json').read_bytes());numericalsum=math.fsum(review['summary']['added_public_area_by_estate_m2'].values());capmissing=review['summary']['cap_traffic_missing_area_m2']
 report=dict(status='PASS_PUBLIC_NOTCH_AND_EXISTING_NONWALKING_REMAINDER_COVERAGE'if not nativehits and max(r['uncovered_length_m']for r in results)<1e-8 else'REVIEW_EDGE_OR_OVERLAP',sources=refs,authoritative_public_source=ref(src),public_data_changed=False,no_new_public_triangles=True,full_E1_E2_traffic_missing_area_m2=capmissing,old_four_notches_uncovered_numerical_area_m2=numericalsum,numerical_residuals_not_emitted=True,source_kernel=ref(HERE/'finite_geometry_r03.py'),public_overlap_area_by_class_m2=classareas,max_individual_roundoff_overlap_m2=maxround,positive_area_owner_conflicts=nativehits,existing_nonwalking_cap_owner_count=len(capowners),edge_count=len(results),max_uncovered_edge_length_m=max(r['uncovered_length_m']for r in results),edges=results,upstream_notch_partition_review=ref(HERE/'noble_r02_public_rebind_review.json'),seconds=time.monotonic()-start,runtime_ready=False)
 out=HERE/'noble_r02_public_ownership_final_review.json';out.write_text(json.dumps(report,separators=(',',':'))+'\n');print(json.dumps({k:v for k,v in report.items()if k not in ['edges','sources']}));print(ref(out))
if __name__=='__main__':main()
