"""Actual unchanged 3D source CPU renders and pixel-center reference overlays."""
from boundary_atlas import *
import review_surface as view
view.A=A;view.BASE=BASE;view.C=C;view.F=F;view.SOURCE=SOURCE

def run():
 m,a=load();ma=gzread(BASE/'generated/costume_master.json.gz');s=np.load(BASE/'generated/continuous_costume.npz');r=view.source_render(s['vertices'],s['triangles'],ma['materials']);stats,preds=view.metrics(r,a)
 for name,v in stats.items():v['correspondence_status']='Actual visible costume classification; full illustration is uncalibrated.' if name=='front' else 'Only named paired charts have tentative correspondence; remainder conservative support, occlusion unmodeled.' if name=='side' else 'Rear material-point identity UNKNOWN; held-out candidate support, not reconstruction truth.'
 im,camera=view.view_sheet(r,'BOUNDARY ATLAS02: measured multi-view curves + curvature prior | COSTUME-ONLY source, unknown roots/backs');im.resize((1152,330)).save(BASE/'generated/costume_source_four_views.jpg',quality=73)
 view.overlays(a,preds,'ACTUAL source projection: visible agreement / outside / missing; no texture plane').resize((1152,390)).save(BASE/'generated/costume_source_overlay.jpg',quality=73)
 # Measurement overlay preserves original image and the manual-vs-gradient distinction.
 im=Image.fromarray(SOURCE.copy());d=ImageDraw.Draw(im)
 for q in m['charts']:
  for v in q['views'].values():
   for p in v['boundary']:
    x,y=p['xy_px'];d.ellipse((x-1,y-1,x+1,y+1),fill='lime' if p['status']=='measured_edge' else 'orange')
 im.crop((64,275,1536,624)).resize((1104,262)).save(BASE/'generated/measurement_boundary_overlay.jpg',quality=68)
 estimates={str(p):view.candidate_count(ma,p) for p in [.025,.0125]}
 report={'status':'SOURCE CANDIDATE; visual approval pending, not full character','metrics':stats,'candidate_estimates':estimates,'camera':camera,'master_sha256':sha(BASE/'generated/costume_master.json.gz'),'source_sha256':sha(BASE/'generated/continuous_costume.npz'),'renderer_sha256':sha(CPU_SOURCE),'projection_evaluator_sha256':sha(view.__file__),'script_sha256':sha(__file__),'actual_common_compile':False,'unknowns':['rear identity','body attachment','hidden waist','sockets','rig','material sides'],'bytes':sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file())};write(BASE/'evidence/source_review.json',report);print(json.dumps(report))
if __name__=='__main__':run()
