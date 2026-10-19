#!/usr/bin/env python3
"""Read-only source/first-hit audit. No sampler, compiler, geometry or normal write."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(45,)*2)
import sys,json,gzip,hashlib,time,collections,gc,csv
from pathlib import Path
import numpy as np
from PIL import Image
O=Path(__file__).resolve().parent;A=O.parent;ROOT=next(p for p in A.parents if (p/'voxel_character/common/core.py').exists());P=.03125
R1=A/'roof_repair_r01';R2=A/'roof_repair_r02';R3=A/'roof_repair_r03';R4=A/'roof_repair_r04'
SOURCE=ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png'
sys.path.insert(0,str(R1/'tile_measurement_r01'))
from measure_tiles import peaks
resource.setrlimit(resource.RLIMIT_CPU,(30,)*2)
def read(p):
 with gzip.open(p,'rt') if str(p).endswith('.gz') else open(p) as f:return json.load(f)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(65536),b''):h.update(b)
 return h.hexdigest()
def write(n,d): (O/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def boxmask(U,V,b):return (U>=b[0])&(U<b[2])&(V>=b[1])&(V<b[3])
def rle(mask):
 out=[]
 for v,row in enumerate(mask):
  changes=np.flatnonzero(np.diff(np.r_[False,row,False].astype(np.int8)))
  out.extend([[int(v),int(l),int(r)] for l,r in zip(changes[::2],changes[1::2])])
 return out
def main():
 start=time.monotonic();cpu=time.process_time();pins={}
 def pin(p):pins[str(p.relative_to(ROOT))]=sha(p);return p
 assert sha(SOURCE)=='552b0bd61eba3c3f5bee98a6b3a5fac085362dc8804e049e325db55fb902ec93';pin(SOURCE)
 m=read(pin(R1/'tile_measurement_r01/tile_regions.json'));p2=read(pin(R2/'plan.json'));p3=read(pin(R3/'plan.json'));coef=m['conditional_mapping']['coefficients'];sx,tx,sz,tz=[coef[k] for k in ['sx','tx','sz','tz']]
 render=pin(R4/'roof_repaired.render.json.gz');assert pins[str(render.relative_to(ROOT))]=='45e9b206d2b126df7dd2ce878f70ada312a122a49c9a958098d08ae1406cb4d5'
 u=np.load(pin(R4/'upper_union_arrays.npz'));mat=u['materials'];origin=u['origin_cell_xyz'].tolist();names=u['material_names'].tolist();mids={n:i for i,n in enumerate(names)}
 top_y=mat.shape[0]-1-np.argmax(mat[::-1]>=0,axis=0);present=(mat>=0).any(axis=0);gx,gz=np.indices(top_y.shape);topmat=mat[top_y,gx,gz];del mat;gc.collect()
 d=np.load(pin(R3/'delta_ownership_arrays.npz'))['delta_class'];topdelta=d[top_y,gx,gz];del d;gc.collect()
 fids=['unproven_current_owner'];idx={fids[0]:0};owner=np.zeros(top_y.shape,np.uint16);kind={};links={}
 def fid_index(fid):
  if fid not in idx:idx[fid]=len(fids);fids.append(fid)
  return idx[fid]
 for k,pl in enumerate([p2,p3]):
  for l in pl['tile_source_links']:
   fid=l['operation'];fid_index(fid);links[fid]=l;kind[fid]='old_measured_tile' if k==0 else 'recovered_tile'
 scanned=0;accepted=collections.Counter();r4_ids=set();compiled_records=[]
 for rev in [R2,R3,R4]:
  c=read(pin(rev/'compile.json'));records=[r['compiled'] for r in c['chunks']] if rev==R2 else [c['delta']]
  for rec in records:
   path=pin(ROOT/rec['path']);assert sha(path)==rec['sha256'];compiled_records.append((rev,path));data=read(path)
   for x,y,z,inst,part,material,fid in data['cells']:
    ix,iz=x-origin[0],z-origin[2]
    if ix<0 or iz<0 or ix>=top_y.shape[0] or iz>=top_y.shape[1] or y-origin[1]!=top_y[ix,iz] or topmat[ix,iz]!=mids[material]:continue
    if rev==R2 and topdelta[ix,iz]!=0:continue
    if rev==R3 and not ((part=='observed_shadow_tile_extensions' and topdelta[ix,iz]==3) or (part=='foreground_resampled_gable_edge' and topdelta[ix,iz]==2)):continue
    owner[ix,iz]=fid_index(fid);accepted[rev.name]+=1
    if rev==R4:r4_ids.add(idx[fid])
   scanned+=len(data['cells']);del data;gc.collect()
 ownkind={i:kind.get(fid,'backing' if fid.startswith('support_') else 'chimney' if fid.startswith('finite_chimney_') else 'R4_recolor' if i in r4_ids else 'other') for i,fid in enumerate(fids)}
 # Source-region evidence and authored (separator-inset) footprint masks on the exact current XZ lattice.
 U=((gx+origin[0]+.5)*P-tx)/sx;V=((gz+origin[2]+.5)*P-tz)/sz
 roi=boxmask(U,V,[783,791,919,974]);whole=boxmask(U,V,[613,787,922,977]);hold=boxmask(U,V,[868,795,908,849]);raw=np.zeros(U.shape,bool);foot=np.zeros(U.shape,bool);expected=np.zeros(U.shape,np.uint16);partial_inset=np.zeros(U.shape,bool);observed_trough_inset=np.zeros(U.shape,bool);region_by_id={r['id']:r for r in m['regions']}
 for fid,l in links.items():
  b=l.get('source_bbox_px',l.get('source',{}).get('bbox_px'));raw|=boxmask(U,V,b)
  x0,z0,x1,z1=l['horizontal_footprint_xz'];fb=[(x0-tx)/sx,(z0-tz)/sz,(x1-tx)/sx,(z1-tz)/sz];mask=boxmask(U,V,fb);assert not np.any(expected[mask]);expected[mask]=idx[fid];foot|=mask
  rb=boxmask(U,V,b);flags=region_by_id[fid]['partial_endpoints_left_top_right_bottom'] if fid in region_by_id else [False]*4
  for side,flag in enumerate(flags):
   edge=[U<fb[0],V<fb[1],U>=fb[2],V>=fb[3]][side]&rb
   if flag:partial_inset|=edge
   else:observed_trough_inset|=edge
 tile_ids=[i for i,k in ownkind.items() if k in ('old_measured_tile','recovered_tile')];tile=np.isin(owner,tile_ids);back=np.isin(owner,[i for i,k in ownkind.items() if k=='backing']);chim=np.isin(owner,[i for i,k in ownkind.items() if k=='chimney'])
 categories={'inside_authored_tile_footprint':foot,'measured_raw_interval_separator_outside_footprint':raw&~foot,'source_chimney_holdout':hold&~raw,'other_unmeasured':~raw&~hold}
 cross={}
 for nm,mask in categories.items():
  q=mask&roi;cnt=collections.Counter(ownkind[int(i)] for i in owner[q]);cross[nm]={'xz_lattice_columns':int(q.sum()),'top_first_hit_owner_counts':dict(cnt),'conditional_projected_area_units2':float(q.sum()*P*P)}
 output={'schema':'riverstone.roof.backing_source_audit.r1','source_dependencies':pins,'source_image_size':[1536,1024],'render_sha256':pins[str(render.relative_to(ROOT))], 'global_TOP_registration_accepted':False,'physical_scale_verified':False,'conditional_mapping':coef,'lattice_pitch':P,'lattice_array_shape_xz':list(owner.shape),'lattice_origin_xyz':origin,'right_safe_plane_px':[783,791,919,974],'true_holdout_conservative_px':[868,795,908,849],'current_top_first_hit_summary_right_plane':dict(collections.Counter(ownkind[int(i)] for i in owner[roi])),'cross_source_evidence_current_first_hit_right_plane':cross,'tile_owner_inside_expected_authored_footprint':int((tile&foot&roi).sum()),'wrong_or_missing_tile_owner_inside_footprint':int(((owner!=expected)&foot&roi).sum()),'backing_inside_authored_footprint':int((back&foot&roi).sum()),'backing_in_source_holdout':int((back&hold&roi).sum()),'current_chimney_in_source_holdout':int((chim&hold&roi).sum()),'source_holdout_not_current_chimney':int((~chim&hold&roi).sum()),'current_chimney_outside_source_holdout':int((chim&~hold&roi).sum()),'cached_compiled_rows_scanned':scanned,'accepted_top_rows_by_revision':dict(accepted)}
 output['backing_in_authored_inset_bands_detail']={'detected_trough_only':int((back&raw&~foot&observed_trough_inset&~partial_inset&roi).sum()),'declared_partial_ROI_edge_only':int((back&raw&~foot&partial_inset&~observed_trough_inset&roi).sum()),'both_detected_trough_and_partial_ROI_corner':int((back&raw&~foot&partial_inset&observed_trough_inset&roi).sum()),'note':'R1 declares zero separator at partial endpoints; frozen R2 author actually uses gap=.5 on every U/V endpoint. These ROI-clipped inset bands are not observed seams.'}
 # Exact footprint membership above uses cell centers. Separately test whole XZ cells,
 # distance-to-edge bands, analytic finite source extrusion, and cached tile rows.
 missing=back&foot&roi;emin=np.full(owner.shape,32767,np.int16);emax=np.full(owner.shape,-32768,np.int16);same_y=np.zeros(owner.shape,bool)
 for rev,path in compiled_records:
  if rev==R4:continue
  d=read(path)
  for x,y,z,inst,part,material,fid in d['cells']:
   ix,iz=x-origin[0],z-origin[2]
   if 0<=ix<owner.shape[0] and 0<=iz<owner.shape[1] and missing[ix,iz] and fid in idx and idx[fid]==int(expected[ix,iz]):
    emin[ix,iz]=min(emin[ix,iz],y);emax[ix,iz]=max(emax[ix,iz],y);same_y[ix,iz]|=y-origin[1]==int(top_y[ix,iz])
  del d;gc.collect()
 ops={}
 for rev in [R2,R3]:
  master=read(pin(rev/'roof_patch.master.json.gz'))
  ops.update({o['id']:o for c in master['components'] for o in c['operations'] if o['id'] in links})
 distcounts=collections.Counter();checks=collections.Counter();auditrows=[];examples=[]
 for ix,iz in np.argwhere(missing):
  fid=fids[int(expected[ix,iz])];l=links[fid];op=ops[fid];x=(ix+origin[0]+.5)*P;z=(iz+origin[2]+.5)*P;y=(top_y[ix,iz]+origin[1]+.5)*P;x0,z0,x1,z1=l['horizontal_footprint_xz'];dist=min(x-x0,x1-x,z-z0,z1-z)
  band='<=P' if dist<=P else '<=2P' if dist<=2*P else '>2P';distcounts[band]+=1;whole_cell=dist>=P/2-1e-10;checks['whole_XZ_cell_inside_footprint']+=int(whole_cell)
  B=op['transform']['basis'];t=op['transform']['translation'];q=[x-t[0],y-t[1],z-t[2]];local=[sum(B[j][i]*q[j] for j in range(3)) for i in range(3)];top=list(reversed(op['shape']['polygon'][5:]));height=None
  for a,b in zip(top,top[1:]):
   if a[0]-1e-10<=local[0]<=b[0]+1e-10:height=a[1]+(local[0]-a[0])*(b[1]-a[1])/(b[0]-a[0]);break
  assert height is not None
  finite=op['shape']['z_min']<=local[2]<=op['shape']['z_max'];inside=finite and height-.0625-1e-10<=local[1]<=height+1e-10
  checks['current_backing_voxel_center_inside_analytic_tile_source']+=int(inside);checks['current_backing_voxel_center_in_cached_expected_tile_rows']+=int(same_y[ix,iz]);checks['any_cached_expected_tile_row_at_XZ']+=int(emax[ix,iz]>-32768);checks['cached_expected_tile_row_above_current_top']+=int(emax[ix,iz]>top_y[ix,iz]+origin[1]);checks['outside_finite_extrusion_depth']+=int(not finite)
  top_world_y=t[1]+(height-B[0][1]*(x-t[0])-B[2][1]*(z-t[2]))/B[1][1]
  row=[int(ix+origin[0]),int(top_y[ix,iz]+origin[1]),int(iz+origin[2]),fid,fids[int(owner[ix,iz])],round(float(dist),9),band,bool(whole_cell),bool(inside),bool(same_y[ix,iz]),int(emin[ix,iz]) if emin[ix,iz]!=32767 else None,int(emax[ix,iz]) if emax[ix,iz]!=-32768 else None,round(float(top_world_y),9),round(float(y),9),round(float(local[1]-height),9)]
  auditrows.append(row)
  if len(examples)<12 and (band=='>2P' or len(examples)<4):examples.append(row)
 cols=['grid_x','current_top_grid_y','grid_z','expected_tile','current_owner','nearest_XZ_footprint_boundary_distance','distance_band','whole_XZ_cell_inside','current_center_inside_analytic_tile','current_center_in_cached_tile_rows','cached_tile_min_y','cached_tile_max_y','analytic_tile_top_world_y','current_top_voxel_center_world_y','local_normal_height_minus_tile_top']
 with (O/'authored_footprint_backing.csv').open('w') as f:
  w=csv.writer(f);w.writerow(cols);w.writerows(auditrows)
 output['authored_footprint_membership_definition']='Current lattice XZ cell center lies within exact authored horizontal_footprint_xz; whole-cell containment is separately reported.'
 output['backing_inside_authored_footprint_detail']={'count':int(missing.sum()),'distance_to_nearest_XZ_footprint_boundary':dict(distcounts),'checks':dict(checks),'csv_columns':cols,'examples':examples,'analytic_check':'Exact stored orthonormal transform to source polygon; five-point upper profile, uniform .0625 normal thickness, exact finite local extrusion range and authored X crop. Predicate evaluated only at existing first-hit centers; no cells generated.'}
 # Pixel-center correspondence samples, not an image warp or all-view registration.
 py,px=np.indices((1024,1536));praw=np.zeros(px.shape,bool)
 for l in links.values():praw|=boxmask(px,py,l.get('source_bbox_px',l.get('source',{}).get('bbox_px')))
 proi=boxmask(px,py,[783,791,919,974]);phold=boxmask(px,py,[868,795,908,849]);unmeasured=proi&~praw&~phold
 # Source pixel masks are disjoint categories; emitted as original-raster horizontal runs.
 masks={'existing_raw_measurement':praw&proi,'true_conservative_chimney_holdout':phold,'unmeasured_outside_holdout':unmeasured}
 output['source_pixel_area_right_plane']={k:int(v.sum()) for k,v in masks.items()};output['source_pixel_area_right_plane']['total']=int(proi.sum())
 write('source_uncertainty_masks.json',{'coordinate_convention':'Original 1536x1024 raster; each run [v,u0,u1) in source pixels. No warp.','runs':{k:rle(v) for k,v in masks.items()}})
 # Evidence at source pixel centers inside current backing, bounded to the roof rectangle.
 im=np.asarray(Image.open(SOURCE).convert('RGB'));data=[];examples=[]
 for v in range(791,974):
  for x in range(783,919):
   ix=int(np.floor((sx*(x+.5)+tx)/P))-origin[0];iz=int(np.floor((sz*(v+.5)+tz)/P))-origin[2];k=ownkind[int(owner[ix,iz])]
   if k=='backing':
    category='existing_raw_interval' if praw[v,x] else 'true_holdout' if phold[v,x] else 'unmeasured_outside_holdout';data.append((x,v,category,int(owner[ix,iz])))
    if len(examples)<20 and x%7==0 and v%11==0:examples.append({'source_px':[x,v],'source_rgb':im[v,x].tolist(),'conditional_XZ':[sx*(x+.5)+tx,sz*(v+.5)+tz],'current_top_cell_xyz':[ix+origin[0],int(top_y[ix,iz])+origin[1],iz+origin[2]],'current_top_owner':fids[int(owner[ix,iz])],'source_evidence_category':category})
 output['pixel_center_samples_mapping_to_current_backing']=dict(collections.Counter(r[2] for r in data));output['pixel_to_backing_examples']=examples
 write('top_first_hit_masks.json',{'coordinate_convention':'Array [x-index,z-index]; runs [x-index,z0,z1). Cells map with origin_xyz and pitch in audit.json. Diagnostic masks, no geometry.','runs':{'backing_within_authored_footprint':rle(back&foot&roi),'backing_in_unmeasured_source':rle(back&~raw&~hold&roi),'backing_in_source_holdout':rle(back&hold&roi),'current_chimney_outside_source_holdout':rle(chim&~hold&roi)},'owner_kind_counts':dict(collections.Counter(ownkind[int(i)] for i in owner[whole]))})
 # Missing-margin candidates from actual independent local V profiles, never extrapolated neighboring rows.
 candidates=[];profiles=[]
 for label,u0,u1,c in [('chimney_left_margin',859,868,863),('chimney_right_margin',908,913,910),('unaccepted_outer_strip',913,919,916)]:
  vb=[c-1,791,c+2,974];vp=im[791:974,c-1:c+2].mean(axis=(1,2));troughs=peaks(vp,6,10);edges=[(791,0,True)]+[(791+i,q,False) for i,q in troughs]+[(974,0,True)]
  profiles.append({'id':label,'source_profile_bbox':vb,'profile_sha256':hashlib.sha256(im[791:974,c-1:c+2].tobytes()).hexdigest(),'mean_RGB_profile':[round(float(q),6) for q in vp],'observed_troughs_v':[v for v,q,p in edges if not p],'observed_local_contrasts':[round(q,6) for v,q,p in edges if not p]})
  for (v0,q0,p0),(v1,q1,p1) in zip(edges,edges[1:]):
   if not 5<=v1-v0<=21:continue
   # Offer only wholly unmeasured rectangles, avoiding all 354 existing raw boxes and holdout.
   mask=unmeasured[v0:v1,u0:u1]
   if not mask.all():continue
   rgb=im[v0:v1,u0:u1].astype(np.int16);chroma=(rgb[:,:,0]>1.45*rgb[:,:,1])&(rgb[:,:,1]>1.15*rgb[:,:,2]);interior=im[v0+1:v1-1,u0+1:u1-1];flat=interior.reshape(-1,3);med=np.median(flat,axis=0);ki=int(np.argmin(((flat.astype(float)-med)**2).sum(axis=1)));w=u1-u0-2;sample=[u0+1+ki%w,v0+1+ki//w]
   b=[u0,v0,u1,v1];candidates.append({'id':f'{label}_v{v0}_{v1}','bbox_px':b,'local_profile_ref':label,'v_boundary_strengths':[q0,q1],'partial_V_endpoints':[p0,p1],'u_boundary_status':'One or both U ends are clipped conservative ROI boundaries, not newly traced tile seams.','terracotta_chroma_pixels':int(chroma.sum()),'pixels':int(chroma.size),'source_sample_px':sample,'source_sample_rgb':im[sample[1],sample[0]].tolist(),'conditional_diagnostic_xz_bbox':[sx*u0+tx,sz*v0+tz,sx*u1+tx,sz*v1+tz],'candidate_only_not_geometry_authorization':True})
 covered=np.zeros(px.shape,bool)
 for c in candidates:covered|=boxmask(px,py,c['bbox_px'])
 assert not np.any(covered&praw) and not np.any(covered&phold)
 output['candidate_interval_count']=len(candidates);output['candidate_source_pixels']=int(covered.sum());output['remaining_unmeasured_outside_holdout_pixels']=int((unmeasured&~covered).sum());output['candidate_caveat']='Local observed V intervals in previously unmeasured margins; U ends are conservative clipped fragment bounds. Not complete physical tiles. No height, full outline or global registration claim.'
 write('candidate_intervals.json',{'source_image_sha256':sha(SOURCE),'original_global_registration_accepted':False,'physical_scale_verified':False,'profiles':profiles,'candidate_intervals':candidates})
 output['all_source_dependencies_unchanged']=all(sha(ROOT/k)==v for k,v in pins.items());assert output['all_source_dependencies_unchanged'];output['elapsed_seconds']=time.monotonic()-start;output['cpu_seconds']=time.process_time()-cpu;output['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;output['sampler_calls']=0;output['compiler_calls']=0;output['geometry_or_normal_changes']=0
 write('audit.json',output);assert sum(p.stat().st_size for p in O.iterdir() if p.is_file())<2*1024**2
 print(json.dumps({k:v for k,v in output.items() if k not in ['source_dependencies','pixel_to_backing_examples']},indent=2))
if __name__=='__main__':main()
