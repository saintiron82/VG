"""Reuse unchanged source solids; isolate each tile's feature cuts in its own instance."""
from pathlib import Path
import argparse,copy,gc,gzip,hashlib,itertools,json,math,os,resource,sys,time
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
R=next(p for p in Path(__file__).resolve().parents if (p/'voxel_character/common/core.py').exists());sys.path.insert(0,str(R))
from voxel_character.common import core,prepared_sampling_v3 as sampler,render_data
H=Path(__file__).resolve().parent;A=H.parent;OLD=A/'roof_repair_r04';F=A/'foundation_repair_r01';P=.03125;JOIN=9.5

def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(65536),b''):h.update(b)
 return h.hexdigest()
def ref(p):return {'path':str(p.relative_to(R)),'sha256':sha(p)}
def read(p):
 with gzip.open(p,'rt')if p.suffix=='.gz'else p.open()as f:return json.load(f)
def write(name,value):
 p=H/name;assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.pending');assert not tmp.exists()
 with tmp.open('xb')as raw:
  output=gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0)if p.suffix=='.gz'else raw
  try:
   for s in json.JSONEncoder(separators=(',',':'),allow_nan=False).iterencode(value):output.write(s.encode())
  finally:
   if output is not raw:output.close()
 tmp.rename(p);return ref(p)
def pins():
 ps=[OLD/'upper_union_arrays.npz',OLD/'roof_repaired.render.json.gz',OLD/'plan.json',OLD/'compile.json',OLD/'cache_plan.json',OLD/'composition.json',A/'roof_repair_r02/roof_patch.master.json.gz',A/'roof_repair_r02/compile.json',A/'roof_repair_r03/roof_patch.master.json.gz',A/'roof_repair_r03/compile.json',A/'roof_repair_r03/delta_ownership_arrays.npz',F/'foundation_arrays.npz',F/'foundation_repaired.render.json.gz',F/'foundation_revised.master.json.gz',A/'roof_backing_measurement_r01/source_ordering_audit.json',Path(core.__file__),Path(sampler.__file__),Path(render_data.__file__),Path(render_data.mesh.__file__)]
 return {str(p.relative_to(R)):sha(p)for p in ps}
def source_tiles():
 out=[];mats={};base=None
 for revision,part in [(2,'measured_tile_regions'),(3,'observed_shadow_tile_extensions')]:
  path=A/f'roof_repair_r0{revision}/roof_patch.master.json.gz';m=read(path);base=base or m;mats.update(m['materials']);ops=m['components'][0]['operations'];byid={o['id']:o for o in ops}
  for op in ops:
   if op['part']!=part or op['action']!='paint':continue
   cuts=[byid[op['id']+'_crop_'+s]for s in ['left','right']]
   assert all(c['selector']=={'feature':op['id']}for c in cuts)
   out.append((revision,path,[op]+cuts))
 assert len(out)==354
 return base,mats,out

