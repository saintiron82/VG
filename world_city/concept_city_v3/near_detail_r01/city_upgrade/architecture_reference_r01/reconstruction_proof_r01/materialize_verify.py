"""Materialize only completed original-core slabs; zero new source sampling.
Verify every render unit-face against the exact original-core owned cell union.
"""
import copy,gc,gzip,hashlib,json,resource,sys,time
from pathlib import Path
import numpy as np
import compile_slabs as c
ROOT,HERE,PITCH=c.ROOT,c.HERE,c.PITCH

def main():
 start=time.monotonic();stats=[c.load(HERE/'slabs/000.stats.json')]+[c.load(p) for p in sorted((HERE/'slabs_v2').glob('*.stats.json'))];assert len(stats)==15
 cursor=0;owned=[];template=None;inputs=[]
 for s in stats:
  assert s['y_cells'][0]==cursor;cursor=s['y_cells'][1]
  for typ in ('compiled','render'):
   p=ROOT/s[typ]['path'];assert c.sha(p)==s[typ]['sha256'];inputs.append(s[typ])
  compiled=c.load(ROOT/s['compiled']['path']);template=copy.deepcopy({k:v for k,v in compiled.items() if k!='cells'});cells=[r for r in compiled['cells'] if s['y_cells'][0]<=r[1]<s['y_cells'][1]];assert len(cells)==s['owned_cell_count'] and c.core.digest(cells)==s['owned_cells_hash'];owned.extend(cells);del compiled,cells
 assert cursor==112;owned.sort();assert len({tuple(r[:3]) for r in owned})==len(owned)
 arrays=np.load(HERE/'image_derived_arrays.npz');occ=arrays['occupancy'];mats=arrays['materials'];assert len(owned)==int(occ.sum());payload=c.core.digest(owned)
 # Aggregated common cells keep provenance of every exact bounded compile.
 for k in ('evaluation_scope','valid_scope','global_constraints_evaluated','global_constraints_valid'):template.pop(k,None)
 template.update(cells=owned,payload_hash=payload,candidate_cells=sum(c.load(ROOT/s['compiled']['path'])['candidate_cells'] for s in stats),constraints=[{'id':'diagnostic_nonempty','kind':'nonempty','pass':bool(owned),'occupied_cells':len(owned)}],valid=bool(owned),aggregation={'kind':'complete_disjoint_y_ownership_union','slab_count':15,'original_core_sha256':c.sha(c.core.__file__),'sampling_in_this_step':0,'every_cell_and_material_matched_authored_image_grid':True})
 c.save(HERE/'diagnostic.compiled.json.gz',template);template.pop('cells');del owned;gc.collect()
 groups={};duplicates=0;actual=np.full((6,*occ.shape),-1,dtype=np.int16);axis_to_array=[1,0,2];offset=[48,0,40]
 for s in stats:
  r=c.load(ROOT/s['render']['path'])
  for g in r['groups']:
   mat=int(g['material'].split('_')[1]);groups.setdefault(g['material'],[]).extend(g['quads'])
   for q in g['quads']:
    grid=np.rint(np.asarray(q)/PITCH).astype(int);assert np.max(np.abs(grid*PITCH-np.asarray(q)))<1e-9
    cross=np.cross(grid[1]-grid[0],grid[2]-grid[0]);axis=int(np.argmax(np.abs(cross)));sign=1 if cross[axis]>0 else -1;plane=int(grid[0,axis]);owner=plane-(1 if sign>0 else 0);direction=2*axis+(sign>0);lo=grid.min(axis=0);hi=grid.max(axis=0);ss=[None]*3
    for a in range(3):ss[axis_to_array[a]]=owner+offset[a] if a==axis else slice(int(lo[a]+offset[a]),int(hi[a]+offset[a]))
    view=actual[(direction,*ss)];duplicates+=int(np.count_nonzero(view>=0));actual[(direction,*ss)]=mat
 del r;gc.collect()
 mismatches=0;faces=0;per=[]
 for axis in range(3):
  a=axis_to_array[axis]
  for sign in (-1,1):
   neighbor=np.zeros_like(occ);dst=[slice(None)]*3;src=[slice(None)]*3
   if sign>0:dst[a]=slice(None,-1);src[a]=slice(1,None)
   else:dst[a]=slice(1,None);src[a]=slice(None,-1)
   neighbor[tuple(dst)]=occ[tuple(src)];exposed=occ&~neighbor;expected=np.where(exposed,mats,-1);direction=2*axis+(sign>0);n=int(np.count_nonzero(actual[direction]!=expected));mismatches+=n;faces+=int(exposed.sum());per.append({'axis':'XYZ'[axis],'sign':sign,'expected_unit_faces':int(exposed.sum()),'mismatch_unit_faces':n})
 assert duplicates==0 and mismatches==0,(duplicates,mismatches)
 del actual;gc.collect();y,x,z=np.where(occ);bounds={'min':[(int(x.min())-48)*PITCH,int(y.min())*PITCH,(int(z.min())-40)*PITCH],'max':[(int(x.max())-47)*PITCH,(int(y.max())+1)*PITCH,(int(z.max())-39)*PITCH]};qs=sum(len(v) for v in groups.values())
 render={'schema':'riverstone.voxel.render.v1','unit':'m',**{k:template[k] for k in ('source_id','source_revision','master_hash','pitch','grid_origin','materials')},'payload_hash':payload,'cell_count':int(occ.sum()),'bounds':bounds,'groups':[{'material':k,'quads':groups[k]} for k in sorted(groups)],'quad_count':qs,'geometry':'Actual common greedy surface of original-core owned cells. Halo-only caps removed by ownership; every material unit-face independently equals full-cell exterior.','provenance':{'compiler_source_hash':c.sha(c.core.__file__),'exporter_sha256':c.sha(c.render_data.__file__),'mesher_sha256':c.sha(c.render_data.mesh.__file__),'materialization_driver_sha256':c.sha(__file__),'diagnostic_only':True,'production_gate_open':False}}
 c.save(HERE/'diagnostic.render.json.gz',render);del groups,render;gc.collect()
 report={'schema':'riverstone.image_voxel_reconstruction.common_mesh_verification.v1','all_pass':True,'diagnostic_only':True,'production_gate_open':False,'source_image':c.load(HERE/'prepare.json')['source_image'],'master':c.ref(HERE/'image_derived.master.json.gz'),'compiled':c.ref(HERE/'diagnostic.compiled.json.gz'),'render':c.ref(HERE/'diagnostic.render.json.gz'),'driver':c.ref(__file__),'sampled_cell_count':int(occ.sum()),'quad_count':qs,'unit_faces':faces,'same_direction_duplicate_unit_faces':duplicates,'external_face_material_mismatch_count':mismatches,'per_direction':per,'internal_chunk_cap_count':0,'ownership_slabs':15,'sampling_in_this_step':0,'bounds':bounds,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'pitch':PITCH,'compile_seconds':sum(s['common_sample_seconds'] for s in stats),'mesh_seconds':sum(s['common_mesh_seconds'] for s in stats),'total_slab_seconds':sum(s['elapsed_seconds'] for s in stats),'materialization_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'vertex_normal_material_bytes':qs*144,'input_slabs':inputs,'image_registration_pass':False,'four_view_reprojection':c.load(HERE/'prepare.json')['four_view_reprojection'],'limits':['Diagnostic image reconstruction, not a production asset or approved architecture.','Visual hull has no unique hidden-depth solution. Explicit shell/gallery/floor priors determine hidden volume.','12-color input palette includes baked shadows/highlights; it is not recovered albedo.','Actual walkability, structure, reference-photo likeness and navigation are unverified.']};c.save(HERE/'verification.json',report);print(json.dumps({k:report[k] for k in ['all_pass','sampled_cell_count','quad_count','unit_faces','compile_seconds','mesh_seconds','materialization_seconds','peak_rss_kib','render','bounds']}),flush=True)

if __name__=='__main__':resource.setrlimit(resource.RLIMIT_AS,(384*1024**2,384*1024**2));main()
