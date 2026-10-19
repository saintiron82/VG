"""Bounded fine roof union; exact untouched coarse lower house surface."""
from pathlib import Path
import gc,gzip,hashlib,json,os,resource,time
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from author_roof import R,H,F,Q,P,JOIN,sha,ref,read,write,pins,core,render_data

def clip(q,axis,low,high):
 # Exact scalar equivalent of prior axis-aligned common-quad ownership clip.
 a=[q[1][i]-q[0][i] for i in range(3)];b=[q[2][i]-q[0][i] for i in range(3)]
 normal=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
 direction=max(range(3),key=lambda i:abs(normal[i]))
 if direction==axis:
  owner=round(q[0][axis]/P)-(1 if normal[axis]>0 else 0)
  return q if low<=owner<high else None
 lo=max(min(p[axis]for p in q),low*P);hi=min(max(p[axis]for p in q),high*P)
 if hi-lo<1e-9:return None
 out=[list(p)for p in q]
 for p in out:p[axis]=max(lo,min(hi,p[axis]))
 return out

def stream_write(name,value):
 target=H/name;assert not target.exists(),target;target.parent.mkdir(parents=True,exist_ok=True)
 temporary=target.with_name(target.name+'.pending');assert not temporary.exists()
 digest=hashlib.sha256();size=0
 with temporary.open('xb')as raw:
  with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0)as output:
   for token in json.JSONEncoder(separators=(',',':'),allow_nan=False).iterencode(value):
    data=token.encode();output.write(data);digest.update(data);size+=len(data)
 # Streaming byte roundtrip; no second full JSON string/object allocation.
 check=hashlib.sha256();decoded_size=0
 with gzip.open(temporary,'rb')as input_:
  while True:
   block=input_.read(65536)
   if not block:break
   check.update(block);decoded_size+=len(block)
 assert check.digest()==digest.digest()and decoded_size==size
 assert sum(p.stat().st_size for p in H.rglob('*')if p.is_file())<15_000_000
 temporary.rename(target)
 return {**ref(target),'uncompressed_sha256':digest.hexdigest(),'uncompressed_bytes':size,'gzip_byte_roundtrip_verified':True}

