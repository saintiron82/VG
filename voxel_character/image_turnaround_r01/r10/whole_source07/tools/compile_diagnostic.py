"""Actual unchanged common compiler/mesher. Shape and art failure remain explicit."""
from common_preflight07 import *
from review_hole_aware import mats
import review_surface as view
view.A=previous.A;view.BASE=BASE;view.C=C;view.F=F;view.SOURCE=SOURCE

def run():
 t=time.monotonic();ma,ch=master_from_source();pre=read(BASE/'evidence/common_preflight.json');assert digest(ma)==pre['master_semantic_sha256'];assert pre['total_candidates']<=220000
 co=compile_master(ma,{'pitch':.025},max_candidate_cells=220000,max_output_cells=20000);first=time.monotonic()-t;assert co['candidate_cells']==pre['total_candidates'];r=make_render_data(co);gzwrite(BASE/'generated/common25.cells.json.gz',co);gzwrite(BASE/'generated/common25.render.json.gz',r)
 write(BASE/'evidence/common_first_compile.json',{'seconds':first,'cells':len(co['cells']),'candidates':co['candidate_cells'],'structure':components(co['cells']),'compiler_sha256':co['compiler_source_hash'],'master_semantic_sha256':co['master_hash'],'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'valid_common_constraints_only':co['valid'],'art_or_shape_pass':False});print('FIRST_COMPILE',json.dumps(read(BASE/'evidence/common_first_compile.json')),flush=True)
 # Recompile by immutable named charts, preserving operation order/feature IDs.
 # Paint-only composition must exactly match the independent complete compile.
 sets={};merged={};chunk_reports=[];ops=ma['components'][0]['operations']
 for i in sorted(set(ch.tolist())):
  sub={**ma,'components':[{**ma['components'][0],'operations':[op for op,k in zip(ops,ch) if k==i]}]};small=compile_master(sub,{'pitch':.025},max_candidate_cells=80000,max_output_cells=20000);sets[int(i)]={tuple(row[:3]) for row in small['cells']};merged.update({tuple(row[:3]):row for row in small['cells']});chunk_reports.append({'chart':int(i),'candidates':small['candidate_cells'],'cells':len(small['cells']),'common_nonempty':small['valid']})
 merged_rows=[merged[k] for k in sorted(merged)];repeat_exact=merged_rows==co['cells'];assert repeat_exact
 contacts=[]
 for i in sorted(sets):
  for j in sorted(sets):
   if j<=i:continue
   overlap=len(sets[i]&sets[j]);near=sum(any(tuple(c[k]+(d if k==ax else 0) for k in range(3)) in sets[j] for ax in range(3) for d in [-1,1]) for c in sets[i])
   if overlap or near:contacts.append({'a_chart':i,'b_chart':j,'overlap_cells':overlap,'a_cells_with_six_neighbor_in_b':near,'meaning':'Actual representation contact/overlap; not proof of intended sewing. Rear overlap must be interpreted against unresolved thickness contradictions.'})
 m,a=load();stats,pred=view.metrics(r,a);from review_height import fixed_views
 im,cam=fixed_views(r,'ACTUAL COMMON25 WIDTH07 | same source/thickness/origin | fixed04 camera; all cells retained');im.resize((1152,330)).save(BASE/'generated/common25_four_views.jpg',quality=80);view.overlays(a,pred,'ACTUAL common occupancy; no deleted islands, no image correction').resize((1152,390)).save(BASE/'generated/common25_overlay.jpg',quality=78)
 report={'status':'COMMON OCCUPANCY PROCESS VERIFIED; NOT ART/COMPLETE CHARACTER APPROVAL','same_source_independent_full_vs_chart_common_cells_exact':repeat_exact,'ordered_paint_composition_verified':True,'full_master_semantic_sha256':co['master_hash'],'common_payload_sha256':co['payload_hash'],'compiled_file_sha256':sha(BASE/'generated/common25.cells.json.gz'),'render_file_sha256':sha(BASE/'generated/common25.render.json.gz'),'source_geometry_sha256':sha(BASE/'generated/continuous_costume.npz'),'compiler_sha256':co['compiler_source_hash'],'mesher_sha256':r['provenance']['mesher_sha256'],'render_exporter_sha256':r['provenance']['exporter_sha256'],'CPU_renderer_sha256':sha(CPU_SOURCE),'script_sha256':sha(__file__),'cells':len(co['cells']),'candidates':co['candidate_cells'],'quad_count':r['quad_count'],'six_connected_structure':components(co['cells']),'by_chart':chunk_reports,'actual_contacts':contacts,'projection':stats,'camera':cam,'pitch_m':.025,'grid_origin':[0,0,0],'normal_thickness_m':.025,'no_output_repair':True,'rear_depth_limit':'25mm front-rear ordering is an explicit inferred prior; side camera and panel identity remain provisional. No hidden thickness change.','body_attachment_socket_rig':None,'GPU':False,'seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'bytes':sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file())};write(BASE/'evidence/common_verification.json',report);print(json.dumps(report))
if __name__=='__main__':run()
