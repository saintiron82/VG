"""Compare immutable actual Godot screenshots with source-derived masks.
Only comparison crops/annotations are written. No screenshot or source-image warp,
geometry change, screenshot recoloring, or best-fit shape alignment is performed.
"""
import hashlib,json,time,resource
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'voxel_character/common/core.py').exists());O=Path(__file__).resolve().parent;D=O.parent;C=D/'actual_godot_r02';P=ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01';pitch=.125
ROIS={'front':[64,48,448,496],'back':[1088,48,1472,496],'right':[608,48,928,496],'left':[96,560,416,1008]}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size}
def save_json(p,o):
 assert not p.exists();p.write_text(json.dumps(o,indent=2,allow_nan=False)+'\n')
def save_png(p,im):assert not p.exists();im.save(p)
def metric(actual,expected,valid):
 inter=int((actual&expected&valid).sum());union=int(((actual|expected)&valid).sum());fp=int((actual&~expected&valid).sum());fn=int((~actual&expected&valid).sum())
 return {'iou':inter/union if union else 1,'intersection':inter,'union':union,'false_positive':fp,'false_negative':fn,'symmetric_difference':fp+fn,'valid_samples':int(valid.sum())}
def rgb_error(a,b,valid):
 e=a[valid].astype(float)-b[valid].astype(float)
 return {'samples':int(valid.sum()),'mae_0_255':float(np.abs(e).mean()),'rmse_0_255':float(np.sqrt((e*e).mean()))}
