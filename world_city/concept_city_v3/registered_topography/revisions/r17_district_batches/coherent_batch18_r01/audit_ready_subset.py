"""Measured native, top winding and finite support checks for the ready subset."""
import json,time,math,collections
import numpy as np
from .screen import HERE,write
from .. import author as a,native_clearance

def run():
 start=time.monotonic();hand=json.loads((HERE/'physical_owner_handoff_r02.json').read_bytes());selected=set(hand['accepted_holding_ids']);source=json.loads((HERE/'effective_source_layout_r03.json').read_bytes());retired={r['source_id']for r in hand['retirement_records']}|{r['source_id']for r in json.loads((HERE.parent/'contour_bulk_r01/physical_owner_handoff_r02.json').read_bytes())['retirement_records']};filtered=dict(source,placements=[r for r in source['placements']if r['holding_id']in selected],actual_doors=[r for r in source['actual_doors']if r['holding_id']in selected],holdings=[r for r in source['holdings']if r['id']in selected],shared_private_routes=[],retired_source_ids=sorted(retired),retirement_records=[r['source_record']for r in hand['retirement_records']]);native=native_clearance.check(filtered);write('native_ready_subset_audit_r01.json',native);print('Native',native['summary'],flush=True)
 patch=json.loads((HERE/'top_scene_patch_r02.json').read_bytes());top=[];exception=json.loads((HERE/'profiles/PRIVATE_GROUP_BLOCK_010_R8_C006.json').read_bytes())['private_domain_polygons_xz_m'];exception_outside=[]
 for material,vertices in patch['appended_surfaces'].items():
  tr=np.array(vertices).reshape(-1,3,3);norm=np.cross(tr[:,1]-tr[:,0],tr[:,2]-tr[:,0]);g=np.linalg.norm(norm[:,[0,2]],axis=1)/norm[:,1];top.append(dict(material=material,triangles=len(tr),downward=int((norm[:,1]<=0).sum()),maximum_actual_gradient=float(g.max()),over_grade=int((g>.15000001).sum()),over_12_percent=int((g>.12000001).sum()),projected_area_m2=float(norm[:,1].sum()/2)))
 for material,vertices in patch['appended_surfaces'].items():
  for j in range(0,len(vertices),3):
   tri=vertices[j:j+3];plane=a.common.plane(tri)
   if math.hypot(*plane[:2])<=.12000001:continue
   poly=[[v[0],v[2]]for v in tri];outside=sum(a.geo.polygon_area(p)for p in a.common.subtract([poly],exception))
   if outside>1e-9:exception_outside.append(dict(material=material,appended_triangle_index=j//3,outside_exception_area_m2=outside))
 hi=a.geo._SpatialIndex(2)
 for i,r in enumerate(hand['native_holes']):hi.add(i,r['polygon_xz_m'])
 conflicts=[]
 for r in hand['rendered_plane_owners']:
  p=r['polygon_xz_m']
  for j in hi.candidates(p):
   q=a.clip(p,hand['native_holes'][j]['polygon_xz_m'])
   if q and(a0:=a.geo.polygon_area(q))>1e-7:conflicts.append(dict(render_owner_id=r['id'],native_owner_id=hand['native_holes'][j]['id'],area_m2=a0,polygon_xz_m=q))
 print('Native top overlap',len(conflicts),flush=True);oi=a.geo._SpatialIndex(2)
 for i,r in enumerate(hand['physical_earth_owners']):oi.add(i,r['polygon_xz_m'])
 support=[]
 for r in hand['native_earth_bearings']:
  covers=[];height_error=0.
  for j in oi.candidates(r['polygon_xz_m']):
   o=hand['physical_earth_owners'][j];q=a.clip(r['polygon_xz_m'],o['polygon_xz_m'])
   if not q:continue
   err=max(abs(a.common.height(o['plane_y_xz_m'],v)-r['floor_y_m'])for v in q);height_error=max(height_error,err)
   if err<=1e-7:covers.append(q)
  gap=sum(a.geo.polygon_area(p)for p in a.common.subtract([r['polygon_xz_m']],covers));support.append(dict(id=r['id'],holding_id=r['holding_id'],missing_equal_datum_earth_m2=gap,maximum_earth_height_error_m=height_error,embedded_depth_m=r['floor_y_m']-r['native_bottom_y_m']))
 failures=[r for r in support if r['missing_equal_datum_earth_m2']>1e-7 or r['embedded_depth_m']< -1e-7];write('ready_subset_acceptance_r01.json',dict(status='SOURCE_TOP_NATIVE_SUPPORT_PASS_PENDING_JOINT_SIDE_AND_RUNTIME'if not failures and not conflicts and not exception_outside and native['passes_source_gate']and not any(r['downward']or r['over_grade']for r in top)else'HELD_SOURCE_SUBSET',source_handoff_sha256=a.sha(HERE/'physical_owner_handoff_r02.json'),source_patch_sha256=a.sha(HERE/'top_scene_patch_r02.json'),native_subset_report_sha256=a.sha(HERE/'native_ready_subset_audit_r01.json'),emitted_top_report=top,grade_exception_outside=exception_outside,grade_exception_holding_id='BLOCK_010:R8_C006',native_top_overlaps=conflicts,native_bearing_support=support,support_failures=failures,summary=dict(native_conflicts=len(native['retained_native_conflicts']),native_top_overlaps=len(conflicts),native_bearings=len(support),support_failures=len(failures),elapsed_s=time.monotonic()-start),activation=False));print('Complete',len(failures),'support failures',time.monotonic()-start,flush=True)
if __name__=='__main__':run()