def prepare():
 t=time.monotonic();deps=pins();base,mats,tiles=source_tiles();components=[];instances=[];links=[];candidate_bound=0
 for rev,path,ops in tiles:
  ident='tile_'+ops[0]['id'];components.append({'id':ident,'parts':[{'id':ops[0]['part'],'pivot':[0,0,0]}],'operations':copy.deepcopy(ops)});instances.append({'id':ident,'component':ident});ranges=[]
  for op in ops:
   s=core.prepare_shape(op['shape'],P);lo,hi=core.shape_bounds(s);tr=core.transform(op.get('transform'));cs=[core.apply(tr,p)for p in itertools.product(*zip(lo,hi))];low=[min(p[k]for p in cs)for k in range(3)];high=[max(p[k]for p in cs)for k in range(3)];rs=[[math.floor(a/P+core.EPS),math.ceil(b/P-core.EPS)]for a,b in zip(low,high)];candidate_bound+=math.prod(b-a for a,b in rs);ranges.append(rs)
  links.append({'source_revision':rev,'source_master':ref(path),'source_feature':ops[0]['id'],'component':ident,'instance':ident,'operations_sha256':core.digest(ops),'candidate_index_bounds_xyz':ranges})
 master={'schema':core.SCHEMA,'id':'architecture_A_roof_repair_r05_isolated_tiles','revision':5,'axes':base['axes'],'grid_origin':[0,0,0],'materials':mats,'components':components,'instances':instances,'assembly_cuts':[],'constraints':[],'metadata':{'diagnostic_only':True,'production_gate_open':False,'original_global_registration_accepted':False,'brightness_to_height':False,'local_pitch_m':P,'unchanged_source_tiles':354,'new_measured_regions':0,'tile_operations_byte_semantics_unchanged':True,'change':'Only component/instance ownership. Each exact existing paint and its feature cuts execute locally before instance union.'}}
 core.validate_master(master,P);mr=write('roof_patch.master.json.gz',master);plan=sampler.prepare_master(master,{'pitch':P});edges=list(range(-164,164,16))+[164]
 report={'schema':'riverstone.roof.isolated_source_tiles.plan.v1','source_dependencies':deps,'master':mr,'driver':ref(Path(__file__)),'tile_count':354,'operation_count':1062,'source_tile_links':links,'prepared_plan_key':plan.plan_key,'candidate_cells_transformed_AABB_sum':candidate_bound,'compile_owned_z_edges':edges,'compile_bounds_x_y':[[-200,200],[300,448]],'max_output_cells_per_chunk':150000,'max_candidate_cells_per_chunk':1000000,'source_geometry_material_transform_changes':0,'new_measured_regions':0,'new_roof_pitch_m':P,'normal_sidecar_binding_allowed':False,'normal_reason':'Changed render/group geometry requires newly derived render-hash-bound normals; frozen r04 sidecar must not bind.','preserve_base':'Frozen r04 union; only proven previously lost tile cells may add or replace original support cells. Existing tiles, finite chimney, original body/foundation, r03 foreground and r04 ownership cells remain protected.','planned_process_caps':{'author_compile_AS_MiB':256,'author_compile_CPU_seconds':120,'meshing_AS_MiB':512,'meshing_CPU_seconds_per_resume':120,'per_chunk_cache':True},'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 assert deps==pins();write('plan.json',report);print(json.dumps({k:v for k,v in report.items()if k not in ['source_dependencies','source_tile_links']}),flush=True)
def compile_tiles():
 t=time.monotonic();p=read(H/'plan.json');assert p['source_dependencies']==pins();master=read(H/'roof_patch.master.json.gz');plan=sampler.prepare_master(master,{'pitch':P});assert plan.plan_key==p['prepared_plan_key'];chunks=[];edges=p['compile_owned_z_edges']
 for i,(z0,z1)in enumerate(zip(edges,edges[1:])):
  dest=H/f'compiled/chunk_{i:02d}.json.gz';bounds={'min':[-200,300,z0],'max':[200,448,z1]};start=time.monotonic()
  if dest.exists():
   c=read(dest);assert c['master_hash']==core.digest(master)and c['evaluation_scope']=={'kind':'cell_bounds',**bounds};reuse=True
  else:
   c=sampler.compile_prepared(plan,cell_bounds=bounds,max_candidate_cells=1000000,max_output_cells=150000);assert c['valid'];write(str(dest.relative_to(H)),c);reuse=False
  row={'index':i,'owned_z_cells':[z0,z1],'compiled':ref(dest),'cells':len(c['cells']),'candidates':c['candidate_cells'],'reused_exact_cache':reuse,'seconds':time.monotonic()-start};chunks.append(row);print(json.dumps(row),flush=True);del c;gc.collect()
 assert p['source_dependencies']==pins();write('compile.json',{'schema':'riverstone.roof.isolated_tiles.compile.v1','status':'PASS','chunks':chunks,'cells':sum(c['cells']for c in chunks),'candidates':sum(c['candidates']for c in chunks),'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'source_dependencies_unchanged':True,'support_chimney_body_resampling':False,'new_regions':0})
if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(120,)*2);p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--compile',action='store_true');a=p.parse_args()
 if a.prepare:prepare()
 if a.compile:compile_tiles()
