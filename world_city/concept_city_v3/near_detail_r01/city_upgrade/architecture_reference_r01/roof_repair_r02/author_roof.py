"""r02: remove diagnostic full-depth roof artifacts; source-bound finite tiles.
Common master grammar and common prepared sampler only. No body resampling.
"""
from pathlib import Path
import argparse,copy,gzip,hashlib,json,math,os,resource,sys,time,gc
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from PIL import Image
R=next(p for p in Path(__file__).resolve().parents if(p/'voxel_character/common/core.py').exists());sys.path.insert(0,str(R))
from voxel_character.common import core,prepared_sampling_v3 as sampler,render_data
H=Path(__file__).resolve().parent;A=H.parent;OLD=A/'roof_repair_r01';F=A/'foundation_repair_r01';Q=A/'reconstruction_proof_r01';M=Q/'roof_measurement_r01';P=.03125;JOIN=9.5

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(R)),'sha256':sha(p)}
def read(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def write(name,v):
 p=H/name;assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True)
 b=json.dumps(v,separators=(',',':'),allow_nan=False).encode();b=gzip.compress(b,mtime=0)if p.suffix=='.gz'else b
 assert sum(x.stat().st_size for x in H.rglob('*')if x.is_file())+len(b)<15_000_000
 p.write_bytes(b);return ref(p)
