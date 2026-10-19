"""Actual whole visible-costume CPU evidence; no geometry or texture retouching."""
from joint_costume import *
import review_surface as view
view.A=A;view.BASE=BASE;view.C=C;view.F=F;view.SOURCE=SOURCE

def run():
 m,a=load_measurement();ma=gzread(BASE/'generated/costume_master.json.gz');sf=np.load(BASE/'generated/continuous_costume.npz');r=view.source_render(sf['vertices'],sf['triangles'],ma['materials']);stats,preds=view.metrics(r,a);im,cam=view.view_sheet(r,'WHOLE VISIBLE COSTUME SOURCE01 | joint pixel-bound chart depths | incomplete roots/body/head/hair');im.save(BASE/'generated/costume_source_four_views.jpg',quality=88)
 view.overlays(a,preds,'SOURCE ONLY: green agreement / red outside / blue missing; side/back material identity uncertain').save(BASE/'generated/costume_source_overlay.jpg',quality=88)
 estimates={str(p):view.candidate_count(ma,p) for p in [.025,.0125]};report={'status':'SOURCE PROTOTYPE, solver iteration limit reached; no full-character or topology approval','source_projection':stats,'exact_front_pixel_domain':bool(np.array_equal(preds['front'],a['front_support'])),'front_domain_components_four_connected':int(ndi.label(a['front_support'])[1]),'costume_only':True,'body_head_hair_not_changed_or_generated':True,'source_operations':len(sf['triangles']),'candidate_estimates_for_later_common_compile':estimates,'camera':cam,'master_sha256':sha(BASE/'generated/costume_master.json.gz'),'source_geometry_sha256':sha(BASE/'generated/continuous_costume.npz'),'CPU_renderer_sha256':sha(CPU_SOURCE),'evaluator_sha256':sha(view.__file__),'script_sha256':sha(__file__),'common_compile_performed':False,'budget':'source and evidence target3,000,000 bytes; current whole directory '+str(sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file()))};write(BASE/'evidence/source_review.json',report);print(json.dumps(report))
if __name__=='__main__':run()
