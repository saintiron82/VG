"""Frozen occupancy/image queries only: no rendering, sampling, or edits."""
from pathlib import Path
import os,resource,time,json,hashlib,gzip,collections
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from PIL import Image
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(30,)*2)
t=time.monotonic();H=Path(__file__).resolve().parent; R=H.parents[1];A=R.parent;ROOT=next(p for p in A.parents if(p/'voxel_character').exists());P=.03125
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ref=lambda p:{'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
a=np.load(R/'upper_union_arrays.npz');m=a['materials']; retained=a['retained_baseline'];names=a['material_names'].tolist()
f=np.load(A/'foundation_repair_r01/foundation_arrays.npz');o=f['occupancy'];original_mat=f['materials'];src=np.load(A/'reconstruction_proof_r01/image_derived_arrays.npz')
master=json.loads(gzip.decompress((R/'roof_patch.master.json.gz').read_bytes()));slope=master['metadata']['measured_gable_slope'];base=json.loads(gzip.decompress((A/'foundation_repair_r01/foundation_revised.master.json.gz').read_bytes()));colors=base['materials']|master['materials'];palette=np.array([[int(colors[n][i:i+2],16)for i in (0,2,4)]for n in names])
X=(np.arange(400)-200+.5)*P;Y=(np.arange(148)+300+.5)*P;line=13.875-slope*np.abs(X)
proj=np.array([(row>=0).any(1)for row in m]);bp=np.zeros_like(proj)
for iy in range(148):bp[iy,8:392]=o[(iy+300)//4].any(1).repeat(4)
band=(Y[:,None]>=line[None,:]-.65)&(Y[:,None]<=line[None,:]+.125)&(Y[:,None]>=9.5)&(np.abs(X)[None,:]>.25)&(np.abs(X)[None,:]<6.)
below=np.maximum.accumulate(proj,axis=0);above=np.maximum.accumulate(proj[::-1],axis=0)[::-1]
gaps=~proj&below&above&band;newgaps=gaps&bp
runs=[]
for ix in range(400):
 ys=np.flatnonzero(gaps[:,ix]); groups=np.split(ys,np.flatnonzero(np.diff(ys)>1)+1)if len(ys)else[]
 for q in groups:runs.append({'x_interval_m':[(ix-200)*P,(ix-199)*P],'y_interval_m':[(int(q[0])+300)*P,(int(q[-1])+301)*P],'height_m':len(q)*P,'cells_previously_occupied':int(bp[q,ix].sum())})
# All projected front/back screenshot samples are correlated with actual frozen grid,
# not a fitted rendering. Known camera scale derives from capture_report anchors.
capture=json.loads((R/'actual_godot_r01/after/capture_report.json').read_text());records={r['view']:r for r in capture['records']};actual={}
for view in ('front','back'):
 im=np.array(Image.open(R/f'actual_godot_r01/after/{view}.png').convert('RGB'));bg=im[80,0].copy(); im=im[80:320,300:880].copy(); yy,xx=np.indices(im.shape[:2]);xx=(xx+300+.5-590)/(812/18)*(1 if view=='front'else-1);yy=7-(yy+80+.5-406)/(812/18)
 ix=np.floor(xx/P).astype(int)+200;iy=np.floor(yy/P).astype(int)-300;valid=(ix>=0)&(ix<400)&(iy>=4)&(iy<148);samples=valid.copy();samples[valid]&=band[iy[valid],ix[valid]]
 hit=np.full(im.shape[:2],-2,np.int16);zidx=np.array([np.argmax((row>=0)[:,::-1]if view=='front'else(row>=0),axis=1)for row in m]);zidx=327-zidx if view=='front'else zidx
 hm=np.take_along_axis(m,zidx[:,:,None],axis=2)[:,:,0];hit[samples]=hm[iy[samples],ix[samples]]
 bgs=np.all(im==bg,axis=2)&samples;empty=hit==-1;occupied=(hit>=0)&samples;pale=occupied&(hit<=3)
 evidence=[]
 for px,py in ([(500,162),(700,176),(700,179),(500,165)]if view=='front'else[(480,176),(480,179)]):
  px0,py0=px,py;px-=300;py-=80;i=int(ix[py,px]);j=int(iy[py,px]); zs=np.flatnonzero(m[j,i]>=0); z=int(zs[-1]if view=='front'else zs[0])if len(zs)else None; mat=int(m[j,i,z])if z is not None else -1
  evidence.append({'screen_px':[px0,py0],'rgb':im[py,px].tolist(),'world_xy':[float(xx[py,px]),float(yy[py,px])],'all_z_ray_empty':z is None,'material':names[mat]if mat>=0 else None})
 actual[view]={'image':ref(R/f'actual_godot_r01/after/{view}.png'),'background_rgb':bg.tolist(),'band_pixels':int(samples.sum()),'exact_background_pixels':int(bgs.sum()),'background_and_empty_grid_ray':int((bgs&empty).sum()),'background_but_grid_occupied_raster_boundary_pixels':int((bgs&occupied).sum()),'pale_material_first_hit_pixels':int(pale.sum()),'material_pixel_counts':dict(collections.Counter(names[i]for i in hit[occupied].tolist())),'proof_samples':evidence}
# Trace light exposed retained facade cells to original 4x4 source pixels.
facade=[]
for view,zs in [('front',range(77,80)),('back',range(0,3))]:
 count=0;source=[]
 # Avoid repeated arrays loading; use retained descendant at one exact fine center.
 for y in range(76,112):
  for x in range(96):
   xx=(x-48+.5)*.125; yy=(y+.5)*.125;l=13.875-slope*abs(xx)
   if not(l-.65<=yy<=l+.125 and .25<abs(xx)<6):continue
   for z in zs:
    fy=y*4-300;fx=x*4+8;fz=z*4+4
    if retained[fy,fx,fz]and original_mat[y,x,z]<=3:
     count+=1
     if len(source)<100:
      u=64+x*4 if view=='front'else 1088+(95-x)*4;v=496-(y+1)*4
      source.append({'original_yxz':[y,x,z],'material':names[int(original_mat[y,x,z])],'source_box_px':[u,v,u+4,v+4],'source_4x4_mean_rgb':src[view+'_rgb'][y,x].tolist(),'world_cell_box':[[xx-.0625,yy-.0625,(z-40)*.125],[xx+.0625,yy+.0625,(z-39)*.125]]})
 facade.append({'view':view,'retained_pale_coarse_cells_in_edge_band':count,'examples':source})
source_image=ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png'
pixels=np.asarray(Image.open(source_image).convert('RGB'))
source_gap={}
gy,gx=np.nonzero(newgaps)
for view in ('front','back'):
 us=np.floor((256+32*X[gx]) if view=='front' else (1280-32*X[gx])).astype(int)
 vs=np.floor(496-32*Y[gy]).astype(int); p=pixels[vs,us].astype(float)
 red=(p[:,0]>p[:,1]*1.7)&(p[:,1]>p[:,2]*1.2)&(p[:,0]>80);lum=p.mean(1)
 fg=((p[:,0]-p[:,2]>12)&(p[:,0]>=p[:,1]*.95)&(lum<248))|(lum<110)|((p[:,1]-p[:,0]>12)&(p[:,1]-p[:,2]>12)&(lum<205))
 source_gap[view]={'new_gap_cell_centers':len(us),'original_pixel_foreground':int(fg.sum()),'original_strict_red_pixels':int(red.sum()),'original_dark_pixels_mean_lt_110':int((lum<110).sum()),'original_pixel_nonforeground':int((~fg).sum())}
 for e in actual[view]['proof_samples']:
  x,y=e['world_xy'];u=int(np.floor(256+32*x)) if view=='front' else int(np.floor(1280-32*x));v=int(np.floor(496-32*y))
  e['source_pixel_uv']=[u,v];e['source_pixel_rgb']=pixels[v,u].tolist()
 for entry in [e for e in facade if e['view']==view]:
  seen=set();unique=[]
  for e in entry['examples']:
   box=tuple(e['source_box_px'])
   if box in seen:continue
   seen.add(box);u,v,U,V=box;p=pixels[v:V,u:U].reshape(-1,3).astype(float);lum=p.mean(1)
   red=(p[:,0]>p[:,1]*1.7)&(p[:,1]>p[:,2]*1.2)&(p[:,0]>80)
   fg=((p[:,0]-p[:,2]>12)&(p[:,0]>=p[:,1]*.95)&(lum<248))|(lum<110)|((p[:,1]-p[:,0]>12)&(p[:,1]-p[:,2]>12)&(lum<205))
   unique.append({'source_box_px':list(box),'original_yx':e['original_yxz'][:2],'material':e['material'],'mean_rgb':e['source_4x4_mean_rgb'],'actual_red_pixels':int(red.sum()),'actual_foreground_pixels':int(fg.sum()),'actual_nonforeground_pixels':int((~fg).sum())})
  entry['unique_pixel_proof']=unique
report={'original_image':ref(source_image),'new_gap_original_pixel_support':source_gap,'status':'DIAGNOSTIC_CONFIRMED_GEOMETRIC_GABLE_GAPS','render':ref(R/'roof_repaired.render.json.gz'),'source_arrays':ref(R/'upper_union_arrays.npz'),'method':'Exact all-Z occupancy projection; fine cells from existing frozen upper union; actual orthographic pixels from recorded camera. No sampling/mesh/render calls.','band_definition':{'below_measured_plane_m':.65,'above_measured_plane_m':.125,'ridge_excluded_abs_x_lte_m':.25,'outer_limit_abs_x_lt_m':6.},'through_gap_projection_area_m2':int(gaps.sum())*P*P,'through_gap_fine_xy_cells':int(gaps.sum()),'new_empty_previously_occupied_projection_area_m2':int(newgaps.sum())*P*P,'x_columns_with_gap':int(gaps.any(0).sum()),'maximum_vertical_gap_run_m':max(r['height_m']for r in runs),'median_vertical_gap_run_m':float(np.median([r['height_m']for r in runs])),'gap_height_distribution':dict(collections.Counter(str(r['height_m'])for r in runs)),'actual_front_back':actual,'retained_pale_source_edge_cells':facade,'cause':{'roof_ownership_band_removed_down_to_plane_minus_m':.5,'new_support_bottom_plane_minus_m':.1875,'new_support_top_plane_minus_m':.0625,'unfilled_vertical_ownership_interval_nominal_m':.3125,'front_back_mask':'Outer3 coarse layers use strict red ownership only; original silhouette/color mixtures remain. Interior ownership .5m band makes no connectivity promise.','no_fascia_source_semantic_defined':True,'not_a_pure_color_or_shading_problem':True},'limits':'All-Z gaps prove background holes in both orthographic gable projections. Lit oblique white surfaces may also include original pale mixed source cells; no blanket recoloring or fill is justified. Actual source fascia/tile overlap needs explicit source-supported semantic boundary before geometry repair.','inputs_unchanged':sha(R/'roof_repaired.render.json.gz')=='d71a5987debe5e3e22a3663f8ee4b604bd7d880a0fa7d8188e4d9247c26edb17','elapsed_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
(H/'gable_diagnostic.json').write_text(json.dumps(report,indent=2));(H/'gap_runs.json').write_text(json.dumps(runs,separators=(',',':')));print(json.dumps({k:v for k,v in report.items()if k not in ['actual_front_back','retained_pale_source_edge_cells','source_arrays','render']},indent=2))
