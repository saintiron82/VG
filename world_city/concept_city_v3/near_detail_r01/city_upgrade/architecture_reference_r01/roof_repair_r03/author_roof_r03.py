"""Source-supported r03 delta only; frozen r02 roof sampling is reused."""
from pathlib import Path
import argparse,gc,gzip,hashlib,itertools,json,math,os,resource,sys,time
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from PIL import Image
R=next(p for p in Path(__file__).resolve().parents if (p/'voxel_character/common/core.py').exists());sys.path.insert(0,str(R))
from voxel_character.common import core,prepared_sampling_v3 as sampler,render_data
H=Path(__file__).resolve().parent;A=H.parent;OLD=A/'roof_repair_r02';F=A/'foundation_repair_r01';Q=A/'reconstruction_proof_r01';P=.03125;JOIN=9.5
IMAGE=R/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png'
DIAG=OLD/'gap_diagnostic_r01/source_shadow/diagnostic.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(R)),'sha256':sha(p)}
def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def write(name,obj):
 p=H/name;assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);b=json.dumps(obj,separators=(',',':'),allow_nan=False).encode();b=gzip.compress(b,mtime=0) if p.suffix=='.gz' else b
 assert sum(x.stat().st_size for x in H.rglob('*') if x.is_file())+len(b)<15_000_000
 p.write_bytes(b);return ref(p)
def pins():
 paths=[IMAGE,DIAG,F/'foundation_arrays.npz',F/'foundation_repaired.render.json.gz',F/'foundation_revised.master.json.gz',OLD/'upper_union_arrays.npz',OLD/'roof_patch.master.json.gz',OLD/'roof_repaired.render.json.gz',OLD/'plan.json',OLD/'compile.json',OLD/'ownership_arrays.npz',A/'roof_repair_r01/tile_measurement_r01/tile_regions.json',Path(core.__file__),Path(sampler.__file__),Path(render_data.__file__),Path(render_data.mesh.__file__)]
 return {str(p.relative_to(R)):sha(p) for p in paths}
def foreground(p):
 r,g,b=[p[...,i].astype(float)for i in range(3)];l=(r+g+b)/3
 return ((r-b>12)&(r>=g*.95)&(l<248))|(l<110)|((g-r>12)&(g-b>12)&(l<205))
