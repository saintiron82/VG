"""Read-only candidate mask/counts; does not author or alter any voxel."""
from pathlib import Path
import os,resource,json,hashlib,gzip,time,collections
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from PIL import Image
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(30,)*2)
t=time.monotonic();D=Path(__file__).resolve().parent;H=D.parent;A=H.parent;ROOT=next(p for p in A.parents if(p/'voxel_character/common/core.py').exists());P=.03125
imagepath=ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png';im=np.array(Image.open(imagepath).convert('RGB'));a=np.load(H/'upper_union_arrays.npz');m=a['materials'];names=a['material_names'].tolist();ty=np.full((400,328),-1,np.int16);tm=np.full_like(ty,-1);front=np.full((148,400),-1,np.int16);back=front.copy()
for iy,row in enumerate(m):
 mask=row>=0;hit=mask.any(1);front[iy,hit]=327-np.argmax(mask[hit,::-1],1);back[iy,hit]=np.argmax(mask[hit],1);ty[mask]=iy+300;tm[mask]=row[mask]
old=json.loads(gzip.decompress((A/'roof_repair_r02/roof_patch.master.json.gz').read_bytes()));s=old['metadata']['measured_gable_slope'];coef=json.loads((A/'roof_repair_r01/tile_measurement_r01/tile_regions.json').read_text())['conditional_mapping']['coefficients'];pal=np.array([[int(old['materials'][f'top_tile_{i:02d}'][j:j+2],16)for j in (0,2,4)]for i in range(6)]);records=[];rejected=collections.Counter();pale_reject=collections.Counter();oldpale=0
for ix in range(400):
 for iz in list(range(4,16))+list(range(312,324)):
  material=int(tm[ix,iz]);y=int(ty[ix,iz]);x=ix-200;z=iz-164
  if not(0<=material<15):continue
  X=(x+.5)*P;Y=(y+.5)*P;line=13.875-s*abs(X);is_pale=material<=4;oldpale+=int(is_pale)
  def reject(reason):
   rejected[reason]+=1
   if is_pale:pale_reject[reason]+=1
  if not(.25<abs(X)<6 and line-.65<=Y<=line+.1875):reject('outside_roof_band_or_ridge');continue
  if iz in (int(front[y-300,ix]),int(back[y-300,ix])):reject('F_or_B_first_hit_color_conflict');continue
  u0=(x*P-coef['tx'])/coef['sx'];u1=((x+1)*P-coef['tx'])/coef['sx'];v0=(z*P-coef['tz'])/coef['sz'];v1=((z+1)*P-coef['tz'])/coef['sz']
  if not(613<=u0<u1<=922 and 787<=v0<v1<=977):reject('outside_conditional_roof_rectangle');continue
  if u0<908 and u1>868 and v0<849 and v1>795:reject('chimney_holdout_overlap');continue
  px=im[int(np.floor(v0)):int(np.ceil(v1)),int(np.floor(u0)):int(np.ceil(u1))].astype(float);r,g,b=[px[:,:,i]for i in range(3)];red=(r>g*1.7)&(g>b*1.2)&(r>80)
  if not red.all():reject('TOP_footprint_mixed_or_shadow_or_antialias');continue
  rgb=np.median(px.reshape(-1,3),axis=0);pid=int(np.argmin(((pal-rgb)**2).sum(1)));records.append({'cell_xyz':[x,y,z],'old_material':names[material],'proposed_material':f'top_tile_{pid:02d}','whole_TOP_pixel_support_box':[int(np.floor(u0)),int(np.floor(v0)),int(np.ceil(u1)),int(np.ceil(v1))],'conditional_TOP_footprint_uv':[u0,v0,u1,v1],'source_TOP_median_rgb':rgb.tolist(),'palette_sample_rgb':pal[pid].tolist(),'original_pale':is_pale,'F_B_first_hit_unchanged':True})
report={'schema':'riverstone.roof_top_cell_material_ownership_proposal.v1','status':'READ_ONLY_SOURCE_SUPPORTED_PROPOSAL_NOT_AUTHORED','render_sha256':hashlib.sha256((H/'roof_repaired.render.json.gz').read_bytes()).hexdigest(),'geometry_change':False,'palette_expansion':False,'per_face_color_override':False,'core_changes_needed':False,'rule':'Whole topmost original facade-derived cell material ownership may transfer to source TOP only in original .375m depth bands, declared gable roof band, strict conditional TOP rectangle, outside ridge/chimney holdouts, with every overlapped source pixel supporting terracotta and no FRONT/BACK first-hit material change. Existing palette only.','eligible_cell_count':len(records),'eligible_original_pale_count':sum(r['original_pale']for r in records),'pale_before':oldpale,'pale_remaining_if_applied':oldpale-sum(r['original_pale']for r in records),'rejected_counts':dict(rejected),'pale_rejected_counts':dict(pale_reject),'bounded_authoring_estimate':'At most one existing common box paint per eligible .03125m cell, or equal-color run compression; compile only explicit delta cells. No new geometry sampling outside those cells. Existing full roof cells retained; changed-edge mesh partitions only need rebuilding.','strict_limitations':['This is source appearance ownership, not recovered calibrated albedo. Source RGB may contain illumination. No height, shadow or normal is changed.','Whole original cell color changes on all its faces; voxel source and render stay consistent.','F/B-facing antialias conflict cells are deliberately excluded. Their observed pale RGB and TOP terracotta cannot both be enforced on one same-color voxel without an explicit source interpretation; no automatic white deletion.','Whole TOP registration and physical scale remain rejected.'],'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
(D/'material_ownership_proposal.json').write_text(json.dumps(report,indent=2));(D/'eligible_cell_proposals.json').write_text(json.dumps(records,separators=(',',':')));print(json.dumps(report,indent=2))
