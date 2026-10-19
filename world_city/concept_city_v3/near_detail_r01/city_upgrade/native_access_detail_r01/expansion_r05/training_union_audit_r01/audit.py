"""Read-only area audit: original top-quad union versus frozen 1m patch grid.
No candidate, module, sampling or source modification. Exact source proofs only.
"""
from pathlib import Path
from fractions import Fraction as F
import collections,json,resource,sys,time
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;N=H.parents[1];OLD=N/'expansion_r04';E=OLD/'extrusion_support_r01';sys.path.insert(0,str(E));import author_extrusion as e
b=e.b;a=e.a;R=e.R;P=e.P

def ref(p):return {'path':str(p.relative_to(R)),'sha256':e.sha(p)}
def ratio(x):return [x.numerator,x.denominator]
def inside(r,s):return s[0]<=r[0]and s[1]<=r[1]and r[2]<=s[2]and r[3]<=s[3]
def cross(r,s):return min(r[2],s[2])>max(r[0],s[0])and min(r[3],s[3])>max(r[1],s[1])
def exact_area(r):return (F(r[2])-F(r[0]))*(F(r[3])-F(r[1]))

def main():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(90,)*2);start=time.monotonic();plan=e.read(E/'source_plan.json');row=plan['assets'][0];audit=e.read(E/'source_application_audit.json');master=e.read(R/row['source_master_path']);source=e.read(R/row['source_render_path']);assert e.sha(R/row['source_master_path'])==row['source_master_sha256']and e.sha(R/row['source_render_path'])==row['source_render_sha256'];assert not master.get('assembly_cuts')and not any(op['action']=='cut'for c in master['components']for op in c['operations']);owners=e.source_caps(master,row['rule']);assert owners==row['source_polygon_owners'];faces=[];cells={}
 for gi,g in enumerate(source['groups']):
  if g['material']!=row['rule']['material']:continue
  for qi,q in enumerate(g['quads']):
   try:r=a.top_rectangle(q)
   except ValueError:continue
   assert q[0][1]==0
   face={'ref':[gi,qi],'rect':r};faces.append(face)
   for patch in a.previous.patches(r):cells.setdefault(tuple(patch['grid_xy']),[]).append(face)
 accepted=[([a.strict_grid(v)for v in p['bounds_uv_m']],p['source_plane_y_m'])for p in row['placements']];assert all(y==0for r,y in accepted);existing_area=sum((r[2]-r[0])*(r[3]-r[1])*F(P)*F(P)for r,y in accepted)
 boundary_inside=F(0);boundary_outside=F(0);boundary_total=F(0);positive=0
 for r in audit['rejected_patches']:
  gi,qi=r['source_face_ref'];plane=source['groups'][gi]['quads'][qi][0][1];proof=e.semantic_proof(r['bounds_uv_m'],plane,owners);assert proof==r['proof']and not proof['supported'];outside=F(*proof['exact_uncovered_area_ratio']);assert outside>0;total=exact_area(r['bounds_uv_m']);assert 0<outside<=total;boundary_total+=total;boundary_outside+=outside;boundary_inside+=total-outside;positive+=1
 results=[];accepted_full=0;spanning=0;gained=F(0);fullarea=F(0)
 for (ix,iy),local in sorted(cells.items()):
  rect=[80*ix,80*iy,80*(ix+1),80*(iy+1)];rect_m=[v*P for v in rect];support=a.union_proof(rect,[f['rect']for f in local]);
  if support['uncovered_area_cells2']!=0:continue
  proof=e.semantic_proof(rect_m,0,owners)
  if not proof['supported']:continue
  accepted_full+=1;single=any(inside(rect,f['rect'])for f in local);oldcovers=[r for r,y in accepted if cross(rect,r)];old=a.union_proof(rect,oldcovers);new=F(old['uncovered_area_cells2'])*F(P)*F(P);gained+=new;fullarea+=exact_area(rect_m)
  if not single:
   spanning+=1;results.append({'grid_xy':[ix,iy],'bounds_uv_m':rect_m,'actual_source_face_refs':[f['ref']for f in local],'single_source_quad_contains_patch':False,'actual_quad_union_uncovered_area_cells2':support['uncovered_area_cells2'],'walk_union_uncovered_area_ratio':proof['exact_uncovered_area_ratio'],'already_covered_by_old_accepted_patch_union':old['uncovered_area_cells2']==0,'additional_supported_area_m2':float(new)})
 assert positive==397 and gained==0
 report={'schema':'riverstone.native_access_detail.quad_union_audit.v1','all_pass':True,'scope':'Original training source only; same horizontal plane, original actual top quad union AND unchanged exact source walk union. No cut/site expansion.','source_plan':ref(E/'source_plan.json'),'source_audit':ref(E/'source_application_audit.json'),'source_master':ref(R/row['source_master_path']),'source_render':ref(R/row['source_render_path']),'author':ref(Path(__file__)),'actual_top_quads':len(faces),'current_accepted_patches':len(accepted),'current_supported_area_m2':float(existing_area),'rejected_patches_replayed':positive,'every_rejected_patch_has_positive_area_outside_exact_walk_union':True,'rejected_patch_total_area_m2':float(boundary_total),'forbidden_area_inside_rejected_rectangles_m2':float(boundary_outside),'potential_exact_polygon_clip_recovery_area_m2':float(boundary_inside),'potential_recovery_area_ratio':ratio(boundary_inside),'potential_exact_supported_total_area_m2':float(existing_area+boundary_inside),'current_grid_union_cells_audited':len(cells),'full_1m_cells_supported_by_actual_quad_union_and_walk_union':accepted_full,'full_1m_cells_spanning_multiple_actual_quads':spanning,'additional_area_from_quad_union_only_m2':float(gained),'spanning_cell_proofs':results,'interpretation':'On the frozen 1m grid, source-quad union admits multi-quad patches but they are already fully covered by accepted old fragments. It cannot recover any of the 397 rejected original rectangles because each also crosses the unchanged walk boundary. Recovery requires bounded partial-cell clipping/subdivision inside both original source regions; the analytic potential is an upper bound before microgrid/crop constraints, not authorized generated geometry.','original_source_cuts':0,'new_geometry_bytes':0,'source_or_runtime_changed':False,'compile_or_sampling_performed':False,'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limits':{'address_space_bytes':256*1024*1024,'cpu_seconds':90}}
 assert not(H/'area_audit.json').exists();(H/'area_audit.json').write_bytes(a.common.payload(report));print(json.dumps({k:v for k,v in report.items()if k!='spanning_cell_proofs'}))
if __name__=='__main__':main()
