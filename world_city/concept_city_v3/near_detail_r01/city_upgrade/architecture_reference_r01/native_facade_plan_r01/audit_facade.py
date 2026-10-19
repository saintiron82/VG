"""Read-only source/quantization audit. No common sampling, meshing or source edit."""
import os,resource,sys,json,hashlib,time,math
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(110,)*2)
import numpy as np
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parent;A=O.parent;R=next(p for p in O.parents if (p/'voxel_character/common/core.py').exists())
S=R/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png'
V=A/'gallery_panel_actual_r01/after'
ROIS={'front':(64,48,448,496),'back':(1088,48,1472,496),'right':(608,48,928,496),'left':(96,560,416,1008)}
PROBES=[
 ('front_masonry','front','light_masonry_plaster_appearance',(176,216,220,240)),
 ('front_upper_window','front','window_frame_and_pane',(120,224,168,252)),
 ('front_timber_post','front','visible_timber',(80,212,92,244)),
 ('front_upper_glass','front','blue_pane_appearance',(132,232,156,248)),
 ('back_masonry','back','light_masonry_plaster_appearance',(1240,216,1312,392)),
 ('back_upper_window','back','window_frame_and_pane',(1176,224,1232,280)),
 ('back_upper_glass','back','blue_pane_appearance',(1188,232,1220,264)),
 ('back_door_wood','back','visible_timber',(1188,420,1216,444)),
 ('right_masonry','right','light_masonry_plaster_appearance',(832,216,896,440)),
 ('right_upper_window','right','window_frame_and_pane',(772,212,824,264)),
 ('right_upper_glass','right','blue_pane_appearance',(784,220,812,252)),
 ('left_masonry','left','light_masonry_plaster_appearance',(128,720,192,936)),
 ('left_upper_window','left','window_frame_and_pane',(204,708,256,764)),
 ('left_upper_glass','left','blue_pane_appearance',(216,716,244,752)),
]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(Path(p).relative_to(R)),'sha256':sha(p)}
def save(name,v):
 p=O/name;assert not p.exists();p.write_text(json.dumps(v,indent=2,allow_nan=False));return ref(p)
