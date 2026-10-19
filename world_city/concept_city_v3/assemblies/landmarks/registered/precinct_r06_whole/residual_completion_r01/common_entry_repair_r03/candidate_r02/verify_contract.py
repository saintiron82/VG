"""Independent source and triangle checks before actual unchanged-controller replay."""
from pathlib import Path
import sys,json,math
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[2];sys.path.insert(0,str(BASE))
from resolve_pack import *
OUT=Path(__file__).resolve().parent

def main():
 c=load(OUT/'collision_contract.json');a=load(OUT/'geometry_audit.json');native=load(ROOT/c['native_source']['path']);refs=[];bad=[]
 def scan(x):
  if isinstance(x,dict):
   if isinstance(x.get('path'),str)and'sha256'in x:
    refs.append(x);p=ROOT/x['path']
    if not p.is_file()or sha(p)!=x['sha256']:bad.append(x)
   for v in x.values():scan(v)
  elif isinstance(x,list):
   for v in x:scan(v)
 scan(c);scan(a);pose=[-343,9,-69];face_errors=[]
 for r in c['removed_native_face_ledger']:
  q=native['groups'][r['group_index']]['quads'][r['quad_index']];world=[[v[k]+pose[k]for k in range(3)]for v in q]
  if world!=r['source_quad_xyz_m']:face_errors.append([r['group_index'],r['quad_index']])
 ts=c['add_triangles_world_xyz_m'];walk=ts[-c['walking_triangle_count']:];grades=[];degenerate=[];finite=True
 for i,t in enumerate(ts):
  finite &= all(math.isfinite(v)for p in t for v in p)
  if np.linalg.norm(np.cross(np.subtract(t[1],t[0]),np.subtract(t[2],t[0])))<1e-11:degenerate.append(i)
 for t in walk:grades.append(math.hypot(*terrain.common.plane(t)[:2]))
 checks=dict(all_refs_match=not bad,actual_removed_face_records_exact=not face_errors,all_triangles_finite=finite,no_degenerate_triangles=not degenerate,walking_winding_Godot_clockwise=all(terrain.normal_y(t)<0 for t in walk),maximum_euclidean_grade_bounded=max(grades)<=.12000001,partition_area_exact=abs(a['area_partition_error_m2'])<1e-8,visible_envelope_error_bounded=c['maximum_visual_above_collision_m']<=.15000001 and c['maximum_collision_above_visual_m']<1e-7,fixed_public_and_landing_vertices_exact=a['maximum_fixed_error_m']<1e-9,only_fine_access_collider_disabled=c['disable_native_mesh_collider_ids']==['R06_COMMON_R02:fine_access'],all_native_visual_hashes_bound=len(a['native_visual_refs'])==2)
 result=dict(status='PASS_STATIC_READY_FOR_REPLAY'if all(checks.values())else'FAIL',checks=checks,source_contract=ref(OUT/'collision_contract.json'),reference_records_checked=len(refs),mismatched_refs=bad,face_errors=face_errors,degenerate_triangles=degenerate,runtime_ready=False);(OUT/'source_contract_tests.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],checks);assert all(checks.values())
if __name__=='__main__':main()
