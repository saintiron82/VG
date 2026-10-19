"""DIAGNOSTIC pixel→mask→visual hull/depth→common source, never production.
No hand-authored building boxes: every run is compressed from image-derived
occupancy. Planned shell/floor/gallery depths remain explicit semantic priors.
"""
import argparse,copy,gzip,hashlib,json,math,os,resource,sys,time
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import binary_fill_holes,binary_erosion,label
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'voxel_character/common/core.py').exists());sys.path.insert(0,str(ROOT))
from voxel_character.common import core,prepared_sampling_v3 as sampler,render_data
HERE=Path(__file__).resolve().parent;P=ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01';PITCH=.125
ROIS={'front':[64,48,448,496],'back':[1088,48,1472,496],'right':[608,48,928,496],'left':[96,560,416,1008]}
# Human semantic image annotations only; these are not authored source cuboids.
GALLERIES=[{'id':'front_gallery_upper','roi_px':[80,210,434,298],'rail_y_px':[250,298]}, {'id':'front_gallery_lower','roi_px':[80,310,434,398],'rail_y_px':[350,398]}, {'id':'attic_loggia','roi_px':[149,145,360,204],'rail_y_px':[177,204]}]
PRIORS={'wall_shell_m':.375,'floor_thickness_m':.25,'floor_top_planes_m':[.5,3.5,6.5,9.5],'gallery_recess_m':1.125,'gallery_prior_reason':'Approved planned1.1m depth rounded explicitly to9 diagnostic cells; side-visible depth is inconsistent and is reported separately.','glass_recess_m':.25,'surface_layer_m':.125,'roof_depth_m':10,'roof_depth_reason':'TOP/BOTTOM rejected and SIDE upper roof height conflicts. Planned10m depth prior is not a measured roof depth.','all_inferred':True}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def ref(p):return {'path':str(Path(p).relative_to(ROOT)),'sha256':sha(p)}
def write(name,obj):
 data=json.dumps(obj,separators=(',',':'),allow_nan=False).encode();path=HERE/name;raw=gzip.compress(data,mtime=0) if str(name).endswith('.gz') else data
 if sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())+len(raw)>20_000_000:raise RuntimeError('20MB diagnostic cap exceeded')
 if path.exists():raise RuntimeError('Immutable output already exists: '+str(path))
 path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);return ref(path)