def blockmean(crop):
 h,w=crop.shape[:2];return crop.reshape(h//4,4,w//4,4,3).mean((1,3)).repeat(4,0).repeat(4,1)
def nearest(img,palette):
 # Chunk rows so candidate palettes never allocate a full high-resolution tensor.
 out=np.empty(img.shape,np.float32)
 for y in range(0,len(img),16):
  c=img[y:y+16].astype(np.float32);idx=np.argmin(((c[:,:,None,:]-palette[None,None,:,:])**2).sum(3),2);out[y:y+16]=palette[idx]
 return out
def mse(a,b):return float(np.mean((a.astype(float)-b.astype(float))**2))
def error(a,b):
 d=a.astype(float)-b.astype(float)
 return {'rgb_rmse_0_255':math.sqrt(float(np.mean(d*d))),'rgb_mae_0_255':float(np.mean(abs(d))),'max_channel_abs_error':float(abs(d).max())}
def edge_energy(im):
 im=im.astype(float);return float((abs(np.diff(im,axis=0)).sum()+abs(np.diff(im,axis=1)).sum())/(3*((im.shape[0]-1)*im.shape[1]+(im.shape[1]-1)*im.shape[0])))
def world(view,px,py):
 if view=='front':return [(px+.5-256)/32,(496-py-.5)/32,5]
 if view=='back':return [(1280-px-.5)/32,(496-py-.5)/32,-5]
 if view=='right':return [6,(496-py-.5)/32,(768-px-.5)/32]
 return [-6,(1008-py-.5)/32,(px+.5-256)/32]
def projected_actual(view,px,py,records):
 rec=records[view];a=np.asarray([[*v['world'],1] for v in rec['world_to_pixel_anchors']]);b=np.asarray([v['pixel'] for v in rec['world_to_pixel_anchors']]);fit=np.linalg.lstsq(a,b,rcond=None)[0];return (np.asarray([*world(view,px,py),1])@fit).tolist()
def ray_hit(view,w,a):
 ix=int(math.floor(w[0]*8))+48;iy=int(math.floor(w[1]*8));iz=int(math.floor(w[2]*8))+40
 if not 0<=iy<112:return None
 if view in ('front','back'):
  if not 0<=ix<96:return None
  z=np.flatnonzero(a[iy,ix]>=0)
  if not len(z):return None
  iz=int(z[-1] if view=='front' else z[0])
 else:
  if not 0<=iz<80:return None
  x=np.flatnonzero(a[iy,:,iz]>=0)
  if not len(x):return None
  ix=int(x[-1] if view=='right' else x[0])
 return {'coarse_array_yxz':[iy,ix,iz],'material_index':int(a[iy,ix,iz]),'world_min_m':[(ix-48)/8,iy/8,(iz-40)/8]}
def run():
 start=time.monotonic();src=np.asarray(Image.open(S).convert('RGB'));old=np.load(A/'reconstruction_proof_r01/image_derived_arrays.npz');pal=old['palette'];foundation=np.load(A/'foundation_repair_r01/foundation_arrays.npz');arr=np.where(foundation['occupancy'],foundation['materials'],-1)
 records={r['view']:r for r in json.load(open(V/'capture_report.json'))['records']};results=[];examples=[];crops={}
 for ident,view,kind,box in PROBES:
  x0,y0,x1,y1=box;c=src[y0:y1,x0:x1];mean=blockmean(c);quant=nearest(mean,pal);native12=nearest(c,pal);crops[ident]=(c,mean,quant)
  r={'id':ident,'view':view,'manual_appearance_probe':kind,'roi_half_open':box,'native_pixels':int(c.shape[0]*c.shape[1]),'old_coarse_samples':int(c.shape[0]*c.shape[1]//16),'source_raw_crop_sha256':hashlib.sha256(c.tobytes()).hexdigest(),'source_to_4x4_mean':error(c,mean),'source_to_old_mean_then_palette12':error(c,quant),'source_to_native_with_old_palette12':error(c,native12),'source_edge_energy':edge_energy(c),'coarse_palette_edge_energy':edge_energy(quant),'old_quantized_colors_used':len(np.unique(quant.reshape(-1,3),axis=0)),'semantic_limit':'Broad manually located appearance probe, not certified per-pixel owner segmentation; light blocks cannot distinguish plaster from brick material/depth.'}
  if 'glass' in ident:
   blue=(c[:,:,2]>c[:,:,0]*1.05)&(c[:,:,1]>c[:,:,0]*1.1)&(c.mean(2)<150);r['blue_pixels_source']=int(blue.sum());r['blue_pixels_after_old_pipeline']=int(((quant[:,:,2]>quant[:,:,0]*1.05)&(quant[:,:,1]>quant[:,:,0]*1.1)&(quant.mean(2)<150)).sum())
  results.append(r)
 # Representative blue-pane and mortar/brick-edge source pixels: largest original-to-coarse
 # local loss within the manually labelled probe; selection rule is explicit, not hand altered.
 for ident in ['back_upper_glass','right_masonry']:
  p=next(p for p in PROBES if p[0]==ident);_,view,kind,box=p;c,mean,q=crops[ident];diff=((c.astype(float)-q)**2).sum(2)
  if 'glass' in ident:
   mask=(c[:,:,2]>c[:,:,0]*1.05)&(c[:,:,1]>c[:,:,0]*1.1)&(c.mean(2)<150);diff[~mask]=-1
  else:
   # Exclude very dark pixels: this is visible fine masonry appearance, not a void decision.
   diff[c.mean(2)<160]=-1
  yy,xx=np.unravel_index(np.argmax(diff),diff.shape);px=box[0]+int(xx);py=box[1]+int(yy);hit=ray_hit(view,world(view,px,py),arr);ap=projected_actual(view,px,py,records);im=np.asarray(Image.open(V/f'{view}.png').convert('RGB'));sx,sy=[int(round(v)) for v in ap]
  examples.append({'probe':ident,'view':view,'selection':'Maximum RGB squared loss in manually chosen blue-pane or bright masonry probe. Not a depth classifier.','source_pixel_xy':[px,py],'source_rgb':c[yy,xx].tolist(),'old_block_roi':[px//4*4,py//4*4,px//4*4+4,py//4*4+4],'block_mean_rgb':mean[yy,xx].tolist(),'old_palette_rgb':q[yy,xx].astype(int).tolist(),'native_old_palette_rgb':nearest(c,pal)[yy,xx].astype(int).tolist(),'inherited_actual_ray_hit':hit,'inherited_ray_material_rgb':pal[hit['material_index']].tolist() if hit and hit['material_index']<12 else None,'template_world_xyz':world(view,px,py),'actual_camera_pixel_float':ap,'actual_sample_xy':[sx,sy],'actual_rgb':im[sy,sx].tolist(),'actual_capture':ref(V/f'{view}.png'),'comparison_limit':'Original template correspondence only, not global source registration or an albedo calibration. The source of body captures is gallery+r04, not roof_r05.'})
 # Surface-only upper bounds from native projected inherited ray coverage, never fill volume.
 capacity=[]
 for view,roi in ROIS.items():
  x0,y0,x1,y1=roi;ys=(704,960) if view=='left' else (192,448);c=src[ys[0]:ys[1],x0:x1];hh,ww=c.shape[:2];eligible=np.zeros((hh,ww),bool)
  # Each 4x4 block shares the existing endpoint; test geometry once per coarse block.
  for yy in range(0,hh,4):
   for xx in range(0,ww,4):
    if ray_hit(view,world(view,x0+xx,ys[0]+yy),arr):eligible[yy:yy+4,xx:xx+4]=True
  r,g,b=np.moveaxis(c.astype(float),-1,0);lum=c.mean(2)
  plant=((g>r*.95)&(g>b*1.1)&(lum<190))|((r-g>70)&(r-b>80)&(g<95))
  dark=lum<75;warm=(r>=90)&(r-g>=12)&(g-b>=12)&(r>=1.3*b)&(lum>=80)
  light=(lum>=160)&((c.max(2).astype(int)-c.min(2).astype(int))<80)
  blue=(b>r*1.05)&(g>r*1.1)&(lum<150)
  candidate=eligible&(warm|light|blue)&~plant&~dark
  # Broad gallery/vegetation bands remain excluded until separately segmented.
  excluded=np.zeros_like(eligible)
  if view=='front':
   for ya,yb in [(210,298),(310,398)]:excluded[max(0,ya-ys[0]):min(hh,yb-ys[0])]=True
   excluded[:,max(0,216-x0):min(ww,296-x0)]=True
  elif view=='right':excluded[:,:max(0,700-x0)]=True
  elif view=='left':excluded[:,max(0,326-x0):]=True
  # Upper bound is explicitly preliminary; shadow and object segmentation remain incomplete.
  count=int((candidate&~excluded).sum());tiles=0
  for yy in range(0,hh,64):
   for xx in range(0,ww,64):tiles+=int(bool((candidate&~excluded)[yy:yy+64,xx:xx+64].any()))
  capacity.append({'view':view,'source_body_roi':[x0,ys[0],x1,ys[1]],'all_projected_pixels':hh*ww,'inherited_hit_native_pixels':int(eligible.sum()),'broad_appearance_candidates_after_explicit_exclusions':count,'occupied_64px_tiles_upper_bound':tiles,'classification_is_measurement_candidate_only':True,'overlap_at_corners_not_deduplicated':True,'broad_exclusions':'Y<1.5m and Y>=9.5m frozen. FRONT complete gallery bands and central foliage strip; SIDE front gallery strips excluded. RGB plant/dark exclusions are not semantic ground truth.'})
 # Native palette experiment on manually located appearance probes, not a new source or mesh.
 pix=np.concatenate([crops[p[0]][0].reshape(-1,3) for p in PROBES]);experiments=[]
 for n in [12,32,64]:
  palette_image=Image.fromarray(pix[None,:,:]).quantize(colors=n,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE);new=np.asarray(palette_image.getpalette()[:3*n],np.uint8).reshape(n,3)
  errors={p[0]:error(crops[p[0]][0],nearest(crops[p[0]][0],new)) for p in PROBES}
  experiments.append({'colors':n,'palette_rgb':new.tolist(),'input':'Only manual probe appearance pixels, equal pixel weighting, median cut; no albedo recovery or final palette approval.','native_no_spatial_averaging_errors':errors})
 save('sampling_loss.json',{'schema':'riverstone.native_facade.readonly_sampling_audit.v1','source':ref(S),'old_palette_rgb':pal.tolist(),'old_palette_has_blue_pane_color':bool(((pal[:,2]>pal[:,0]*1.05)&(pal[:,1]>pal[:,0]*1.1)).any()),'probes':results,'representative_pixels':examples,'palette_experiments':experiments,'wholehouse_native_volume_created':False,'sampling_calls':0,'mesher_calls':0,'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
 save('surface_budget.json',{'schema':'riverstone.native_facade.surface_budget.v1','views':capacity,'sum_projected_pixels':sum(r['all_projected_pixels'] for r in capacity),'sum_inherited_hit_native_pixels':sum(r['inherited_hit_native_pixels'] for r in capacity),'candidate_pixels_upper_bound':sum(r['broad_appearance_candidates_after_explicit_exclusions'] for r in capacity),'candidate_chunk_count_upper_bound':sum(r['occupied_64px_tiles_upper_bound'] for r in capacity),'candidate_is_not_authorized_or_complete_segmentation':True,'max_native_full_box_cells_for_contrast_only':384*304*320,'full_volume_forbidden':True})
 # Exact source and actual-capture crops only. Center images show numerical old sampling,
 # labelled as an analysis diagram, not a newly generated render.
 chosen=['back_upper_glass','right_masonry','front_timber_post','left_upper_window'];board=Image.new('RGB',(1520,1180),'#f6f3ed');d=ImageDraw.Draw(board);font=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
 d.text((20,16),'NATIVE FACADE LOSS | original pixels / old sampling / actual Godot',font=font(25),fill='black');d.text((20,52),'Read-only analysis. Source remains unregistered. Actual body capture = gallery+r04; roof_r05 is frozen separately.',font=font(15),fill='black')
 for i,ident in enumerate(chosen):
  p=next(p for p in PROBES if p[0]==ident);_,view,kind,box=p;c,mean,q=crops[ident];yy=95+i*265;d.text((20,yy),f'{ident}: SOURCE ROI {box}',font=font(17),fill='black')
  # Use smaller masonry crop for meaningful inspection rather than downsample full wall.
  if ident=='right_masonry':box=(832,232,864,264);c=src[232:264,832:864];q=nearest(blockmean(c),pal)
  for x,im,label in [(20,c,'Original source, nearest display'),(515,q.astype(np.uint8),'4x4 mean + old12 palette (analysis)')]:
   scale=min(440/im.shape[1],200/im.shape[0]);out=Image.fromarray(im).resize((int(im.shape[1]*scale),int(im.shape[0]*scale)),Image.Resampling.NEAREST);board.paste(out,(x,yy+45));d.text((x,yy+25),label,font=font(15),fill='black')
  p0=projected_actual(view,box[0],box[1],records);p1=projected_actual(view,box[2]-1,box[3]-1,records);ab=(math.floor(min(p0[0],p1[0]))-2,math.floor(min(p0[1],p1[1]))-2,math.ceil(max(p0[0],p1[0]))+3,math.ceil(max(p0[1],p1[1]))+3)
  actual=Image.open(V/f'{view}.png').convert('RGB').crop(ab);scale=min(440/actual.width,200/actual.height);board.paste(actual.resize((int(actual.width*scale),int(actual.height*scale)),Image.Resampling.NEAREST),(1010,yy+45));d.text((1010,yy+25),f'Actual {view} crop {ab}',font=font(14),fill='black')
 d.text((20,1160),'Appearance detail is recoverable only on confirmed existing solid owners; RGB and dark pixels do not measure hidden depth.',font=font(15),fill='black');board.save(O/'source_actual_loss_board.png')
 print(json.dumps({'probes':len(results),'examples':examples,'capacity':capacity,'seconds':time.monotonic()-start,'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True)
if __name__=='__main__':run()