def pins():
 paths=[F/'foundation_arrays.npz',F/'foundation_revised.master.json.gz',F/'foundation_repaired.render.json.gz',Q/'image_derived_arrays.npz',M/'measurement_contract.json',M/'measurements.json',OLD/'tile_measurement_r01/tile_regions.json',OLD/'roof_repaired.render.json.gz',R/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png',Path(core.__file__),Path(sampler.__file__),Path(render_data.__file__),Path(render_data.mesh.__file__)]
 return {str(p.relative_to(R)):sha(p)for p in paths}

def prepare():
 t=time.monotonic();dependencies=pins();tiles=read(OLD/'tile_measurement_r01/tile_regions.json');meas=read(M/'measurements.json');base=read(F/'foundation_revised.master.json.gz')
 a=np.load(F/'foundation_arrays.npz');o=a['occupancy'];mat=a['materials'];src=np.load(Q/'image_derived_arrays.npz');image=np.asarray(Image.open(R/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png').convert('RGB'))
 slopes=[abs(z['slope_px_per_px'])for v in meas['front_back_gable_profile_fits'].values()for z in v['left_right_upper_tile_envelope_fits']];slope=sum(slopes)/len(slopes);ridge=13.875
 yy,xx,zz=np.indices(o.shape,sparse=True);X=(xx-48+.5)*.125;Y=(yy+.5)*.125;line=ridge-slope*abs(X)
 def red(rgb):return (rgb[:,:,0]>rgb[:,:,1]*1.7)&(rgb[:,:,1]>rgb[:,:,2]*1.2)&(rgb[:,:,0]>80)
 # Two separate source semantics: finite roof shell near gable; false chimney
 # columns extruded through Z. Preserve wooden gable planes outside red/stone.
 front=red(src['front_rgb']);back=red(src['back_rgb'])
 gray_masks=[];gray_colors=[]
 for name,box,xcenter,yorigin,reverse in [('front',[360,60,400,141],256,496,False),('back',[1136,60,1176,141],1280,496,True)]:
  mask=np.zeros((112,96),bool);colors=np.zeros((112,96,3),np.float32)
  for y in range(88,110):
   v0=yorigin-4*(y+1);v1=v0+4
   for x in range(74,86):
    u0=xcenter+(x-48)*4 if not reverse else xcenter-(x-47)*4;u1=u0+4
    if u0<box[0]or u1>box[2]or v0<box[1]or v1>box[3]:continue
    pixels=image[v0:v1,u0:u1].reshape(-1,3).astype(float);lum=pixels.mean(1);good=(np.ptp(pixels,axis=1)<40)&(lum>=55)&(lum<210)
    if good.mean()>=.375:mask[y,x]=True;colors[y,x]=np.median(pixels[good],axis=0)
  gray_masks.append(mask);gray_colors.append(colors)
 chimney_observed=gray_masks[0]|gray_masks[1];chimney_intersection=gray_masks[0]&gray_masks[1]
 roof_band=(Y>=line-.5)&(Y<=line+.1875)&(yy>=76)
 roof_owned=o&roof_band&(((zz>=3)&(zz<77))|((zz>=77)&front[:,:,None])|((zz<3)&back[:,:,None]))
 # Above the measured gable roof, all interior occupancy comes from the old
 # FRONT/BACK full-depth visual hull, not a supported body surface.
 roof_artifacts=o&(Y>line+.1875)&(yy>=76)&(zz>=3)&(zz<77)
 chimney_owned=o&chimney_observed[:,:,None]&(yy>=76)
 removed=roof_owned|roof_artifacts|chimney_owned
 # Only the original narrow ridge cap is kept as an explicit unresolved part.
 ridge_cap=o&(abs(X)<.1875)&(Y>=13.75)
 removed &= ~ridge_cap
 keep=o&~removed
 np.savez_compressed(H/'ownership_arrays.npz',removed_roof=removed,roof_shell=roof_owned,unsupported_upper_extrude=roof_artifacts,chimney_extrude=chimney_owned,retained_ridge_cap=ridge_cap,kept_occupancy=keep,kept_materials=np.where(keep,mat,-1).astype(np.int16),chimney_front_gray=gray_masks[0],chimney_back_gray=gray_masks[1],chimney_supported_intersection=chimney_intersection)
 coefficients=tiles['conditional_mapping']['coefficients'];sx,sz,tx,tz=[coefficients[k]for k in ('sx','sz','tx','tz')]
 def top(x):return ridge-slope*abs(x)
 def slab(x0,x1,z0,z1,lower,upper):return {'kind':'extrusion','polygon':[[x0,top(x0)+lower],[x1,top(x1)+lower],[x1,top(x1)+upper],[x0,top(x0)+upper]],'z_min':z0,'z_max':z1}
 materials={f'top_tile_{p["id"]:02d}':''.join(f'{v:02x}'for v in p['rgb'])for p in tiles['palette']};ops=[];links=[]
 xlo,xhi=tiles['conditional_mapping']['anchors']['target_x_interval_diagnostic_m'];zlo,zhi=tiles['conditional_mapping']['anchors']['target_z_interval_diagnostic_m']
 for side,lo,hi in [('left',xlo,0.),('right',0.,xhi)]:
  n=math.ceil((hi-lo)/.25)
  for i in range(n):
   x0=lo+(hi-lo)*i/n;x1=lo+(hi-lo)*(i+1)/n
   ops.append({'id':f'support_{side}_{i:02d}','part':'thin_roof_support','action':'paint','material':'top_tile_00','shape':slab(x0,x1,zlo,zhi,-.1875,-.0625)})
 for region in tiles['regions']:
  u0,v0,u1,v1=region['bbox_px'];gap=.5
  x0=sx*(u0+gap)+tx;x1=sx*(u1-gap)+tx;z0=sz*(v0+gap)+tz;z1=sz*(v1-gap)+tz
  local_slope=slope if x1<0 else -slope;c=1/math.sqrt(1+local_slope**2)
  basis=[[0,-local_slope*c,c],[0,c,local_slope*c],[-1,0,0]]
  width=z1-z0;crest=.0625;thickness=.0625
  xs=[-width/2,-width/4,0,width/4,width/2];heights=[0,crest*.75,crest,crest*.75,0]
  polygon=[[x,y-thickness]for x,y in zip(xs,heights)]+[[x,y]for x,y in reversed(list(zip(xs,heights)))]
  # Expand in local along-slope extent, then original common feature cuts trim
  # horizontal X exactly to the actual source interval. No shear/new shape API.
  transform={'translation':[x0,top(x0)-.0625,(z0+z1)/2],'basis':basis}
  shape={'kind':'extrusion','polygon':polygon,'z_min':-.125,'z_max':(x1-x0)/c+.125}
  paint={'id':region['id'],'part':'measured_tile_regions','action':'paint','material':f'top_tile_{region["color"]["palette_id"]:02d}','shape':shape,'transform':transform};ops.append(paint)
  prepared=core.prepare_shape(shape,P);low,high=core.shape_bounds(prepared);corners=[core.apply(core.transform(transform),p)for p in __import__('itertools').product(*zip(low,high))];wlo=[min(p[k]for p in corners)-P for k in range(3)];whi=[max(p[k]for p in corners)+P for k in range(3)]
  for tag,left,right in [('left',wlo[0],x0),('right',x1,whi[0])]:
   ops.append({'id':region['id']+'_crop_'+tag,'part':'measured_tile_regions','action':'cut','selector':{'feature':region['id']},'shape':{'kind':'box','min':[left,wlo[1],wlo[2]],'max':[right,whi[1],whi[2]]}})
  links.append({'operation':region['id'],'source_bbox_px':region['bbox_px'],'source_color':region['color'],'horizontal_footprint_xz':[x0,z0,x1,z1],'thin_normal_thickness_prior_m':thickness,'normal_crest_prior_m':crest,'profile':'five-point symmetric barrel arch; no brightness input','common_feature_crop_ops':[region['id']+'_crop_left',region['id']+'_crop_right'],'partial_endpoints':region['partial_endpoints_left_top_right_bottom']})
 # Finite chimney: observed FRONT/BACK intersection only; depth and reconciled
 # Z position are explicit priors because TOP/side correspondence still fails.
 yyxx=np.argwhere(chimney_intersection);assert len(yyxx)>0
 observed=np.array([(gray_colors[0][y,x]+gray_colors[1][y,x])/2 for y,x in yyxx]);lum=observed.mean(1);order=np.argsort(lum);selected=[order[int((len(order)-1)*f)]for f in (.15,.5,.85)];stone_palette=np.rint(observed[selected]).astype(int)
 for i,rgb in enumerate(stone_palette):materials[f'chimney_gray_{i:02d}']=''.join(f'{v:02x}'for v in rgb)
 chimney_z=-3.5625;depth=1.;chimneylinks=[]
 for y,x in yyxx:
  rgb=(gray_colors[0][y,x]+gray_colors[1][y,x])/2;material=int(np.argmin(((stone_palette-rgb)**2).sum(1)));oid=f'finite_chimney_y{y}_x{x}'
  ops.append({'id':oid,'part':'finite_chimney_prior','action':'paint','material':f'chimney_gray_{material:02d}','shape':{'kind':'box','min':[(int(x)-48)*.125,int(y)*.125,chimney_z-depth/2],'max':[(int(x)-47)*.125,(int(y)+1)*.125,chimney_z+depth/2]}})
  chimneylinks.append({'operation':oid,'front_back_grid_yx':[int(y),int(x)],'source_rgb_mean':rgb.tolist(),'material_id':material})
 master={'schema':core.SCHEMA,'id':'architecture_A_top_bound_roof_repair_r02','revision':2,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':materials,'components':[{'id':'top_bound_roof','parts':[{'id':p,'pivot':[0,0,0]}for p in ['thin_roof_support','measured_tile_regions','finite_chimney_prior']],'operations':ops}],'instances':[{'id':'top_bound_roof','component':'top_bound_roof'}],'assembly_cuts':[],'constraints':[{'id':'nonempty_roof','kind':'nonempty'}],'metadata':{'diagnostic_only':True,'production_gate_open':False,'image_bound_2d_regions':True,'brightness_to_height':False,'measured_gable_slope':slope,'original_max_y':ridge,'original_global_registration_accepted':False,'chimney_consistency_accepted':False,'thin_tile_normal_thickness_prior_m':.0625,'barrel_normal_crest_prior_m':.0625,'continuous_support_vertical_thickness_prior_m':.125,'seam_separator_prior_px':1,'local_pitch_m':P,'chimney_depth_prior_m':depth,'chimney_center_z_prior_m':chimney_z,'chimney_z_observation_disagreement_m':.5}}
 core.validate_master(master,P);masterref=write('roof_patch.master.json.gz',master)
 plan=sampler.prepare_master(master,{'pitch':P});chunk_edges=list(range(-164,165,16));assert chunk_edges[-1]==156;chunk_edges.append(164)
 report={'schema':'riverstone.image_roof_repair.plan.v2','source_dependencies':dependencies,'driver':ref(Path(__file__)),'master':masterref,'roof_regions':len(tiles['regions']),'tile_source_links':links,'chimney_source_links':chimneylinks,'chimney_silhouette_intersection_cells':len(yyxx),'chimney_prior':{'depth_m':depth,'center_z_m':chimney_z,'z_uncertainty_m':.25,'source_side_centers_m':[-3.8125,-3.3125],'top_chimney_registration_accepted':False,'gray_mask_rule':'FRONT/BACK intersection of 4x4 cells, >=.375 actual neutral pixels, RGB chroma<40 and luminance55..210; semantic chimney ROIs only','palette_rgb':stone_palette.tolist()},'roof_ownership':{'removed_cells':int(removed.sum()),'roof_shell_cells':int(roof_owned.sum()),'unsupported_above_gable_interior_extrude_cells':int(roof_artifacts.sum()),'chimney_full_depth_extrude_cells':int(chimney_owned.sum()),'kept_ridge_cap_cells':int(ridge_cap.sum()),'kept_nonroof_cells':int(keep.sum()),'retained_upper_coarse_cells':int(keep[76:].sum()),'all_geometry_below_join_identical':bool(np.array_equal(keep[:76],o[:76]))},'pitch_m':P,'join_y_m':JOIN,'compile_chunk_edges_z':chunk_edges,'max_candidates_per_chunk':350000,'max_output_cells_per_chunk':100000,'prepared_plan_key':plan.plan_key,'prepared_provenance':dict(plan.provenance),'source_modifications':False,'whole_house_highres_compile':False,'elapsed_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 assert dependencies==pins();write('plan.json',report);print(json.dumps({k:v for k,v in report.items()if k not in ['source_dependencies','tile_source_links','chimney_source_links','prepared_provenance']}),flush=True)

def compile_chunks():
 t=time.monotonic();report=read(H/'plan.json');assert report['source_dependencies']==pins();master=read(H/'roof_patch.master.json.gz');plan=sampler.prepare_master(master,{'pitch':P});assert plan.plan_key==report['prepared_plan_key'];chunks=[]
 for i,(lo,hi)in enumerate(zip(report['compile_chunk_edges_z'],report['compile_chunk_edges_z'][1:])):
  st=time.monotonic();bounds={'min':[-202,300,lo],'max':[202,448,hi]}
  c=sampler.compile_prepared(plan,cell_bounds=bounds,max_candidate_cells=350000,max_output_cells=100000)
  assert c['valid'];r=write(f'compiled/chunk_{i:02d}.json.gz',c);chunks.append({'index':i,'owned_z_cells':[lo,hi],'compiled':r,'cells':len(c['cells']),'candidates':c['candidate_cells'],'seconds':time.monotonic()-st});print(json.dumps(chunks[-1]),flush=True);del c;gc.collect()
 assert report['source_dependencies']==pins();write('compile.json',{'status':'PASS_BOUNDED_ROOF_CHUNKS','chunks':chunks,'total_candidate_cells':sum(c['candidates']for c in chunks),'total_occupied_cells':sum(c['cells']for c in chunks),'elapsed_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'source_dependencies_unchanged':True,'whole_house_highres_compile':False})
if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(90,)*2)
 p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--compile',action='store_true');a=p.parse_args()
 if a.prepare:prepare()
 if a.compile:compile_chunks()
