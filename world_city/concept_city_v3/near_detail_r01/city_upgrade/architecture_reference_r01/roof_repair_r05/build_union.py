"""Merge only isolated-tile cells missing from frozen ordered source; preserve all other owners."""
from author_isolated_tiles import *
import numpy as np
from collections import Counter

def main():
 t=time.monotonic();p=read(H/'plan.json');assert p['source_dependencies']==pins();src=np.load(OLD/'upper_union_arrays.npz');arr=src['materials'];lo=src['origin_cell_xyz'];names=src['material_names'].tolist();ids={n:i for i,n in enumerate(names)};assert lo.tolist()==[-200,300,-164]
 labels=np.load(A/'roof_repair_r03/delta_ownership_arrays.npz')['delta_class'];assert labels.shape==arr.shape
 r4=read(R/read(OLD/'compile.json')['delta']['path']);protected={tuple(row[:3])for row in r4['cells']};del r4
 old3=read(R/read(A/'roof_repair_r03/compile.json')['delta']['path']);shadow={tuple(r[:3]):r for r in old3['cells']if r[4]=='observed_shadow_tile_extensions'};del old3
 original=read(A/'roof_repair_r02/compile.json')['chunks'];new=read(H/'compile.json')['chunks'];delta=[];blocked=Counter();stable=0;old_tile_count=0;isolated_count=0;supports_replaced=empty_added=0
 for oldchunk,newchunk in zip(original,new):
  assert oldchunk['owned_z_cells']==newchunk['owned_z_cells'];z0,z1=newchunk['owned_z_cells'];oldc=read(R/oldchunk['compiled']['path']);oldtiles={tuple(r[:3]):r for r in oldc['cells']if r[4]=='measured_tile_regions'};support={tuple(r[:3]):r for r in oldc['cells']if r[4]=='thin_roof_support'};oldtiles.update({xyz:r for xyz,r in shadow.items()if z0<=xyz[2]<z1});del oldc
  nc=read(R/newchunk['compiled']['path']);rows={tuple(r[:3]):r for r in nc['cells']};assert len(rows)==len(nc['cells']);isolated_count+=len(rows);old_tile_count+=len(oldtiles)
  for xyz,r in oldtiles.items():
   assert xyz in rows and rows[xyz][5:]==r[5:],('old_tile_changed',xyz,r,rows.get(xyz))
  for xyz,r in rows.items():
   if xyz in oldtiles:stable+=1;continue
   x,y,z=xyz;iy,ix,iz=y-lo[1],x-lo[0],z-lo[2];old=int(arr[iy,ix,iz]);label=int(labels[iy,ix,iz]);reason=None
   if xyz in protected:reason='r04_TOP_material_owner'
   elif label in [1,2]:reason='r03_original_restoration_or_foreground'
   elif old>=0 and not(xyz in support and ids[support[xyz][5]]==old and label==0):reason='other_preserved_source_owner'
   if reason:blocked[reason]+=1;continue
   assert y>=round(JOIN/P);newmat=ids[r[5]];delta.append([x,y,z,old,newmat,r[6],('empty'if old<0 else 'original_support')]);arr[iy,ix,iz]=newmat;empty_added+=int(old<0);supports_replaced+=int(old>=0)
  del nc,rows,oldtiles,support;gc.collect()
 assert stable==old_tile_count
 np.savez_compressed(H/'upper_union_arrays.npz',materials=arr,origin_cell_xyz=lo,pitch_m=P,material_names=np.asarray(names),join_y_m=JOIN)
 dr=write('delta_cells.json.gz',{'schema':'riverstone.roof.isolated_source_delta.v1','columns':['x','y','z','prior_material_index','new_material_index','source_tile_id','prior_owner_class'],'cells':delta})
 prior=np.load(OLD/'upper_union_arrays.npz')['materials'];mask=np.zeros(arr.shape,bool)
 for x,y,z,old,newmat,fid,owner in delta:mask[y-lo[1],x-lo[0],z-lo[2]]=True
 assert int((arr!=prior).sum())==sum(row[3]!=row[4]for row in delta)and not np.any((arr!=prior)&~mask);assert np.array_equal(arr[:4],prior[:4])
 witness=read(A/'roof_backing_measurement_r01/source_ordering_witnesses.json')['queries']
 tilemats={ops[0]['id']:ids[ops[0]['material']]for rev,path,ops in source_tiles()[2]};restored_witness=sum(int(arr[q['point_grid_xyz'][1]-lo[1],q['point_grid_xyz'][0]-lo[0],q['point_grid_xyz'][2]-lo[2]])==tilemats[q['expected_source_tile']]for q in witness);assert restored_witness==1781
 def top(a):
  ys=np.full((a.shape[1],a.shape[2]),-1,np.int16);ms=ys.copy()
  for y in range(4,a.shape[0]):
   hit=a[y]>=0;ys[hit]=y+lo[1];ms[hit]=a[y][hit]
  return ys,ms
 by,bm=top(prior);ay,am=top(arr);changed_top=(by!=ay)|(bm!=am);top_delta=int(changed_top.sum());old_r4_plan=read(OLD/'cache_plan.json');cache=[]
 for i,c in enumerate(old_r4_plan['chunks']):
  oldpath=R/c['original_cache']['path']if c['reuse_exact_cache']else OLD/f'mesh_cache/chunk_{i:03d}.json.gz';oldpayload=read(oldpath);za,zb=c['halo_z_cells'];sh=hashlib.sha256(prior[:,:,za-lo[2]:zb-lo[2]].tobytes()).hexdigest();nh=hashlib.sha256(arr[:,:,za-lo[2]:zb-lo[2]].tobytes()).hexdigest();assert sh==c['r04_halo_material_sha256'];cache.append({'index':i,'owned_z_cells':c['owned_z_cells'],'halo_z_cells':[za,zb],'original_cache':ref(oldpath),'original_cache_union_sha256':oldpayload['upper_union_sha256'],'r04_halo_material_sha256':sh,'r05_halo_material_sha256':nh,'reuse_exact_cache':sh==nh});del oldpayload
 write('cache_plan.json',{'schema':'riverstone.roof.halo_cache_plan.v1','previous_render':ref(OLD/'roof_repaired.render.json.gz'),'previous_union':ref(OLD/'upper_union_arrays.npz'),'new_union':ref(H/'upper_union_arrays.npz'),'chunks':cache,'exact_reused':sum(c['reuse_exact_cache']for c in cache),'rebuild_required':sum(not c['reuse_exact_cache']for c in cache)})
 report={'schema':'riverstone.roof.isolated_source_union.v1','status':'PASS','previous_union':ref(OLD/'upper_union_arrays.npz'),'union':ref(H/'upper_union_arrays.npz'),'delta':dr,'isolated_tile_cells':isolated_count,'original_tile_cells_preserved':stable,'lost_tile_cells_recovered':len(delta),'changed_occupancy_or_material_cells':int((arr!=prior).sum()),'same_material_support_owner_transfers':sum(row[3]==row[4]for row in delta),'empty_cells_added':empty_added,'original_support_cells_replaced':supports_replaced,'protected_source_conflicts_deferred':dict(blocked),'changed_TOP_first_hit_columns':top_delta,'changed_TOP_left_columns':int(changed_top[:200].sum()),'changed_TOP_right_columns':int(changed_top[200:].sum()),'right_audit_witnesses_recovered':restored_witness,'unchanged_outside_exact_delta':True,'lower_join_halo_unchanged':True,'new_measured_regions':0,'old_normal_sidecar_forbidden':True,'new_union_occupied_cells':int((arr[4:]>=0).sum()),'cache_reused':sum(c['reuse_exact_cache']for c in cache),'cache_rebuild_required':sum(not c['reuse_exact_cache']for c in cache),'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'source_dependencies_unchanged':p['source_dependencies']==pins()}
 assert report['source_dependencies_unchanged'];write('union_validation.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(384*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(120,)*2);main()
