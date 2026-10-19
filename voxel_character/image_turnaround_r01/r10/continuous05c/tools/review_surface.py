"""Exact-pixel-center projection and CPU multi-angle evidence for same master."""
from measured_surface import *
from core import EPS

def source_render(v,f,mats):
 q=[[v[i].tolist() for i in tri]+[v[tri[-1]].tolist()] for tri in f]
 # Render both faces, with identical measured outer median for geometry review.
 return {'materials':mats,'groups':[{'material':'outer','quads':q+[[p[0],p[2],p[1],p[1]] for p in q]}]}

def project_exact(r,view):
 x0,y0,x1,y1=view['crop'];out=np.zeros((y1-y0,x1-x0),bool);theta=math.radians(view['yaw_degrees']);s=HEIGHT/view['scale_px_per_unit']
 for group in r['groups']:
  for quad in group['quads']:
   p=np.array([[view['axis_u']+(math.cos(theta)*x-math.sin(theta)*z)/s-x0,view['sole_y']-y/s-y0] for x,y,z in quad])
   for ids in ((0,1,2),(0,2,3)):
    t=p[list(ids)];lo=np.maximum(np.floor(t.min(0)).astype(int),0);hi=np.minimum(np.ceil(t.max(0)).astype(int),[x1-x0,y1-y0])
    if np.any(hi<=lo):continue
    xx,yy=np.meshgrid(np.arange(lo[0],hi[0])+.5,np.arange(lo[1],hi[1])+.5);a,b,c=t;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(den)<1e-12:continue
    wa=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den;wb=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;wc=1-wa-wb;out[lo[1]:hi[1],lo[0]:hi[0]]|=(wa>=-1e-8)&(wb>=-1e-8)&(wc>=-1e-8)
 return out

def metrics(r,a):
 result={};preds={}
 for name,view in C['views'].items():
  pred=project_exact(r,view);vis=a[name+'_visible'];unknown=a[name+'_occluded_unknown'];support=vis|unknown;inter=int((pred&vis).sum());pr=int(pred.sum());union=int(((pred&~unknown)|vis).sum());preds[name]=pred
  result[name]={'predicted_pixels':pr,'measured_visible_pixels':int(vis.sum()),'intersection_visible_pixels':inter,'unknown_occluded_projection_pixels':int((pred&unknown).sum()),'visible_target_coverage':inter/int(vis.sum()),'candidate_region_IoU_excluding_occlusion_unknown':inter/union if union else 0,'projected_outside_candidate_region_pixels':int((pred&~support).sum()),'projected_outside_conservative_foreground_pixels':int((pred&~a[name+'_foreground']).sum()),'source_support_fraction':int((pred&support).sum())/pr if pr else None,'correspondence_status':'front visible measured patch target' if name=='front' else 'provisional side same-flap hypothesis; not calibrated truth' if name=='side' else 'held-out uncertain counterpart; not a fit target or art pass'}
 return result,preds

def overlays(a,preds,label):
 sheet=Image.new('RGB',(1536,520),'white');d=ImageDraw.Draw(sheet);d.text((10,10),label+' | green visible agreement / red outside candidate / blue missing / amber occluded',fill='black')
 for i,name in enumerate(['front','side','back']):
  view=C['views'][name];x0,y0,x1,y1=view['crop'];rgb=SOURCE[y0:y1,x0:x1].astype(float);p=preds[name];vis=a[name+'_visible'];u=a[name+'_occluded_unknown'];good=p&vis;bad=p&~(vis|u);miss=vis&~p;unk=p&u
  rgb[good]=.5*rgb[good]+[20,110,30];rgb[bad]=.4*rgb[bad]+[140,10,10];rgb[miss]=.5*rgb[miss]+[15,40,110];rgb[unk]=.4*rgb[unk]+[140,80,0]
  box=A['views'][name]['crop_review'];im=Image.fromarray(np.clip(rgb,0,255).astype(np.uint8)).crop([box[0]-x0,box[1]-y0,box[2]-x0,box[3]-y0]);im.thumbnail((490,420));im=im.resize((im.width*2,im.height*2));im.thumbnail((490,420));sheet.paste(im,(512*i+10,50));d.text((512*i+10,480),name+(' candidate identity UNKNOWN' if name=='back' else ' correspondence provisional' if name=='side' else ' measured visible patch'),fill='black')
 return sheet

