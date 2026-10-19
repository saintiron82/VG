"""Bounded fine roof union; exact untouched coarse lower house surface."""
from pathlib import Path
import gc,json,os,resource,time
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from author_roof import R,H,F,Q,P,JOIN,sha,ref,read,write,pins,core,render_data

def clip(q,axis,low,high):
 a=np.asarray(q);n=np.cross(a[1]-a[0],a[2]-a[0]);direction=int(np.argmax(abs(n)))
 if direction==axis:
  owner=round(q[0][axis]/P)-(1 if n[axis]>0 else 0)
  return q if low<=owner<high else None
 lo=max(float(a[:,axis].min()),low*P);hi=min(float(a[:,axis].max()),high*P)
 if hi-lo<1e-9:return None
 out=[list(p)for p in q]
 for p in out:p[axis]=max(lo,min(hi,p[axis]))
 return out

def main():
 started=time.monotonic();plan=read(H/'plan.json');assert plan['source_dependencies']==pins();compilation=read(H/'compile.json');base=read(F/'foundation_repaired.render.json.gz');master=read(H/'roof_patch.master.json.gz')
 materials=dict(base['materials']);materials.update(master['materials']);names=list(materials);ids={n:i for i,n in enumerate(names)}
 a=np.load(H/'ownership_arrays.npz');keep=a['kept_occupancy'];km=a['kept_materials'];lo=np.array([-200,300,-164],int);hi=np.array([200,448,164],int);dims=hi-lo
 arr=np.full((dims[1],dims[0],dims[2]),-1,np.int16)
 oldnames=[]
 for i in range(15):
  values=[n for n in base['materials']if int(n.rsplit('_',1)[1])+(12 if n.startswith('stone')else 0)==i];assert len(values)==1;oldnames.append(values[0])
 lookup=np.array([ids[n]for n in oldnames],np.int16);coarse=np.where(keep[75:],lookup[np.maximum(km[75:],0)],-1)
 for dy in range(4):
  for dx in range(4):
   for dz in range(4):arr[dy:148:4,8+dx:392:4,4+dz:324:4]=coarse
 del coarse;retained=arr>=0;inserted=blocked=0;feature_stats={}
 for record in compilation['chunks']:
  c=read(R/record['compiled']['path']);assert sha(R/record['compiled']['path'])==record['compiled']['sha256'];assert core.digest(c['cells'])==c['payload_hash']
  for x,y,z,instance,part,material,feature in c['cells']:
   iy,ix,iz=y-lo[1],x-lo[0],z-lo[2];assert 0<=iy<arr.shape[0]and 0<=ix<arr.shape[1]and 0<=iz<arr.shape[2]
   s=feature_stats.setdefault(feature,[0,0]);s[0]+=1
   if arr[iy,ix,iz]<0:arr[iy,ix,iz]=ids[material];inserted+=1;s[1]+=1
   else:blocked+=1
  del c;gc.collect()
 np.savez_compressed(H/'upper_union_arrays.npz',materials=arr,retained_baseline=retained,origin_cell_xyz=lo,pitch_m=np.array(P),material_names=np.array(names),join_y_m=np.array(JOIN))
 write('feature_union_counts.json',{'counts_compiled_and_inserted':feature_stats,'retained_source_has_priority':True})
 groups={};lower_kept=lower_clipped=0
 for g in base['groups']:
  for q in g['quads']:
   new=clip(q,1,-10000,round(JOIN/P))
   if new is not None:groups.setdefault(g['material'],[]).append(new);lower_kept+=int(new==q);lower_clipped+=int(new!=q)
 del base,retained;gc.collect()
 # Adapt only execution partitions to actual union demand; cell geometry,
 # predicates, materials and shared mesher are fixed independently of chunks.
 counts=(arr>=0).sum(axis=(0,1));edges=[int(lo[2])];accum=0
 for iz,count in enumerate(counts):
  if accum and accum+count>35000:edges.append(int(lo[2]+iz));accum=0
  accum+=int(count)
 edges.append(int(hi[2]));chunks=[]
 for z0,z1 in zip(edges,edges[1:]):
  t=time.monotonic();za=max(int(lo[2]),z0-1);zb=min(int(hi[2]),z1+1);sl=arr[:,:,za-lo[2]:zb-lo[2]];positions=np.argwhere(sl>=0)
  rows=[[int(ix+lo[0]),int(iy+lo[1]),int(iz+za),'upper_union','roof_and_source',names[int(sl[iy,ix,iz])],'actual_union_cell']for iy,ix,iz in positions]
  c={'schema':'riverstone.voxel.compiled.v1','valid':True,'pitch':P,'grid_origin':[0,0,0],'materials':materials,'cells':rows,'source_id':'architecture_A_roof_repair_r02','source_revision':2,'master_hash':core.digest({'base':sha(F/'foundation_revised.master.json.gz'),'roof':sha(H/'roof_patch.master.json.gz')}),'payload_hash':core.digest(rows),'compiler_source_hash':sha(Path(core.__file__))}
  local=render_data.make_render_data(c);owned=0
  for g in local['groups']:
   for q in g['quads']:
    new=clip(q,1,round(JOIN/P),int(hi[1]))
    if new is not None:new=clip(new,2,z0,z1)
    if new is not None:groups.setdefault(g['material'],[]).append(new);owned+=1
  chunks.append({'owned_z_cells':[z0,z1],'halo_z_cells':[za,zb],'union_cells_with_halo':len(rows),'exported_quads':local['quad_count'],'owned_quads':owned,'seconds':time.monotonic()-t});print(json.dumps(chunks[-1]),flush=True)
  del positions,rows,c,local;gc.collect()
 n=sum(len(qs)for qs in groups.values());bounds={'min':[min(p[i]for qs in groups.values()for q in qs for p in q)for i in range(3)],'max':[max(p[i]for qs in groups.values()for q in qs for p in q)for i in range(3)]}
 render={'schema':'riverstone.voxel.render.v1','unit':'m','source_id':'architecture_A_roof_repair_r02','source_revision':2,'master_hash':core.digest({'base':sha(F/'foundation_revised.master.json.gz'),'roof':sha(H/'roof_patch.master.json.gz')}),'payload_hash':core.digest({'base_render':sha(F/'foundation_repaired.render.json.gz'),'upper_union':sha(H/'upper_union_arrays.npz')}),'pitch':P,'grid_origin':[0,0,0],'materials':materials,'cell_count':int(keep[:76].sum())+int((arr[4:]>=0).sum()),'bounds':bounds,'groups':[{'material':m,'quads':groups[m]}for m in sorted(groups)],'quad_count':n,'geometry':'Common mesher exterior of source-priority exact bounded upper union; original lower .125m render identical; roof-only .03125m sampling.','provenance':{'base_render':ref(F/'foundation_repaired.render.json.gz'),'roof_master':ref(H/'roof_patch.master.json.gz'),'compiled_index':ref(H/'compile.json'),'ownership':ref(H/'ownership_arrays.npz'),'upper_union':ref(H/'upper_union_arrays.npz'),'driver':ref(Path(__file__)),'common_mesher':ref(Path(render_data.mesh.__file__)),'common_exporter':ref(Path(render_data.__file__)),'diagnostic_only':True,'production_gate_open':False,'original_global_registration_accepted':False,'chimney_depth_is_explicit_prior':True,'underside_validated':False}}
 renderref=write('roof_repaired.render.json.gz',render);assert plan['source_dependencies']==pins()
 report={'schema':'riverstone.image_roof_repair.composition.v2','render':renderref,'quad_count':n,'bounds':bounds,'fine_upper_occupied_cells':int((arr[4:]>=0).sum()),'new_roof_cells_inserted':inserted,'new_roof_cells_blocked_by_unchanged_source':blocked,'lower_original_quads_kept':lower_kept,'lower_original_quads_clipped_at_join':lower_clipped,'mesher_chunk_edges_z':edges,'chunks':chunks,'common_mesher_calls':len(chunks),'sampling_calls':0,'whole_house_highres_compile':False,'elapsed_seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'generated_bytes':sum(p.stat().st_size for p in H.rglob('*')if p.is_file()),'actual_six_view_and_oblique_review':'PENDING_PARENT_GUI','source_dependencies_unchanged':True}
 write('composition.json',report);print(json.dumps({k:v for k,v in report.items()if k!='chunks'}),flush=True)
if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(90,)*2);main()
