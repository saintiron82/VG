"""Frozen first-hit/source-pixel audit; no geometry or shader changes."""
from pathlib import Path
import os,resource,json,hashlib,gzip,time,gc,collections
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from PIL import Image
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(30,)*2)
t=time.monotonic();D=Path(__file__).resolve().parent;H=D.parent;A=H.parent;ROOT=next(p for p in A.parents if(p/'voxel_character/common/core.py').exists());P=.03125
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();ref=lambda p:{'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
imagepath=ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png';image=np.asarray(Image.open(imagepath).convert('RGB'))
a=np.load(H/'upper_union_arrays.npz');arr=a['materials'];names=a['material_names'].tolist();ty=np.full((400,328),-1,np.int16);tm=np.full((400,328),-1,np.int16)
for iy,row in enumerate(arr):
 mask=row>=0;ty[mask]=iy+300;tm[mask]=row[mask]
del arr;gc.collect();labels=np.load(H/'delta_ownership_arrays.npz')['top_first_hit_delta_class'];measure=json.loads((A/'roof_repair_r01/tile_measurement_r01/tile_regions.json').read_text());coef=measure['conditional_mapping']['coefficients']
before=np.load(A/'roof_repair_r02/upper_union_arrays.npz')['materials'];oldtm=np.full_like(tm,-1)
for row in before:
 mask=row>=0;oldtm[mask]=row[mask]
del before;gc.collect()

def fg(p):
 r,g,b=map(float,p);l=(r+g+b)/3;return ((r-b>12)and(r>=g*.95)and(l<248))or(l<110)or((g-r>12)and(g-b>12)and(l<205))
def red(p):
 r,g,b=map(float,p);return r>g*1.7 and g>b*1.2 and r>80
records=[];sides={}
for view,iz0,iz1 in [('back',4,16),('front',312,324)]:
 sl=tm[:,iz0:iz1];pale=(sl>=0)&(sl<=4);counter=collections.Counter();unique={}
 for ix,jz in np.argwhere(pale):
  iz=int(jz+iz0);x=int(ix)-200;y=int(ty[ix,iz]);z=iz-164;X=(x+.5)*P;Z=(z+.5)*P;kind=int(labels[ix,iz]);mat=int(tm[ix,iz]);u=256+x if view=='front' else 1280-x-1;v=496-y-1
  cx=x//4+48;cy=y//4;bu=64+cx*4 if view=='front' else 1088+(95-cx)*4;bv=496-(cy+1)*4
  raw=image[v,u].tolist();rawmean=image[bv:bv+4,bu:bu+4].mean(axis=(0,1)).tolist()
  tu=int(np.floor((X-coef['tx'])/coef['sx']));tv=int(np.floor((Z-coef['tz'])/coef['sz']));trgb=image[tv,tu].tolist()
  key=(view,x,y,mat,kind)
  if key not in unique:unique[key]={'view':view,'fine_xy_cell':[x,y],'material':names[mat],'origin':'r03_foreground_resample' if kind==2 else 'preserved_r02_source_facade','source_pixel_uv':[u,v],'source_pixel_rgb':raw,'source_pixel_passes_original_foreground_rule':fg(raw),'source_pixel_strict_red':red(raw),'source_original4x4_box_px':[bu,bv,bu+4,bv+4],'source_original4x4_mean_rgb':rawmean,'depth_cells':[],'conditional_top_pixel_examples':[]}
  item=unique[key];item['depth_cells'].append(z)
  if len(item['conditional_top_pixel_examples'])<3:item['conditional_top_pixel_examples'].append({'uv':[tu,tv],'rgb':trgb,'strict_red':red(trgb)})
  counter['top_pale_cells']+=1;counter['top_pixels_strict_red']+=int(red(trgb));counter['front_back_source_fine_pixel_strict_red']+=int(red(raw));counter['front_back_source_fine_pixel_foreground']+=int(fg(raw));counter['front_back_source_fine_pixel_mean_gt_200']+=int(np.mean(raw)>200);counter['from_resampled_edge' if kind==2 else 'from_preserved_source']+=1
  assert kind in (0,2),'Restored interior or newshadow region cannot create these bright top hits'
 records.extend(unique.values());oldsl=oldtm[:,iz0:iz1];sides[view]={'source_depth_interval_m':[-5,-4.625]if view=='back'else[4.625,5],'material_first_hit_counts':{names[k]if k>=0 else'empty':int(v)for k,v in zip(*np.unique(sl,return_counts=True))},'pale_r02_before_cells':int(((oldsl>=0)&(oldsl<=4)).sum()),'pale_r03_after_cells':int(pale.sum()),'pale_horizontal_area_template_m2':int(pale.sum())*P*P,'counts':dict(counter),'distinct_source_fine_pixels':len(unique)}
# Verify there are no pale source first hits elsewhere on the upper roof.
edge=np.zeros(tm.shape,bool);edge[:,4:16]=True;edge[:,312:324]=True;pale=(tm>=0)&(tm<=4)
report={'schema':'riverstone.roof_edge_surface_first_hit.v1','status':'CONFIRMED_FACADE_COLOR_EXTRUSION_EXPOSED_ON_ROOF_TOP','render':ref(H/'roof_repaired.render.json.gz'),'union':ref(H/'upper_union_arrays.npz'),'original_image':ref(imagepath),'actual_top_capture':ref(H/'actual_godot_r01/after/top.png'),'conditional_mapping_ref':ref(A/'roof_repair_r01/tile_measurement_r01/tile_regions.json'),'pale_material_definition':'Existing source pixel_00 through pixel_04 inclusive; exact RGB palette values preserved, no appearance threshold applied to rendered pixels.','side_results':sides,'total_pale_top_first_hits':int(pale.sum()),'total_pale_horizontal_area_template_m2':int(pale.sum())*P*P,'pale_top_hits_outside_original_facade_depth_bands':int((pale&~edge).sum()),'source_classification':'Front/back color evidence was projected through original .375m facade thickness; same material is attached to every voxel face including roof-facing +Y. Original foreground predicate retains warm anti-aliased image-edge pixels, so finer same-predicate sampling cannot by itself establish terracotta roof surface ownership.','what_r03_fixed':['Original below-backing gable junction occupancy restored inside exact original source footprint.','3312 fine descendants of rejected foreground pixels removed; surviving460 individual source foreground pixels receive actual-pixel nearest palette rather than4x4-average color.','15 locally observed TOP regions restored outside the conservative chimney holdout.'],'what_r03_did_not_fix':['Source facade color is still used on its exposed horizontal/upward faces through .375m depth.','Warm background-antialias pixels can satisfy the original loose foreground predicate.','Non-pale source facade colors also remain roof-visible; blanket deletion/recoloring of white would not solve semantic ownership.'],'strict_next_boundary':'Preserve measured front/back facade silhouettes and wooden fascia. Adjudicate only roof-facing exposed source faces/cells inside conditionally registered TOP roof rectangle and declared gable roof band; reference actual TOP pixel color/boundaries. Treat vertical facade and horizontal roof ownership separately. Any changed surface requires source-plane/feature proof and preserved exterior/neighbor tests; no arbitrary white recolor or full-depth fill.','global_top_registration_accepted':False,'physical_metric_scale_claimed':False,'geometry_sampling_calls':0,'source_files_changed':False,'elapsed_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
(D/'first_hit_report.json').write_text(json.dumps(report,indent=2));(D/'source_pixel_records.json').write_text(json.dumps(records,indent=2));print(json.dumps(report,indent=2))
