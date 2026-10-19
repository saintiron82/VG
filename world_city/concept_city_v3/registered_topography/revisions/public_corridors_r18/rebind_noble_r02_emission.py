"""Restore only R01-native notch exclusions no longer owned by R02 geometry."""
import json,math,copy,time
from pathlib import Path
from .height_field import HERE
from . import finite_geometry_r03 as g
from .revise_native_emission_r07 import fan,ref,read_bound
from ..r17_district_batches import author as a

def area(ps):return math.fsum(g.area(p)for p in ps)
def main():
 start=time.monotonic();src=HERE/'finite_field_candidate_r07_native_bound.json';old=read_bound(src,'d807f13a82e2639e1e9c7ff37ce8750b60d783b80cee9205fe1ffe8344239683')
 prev_path=HERE/'native_emission_revision_r07_review.json';prev=json.loads(prev_path.read_bytes())
 orig_path=HERE/'finite_field_candidate_r04_common.json';orig=read_bound(orig_path,'9b8852dce39ea122cf6fb2f057d6acd0fd8e826c73bf48916290165be1d94e14');origmap={r['id']:r for r in orig['records']}
 root=a.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_entry_batch_r02'
 auditpath=root/'physical_profile_audit.json';audit=read_bound(auditpath,'234d812e4653bdfa58856a1c19050e538b15d28393b7fa28809e826884e5b199')
 collarpath=root/'private_collars.json';collar=read_bound(collarpath,'37a4a3ed7a99d2737e2eea3da174f9ae8419efde50ac1e6307fdc0d692bb2460')
 packpath=root/'resolved_native_candidate.json';read_bound(packpath,'99737adced398b3a778f40367beed3687ca912560613ea037a7339c51705458d')
 masks=[];refs=[ref(src),ref(prev_path),ref(orig_path),ref(auditpath),ref(collarpath),ref(packpath)]
 for own in audit['owners']:
  for kind in ['actual_native_upward_faces','collar_pieces']:
   for i,r in enumerate(own.get(kind,[])):
    if 'polygon_xz_m' in r:masks.append(dict(id=r.get('id',own['owner_id']+':'+kind+':'+str(i)),owner_id=own['owner_id'],kind=kind,polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m']))
  p=a.ROOT/own['physical_top']['path'];d=read_bound(p,own['physical_top']['sha256']);refs.append(ref(p))
  for i,r in enumerate(d['top_pieces']):masks.append(dict(id=own['owner_id']+':physical:'+str(i),owner_id=own['owner_id'],kind='physical_top',polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m']))
 for r in collar['owners']:masks.append(dict(r,kind='collar'))
 ix=a.geo._SpatialIndex(4)
 for i,r in enumerate(masks):ix.add(i,r['polygon_xz_m'])
 def hitmasks(p):return[masks[i]for i in ix.candidates(p)if g.clip(p,masks[i]['polygon_xz_m'])]
 new=[];ledger=[];byowner={};maxerr=0
 for change in prev['changed']:
  chosen=[m for m in change['removed_native_pieces']if m['native_owner_id']in ['E4','E5','E6','E7']]
  if not chosen:continue
  oldregion=g.union([m['polygon_xz_m']for m in chosen]);source=origmap[change['previous_owner_id']]
  for n,p in enumerate(oldregion):
   hits=hitmasks(p);remain=g.subtract([p],[r['polygon_xz_m']for r in hits]);owned=g.union([g.clip(p,r['polygon_xz_m'])for r in hits]);error=abs(g.area(p)-area(remain)-area(owned));maxerr=max(maxerr,error)
   assert error<1e-8,(source['id'],error)
   ids=[]
   for q in remain:
    rec=dict(source,id=source['id']+':NOBLE_R02_RESTORE:'+str(len(new)),previous_owner_id=source['id'],polygon_xz_m=q,triangles_xyz_m=fan(q,source['plane_y_xz_m']),kind='noble_r02_public_notch_restoration')
    assert rec['triangles_xyz_m'];new.append(rec);ids.append(rec['id'])
   owner=chosen[0]['native_owner_id'];byowner[owner]=byowner.get(owner,0)+area(remain)
   ledger.append(dict(owner_id=owner,source_owner_id=source['id'],previously_native_owned_polygon_xz_m=p,source_plane_y_xz_m=source['plane_y_xz_m'],retained_r02_native_or_private_pieces=owned,new_public_record_ids=ids,new_public_area_m2=area(remain),partition_error_m2=error))
 # Every original R07 value survives, and additions must be public/native disjoint.
 index=a.geo._SpatialIndex(4)
 for i,r in enumerate(old['records']):index.add(i,r['polygon_xz_m'])
 overlaps=[]
 for r in new:
  for i in index.candidates(r['polygon_xz_m']):
   q=g.clip(r['polygon_xz_m'],old['records'][i]['polygon_xz_m'])
   if q and g.area(q)>1e-9:overlaps.append(dict(a=r['id'],b=old['records'][i]['id'],area_m2=g.area(q)))
 assert not overlaps,overlaps[:3]
 # Full E1/E2 cap columns: explicitly account traffic fractions against canonical public and current private/native floors.
 cap_path=a.CITY/'assemblies/property/registered/public_lane_repairs_r01/baseline/cap_columns.json';cap=read_bound(cap_path,'2c54dd9602d7ea943460ceb659d03d76fad25e66a3bd01a03007a96b0d0e1d6c');refs.append(ref(cap_path));capledger=[]
 for group in cap['records']:
  for ci,col in enumerate(group['candidate_columns']):
   for ti,p in enumerate(col['traffic_clip_polygons_xz_m']):
    public=[old['records'][i]for i in index.candidates(p)if g.clip(p,old['records'][i]['polygon_xz_m'])]
    publicpieces=g.union([g.clip(p,r['polygon_xz_m'])for r in public]);other=hitmasks(p);otherpieces=g.union([g.clip(p,r['polygon_xz_m'])for r in other]);missing=g.subtract([p],publicpieces+otherpieces)
    capledger.append(dict(owner_id=group['property_id'],column_index=ci,traffic_clip_index=ti,polygon_xz_m=p,area_m2=g.area(p),public_owner_ids=[r['id']for r in public],public_covered_area_m2=area(publicpieces),current_native_or_private_area_m2=area(otherpieces),missing_polygons_xz_m=missing,missing_area_m2=area(missing)))
 report=copy.deepcopy(old['report']);records=old['records']+new;report.update(finite_records=len(records),finite_area_m2=area([r['polygon_xz_m']for r in records]),rendered_triangles=sum(len(r['triangles_xyz_m'])for r in records),rendered_area_m2=area([[v[0],v[2]]for r in records for t in r['triangles_xyz_m']for v in []]) if False else math.fsum(g.area([[v[0],v[2]]for v in t])for r in records for t in r['triangles_xyz_m']))
 report['noble_r02_revision']=dict(source_refs=refs,all_original_r07_records_value_identical=True,added_public_area_by_estate_m2=byowner,added_record_count=len(new),maximum_partition_error_m2=maxerr,cap_traffic_missing_area_m2=math.fsum(r['missing_area_m2']for r in capledger),runtime_ready=False)
 out=HERE/'finite_field_candidate_r08_noble_r02.json';out.write_text(json.dumps(dict(report=report,records=records),separators=(',',':'))+'\n')
 additions=HERE/'noble_r02_public_additions.json';additions.write_text(json.dumps(dict(source_refs=refs,records=new),separators=(',',':'))+'\n')
 review=dict(schema='riverstone.noble_r02.public_notch_rebind.v1',status='SOURCE_GEOMETRY_REVIEW_PENDING_CAP_MISSING_CLASSIFICATION'if report['noble_r02_revision']['cap_traffic_missing_area_m2']>1e-8 else'PASS_FINITE_SOURCE_GEOMETRY_ONLY',candidate=ref(out),additions=ref(additions),source_refs=refs,summary=report['noble_r02_revision'],notch_ledger=ledger,full_E1_E2_traffic_cap_ledger=capledger,positive_area_original_public_overlap=overlaps,seconds=time.monotonic()-start)
 rp=HERE/'noble_r02_public_rebind_review.json';rp.write_text(json.dumps(review,separators=(',',':'))+'\n');print(json.dumps(dict(candidate=ref(out),review=ref(rp),summary=review['summary'],seconds=review['seconds'])))
if __name__=='__main__':main()
