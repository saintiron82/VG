"""Original lower render plus common-meshed fine upper union with exact halos."""
from pathlib import Path
import gzip,hashlib,json,math,os,resource,sys,time,gc
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from author_roof import R,H,F,Q,M,P,JOIN,sha,ref,read,write,pins,validate_regions
from voxel_character.common import core,render_data

def clip(q,axis,low,high):
 # Ownership clipping is surface composition only, never shape modification.
 points=np.asarray(q);normal=np.cross(points[1]-points[0],points[2]-points[0]);direction=int(np.argmax(abs(normal)))
 if direction==axis:
  owner=round(q[0][axis]/P)-(1 if normal[axis]>0 else 0)
  return q if low<=owner<high else None
 lo=max(float(points[:,axis].min()),low*P);hi=min(float(points[:,axis].max()),high*P)
 if hi-lo<1e-9:return None
 out=[list(p)for p in q]
 for p in out:p[axis]=max(lo,min(hi,p[axis]))
 return out

def main():
 t=time.monotonic();plan=read(H/'plan.json');newpins=pins();changed=[p for p,s in plan['source_dependencies'].items()if newpins[p]!=s]
 # A concurrent additive metadata clarification was received after prepare.
 # Preserve both old plan/hash and sampling record; prove every source-to-shape
 # field unchanged, then pin final measured JSON without recompiling geometry.
 tiles=read(H/'tile_measurement_r01/tile_regions.json');validate_regions(tiles)
 byid={r['id']:r for r in tiles['regions']}
 assert len(byid)==len(plan['source_links'])
 for link in plan['source_links']:
  r=byid[link['operation']]
  assert link['source_bbox_px']==r['bbox_px'] and link['source_color']==r['color'] and link['partial_endpoints']==r['partial_endpoints_left_top_right_bottom']
 assert changed in ([],[str((H/'tile_measurement_r01/tile_regions.json').relative_to(R))]),changed
 write('input_pin_revision_r02.json',{'status':'PASS_ADDITIVE_METADATA_ONLY_GEOMETRY_INPUTS_EXACT','original_plan':ref(H/'plan.json'),'original_compilation':ref(H/'compile.json'),'changed_dependencies':changed,'current_source_dependencies':newpins,'regions_bbox_color_partial_flags_identical':True,'changed_shape_or_palette':False,'recompiled':False,'policy':'Original plan and its dependency-change flag remain preserved. The current JSON only adds declared separators; geometry continues the original fixed 1px-separator prior, including partial ROI ends.'})
 a=np.load(H/'ownership_arrays.npz');kept=a['kept_occupancy'];km=a['kept_materials'];base=read(F/'foundation_repaired.render.json.gz');patch=read(H/'roof_patch.compiled.json.gz')
 assert patch['valid'] and core.digest(patch['cells'])==patch['payload_hash']
 materials=dict(base['materials']);materials.update(patch['materials']);names=list(materials);ids={n:i for i,n in enumerate(names)}
 # Dense bounded upper grid only. Lower .125m house is never resampled.
 lo=np.array([-100,150,-82],dtype=int);hi=np.array([100,224,82],dtype=int)
 dims=hi-lo;arr=np.full((dims[1],dims[0],dims[2]),-1,np.int16)
 oldnames=[f'pixel_{i:02d}'if i<12 else f'stone_{i-12:02d}'for i in range(15)]
 # Inspect actual foundation material spelling rather than assume prefix.
 oldnames=[]
 for i in range(15):
  candidates=[n for n in base['materials']if (int(n.rsplit('_',1)[1])+(12 if n.startswith('stone')else 0))==i]
  assert len(candidates)==1,(i,candidates);oldnames.append(candidates[0])
 coarse=np.where(kept[75:],km[75:],-1);lookup=np.array([ids[n]for n in oldnames],np.int16)
 expanded=np.repeat(np.repeat(np.repeat(coarse,2,axis=0),2,axis=1),2,axis=2);mapped=np.where(expanded>=0,lookup[np.maximum(expanded,0)],-1)
 arr[:mapped.shape[0],4:196,2:162]=mapped;del expanded,mapped,coarse;gc.collect()
 retained=arr>=0;inserted=blocked=0
 for x,y,z,instance,part,material,feature in patch['cells']:
  iy,ix,iz=y-lo[1],x-lo[0],z-lo[2]
  assert 0<=iy<arr.shape[0]and 0<=ix<arr.shape[1]and 0<=iz<arr.shape[2]
  if arr[iy,ix,iz]<0:arr[iy,ix,iz]=ids[material];inserted+=1
  else:blocked+=1
 np.savez_compressed(H/'upper_union_arrays.npz',materials=arr,retained_baseline=retained,origin_cell_xyz=lo,pitch_m=np.array(P),material_names=np.array(names),join_y_m=np.array(JOIN))
 del patch;gc.collect();groups={};lower_kept=lower_clipped=0
 for g in base['groups']:
  for q in g['quads']:
   new=clip(q,1,-10000,round(JOIN/P))
   if new is not None:groups.setdefault(g['material'],[]).append(new);lower_kept+=int(new==q);lower_clipped+=int(new!=q)
 chunks=[];edges=list(range(int(lo[2]),int(hi[2]),32))+[int(hi[2])]
 for z0,z1 in zip(edges,edges[1:]):
  st=time.monotonic();za=max(int(lo[2]),z0-1);zb=min(int(hi[2]),z1+1);slice_=arr[:,:,za-lo[2]:zb-lo[2]];positions=np.argwhere(slice_>=0)
  rows=[[int(ix+lo[0]),int(iy+lo[1]),int(iz+za),'upper_union','roof_and_source',names[int(slice_[iy,ix,iz])],'actual_union_cell']for iy,ix,iz in positions]
  compiled={'schema':'riverstone.voxel.compiled.v1','valid':True,'pitch':P,'grid_origin':[0,0,0],'materials':materials,'cells':rows,'source_id':'architecture_A_roof_repair_r01','source_revision':1,'master_hash':core.digest({'base':ref(F/'foundation_revised.master.json.gz'),'roof':ref(H/'roof_patch.master.json.gz')}),'payload_hash':core.digest(rows),'compiler_source_hash':sha(Path(core.__file__))}
  local=render_data.make_render_data(compiled);kept_count=0
  for g in local['groups']:
   for q in g['quads']:
    new=clip(q,1,round(JOIN/P),int(hi[1]))
    if new is not None:new=clip(new,2,z0,z1)
    if new is not None:groups.setdefault(g['material'],[]).append(new);kept_count+=1
  chunks.append({'owned_z_cells':[z0,z1],'halo_z_cells':[za,zb],'actual_union_cells':len(rows),'exported_quads':local['quad_count'],'owned_quads':kept_count,'seconds':time.monotonic()-st});print(json.dumps(chunks[-1]),flush=True)
  del rows,compiled,local,positions;gc.collect()
 n=sum(len(v)for v in groups.values());allcorners=[p for qs in groups.values()for q in qs for p in q];bounds={'min':[min(p[i]for p in allcorners)for i in range(3)],'max':[max(p[i]for p in allcorners)for i in range(3)]};del allcorners
 render={k:v for k,v in base.items()if k not in ['groups','bounds','quad_count','geometry','provenance']}
 render.update(source_id='architecture_A_roof_repair_r01',source_revision=1,master_hash=core.digest({'base':sha(F/'foundation_revised.master.json.gz'),'roof':sha(H/'roof_patch.master.json.gz')}),payload_hash=core.digest({'base_render':sha(F/'foundation_repaired.render.json.gz'),'upper_union':sha(H/'upper_union_arrays.npz')}),pitch=P,materials=materials,cell_count=int(kept[:76].sum())+int((arr[2:]>=0).sum()),groups=[{'material':m,'quads':groups[m]}for m in sorted(groups)],quad_count=n,bounds=bounds,geometry='Mixed-resolution exact surface: unchanged original lower .125m cells; .0625m upper exact original-cell subdivision plus actual common-compiled bounded roof union; common mesher with one-cell halos.',provenance={'base_render':ref(F/'foundation_repaired.render.json.gz'),'roof_master':ref(H/'roof_patch.master.json.gz'),'roof_compiled':ref(H/'roof_patch.compiled.json.gz'),'ownership':ref(H/'ownership_arrays.npz'),'upper_union':ref(H/'upper_union_arrays.npz'),'input_pin_revision':ref(H/'input_pin_revision_r02.json'),'driver':ref(Path(__file__)),'common_mesher':ref(Path(render_data.mesh.__file__)),'common_exporter':ref(Path(render_data.__file__)),'diagnostic_only':True,'production_gate_open':False,'original_global_registration_accepted':False,'chimney_depth_validated':False,'underside_validated':False})
 renderref=write('roof_repaired.render.json.gz',render)
 report={'schema':'riverstone.image_roof_repair.composition.v1','render':renderref,'quad_count':n,'bounds':bounds,'fine_upper_occupied_cells':int((arr[2:]>=0).sum()),'new_roof_cells_inserted':inserted,'new_roof_cells_blocked_by_unchanged_source':blocked,'source_priority_preserves_existing_nonroof_materials':True,'lower_original_quads_kept':lower_kept,'lower_original_quads_clipped_at_join':lower_clipped,'chunks':chunks,'common_mesher_calls':len(chunks),'sampling_calls':0,'whole_house_highres_compile':False,'elapsed_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'generated_bytes':sum(p.stat().st_size for p in H.rglob('*')if p.is_file()),'actual_six_view_and_oblique_review':'PENDING_PARENT_GUI','source_dependencies_unchanged_since_pin_revision':newpins==pins()}
 assert report['source_dependencies_unchanged_since_pin_revision'];write('composition.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(90,)*2);main()
