"""Remove only newly authoritative native terminal footprints from R18 emission."""
import json, math, collections, copy, time
from .height_field import HERE
from . import finite_geometry_r03 as g
from ..r17_district_batches import author as a

def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def read_bound(p,h):
 assert a.sha(p)==h,(p,a.sha(p));return json.loads(p.read_bytes())
def fan(poly,plane):
 v=[[x,a.common.height(plane,[x,z]),z]for x,z in poly];out=[]
 for i in range(1,len(v)-1):
  t=[v[0],v[i],v[i+1]];n=a.normal_y(t)
  if n>0:out.append(t)
  elif n<0:out.append([t[0],t[2],t[1]])
 return out
def main():
 start=time.monotonic();source=HERE/'finite_field_candidate_r04_common.json';old=read_bound(source,'9b8852dce39ea122cf6fb2f057d6acd0fd8e826c73bf48916290165be1d94e14')
 root=a.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01'
 shoulder_path=root/'common_entry_repair_r03/retained_outer_shoulder_r18.json';shoulder=read_bound(shoulder_path,'26b1127830261ec5cab9ffdde4abe7bc09a0fde214d876c0e3a65884cd27fd5b')
 notch_path=root/'noble_entry_batch_r01/r18_four_terminal_notches.json';notches=read_bound(notch_path,'27bf4fd952f0b6bc05cacf025da39f6ced791d09628948e3c5031a9a58650079')
 holes_path=HERE/'top_hole_classification_r02.json';holes=json.loads(holes_path.read_bytes());holemap={r['owner_id']:r['hole_polygons_xz_m']for r in holes['rows']}
 masks=[];byowner=collections.defaultdict(list)
 for group in notches['groups']:
  for i,r in enumerate(group['new_physical_top_pieces']):
   m=dict(id=group['owner_id']+':NATIVE_TERMINAL:'+str(i),native_owner_id=group['owner_id'],polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'],public_source_owner_id=r['public_source_owner_id'],source=ref(notch_path));masks.append(m);byowner[r['public_source_owner_id']].append(m)
 common=dict(id=shoulder['id'],native_owner_id=shoulder['native_placement_id'],polygon_xz_m=shoulder['polygon_xz_m'],plane_y_xz_m=shoulder['plane_y_xz_m'],source=ref(shoulder_path));masks.append(common)
 records=[];changed=[];removed=[];unaffected=0;nonhole=[];maxerror=0.;native_areas=collections.defaultdict(float)
 for r in old['records']:
  relevant=list(byowner.get(r['id'],[]))
  if a.intersects(a.bounds(r['polygon_xz_m']),a.bounds(common['polygon_xz_m'])):relevant.append(common)
  hits=[]
  for m in relevant:
   q=g.clip(r['polygon_xz_m'],m['polygon_xz_m'])
   if q:hits.append(dict(m,polygon_xz_m=q))
  if not hits:records.append(r);unaffected+=1;continue
  retained=g.subtract([r['polygon_xz_m']],[m['polygon_xz_m']for m in hits]);owned_union=g.union([m['polygon_xz_m']for m in hits]);removed_area=math.fsum(g.area(p)for p in owned_union);kept_area=math.fsum(g.area(p)for p in retained);error=abs(g.area(r['polygon_xz_m'])-kept_area-removed_area);maxerror=max(maxerror,error)
  if error>1e-8:raise ValueError(('partition',r['id'],error))
  outside=g.subtract(owned_union,holemap.get(r['id'],[]));outside_area=math.fsum(g.area(p)for p in outside)
  if outside_area>1e-9:nonhole.append(dict(owner_id=r['id'],polygons_xz_m=outside,area_m2=outside_area))
  ids=[]
  for i,p in enumerate(retained):
   rec=dict(r,id=r['id']+':NATIVE_REMAINDER:'+str(i),previous_owner_id=r['id'],polygon_xz_m=p,triangles_xyz_m=fan(p,r['plane_y_xz_m']));records.append(rec);ids.append(rec['id'])
  changed.append(dict(previous_owner_id=r['id'],previous_owner_sha256=a.canonical_sha(r),previous_polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'],removed_native_pieces=hits,retained_record_ids=ids,removed_area_m2=removed_area,partition_error_m2=error,removed_outside_inherited_source_hole_area_m2=outside_area))
  removed.extend(hits)
  for m in hits:native_areas[m['native_owner_id']]+=g.area(m['polygon_xz_m'])
 if nonhole:raise ValueError(('unexpected non-hole removal',nonhole))
 ar=math.fsum(g.area(r['polygon_xz_m'])for r in records);ta=math.fsum(g.area([[v[0],v[2]]for v in t])for r in records for t in r['triangles_xyz_m']);empty=[r['id']for r in records if not r['triangles_xyz_m']];bad=[r['id']for r in records for t in r['triangles_xyz_m']if a.normal_y(t)<=0]
 assert not empty and not bad,(empty,bad)
 old_by_id={r['id']:r for r in old['records']};same=[r for r in records if r['id']in old_by_id];assert all(r==old_by_id[r['id']]for r in same)
 exception_ids={r['id']for r in old['report']['exceptions']};assert not(exception_ids&{r['previous_owner_id']for r in changed}),'Changed design exception requires explicit re-ledger'
 refs=[ref(source),ref(notch_path),ref(shoulder_path),ref(holes_path),ref(__import__('pathlib').Path(__file__))]
 report=copy.deepcopy(old['report']);report.update(finite_records=len(records),finite_area_m2=ar,rendered_triangles=sum(len(r['triangles_xyz_m'])for r in records),rendered_area_m2=ta,owner_minus_rendered_area_m2=ar-ta,empty_fan_records=empty,native_ownership_revision=dict(id='R18_NATIVE_TERMINALS_R07',source_refs=refs,unchanged_record_count=unaffected,changed_previous_record_count=len(changed),removed_native_area_m2=old['report']['finite_area_m2']-ar,removed_area_by_native_owner_m2=dict(native_areas),all_removed_pieces_are_inherited_source_holes=True,maximum_partition_error_m2=maxerror,native_exclusions=masks,limits=['The exact native physical planes differ from retained R18 planes by up to1.36mm; adjoining side closure and runtime must retain those measured seams.','The common Y8.125 cap is a nonwalking lateral shoulder.','E1/E2 full-notch interfaces remain separately bound; this revision only handles the four declared notch groups plus the common shoulder.']))
 report['source_refs']+=refs;report['activation']=False
 candidate=dict(report=report,records=records);out=HERE/'finite_field_candidate_r07_native_bound.json';out.write_text(json.dumps(candidate,separators=(',',':'))+'\n')
 review=dict(schema='riverstone.r18.native_emission_revision.v1',status='PASS_BOUNDED_NATIVE_EXCLUSION_GEOMETRY_ONLY',sources=refs,candidate=ref(out),unchanged_records=unaffected,changed_previous_records=len(changed),changed=changed,removed_native_area_by_owner_m2=dict(native_areas),all_removals_inside_original_source_holes=True,nonhole_removals=nonhole,maximum_partition_error_m2=maxerror,polygon_minus_rendered_area_m2=ar-ta,empty_fans=empty,downward_triangles=bad,previous_grade_exception_records_unchanged=True,seconds=time.monotonic()-start,scope='Exact finite removal only. All unaffected records and triangles remain value-identical. Heights of retained pieces remain on their exact prior planes. Native and controller semantics are unchanged; composition, side closure and actual traversal are pending.')
 rp=HERE/'native_emission_revision_r07_review.json';rp.write_text(json.dumps(review,separators=(',',':'))+'\n');print(json.dumps(dict(candidate=ref(out),review=ref(rp),summary={k:v for k,v in review.items()if k in('unchanged_records','changed_previous_records','removed_native_area_by_owner_m2','maximum_partition_error_m2','polygon_minus_rendered_area_m2','seconds')})))
if __name__=='__main__':main()
