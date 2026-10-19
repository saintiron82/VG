"""Bounded image-bound tile surface in the unchanged common master grammar."""
from pathlib import Path
import argparse,copy,gzip,hashlib,json,math,os,resource,sys,time
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
R=next(p for p in Path(__file__).resolve().parents if(p/'voxel_character/common/core.py').exists());sys.path.insert(0,str(R))
from voxel_character.common import core,render_data
H=Path(__file__).resolve().parent; A=H.parent;F=A/'foundation_repair_r01';Q=A/'reconstruction_proof_r01';M=Q/'roof_measurement_r01';P=.0625;JOIN=9.5

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(R)),'sha256':sha(p)}
def read(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def write(name,v):
 p=H/name;assert not p.exists(),p
 b=json.dumps(v,separators=(',',':'),allow_nan=False).encode();b=gzip.compress(b,mtime=0)if p.suffix=='.gz'else b
 assert sum(x.stat().st_size for x in H.rglob('*')if x.is_file())+len(b)<15_000_000
 p.write_bytes(b);return ref(p)
def pins():
 paths=[F/'foundation_arrays.npz',F/'foundation_revised.master.json.gz',F/'foundation_repaired.render.json.gz',Q/'image_derived_arrays.npz',M/'measurement_contract.json',M/'measurements.json',H/'tile_measurement_r01/tile_regions.json',R/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png',Path(core.__file__),Path(render_data.__file__),Path(render_data.mesh.__file__)]
 return {str(p.relative_to(R)):sha(p)for p in paths}
def validate_regions(data):
 if data.get('original_global_registration_accepted')is not False:raise ValueError('global registration must remain rejected')
 if data.get('geometry_created')is not False:raise ValueError('only measured appearance input accepted')
 palette=data['palette'];assert len(palette)==6 and [p['id']for p in palette]==list(range(6))
 for p in palette:assert len(p['rgb'])==3 and all(type(x)is int and 0<=x<=255 for x in p['rgb'])
 seen=set();boxes=[]
 for r in data['regions']:
  if r['id']in seen:raise ValueError('duplicate measured region')
  seen.add(r['id']);u,v,x,y=r['bbox_px']
  if not all(type(z)is int for z in [u,v,x,y])or not(613<=u<x<=922 and 787<=v<y<=977):raise ValueError('invalid bounded pixel rectangle')
  if not(0<=r['color']['palette_id']<6):raise ValueError('unknown material')
  for e in data['excluded_regions']:
   a,b,c,d=e['bbox_px']
   if max(u,a)<min(x,c)and max(v,b)<min(y,d):raise ValueError('excluded pixel support')
  for a,b,c,d in boxes:
   if max(u,a)<min(x,c)and max(v,b)<min(y,d):raise ValueError('overlapping tile regions')
  boxes.append((u,v,x,y))
 return True

def prepare():
 t=time.monotonic();dependencies=pins();tiles=read(H/'tile_measurement_r01/tile_regions.json');validate_regions(tiles);measured=read(M/'measurements.json');contract=read(M/'measurement_contract.json');base=read(F/'foundation_revised.master.json.gz')
 a=np.load(F/'foundation_arrays.npz');o=a['occupancy'];mat=a['materials'];src=np.load(Q/'image_derived_arrays.npz')
 # Ownership is source semantic roof band, never a material-only deletion.
 # FRONT/BACK facade layers must be actual red pixels. Interior roof shell uses
 # measured gable distance; the unresolved chimney above that band is retained.
 slopes=[abs(z['slope_px_per_px'])for view in measured['front_back_gable_profile_fits'].values()for z in view['left_right_upper_tile_envelope_fits']]
 slope=sum(slopes)/len(slopes);ridge=13.875
 yy,xx,zz=np.indices(o.shape,sparse=True);X=(xx-48+.5)*.125;Y=(yy+.5)*.125
 roofline=ridge-slope*abs(X);band=(Y>=roofline-.5)&(Y<=roofline+.1875)&(yy>=76)
 def red(rgb):return (rgb[:,:,0]>rgb[:,:,1]*1.7)&(rgb[:,:,1]>rgb[:,:,2]*1.2)&(rgb[:,:,0]>80)
 front=red(src['front_rgb']);back=red(src['back_rgb'])
 owned=o&band&(((zz>=3)&(zz<77))|((zz>=77)&front[:,:,None])|((zz<3)&back[:,:,None]))
 # Existing central ridge and ambiguous chimney remain source-owned.
 owned &= abs(X)>=.1875
 keep=o&~owned
 np.savez_compressed(H/'ownership_arrays.npz',removed_roof=owned,kept_occupancy=keep,kept_materials=np.where(keep,mat,-1).astype(np.int16))
 coefficients=tiles['conditional_mapping']['coefficients'];sx,sz,tx,tz=[coefficients[k]for k in ('sx','sz','tx','tz')]
 def top(x):return ridge-slope*abs(x)
 def extrusion(x0,x1,z0,z1,low,high):
  return {'kind':'extrusion','polygon':[[x0,top(x0)+low],[x1,top(x1)+low],[x1,top(x1)+high],[x0,top(x0)+high]],'z_min':z0,'z_max':z1}
 materials={f'top_tile_{p["id"]:02d}':''.join(f'{v:02x}'for v in p['rgb'])for p in tiles['palette']}
 ops=[];source_links=[]
 # Continuous support is an explicit thin geometric prior, not dark-pixel fill.
 # Narrow source-equivalent strips avoid the empty whole-roof AABB sampling.
 xlo,xhi=tiles['conditional_mapping']['anchors']['target_x_interval_diagnostic_m'];zlo,zhi=tiles['conditional_mapping']['anchors']['target_z_interval_diagnostic_m']
 for side,lo,hi in [('left',xlo,0.),('right',0.,xhi)]:
  n=math.ceil((hi-lo)/.25)
  for i in range(n):
   x0=lo+(hi-lo)*i/n;x1=lo+(hi-lo)*(i+1)/n
   ops.append({'id':f'support_{side}_{i:02d}','part':'thin_roof_support','action':'paint','material':'top_tile_00','shape':extrusion(x0,x1,zlo,zhi,-.25,-.0625)})
 # One observed pixel is reserved as a shallow seam separator. Its depth is
 # fixed by the explicit .0625m tile prior, never derived from luminosity.
 for r in tiles['regions']:
  u0,v0,u1,v1=r['bbox_px'];gap=.5
  x0=sx*(u0+gap)+tx;x1=sx*(u1-gap)+tx;z0=sz*(v0+gap)+tz;z1=sz*(v1-gap)+tz
  assert x0<x1 and z0<z1 and x0*x1>=0
  ops.append({'id':r['id'],'part':'measured_tile_regions','action':'paint','material':f'top_tile_{r["color"]["palette_id"]:02d}','shape':extrusion(x0,x1,z0,z1,-.0625,0.)})
  source_links.append({'operation':r['id'],'source_bbox_px':r['bbox_px'],'source_color':r['color'],'partial_endpoints':r['partial_endpoints_left_top_right_bottom'],'physical_thickness_prior_m':.0625,'seam_separator_prior_px':1.,'shape_bounds':core.shape_bounds(core.prepare_shape(ops[-1]['shape'],P))})
 master={'schema':core.SCHEMA,'id':'architecture_A_top_bound_roof_repair_r01','revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':materials,'components':[{'id':'top_bound_roof','parts':[{'id':'thin_roof_support','pivot':[0,0,0]},{'id':'measured_tile_regions','pivot':[0,0,0]}],'operations':ops}],'instances':[{'id':'top_bound_roof','component':'top_bound_roof'}],'assembly_cuts':[],'constraints':[{'id':'nonempty_roof','kind':'nonempty'}],'metadata':{'diagnostic_only':True,'production_gate_open':False,'image_bound_2d_regions':True,'brightness_to_height':False,'measured_slope':slope,'preserved_original_peak_y':ridge,'original_global_registration_accepted':False,'chimney_consistency_accepted':False,'thin_tile_prior_m':.0625,'continuous_support_prior_m':.1875,'seam_separator_prior_px':1,'local_pitch_m':P}}
 core.validate_master(master,P)
 estimates=[]
 for op in ops:
  lo,hi=core.shape_bounds(core.prepare_shape(op['shape'],P));estimates.append(math.prod(math.ceil(b/P-core.EPS)-math.floor(a/P+core.EPS)for a,b in zip(lo,hi)))
 assert sum(estimates)<900000
 masterref=write('roof_patch.master.json.gz',master)
 report={'schema':'riverstone.image_roof_repair.plan.v1','source_dependencies':dependencies,'driver':ref(Path(__file__)),'master':masterref,'roof_regions':len(tiles['regions']),'source_links':source_links,'common_candidate_cells_estimate':sum(estimates),'max_candidate_cells':900000,'max_output_cells':180000,'pitch_m':P,'join_y_m':JOIN,'roof_ownership':{'removed_cells':int(owned.sum()),'kept_cells':int(keep.sum()),'preserved_upper_cells':int(keep[76:].sum()),'source_yx_band':'abs(actual y center - measured gable upper line) with below .5m / above .1875m ownership envelope; y>=9.5; FRONT/BACK 3 layers require original strict-red source pixel; central |X|<.1875 ridge retained','uncertain_chimney_above_slope_band':'unchanged baseline geometry, not repaired','nonroof_material_only_deletion':False},'thickness_prior_m':.0625,'support_prior_m':.1875,'seam_separator_prior_px':1.,'original_max_y_m':13.875,'measured_gable_average_slope':slope,'conditional_top_mapping':coefficients,'original_global_registration_pass':False,'source_chimney_conflict_preserved':True,'underside_measured':False,'source_modifications':False,'whole_house_highres_compile':False,'ownership_arrays':ref(H/'ownership_arrays.npz'),'elapsed_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 assert dependencies==pins();write('plan.json',report)
 print(json.dumps({k:report[k]for k in ['roof_regions','common_candidate_cells_estimate','roof_ownership','elapsed_seconds','peak_rss_kib']}),flush=True)

def compile_patch():
 t=time.monotonic();plan=read(H/'plan.json');assert plan['source_dependencies']==pins();master=read(H/'roof_patch.master.json.gz');compiled=core.compile_master(master,{'pitch':P},max_candidate_cells=900000,max_output_cells=180000);assert compiled['valid']
 reference=write('roof_patch.compiled.json.gz',compiled)
 write('compile.json',{'status':'PASS_BOUNDED_ROOF_ONLY','compiled':reference,'candidate_cells':compiled['candidate_cells'],'occupied_cells':len(compiled['cells']),'elapsed_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'source_dependencies_unchanged':plan['source_dependencies']==pins(),'whole_house_highres_compile':False})
 print(json.dumps({'candidate_cells':compiled['candidate_cells'],'occupied_cells':len(compiled['cells']),'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True)

if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(90,)*2)
 p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--compile',action='store_true');a=p.parse_args()
 if a.prepare:prepare()
 if a.compile:compile_patch()