def extract(image):
 maps={};all_pixels=[]
 for name,(x0,y0,x1,y1) in ROIS.items():
  crop=image[y0:y1,x0:x1].astype(float);h,w=crop.shape[:2];r,g,b=crop[:,:,0],crop[:,:,1],crop[:,:,2];lum=crop.mean(axis=2)
  # Warm architecture/vegetation against the cool white graph paper. Dark
  # structure remains foreground;4x4 coverage rejects isolated grid lines.
  fg=((r-b>12)&(r>=g*.95)&(lum<248)) | (lum<110) | ((g-r>12)&(g-b>12)&(lum<205))
  coverage=fg.reshape(h//4,4,w//4,4).mean(axis=(1,3));raw=coverage>=.4
  cc,n=label(raw);sizes=np.bincount(cc.ravel());sizes[0]=0;main=cc==sizes.argmax();outer=binary_fill_holes(main)
  rgb=crop.reshape(h//4,4,w//4,4,3).mean(axis=(1,3));raw=raw[::-1];outer=outer[::-1];rgb=rgb[::-1];coverage=coverage[::-1]
  if name in ('back','right'):raw=raw[:,::-1];outer=outer[:,::-1];rgb=rgb[:,::-1];coverage=coverage[:,::-1]
  maps[name]={'raw':raw.copy(),'silhouette':outer.copy(),'rgb':rgb.copy(),'coverage':coverage.copy()};all_pixels.append(rgb[raw].astype(np.uint8))
 # Median-cut12-tone palette comes solely from sampled input foreground RGB.
 pixels=np.concatenate(all_pixels);strip=Image.fromarray(pixels[None,:,:],'RGB').quantize(colors=12,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE);pal=np.array(strip.getpalette()[:36],dtype=np.uint8).reshape(12,3)
 for m in maps.values():m['material']=np.argmin(((m['rgb'][:,:,None,:]-pal[None,None,:,:])**2).sum(axis=3),axis=2).astype(np.int16)
 return maps,pal

def pixels_roi_grid(box):
 x0,y0,x1,y1=box;xs=np.arange(96)*4+66;ys=494-np.arange(112)*4;return (ys[:,None]>=y0)&(ys[:,None]<y1)&(xs[None,:]>=x0)&(xs[None,:]<x1)

def reconstruct(maps,pal):
 f,b,r,l=[maps[n]['silhouette'] for n in ('front','back','right','left')];hull=(f&b)[:,:,None]*np.ones((1,1,80),dtype=bool);body=np.arange(112)<76;hull[body]&=(r&l)[body,None,:]
 interior=binary_erosion(hull,iterations=3,border_value=0);occ=hull&~interior
 for y in (4,28,52,76):occ[max(0,y-2):y]|=hull[max(0,y-2):y]
 y,x,z=np.indices(hull.shape);dist=np.stack([79-z,z,95-x,x]);nearest=np.argmin(dist,axis=0)
 mats=np.where(nearest==0,maps['front']['material'][:,:,None],maps['back']['material'][:,:,None]);mats=np.where(nearest==2,maps['right']['material'][:,None,:],mats);mats=np.where(nearest==3,maps['left']['material'][:,None,:],mats).astype(np.int16)
 # Missing side roof geometry is never used. Its color projection is also
 # missing above the accepted body limit: use actual front red-roof samples.
 src=maps['front']['rgb'];red=(src[:,:,0]>src[:,:,1]*1.42)&(src[:,:,1]>src[:,:,2]*1.35);sample=src[(np.arange(112)[:,None]>=76)&red]
 roof_rgb=np.median(sample,axis=0);roof_mat=int(np.argmin(((pal-roof_rgb)**2).sum(axis=1)));mats[y>=76]=roof_mat
 # FRONT/BACK gable facade colors are measured even when the side roof is not.
 mats[:,:,77:]=maps['front']['material'][:,:,None];mats[:,:,:3]=maps['back']['material'][:,:,None]
 front=maps['front'];rgb=front['rgb'];wood=(rgb[:,:,0]>rgb[:,:,2]*1.3)&(rgb[:,:,1]>rgb[:,:,2]*1.08)&(rgb.mean(axis=2)>55);dark=rgb.mean(axis=2)<60
 depths=[]
 for gallery in GALLERIES:
  roi=pixels_roi_grid(gallery['roi_px']);ys=494-np.arange(112)*4;rail=(ys[:,None]>=gallery['rail_y_px'][0])&(ys[:,None]<gallery['rail_y_px'][1]);xs=np.arange(96)*4+66
  posts=((xs>=78)&(xs<=96))|((xs>=421)&(xs<=438));preserve=roi&wood&~dark&(rail|posts[None,:]);coords=np.argwhere(roi&f)
  carved=added=0
  for yy,xx in coords:
   zs=np.flatnonzero(hull[yy,xx]);
   if not len(zs):continue
   front_z=int(zs[-1]);back_z=max(int(zs[0]),front_z-9);carved+=int(occ[yy,xx,back_z+1:front_z+1].sum());occ[yy,xx,back_z+1:front_z+1]=False
   occ[yy,xx,max(0,back_z-2):back_z+1]=hull[yy,xx,max(0,back_z-2):back_z+1];mats[yy,xx,max(0,back_z-2):back_z+1]=front['material'][yy,xx]
   if preserve[yy,xx]:occ[yy,xx,front_z]=True;mats[yy,xx,front_z]=front['material'][yy,xx];added+=1
  depths.append({'id':gallery['id'],'semantic_image_roi_px':gallery['roi_px'],'carved_cells_before_outer_skin_restore':carved,'measured_wood_skin_cells':added,'depth_m':1.125,'depth_provenance':'planned_prior_not_measured','dark_rail_pixels':'treated as openings, explicitly ambiguous shadow-versus-hole assumption'})
 # Only blue-green pixels in the facade become recessed closed pane voxels.
 glass=(rgb[:,:,2]>rgb[:,:,0]*1.05)&(rgb[:,:,1]>rgb[:,:,0]*1.1)&(rgb.mean(axis=2)<150)&f
 glass_count=0
 for yy,xx in np.argwhere(glass):
  zs=np.flatnonzero(occ[yy,xx]);
  if not len(zs):continue
  top=int(zs[-1]);target=max(0,top-2);occ[yy,xx,target+1:top+1]=False;occ[yy,xx,target]=True;mats[yy,xx,target]=front['material'][yy,xx];glass_count+=1
 mats[~occ]=-1
 return hull,occ,mats,{'gallery_depth_records':depths,'glass_pixel_columns_recessed':glass_count,'roof_palette_rgb_sample_median':roof_rgb.tolist(),'roof_palette_slot':roof_mat}

def master_from_grid(occ,mats,pal):
 ops=[]
 # One box for each exact image-derived equal-material z run. These are
 # lossless run compression, not a hand-designed building substitute.
 for yy,xx in np.argwhere(occ.any(axis=2)):
  zz=0
  while zz<80:
   if not occ[yy,xx,zz]:zz+=1;continue
   start=zz;mat=int(mats[yy,xx,zz]);zz+=1
   while zz<80 and occ[yy,xx,zz] and int(mats[yy,xx,zz])==mat:zz+=1
   ops.append({'id':f'image_run_y{yy}_x{xx}_z{start}','part':'image_reconstruction','action':'paint','material':f'pixel_{mat:02d}','shape':{'kind':'box','min':[float((xx-48)*PITCH),float(yy*PITCH),float((start-40)*PITCH)],'max':[float((xx-47)*PITCH),float((yy+1)*PITCH),float((zz-40)*PITCH)]}})
 return {'schema':core.SCHEMA,'id':'architecture_A_image_reconstruction_diagnostic_r01','revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':{f'pixel_{i:02d}':''.join(f'{int(v):02x}' for v in c) for i,c in enumerate(pal)},'components':[{'id':'image_visual_hull_depth','parts':[{'id':'image_reconstruction','pivot':[0,0,0]}],'operations':ops}],'instances':[{'id':'image_visual_hull_depth','component':'image_visual_hull_depth'}],'assembly_cuts':[],'constraints':[{'id':'diagnostic_nonempty','kind':'nonempty'}],'metadata':{'diagnostic_only':True,'production_gate_open':False,'image_derived_runs':True,'pitch_m':PITCH,'semantic_depth_priors':PRIORS,'no_physics_or_navigation_claim':True}}

def projection_error(occ,maps):
 projections={'front':occ.any(axis=2),'back':occ.any(axis=2),'right':occ.any(axis=1),'left':occ.any(axis=1)};out={}
 for name,pred in projections.items():
  actual=maps[name]['silhouette'];valid=np.ones_like(actual,dtype=bool)
  if name in ('right','left'):valid[76:]=False
  inter=int((pred&actual&valid).sum());union=int(((pred|actual)&valid).sum());fp=int((pred&~actual&valid).sum());fn=int((~pred&actual&valid).sum())
  out[name]={'silhouette_iou':inter/union if union else 1,'false_positive_cells':fp,'false_negative_cells':fn,'symmetric_difference_cells':fp+fn,'pixel_equivalent_difference_area':(fp+fn)*16,'compared_grid_cells':int(valid.sum()),'upper_roof_excluded':name in ('right','left')}
 return out

def prepare():
 start=time.monotonic();image=np.asarray(Image.open(P/'generated_candidate_r03.png').convert('RGB'));maps,pal=extract(image);hull,occ,mats,depth=reconstruct(maps,pal);master=master_from_grid(occ,mats,pal);core.validate_master(master,PITCH)
 maps2,pal2=extract(image);h2,o2,m2,d2=reconstruct(maps2,pal2);det=all(np.array_equal(a,b) for a,b in [(pal,pal2),(hull,h2),(occ,o2),(mats,m2)])
 # Change an actual supported source mask column; recompute the entire rule.
 changed=copy.deepcopy(maps);yy,xx=np.argwhere(maps['front']['silhouette']&maps['back']['silhouette'])[len(np.argwhere(maps['front']['silhouette']&maps['back']['silhouette']))//2];changed['front']['silhouette'][yy,xx]=False;_,changed_occ,_,_=reconstruct(changed,pal)
 color=copy.deepcopy(maps);yy2,xx2=np.argwhere(occ.any(axis=2))[0];color['front']['material'][yy2,xx2]=(int(color['front']['material'][yy2,xx2])+1)%len(pal);_,color_occ,color_mats,_=reconstruct(color,pal)
 # Pick a front-visible source column if the initial column belongs only to a side.
 if np.array_equal(mats,color_mats):
  for yy2,xx2 in np.argwhere(occ[:,:,77:].any(axis=2)):
   color=copy.deepcopy(maps);color['front']['material'][yy2,xx2]=(int(color['front']['material'][yy2,xx2])+1)%len(pal);_,color_occ,color_mats,_=reconstruct(color,pal)
   if not np.array_equal(mats,color_mats):break
 tests={'same_input_same_palette_and_cells':det,'source_mask_change_changes_cells':not np.array_equal(occ,changed_occ),'source_color_label_change_keeps_occupancy':np.array_equal(occ,color_occ),'source_color_label_change_changes_material':not np.array_equal(mats,color_mats)};assert all(tests.values()),tests
 arrays={'occupancy':occ,'materials':mats,'hull':hull,'palette':pal}
 for n,m in maps.items():
  for k,v in m.items():arrays[n+'_'+k]=v
 target=HERE/'image_derived_arrays.npz';assert not target.exists();np.savez_compressed(target,**arrays)
 masterref=write('image_derived.master.json.gz',master)
 report={'schema':'riverstone.image_voxel_reconstruction.prepare.v1','diagnostic_only':True,'production_gate_open':False,'source_image':ref(P/'generated_candidate_r03.png'),'registration':ref(P/'registration_r03.json'),'template':ref(P/'template.json'),'authoring_script':ref(__file__),'accepted_coordinate_policy':'FRONT/BACK unchanged32px/m template; SIDE body only; no image warping. Failed registration remains disclosed.','excluded_constraints':{'side_y_ge_9_5m':'Conflicting roof ridge','top':'Unregistered/deformed','bottom':'Unregistered/deformed'},'semantic_image_rois':GALLERIES,'depth_priors':PRIORS,'depth_results':depth,'mask_policy':'Automatic color separation +4x4 majority +largest connected component +2D hole fill for outer silhouettes. Inner openings are separate color/depth annotations. Vegetation/image shadow can remain ambiguous.','input_grids':{n:{'shape':list(v['silhouette'].shape),'raw_cells':int(v['raw'].sum()),'filled_silhouette_cells':int(v['silhouette'].sum()),'sha256':digest(v['silhouette'])} for n,v in maps.items()},'hull_cells':int(hull.sum()),'authored_cells':int(occ.sum()),'source_operations':len(master['components'][0]['operations']),'palette_rgb':pal.tolist(),'palette_extraction':'12 deterministic median-cut colors from actual four-view foreground4x4 averaged RGB; no random cell noise. Roof median is sampled from actual front red-roof pixels.','source_master':masterref,'arrays':ref(target),'grid_origin':[0,0,0],'pitch_m':PITCH,'occupancy_sha256':digest(occ),'material_grid_sha256':digest(mats),'tests':tests,'mask_mutation':{'front_yx':[int(yy),int(xx)],'changed_output_cells':int(np.count_nonzero(occ!=changed_occ))},'color_mutation':{'front_yx':[int(yy2),int(xx2)],'changed_material_cells':int(np.count_nonzero(mats!=color_mats))},'four_view_reprojection':projection_error(occ,maps),'seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'sampled':False}
 write('prepare.json',report);print(json.dumps({k:report[k] for k in ['hull_cells','authored_cells','source_operations','tests','seconds','peak_rss_kib','four_view_reprojection']}),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');q=p.parse_args()
 if q.prepare:prepare()