def main():
 started=time.monotonic();plan=read(H/'plan.json');assert plan['source_dependencies']==pins();compilation=read(H/'compile.json');base=read(F/'foundation_repaired.render.json.gz');master=read(H/'roof_patch.master.json.gz')
 materials=dict(base['materials']);materials.update(master['materials']);names=list(materials);ids={n:i for i,n in enumerate(names)}
 del base,master;gc.collect()
 a=np.load(H/'ownership_arrays.npz');keep=a['kept_occupancy']
 data=np.load(H/'upper_union_arrays.npz');arr=data['materials'];lo=data['origin_cell_xyz'];hi=lo+np.array([arr.shape[1],arr.shape[0],arr.shape[2]])
 assert data['material_names'].tolist()==names and float(data['pitch_m'])==P
 feature_stats=read(H/'feature_union_counts.json')['counts_compiled_and_inserted'];inserted=sum(v[1]for v in feature_stats.values());blocked=sum(v[0]-v[1]for v in feature_stats.values())
 base=read(F/'foundation_repaired.render.json.gz')
 groups={};lower_kept=lower_clipped=0
 for g in base['groups']:
  for q in g['quads']:
   new=clip(q,1,-10000,round(JOIN/P))
   if new is not None:groups.setdefault(g['material'],[]).append(new);lower_kept+=int(new==q);lower_clipped+=int(new!=q)
 del base;gc.collect()
 # Adapt only execution partitions to actual union demand; cell geometry,
 # predicates, materials and shared mesher are fixed independently of chunks.
 counts=(arr>=0).sum(axis=(0,1));edges=[int(lo[2])];accum=0
 for iz,count in enumerate(counts):
  if accum and accum+count>35000:edges.append(int(lo[2]+iz));accum=0
  accum+=int(count)
 edges.append(int(hi[2]));chunks=[]
 for index,(z0,z1) in enumerate(zip(edges,edges[1:])):
  cache_path=H/f'mesh_cache/chunk_{index:03d}.json.gz'
  if cache_path.exists():
   cache=read(cache_path);assert cache['upper_union_sha256']==sha(H/'upper_union_arrays.npz')and cache['owned_z_cells']==[z0,z1]and cache['mesher_sha256']==sha(Path(render_data.mesh.__file__))
   for g in cache['groups']:groups.setdefault(g['material'],[]).extend(g['quads'])
   chunks.append(cache['record']);print(json.dumps({'reused_exact_mesh_cache':index}),flush=True);del cache;gc.collect();continue
  t=time.monotonic();za=max(int(lo[2]),z0-1);zb=min(int(hi[2]),z1+1);sl=arr[:,:,za-lo[2]:zb-lo[2]];positions=np.argwhere(sl>=0)
  rows=[[int(ix+lo[0]),int(iy+lo[1]),int(iz+za),'upper_union','roof_and_source',names[int(sl[iy,ix,iz])],'actual_union_cell']for iy,ix,iz in positions]
  c={'schema':'riverstone.voxel.compiled.v1','valid':True,'pitch':P,'grid_origin':[0,0,0],'materials':materials,'cells':rows,'source_id':'architecture_A_roof_repair_r02','source_revision':2,'master_hash':core.digest({'base':sha(F/'foundation_revised.master.json.gz'),'roof':sha(H/'roof_patch.master.json.gz')}),'payload_hash':core.digest(rows),'compiler_source_hash':sha(Path(core.__file__))}
  local=render_data.make_render_data(c);owned=0;owned_groups={}
  for g in local['groups']:
   for q in g['quads']:
    new=clip(q,1,round(JOIN/P),int(hi[1]))
    if new is not None:new=clip(new,2,z0,z1)
    if new is not None:groups.setdefault(g['material'],[]).append(new);owned_groups.setdefault(g['material'],[]).append(new);owned+=1
  chunks.append({'owned_z_cells':[z0,z1],'halo_z_cells':[za,zb],'union_cells_with_halo':len(rows),'exported_quads':local['quad_count'],'owned_quads':owned,'seconds':time.monotonic()-t});print(json.dumps(chunks[-1]),flush=True)
  stream_write(f'mesh_cache/chunk_{index:03d}.json.gz',{'upper_union_sha256':sha(H/'upper_union_arrays.npz'),'owned_z_cells':[z0,z1],'mesher_sha256':sha(Path(render_data.mesh.__file__)),'groups':[{'material':m,'quads':qs}for m,qs in sorted(owned_groups.items())],'record':chunks[-1]})
  del owned_groups
  del positions,rows,c,local;gc.collect()
 n=sum(len(qs)for qs in groups.values());bounds={'min':[min(p[i]for qs in groups.values()for q in qs for p in q)for i in range(3)],'max':[max(p[i]for qs in groups.values()for q in qs for p in q)for i in range(3)]}
 render={'schema':'riverstone.voxel.render.v1','unit':'m','source_id':'architecture_A_roof_repair_r02','source_revision':2,'master_hash':core.digest({'base':sha(F/'foundation_revised.master.json.gz'),'roof':sha(H/'roof_patch.master.json.gz')}),'payload_hash':core.digest({'base_render':sha(F/'foundation_repaired.render.json.gz'),'upper_union':sha(H/'upper_union_arrays.npz')}),'pitch':P,'grid_origin':[0,0,0],'materials':materials,'cell_count':int(keep[:76].sum())+int((arr[4:]>=0).sum()),'bounds':bounds,'groups':[{'material':m,'quads':groups[m]}for m in sorted(groups)],'quad_count':n,'geometry':'Common mesher exterior of source-priority exact bounded upper union; original lower .125m render identical; roof-only .03125m sampling.','provenance':{'base_render':ref(F/'foundation_repaired.render.json.gz'),'roof_master':ref(H/'roof_patch.master.json.gz'),'compiled_index':ref(H/'compile.json'),'ownership':ref(H/'ownership_arrays.npz'),'upper_union':ref(H/'upper_union_arrays.npz'),'driver':ref(Path(__file__)),'common_mesher':ref(Path(render_data.mesh.__file__)),'common_exporter':ref(Path(render_data.__file__)),'diagnostic_only':True,'production_gate_open':False,'original_global_registration_accepted':False,'chimney_depth_is_explicit_prior':True,'underside_validated':False}}
 renderref=stream_write('roof_repaired.render.json.gz',render);assert plan['source_dependencies']==pins()
 report={'schema':'riverstone.image_roof_repair.composition.v2','render':renderref,'quad_count':n,'bounds':bounds,'fine_upper_occupied_cells':int((arr[4:]>=0).sum()),'new_roof_cells_inserted':inserted,'new_roof_cells_blocked_by_unchanged_source':blocked,'lower_original_quads_kept':lower_kept,'lower_original_quads_clipped_at_join':lower_clipped,'mesher_chunk_edges_z':edges,'chunks':chunks,'common_mesher_calls':len(chunks),'sampling_calls':0,'whole_house_highres_compile':False,'elapsed_seconds':time.monotonic()-started,'final_writer':'standard_JSONEncoder_iterencode_to_gzip_mtime0','mesh_chunks_cached_immediately':True,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'generated_bytes':sum(p.stat().st_size for p in H.rglob('*')if p.is_file()),'actual_six_view_and_oblique_review':'PENDING_PARENT_GUI','source_dependencies_unchanged':True}
 write('composition.json',report);print(json.dumps({k:v for k,v in report.items()if k!='chunks'}),flush=True)
if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(180,)*2)
 started=time.monotonic();status='RUNNING';error=None
 try:
  main();status='PASS'
 except BaseException as exc:
  status='FAILED';error=repr(exc);raise
 finally:
  metrics={'status':status,'error':error,'as_limit_mib':512,'cpu_limit_seconds':180,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'seconds':time.monotonic()-started,'sampling_calls':0,'uses_preserved_upper_union':True}
  write('compose_r04_metrics.json',metrics)