def font(sz):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',sz)
def board_cell(board,im,xy,size):
 # Display-only uniform scaling; analysis never uses these thumbnails.
 q=im.copy();q.thumbnail(size,Image.Resampling.NEAREST);board.paste(q,(xy[0]+(size[0]-q.width)//2,xy[1]+(size[1]-q.height)//2))
def run():
 start=time.monotonic();cap=json.loads((C/'capture_report.json').read_text());base=json.loads((D/'verification.json').read_text());assert cap['source_render_sha256']==base['render']['sha256']==sha(D/'diagnostic.render.json.gz')
 ar=np.load(D/'image_derived_arrays.npz');src=Image.open(P/'generated_candidate_r03.png').convert('RGB');source_sha=sha(P/'generated_candidate_r03.png');pal=ar['palette'];occ=ar['occupancy'];mats=ar['materials'];initial_inputs=[ref(C/'capture_report.json'),ref(D/'diagnostic.render.json.gz'),ref(D/'image_derived_arrays.npz'),ref(P/'generated_candidate_r03.png'),ref(P/'registration_r03.json'),ref(O/'compare_actual.py')];rows=[];images=[]
 for name in ['front','right','back','left']:
  row=next(r for r in cap['records'] if r['view']==name);assert row['projection']=='orthographic' and row['unshaded'] and row['save_error']==0
  f=C/(name+'.png');assert Path(row['image']).resolve()==f.resolve();initial_inputs.append(ref(f));im=Image.open(f).convert('RGB');a=np.asarray(im);H,W=a.shape[:2];assert [W,H]==row['viewport_size'];side=name in ('right','left');axis=2 if side else 0;half=5 if side else 6;width=80 if side else 96
  anc=row['world_to_pixel_anchors'];design=np.array([[v['world'][axis],v['world'][1],1] for v in anc],float);screen=np.array([v['pixel'] for v in anc]);coef=np.linalg.lstsq(design,screen,rcond=None)[0];resid=float(np.abs(design@coef-screen).max());assert resid<.001
  # Blank corners are fixed far from subject and HUD. Background is read from
  # screenshot, not guessed from source colors or renderer palette.
  patches=[a[90:130,20:60],a[H-70:H-30,W-70:W-30]];bg=np.median(np.concatenate([p.reshape(-1,3) for p in patches]),axis=0);spread=max(float(np.max(np.abs(p.astype(float)-bg))) for p in patches);assert spread<.01
  actual=np.max(np.abs(a.astype(np.int16)-bg),axis=2)>3
  yy,uu=np.indices((112,width));worldu=(uu+.5)*pitch-half;worldy=(yy+.5)*pitch;centers=np.stack([worldu,worldy,np.ones_like(worldu)],axis=-1)@coef;cx=np.floor(centers[:,:,0]).astype(int);cy=np.floor(centers[:,:,1]).astype(int);assert cx.min()>=0 and cy.min()>=0 and cx.max()<W and cy.max()<H
  seen=actual[cy,cx];screenrgb=a[cy,cx];expected=occ.any(axis=1 if side else 2);inputmask=ar[name+'_silhouette'];valid=np.ones_like(inputmask,bool)
  if side:valid[76:]=False
  # HUD is explicit screenshot UI ROI; it must not overlap selected samples.
  hud=((cx>=10)&(cx<850)&(cy>=10)&(cy<67));assert not(hud&valid).any()
  exact_geometry=np.array_equal(seen,expected);assert exact_geometry,'Actual screenshot cell-center silhouette differs from retained common occupancy'
  source_metric=metric(seen,inputmask,valid)
  # Actual nearest cell material projected using camera direction, no new mesh.
  predicted=np.zeros((*seen.shape,3),float)
  for y,u in np.argwhere(expected):
   ids=np.flatnonzero(occ[y,:,u] if side else occ[y,u,:]);idx=int(ids[-1] if name in ('front','right') else ids[0]);mat=int(mats[y,idx,u] if side else mats[y,u,idx]);predicted[y,u]=pal[mat]
  colorvalid=valid&seen&inputmask;measured=ar[name+'_rgb'];labels=ar[name+'_material'];quantized=pal[labels]
  # Invert only the camera affine, never an image-content-derived registration.
  inv=np.linalg.inv(coef[:2,:]);sy,sx=np.indices((H,W));coords=(np.stack([sx+.5,sy+.5],axis=-1)-coef[2])@inv
  gu=np.floor((coords[:,:,0]+half)/pitch).astype(int);gy=np.floor(coords[:,:,1]/pitch).astype(int);domain=(gu>=0)&(gu<width)&(gy>=0)&(gy<112);compare=domain&(coords[:,:,1]<9.5 if side else True);hudfull=(sx>=10)&(sx<850)&(sy>=10)&(sy<67);compare&=~hudfull
  safeu=np.clip(gu,0,width-1);safey=np.clip(gy,0,111);input_projected=inputmask[safey,safeu]&domain;common_projected=expected[safey,safeu]&domain;screen_metric=metric(actual,input_projected,compare);camera_boundary_metric=metric(actual,common_projected,domain&~hudfull)
  overlays=np.full_like(a,[247,244,238]);overlays[domain]=[226,226,226];overlays[compare&actual&input_projected]=[106,144,117];overlays[compare&input_projected&~actual]=[211,47,134];overlays[compare&actual&~input_projected]=[234,137,42];excluded=domain&~compare;overlays[excluded]=[186,192,205];overlays[excluded&(((sx+sy)//8)%2==0)]=[211,216,226]
  overlay=Image.fromarray(overlays);dr=ImageDraw.Draw(overlay);dr.rectangle((10,10,850,67),fill=(47,51,54));dr.text((20,18),f'{name.upper()} | green overlap / magenta source-only / orange actual-only',font=font(17),fill='white');dr.text((20,41),'Gray hatch: excluded upper SIDE roof. Same fixed world-camera anchors.',font=font(16),fill='white')
  crop=src.crop(ROIS[name]);save_png(O/(name+'.source_crop.png'),crop);save_png(O/(name+'.silhouette_overlay.png'),overlay)
  rowout={'view':name,'source_crop':ref(O/(name+'.source_crop.png')),'actual_capture':ref(f),'difference_overlay':ref(O/(name+'.silhouette_overlay.png')),'source_roi_px':ROIS[name],'source_roi_kind':'fixed original template32px/m coordinate annotation, not fitted to capture','camera_affine_world_u_y_1_to_pixel_uv':coef.tolist(),'world_u_axis':'Z' if side else 'X','max_anchor_fit_residual_px':resid,'capture_background_rgb':bg.tolist(),'background_patch_max_deviation':spread,'foreground_threshold_max_channel_distance':3,'hud_roi_px':[10,10,850,67],'selected_center_samples_occluded_by_hud':int((hud&valid).sum()),'cell_center_geometry_matches_common_occupancy':exact_geometry,'actual_screenshot_vs_source_mask_cells':source_metric,'actual_screenshot_vs_source_mask_pixels':screen_metric,'actual_screenshot_vs_common_projected_pixels':camera_boundary_metric,'excluded_world_y_ge_m':9.5 if side else None,'rgb_errors':{'input_to_own_12color_quantization':rgb_error(quantized,measured,colorvalid),'projected_common_palette_to_input':rgb_error(predicted,measured,colorvalid),'actual_unshaded_capture_to_input':rgb_error(screenrgb,measured,colorvalid),'actual_capture_to_common_palette':rgb_error(screenrgb,predicted,colorvalid)},'color_comparison_scope':'Only mutual foreground cell centers; same fixed projection. First error isolates quantization; second includes view material/depth assignment; final capture differences include renderer color conversion. Input already includes baked lighting and foliage. No albedo claim.'};rows.append(rowout);images.append((name,crop,im,overlay,source_metric))
 board=Image.new('RGB',(1610,2240),'white');draw=ImageDraw.Draw(board);draw.text((25,15),'IMAGE -> COMMON VOXELS -> ACTUAL GODOT | DIAGNOSTIC PROJECTION AUDIT',font=font(24),fill=(20,25,30));draw.text((25,51),'r03 input registration FAILED. TOP/BOTTOM excluded. SIDE roof above9.5m excluded. No source/render edits.',font=font(18),fill=(145,40,60));draw.text((25,81),'Pixel RGB has baked light/shadow;12-color quantization is not recovered material. Gallery1.125m is a planned depth prior.',font=font(17),fill=(60,60,60));draw.text((25,118),'Exact input crop (32px/m)',font=font(19),fill='black');draw.text((430,118),'Actual Godot r02, whole original frame, display scale1/2',font=font(16),fill='black');draw.text((1030,118),'Fixed camera-space silhouette difference, scale1/2',font=font(16),fill='black')
 for i,(name,crop,im,overlay,m) in enumerate(images):
  y=155+i*505;draw.text((25,y),f'{name.upper()} | accepted-mask IoU {m["iou"]*100:.2f}%',font=font(20),fill='black');board_cell(board,crop,(25,y+32),(384,448));board_cell(board,im,(425,y+50),(590,406));board_cell(board,overlay,(1025,y+50),(570,406));draw.text((430,y+463),f'Source-only {m["false_negative"]} cells; actual-only {m["false_positive"]}. Actual centers == common cells.',font=font(15),fill=(60,60,60))
 draw.text((25,2180),'Green: both silhouettes   Magenta: source only   Orange: actual only   Gray hatch: missing/conflicting constraint',font=font(19),fill=(35,35,35));draw.text((25,2210),'Original capture files remain unchanged. Crops are literal source pixels. Overlay is diagnostic, not a corrected render.',font=font(17),fill=(35,35,35));save_png(O/'comparison_board.png',board)
 assert all(sha(ROOT/r['path'])==r['sha256'] for r in initial_inputs)
 report={'schema':'riverstone.image_reconstruction.actual_projection.v1','diagnostic_only':True,'production_gate_open':False,'image_registration_pass':False,'source_render_unchanged':True,'source_image_unchanged':True,'original_captures_unchanged':True,'all_actual_cell_center_silhouettes_match_common_occupancy':all(r['cell_center_geometry_matches_common_occupancy'] for r in rows),'input_refs':initial_inputs,'comparison_board':ref(O/'comparison_board.png'),'views':rows,'coordinate_policy':'Fit camera affine only to provided world_to_pixel_anchors. No shape-derived alignment, no source image warp; stored normalized world masks used without extra mirroring.','automatic_measurements':['fixed color/background segmentation','cell center and screen pixel overlap','camera-anchor affine','12color and actual RGB error'],'manual_annotations':['source panel32px/m domains','source gallery/rail semantic ROIs in prepare.json','HUD rectangle from capture script','source side9.5m conflict exclusion'],'depth_priors_reference':ref(D/'side_depth_annotations.json'),'limits':['Raster edge coverage may differ within a screenshot pixel even when all exact cell centers agree.','The four input images remain inconsistent; silhouette agreement cannot validate hidden volume or gallery depth.','Source RGB is shaded and contains vegetation; unshaded actual captures expose the baked palette.','Oblique frame is lit and is not used for RGB or silhouette metrics.','TOP/BOTTOM and upperSIDE roof are not secretly used as geometric constraints.'],'wall_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};save_json(O/'report.json',report);print(json.dumps({'report':ref(O/'report.json'),'board':ref(O/'comparison_board.png'),'views':[{k:r[k] for k in ['view','actual_screenshot_vs_source_mask_cells','actual_screenshot_vs_common_projected_pixels','rgb_errors']} for r in rows],'wall_seconds':report['wall_seconds'],'peak_rss_kib':report['peak_rss_kib']}))
if __name__=='__main__':run()