def view_sheet(r,label):
 vv=np.array([p for g in r['groups'] for q in g['quads'] for p in q]);center=(vv.min(0)+vv.max(0))/2;span=float(max(vv.max(0)-vv.min(0))*1.25);sheet=Image.new('RGB',(1536,440),'white');d=ImageDraw.Draw(sheet);d.text((10,8),label,fill='black')
 for i,(name,yaw,tilt) in enumerate([('front',0,0),('three_quarter',45,12),('side90',90,0),('back',180,0)]):
  im=raster(r,math.radians(yaw),math.radians(tilt),center,span,size=370);sheet.paste(im,(384*i,35));d.text((384*i+10,411),name,fill='black')
 return sheet,{'center_m':center.tolist(),'span_m':span,'views':[0,45,90,180]}

def candidate_count(master,pitch):
 count=0
 for op in master['components'][0]['operations']:
  shape=prepare_shape(op['shape'],pitch);lo,hi=shape_bounds(shape);tr=transform(op.get('transform'));corners=np.array([apply(tr,p) for p in itertools.product(*zip(lo,hi))]);low=corners.min(0);high=corners.max(0);count+=math.prod(max(0,math.ceil(b/pitch-EPS)-math.floor(aa/pitch+EPS)) for aa,b in zip(low,high))
 return count

def source_review():
 m,a=load_measurement();ma=gzread(BASE/'generated/panel_master.json.gz');sf=np.load(BASE/'generated/continuous_surface.npz');r=source_render(sf['vertices'],sf['triangles'],ma['materials']);stats,pred=metrics(r,a);sheet,cam=view_sheet(r,'CONTINUOUS05C: actual minimum-curvature mid-surface | white material is geometry-review only');sheet.save(BASE/'generated/source_four_views.jpg',quality=90);overlays(a,pred,'SOURCE MID-SURFACE').save(BASE/'generated/source_overlay.jpg',quality=92)
 # Measured boundary search result remains inspectable independently of geometry.
 big=Image.fromarray(SOURCE.copy());dr=ImageDraw.Draw(big)
 for name,data in m['views'].items():
  for pt in data['measured_contour']:
   x,y=pt['xy_px'];col='lime' if pt['status']=='measured_edge' else 'orange';dr.ellipse((x-1,y-1,x+1,y+1),fill=col)
 big.crop((0,330,1536,490)).resize((1536,160)).save(BASE/'generated/measurement_boundary_overlay.png')
 estimates={str(p):candidate_count(ma,p) for p in [.025,.0125]};write(BASE/'evidence/source_review.json',{'metrics':stats,'source_vertices':len(sf['vertices']),'source_triangles':len(sf['triangles']),'source_components':int(ndi.label(a['front_support'])[1]),'source_input_mask_components':m['views']['front']['domain_components'],'surface_sha256':sha(BASE/'generated/continuous_surface.npz'),'master_sha256':sha(BASE/'generated/panel_master.json.gz'),'source_pixel_sha256':m['source_pixel_sha256'],'camera':cam,'renderer_sha256':sha(CPU_SOURCE),'projection_evaluator_sha256':sha(__file__),'candidate_estimates':estimates,'normal_thickness_m':A['surface_prior']['normal_representation_thickness_m'],'full_character_complete':False,'GPU':False})
 print(json.dumps({'metrics':stats,'candidate_estimates':estimates,'source_components':int(ndi.label(a['front_support'])[1])}))
if __name__=='__main__':source_review()
