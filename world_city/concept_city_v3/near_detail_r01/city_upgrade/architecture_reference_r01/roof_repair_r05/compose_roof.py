"""Halo-keyed common mesher, resumable bounded chunk work, then streaming assembly."""
from author_isolated_tiles import *
import numpy as np

def clip(q,axis,low,high):
 a=[q[1][i]-q[0][i]for i in range(3)];b=[q[2][i]-q[0][i]for i in range(3)];n=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];direction=max(range(3),key=lambda i:abs(n[i]))
 if direction==axis:return q if low<=round(q[0][axis]/P)-(1 if n[axis]>0 else 0)<high else None
 lo=max(min(p[axis]for p in q),low*P);hi=min(max(p[axis]for p in q),high*P)
 if hi-lo<1e-9:return None
 out=[list(p)for p in q]
 for p in out:p[axis]=max(lo,min(hi,p[axis]))
 return out

def cachepath(c):return R/c['original_cache']['path']if c['reuse_exact_cache']else H/f"mesh_cache/chunk_{c['index']:03d}.json.gz"
def verify(c,cache):
 assert cache['owned_z_cells']==c['owned_z_cells']and cache['mesher_sha256']==sha(Path(render_data.mesh.__file__))
 assert cache['upper_union_sha256']==(c['original_cache_union_sha256']if c['reuse_exact_cache']else sha(H/'upper_union_arrays.npz'))
 if c['reuse_exact_cache']:assert sha(cachepath(c))==c['original_cache']['sha256']and c['r04_halo_material_sha256']==c['r05_halo_material_sha256']