def prepare():
 t=time.monotonic();deps=pins();legacy=read(OLD/'roof_patch.master.json.gz');base=read(F/'foundation_revised.master.json.gz');materials=base['materials']|legacy['materials'];names=list(materials)
 slope=legacy['metadata']['measured_gable_slope'];ridge=legacy['metadata']['original_max_y'];tiles=read(A/'roof_repair_r01/tile_measurement_r01/tile_regions.json');coef=tiles['conditional_mapping']['coefficients'];sx,sz,tx,tz=[coef[k]for k in ('sx','sz','tx','tz')]
 palette=np.array([[int(materials[f'top_tile_{i:02d}'][j:j+2],16)for j in (0,2,4)]for i in range(6)])
 color_names=[n for n in names if n.startswith('pixel_') or n.startswith('top_tile_')];color_rgb=np.array([[int(materials[n][j:j+2],16)for j in (0,2,4)]for n in color_names])
 ops=[];links=[]
 for reg in read(DIAG)['minimal_extension_candidates']:
  u0,v0,u1,v1=reg['bbox_px'];x0=sx*(u0+.5)+tx;x1=sx*(u1-.5)+tx;z0=sz*(v0+.5)+tz;z1=sz*(v1-.5)+tz
  s=-slope;c=1/math.sqrt(1+s*s);width=z1-z0;xs=[-width/2,-width/4,0,width/4,width/2];hs=[0,.046875,.0625,.046875,0];polygon=[[x,h-.0625]for x,h in zip(xs,hs)]+[[x,h]for x,h in reversed(list(zip(xs,hs)))]
  color=int(np.argmin(((palette-np.asarray(reg['median_rgb']))**2).sum(1)));oid=reg['id'];basis=[[0,-s*c,c],[0,c,s*c],[-1,0,0]];transform={'translation':[x0,ridge-slope*abs(x0)-.0625,(z0+z1)/2],'basis':basis};shape={'kind':'extrusion','polygon':polygon,'z_min':-.125,'z_max':(x1-x0)/c+.125}
  ops.append({'id':oid,'part':'observed_shadow_tile_extensions','action':'paint','material':f'top_tile_{color:02d}','shape':shape,'transform':transform})
  low,high=core.shape_bounds(core.prepare_shape(shape,P));corners=[core.apply(core.transform(transform),p)for p in itertools.product(*zip(low,high))];wlo=[min(p[k]for p in corners)-P for k in range(3)];whi=[max(p[k]for p in corners)+P for k in range(3)]
  for tag,left,right in [('left',wlo[0],x0),('right',x1,whi[0])]:ops.append({'id':oid+'_crop_'+tag,'part':'observed_shadow_tile_extensions','action':'cut','selector':{'feature':oid},'shape':{'kind':'box','min':[left,wlo[1],wlo[2]],'max':[right,whi[1],whi[2]]}})
  links.append({'operation':oid,'source':reg,'material':f'top_tile_{color:02d}','horizontal_footprint_xz':[x0,z0,x1,z1],'geometry_prior_identical_to_r02':True})
 a=np.load(F/'foundation_arrays.npz');occ=a['occupancy'];mat=a['materials'];own=np.load(OLD/'ownership_arrays.npz');kept=own['kept_occupancy'];image=np.asarray(Image.open(IMAGE).convert('RGB'));edge_blocks=[];edge_links=[]
 for view,zmin,zmax,zs in [('front',4.625,5.,range(77,80)),('back',-5.,-4.625,range(0,3))]:
  for y in range(76,112):
   for x in range(96):
    X=(x-48+.5)*.125;Y=(y+.5)*.125;line=ridge-slope*abs(X)
    if not(line-.65<=Y<=line+.125 and .25<abs(X)<6):continue
    original=[z for z in zs if kept[y,x,z] and 0<=mat[y,x,z]<=3]
    if not original:continue
    assert list(original)==list(zs),'Mixed depth ownership requires explicit split'
    u=64+x*4 if view=='front' else 1088+(95-x)*4;v=496-(y+1)*4;pix=image[v:v+4,u:u+4];fg=foreground(pix)
    edge_blocks.append({'view':view,'source_yx':[y,x],'original_z_cells':original,'source_box_px':[u,v,u+4,v+4],'foreground_pixels':int(fg.sum()),'background_pixels':int((~fg).sum())})
    for dv,du in np.argwhere(fg):
     wx=(x-48)*.125+(int(du)if view=='front'else 3-int(du))*P;wy=y*.125+(3-int(dv))*P;rgb=pix[dv,du].astype(float);ci=int(np.argmin(((color_rgb-rgb)**2).sum(1)));oid=f'edge_{view}_y{y}_x{x}_v{dv}_u{du}'
     ops.append({'id':oid,'part':'foreground_resampled_gable_edge','action':'paint','material':color_names[ci],'shape':{'kind':'box','min':[wx,wy,zmin],'max':[wx+P,wy+P,zmax]}})
     edge_links.append({'operation':oid,'view':view,'source_pixel_uv':[u+int(du),v+int(dv)],'source_rgb':rgb.astype(int).tolist(),'source_parent_yx':[y,x],'material':color_names[ci],'foreground_rule_identical_to_original_reconstruct':True})
 assert len(edge_blocks)==46 and all(sum(b['view']==v for b in edge_blocks)==23 for v in ('front','back'))
 master={'schema':core.SCHEMA,'id':'architecture_A_roof_repair_r03_delta','revision':3,'axes':legacy['axes'],'grid_origin':[0,0,0],'materials':materials,'components':[{'id':'roof_source_delta','parts':[{'id':p,'pivot':[0,0,0]}for p in ['observed_shadow_tile_extensions','foreground_resampled_gable_edge']],'operations':ops}],'instances':[{'id':'roof_source_delta','component':'roof_source_delta'}],'assembly_cuts':[],'constraints':[{'id':'nonempty_delta','kind':'nonempty'}],'metadata':{'diagnostic_only':True,'production_gate_open':False,'original_global_registration_accepted':False,'brightness_to_height':False,'thin_tile_prior_unchanged_from_r02':True,'measured_gable_slope':slope,'original_max_y':ridge,'local_pitch_m':P,'new_regions_observed_only':15,'true_occluder_auto_filled':False,'existing_facade_depth_prior_m':.375}}
 core.validate_master(master,P);mr=write('roof_patch.master.json.gz',master);pp=sampler.prepare_master(master,{'pitch':P})
 plan={'schema':'riverstone.image_roof_repair.plan.v3','source_dependencies':deps,'master':mr,'driver':ref(Path(__file__)),'reused_roof_compilation':ref(OLD/'compile.json'),'restoration_rule':'Only empty r02 fine cells that descend from occupied original source cells and whose centers are below the exact existing backing bottom Y=13.875-slope*abs(X)-.1875. No invented fill, no source bounds expansion.','backing_bottom_offset_m':-.1875,'tile_source_links':links,'edge_blocks':edge_blocks,'edge_source_links':edge_links,'foreground_color_rule':'Nearest RGB in unchanged original pixel palette plus existing six source TOP colors, selected from the actual individual source foreground pixel. No light-color blanket removal.','edge_sampling_pitch_m':P,'existing_edge_depth_prior_m':.375,'tile_geometry_prior_unchanged':True,'expected_delta_cells_upper_bound':100000,'max_candidate_cells':1000000,'prepared_plan_key':pp.plan_key,'prepared_provenance':dict(pp.provenance),'whole_house_highres_compile':False,'source_modifications':False,'elapsed_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 assert deps==pins();write('plan.json',plan);print(json.dumps({'status':'PREPARED','source_edge_blocks':len(edge_blocks),'foreground_pixel_boxes':len(edge_links),'new_observed_tile_regions':len(links),'operations':len(ops),'seconds':plan['elapsed_seconds']}),flush=True)
def compile_delta():
 t=time.monotonic();plan=read(H/'plan.json');assert plan['source_dependencies']==pins();master=read(H/'roof_patch.master.json.gz');pp=sampler.prepare_master(master,{'pitch':P});assert pp.plan_key==plan['prepared_plan_key']
 c=sampler.compile_prepared(pp,cell_bounds={'min':[-202,300,-164],'max':[202,448,164]},max_candidate_cells=1000000,max_output_cells=100000);assert c['valid'];r=write('compiled/delta.json.gz',c)
 write('compile.json',{'schema':'riverstone.roof_source_delta.compile.v1','status':'PASS_BOUNDED_DELTA','reused_roof_compile':ref(OLD/'compile.json'),'delta':r,'cells':len(c['cells']),'candidates':c['candidate_cells'],'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'no_prior_roof_resampling':True,'source_dependencies_unchanged':plan['source_dependencies']==pins()});print(json.dumps(read(H/'compile.json')),flush=True)
if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(30,)*2)
 p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--compile',action='store_true');a=p.parse_args()
 if a.prepare:prepare()
 if a.compile:compile_delta()
