"""Bind classified finite source omissions without recomputing any triangle."""
import json,time,copy
from .screen import HERE,write
from .. import author as a

def run():
 start=time.monotonic();first=json.loads((HERE/'top_coverage_report_r01.json').read_bytes());restoration=json.loads((HERE/'source_lacuna_classification_r01.json').read_bytes());patch=json.loads((HERE/'top_scene_patch_r01.json').read_bytes());assert restoration['source_top_report_sha256']==a.sha(HERE/'top_coverage_report_r01.json');assert restoration['summary']['existing_owner_hits']==0
 masks=[r['polygon_xz_m']for r in restoration['records']];fail=[];checks=[]
 for r in first['failures']:
  left=a.common.subtract(r['missing_source_polygons_xz_m'],masks);area=sum(a.geo.polygon_area(p)for p in left);checks.append(dict(id=r['id'],original_missing_source_area_m2=r['missing_source_area_m2'],remaining_area_m2=area))
  if area>1e-7 or r['outside_cut_domain_m2']>1e-7:fail.append(dict(r,remaining_after_classified_restoration_m2=area))
 assert not fail and first['downward_top_count']==0
 final=copy.deepcopy(first);final['status']='PASSED_TOP_SOURCE_COVERAGE';final['failures']=[];final['classification_checks']=checks;final['source_initial_report_sha256']=a.sha(HERE/'top_coverage_report_r01.json');final['source_restoration_sha256']=a.sha(HERE/'source_lacuna_classification_r01.json');final['summary']['missing_owner_count']=0;final['summary']['classification_bind_elapsed_s']=time.monotonic()-start
 byid={r['id']:r for r in checks}
 for r in final['owner_coverage']:
  if r['id']in byid:r['inherited_source_missing_area_m2']=r['missing_source_area_m2'];r['missing_source_area_m2']=byid[r['id']]['remaining_area_m2']
 patch['status']='SOURCE_TOP_COVERAGE_PASS_PENDING_JOINT_SIDES_AND_RUNTIME';patch['source_references'].extend(dict(path=str((HERE/n).relative_to(a.ROOT)),sha256=a.sha(HERE/n))for n in('source_lacuna_classification_r01.json','lacuna_scope_review_r01.json'));patch['initial_geometry_sha256']=a.canonical_sha({k:patch[k]for k in('surface_edits','appended_surfaces','removed_foundation_proxy_ids')});final['unchanged_initial_geometry_sha256']=patch['initial_geometry_sha256'];write('top_scene_patch_r02.json',patch);write('top_coverage_report_r02.json',final);write('compact_cut_domains_r02.json',json.loads((HERE/'compact_cut_domains_r01.json').read_bytes()));print(final['summary'],flush=True)
if __name__=='__main__':run()