def mesh_batch():
 t=time.monotonic();plan=read(H/'plan.json');assert plan['source_dependencies']==pins();cp=read(H/'cache_plan.json');d=np.load(H/'upper_union_arrays.npz');arr=d['materials'];lo=d['origin_cell_xyz'];names=d['material_names'].tolist();materials=read(H/'roof_patch.master.json.gz')['materials'];masterhash=core.digest({'base':sha(F/'foundation_revised.master.json.gz'),'roof':sha(H/'roof_patch.master.json.gz')});done=0;records=[]
 for c in cp['chunks']:
  path=cachepath(c)
  if path.exists():
   cache=read(path);verify(c,cache);del cache;continue
  if time.monotonic()-t>85:break
  start=time.monotonic();za,zb=c['halo_z_cells'];z0,z1=c['owned_z_cells'];sl=arr[:,:,za-lo[2]:zb-lo[2]];assert hashlib.sha256(sl.tobytes()).hexdigest()==c['r05_halo_material_sha256'];pos=np.argwhere(sl>=0)
  rows=[[int(ix+lo[0]),int(iy+lo[1]),int(iz+za),'upper_union','roof_and_source',names[int(sl[iy,ix,iz])],'actual_union_cell']for iy,ix,iz in pos]
  compiled={'schema':'riverstone.voxel.compiled.v1','valid':True,'pitch':P,'grid_origin':[0,0,0],'materials':materials,'cells':rows,'source_id':'architecture_A_roof_repair_r05','source_revision':5,'master_hash':masterhash,'payload_hash':core.digest(rows),'compiler_source_hash':sha(Path(core.__file__))};mesh=render_data.make_render_data(compiled);groups={}
  for g in mesh['groups']:
   for q in g['quads']:
    nq=clip(q,1,round(JOIN/P),448)
    if nq is not None:nq=clip(nq,2,z0,z1)
    if nq is not None:groups.setdefault(g['material'],[]).append(nq)
  rec={'index':c['index'],'owned_z_cells':[z0,z1],'halo_z_cells':[za,zb],'union_cells_with_halo':len(rows),'exported_quads':mesh['quad_count'],'owned_quads':sum(map(len,groups.values())),'seconds':time.monotonic()-start}
  write(str(path.relative_to(H)),{'upper_union_sha256':sha(H/'upper_union_arrays.npz'),'owned_z_cells':[z0,z1],'mesher_sha256':sha(Path(render_data.mesh.__file__)),'halo_material_sha256':c['r05_halo_material_sha256'],'groups':[{'material':m,'quads':qs}for m,qs in sorted(groups.items())],'record':rec});done+=1;records.append(rec);print(json.dumps(rec),flush=True);del compiled,mesh,rows,pos,groups;gc.collect()
 remaining=sum(not cachepath(c).exists()for c in cp['chunks']);result={'status':'MESH_READY'if remaining==0 else 'RESUMABLE_PARTIAL','chunks_completed_this_process':done,'remaining':remaining,'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'records':records,'source_dependencies_unchanged':plan['source_dependencies']==pins()};assert result['source_dependencies_unchanged'];n=len(list(H.glob('mesh_batch_*.json')));write(f'mesh_batch_{n:02d}.json',result);print(json.dumps({k:v for k,v in result.items()if k!='records'}),flush=True)
def assemble():
 t=time.monotonic();plan=read(H/'plan.json');assert plan['source_dependencies']==pins();cp=read(H/'cache_plan.json');groups={};base=read(F/'foundation_repaired.render.json.gz');lower_kept=lower_clipped=0
 for g in base['groups']:
  for q in g['quads']:
   nq=clip(q,1,-10000,round(JOIN/P))
   if nq is not None:groups.setdefault(g['material'],[]).append(nq);lower_kept+=int(nq==q);lower_clipped+=int(nq!=q)
 materials=base['materials']|read(H/'roof_patch.master.json.gz')['materials'];del base;gc.collect();records=[]
 for c in cp['chunks']:
  path=cachepath(c);cache=read(path);verify(c,cache)
  for g in cache['groups']:groups.setdefault(g['material'],[]).extend(g['quads'])
  records.append({**cache['record'],'cache_reference':ref(path),'reused_previous_cache':c['reuse_exact_cache']});del cache;gc.collect()
 n=sum(map(len,groups.values()));bounds={'min':[min(p[i]for qs in groups.values()for q in qs for p in q)for i in range(3)],'max':[max(p[i]for qs in groups.values()for q in qs for p in q)for i in range(3)]};uv=read(H/'union_validation.json');keep=np.load(F/'foundation_arrays.npz')['occupancy'];render={'schema':'riverstone.voxel.render.v1','unit':'m','source_id':'architecture_A_roof_repair_r05','source_revision':5,'master_hash':core.digest({'base':sha(F/'foundation_revised.master.json.gz'),'roof':sha(H/'roof_patch.master.json.gz')}),'payload_hash':core.digest({'base_render':sha(F/'foundation_repaired.render.json.gz'),'upper_union':sha(H/'upper_union_arrays.npz')}),'pitch':P,'grid_origin':[0,0,0],'materials':materials,'cell_count':int(keep[:76].sum())+uv['new_union_occupied_cells'],'bounds':bounds,'groups':[{'material':m,'quads':groups[m]}for m in sorted(groups)],'quad_count':n,'geometry':'Existing common mesh of frozen r04 plus previously lost exact source tile cells. Each existing tile paint and cuts execute in an isolated component/instance. No new measured tile, support, chimney, body or foundation shape.','provenance':{'base_render':ref(F/'foundation_repaired.render.json.gz'),'roof_master':ref(H/'roof_patch.master.json.gz'),'compiled_index':ref(H/'compile.json'),'ownership':ref(H/'plan.json'),'previous_roof_render':ref(OLD/'roof_repaired.render.json.gz'),'source_delta_proof':ref(H/'union_validation.json'),'cache_plan':ref(H/'cache_plan.json'),'upper_union':ref(H/'upper_union_arrays.npz'),'driver':ref(Path(__file__)),'common_mesher':ref(Path(render_data.mesh.__file__)),'common_exporter':ref(Path(render_data.__file__)),'diagnostic_only':True,'production_gate_open':False,'original_global_registration_accepted':False,'chimney_depth_is_explicit_prior':True,'underside_validated':False,'frozen_r04_normal_sidecar_forbidden':True}}
 rawhash=hashlib.sha256();rawlen=0
 for s in json.JSONEncoder(separators=(',',':'),allow_nan=False).iterencode(render):b=s.encode();rawhash.update(b);rawlen+=len(b)
 rr=write('roof_repaired.render.json.gz',render);ch=hashlib.sha256();size=0
 with gzip.open(H/'roof_repaired.render.json.gz','rb')as f:
  for b in iter(lambda:f.read(65536),b''):ch.update(b);size+=len(b)
 assert ch.hexdigest()==rawhash.hexdigest()and size==rawlen
 result={'schema':'riverstone.image_roof_repair.composition.v5','render':rr,'raw_sha256':ch.hexdigest(),'raw_bytes':size,'gzip_bytes':(H/'roof_repaired.render.json.gz').stat().st_size,'roundtrip_verified':True,'quad_count':n,'bounds':bounds,'chunks':records,'lower_original_quads_kept':lower_kept,'lower_original_quads_clipped_at_join':lower_clipped,'exact_prior_cache_reused':cp['exact_reused'],'new_common_mesh_cache_count':cp['rebuild_required'],'sample_calls_during_composition':0,'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_visual_gate':'PENDING_PARENT_GUI','source_dependencies_unchanged':plan['source_dependencies']==pins()};assert result['source_dependencies_unchanged'];write('composition.json',result);print(json.dumps({k:v for k,v in result.items()if k!='chunks'}),flush=True)
if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(120,)*2);p=argparse.ArgumentParser();p.add_argument('--mesh-batch',action='store_true');p.add_argument('--assemble',action='store_true');a=p.parse_args()
 if a.mesh_batch:mesh_batch()
 if a.assemble:assemble()
