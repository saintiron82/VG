"""Generated-runtime terrain sanitation at the actual Godot float32 precision.

Authoring triangles remain untouched in their original scene. No geometric
area/width threshold is used; every nonzero float32 triangle is preserved.
"""
import argparse,copy,hashlib,json,math,time
from pathlib import Path
import numpy as np
from .build_scene import a

def canonical(value):return hashlib.sha256(json.dumps(value,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def zero_mask(flat):
 t=np.asarray(flat,dtype=np.float64).reshape(-1,3,3);q=t.astype(np.float32)
 with np.errstate(over='ignore',invalid='ignore'):cross=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0])
 if not np.all(np.isfinite(q))or not np.all(np.isfinite(cross)):raise ValueError('Nonfinite runtime triangle is not a deletion predicate')
 return t,q,cross,np.all(cross==np.float32(0),axis=1)
def normalize_surfaces(surfaces):
 out={};records=[];summary={};index_map={}
 for material,flat in surfaces.items():
  t,q,cross,zero=zero_mask(flat);drop=np.flatnonzero(zero).tolist();keep=np.flatnonzero(~zero).tolist();index_map[material]=keep
  area=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)/2
  out[material]=[v for i in keep for v in flat[3*i:3*i+3]]
  for i in drop:records.append(dict(material=material,source_triangle_index=i,source_triangle_sha256=canonical(flat[3*i:3*i+3]),source_triangle_xyz_m=flat[3*i:3*i+3],runtime_float32_vertices_xyz_m=q[i].tolist(),runtime_float32_cross_xyz=cross[i].tolist(),original_area3_m2=float(area[i])))
  summary[material]=dict(source_triangles=len(t),removed_zero_area=len(drop),retained_triangles=len(keep),removed_original_area3_m2=math.fsum(float(area[i])for i in drop),source_array_sha256=canonical(flat),runtime_array_sha256=canonical(out[material]))
 return out,records,summary,index_map

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--source-sha256',required=True);ap.add_argument('--output',required=True);args=ap.parse_args();start=time.monotonic();source=Path(args.source).resolve();dest=Path(args.output).resolve()
 if a.sha(source)!=args.source_sha256:raise ValueError('Changed authored source scene')
 if(dest/'scene.json').exists():raise ValueError('Preserve prior runtime candidate')
 scene=json.loads(source.read_bytes());surfaces,records,summary,index_map=normalize_surfaces(scene['surfaces']);authored_count=sum(len(v)//3 for v in scene['surfaces'].values());original_non_surface=canonical({k:v for k,v in scene.items()if k not in('surfaces','counts')})
 # Collision contracts are independently bound. Never silently change those.
 contract_review=[]
 for c in scene.get('collision_contracts',[]):
  tris=c.get('add_triangles_world_xyz_m',[])
  if not tris:continue
  flat=[v for t in tris for v in t];_,_,_,zero=zero_mask(flat);contract_review.append(dict(id=c['id'],triangles=len(tris),exact_zero_area_triangles=int(np.count_nonzero(zero))))
 out=dict(scene);out['surfaces']=surfaces;out['counts']=dict(scene.get('counts',{}));out['counts']['authored_terrain_triangles']=authored_count;out['counts']['terrain_triangles']=sum(len(v)//3 for v in surfaces.values())
 assert canonical({k:v for k,v in out.items()if k not in('surfaces','counts')})==original_non_surface
 dest.mkdir(parents=True,exist_ok=True);sp=dest/'scene.json';sp.write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n');mp=dest/'retained_source_index_map.json';mp.write_text(json.dumps(index_map,separators=(',',':'))+'\n');ref=lambda p:dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
 report=dict(schema='riverstone.runtime_precision.exact_float32_zero_area.v1',source=ref(source),runtime_scene=ref(sp),implementation=ref(Path(__file__)),retained_source_index_map=ref(mp),predicate='Exact float32 vector cross product equals zero in all3 components; no area or width cutoff.',removals=records,material_summary=summary,removed_triangle_count=len(records),removed_original_area3_m2=math.fsum(r['original_area3_m2']for r in records),retained_double_vertices_and_order_unchanged=True,non_surface_fields_unchanged_except_terrain_count_metadata=True,collision_contracts_unchanged=True,collision_contract_precision_audit=contract_review,source_preserved=True,elapsed_s=time.monotonic()-start,limits=['Source authoring and native caches are unchanged.','Nonzero runtime triangles remain unchanged even if their precision-sensitive winding needs independent review.','Collision contract degeneracies are reported, not silently removed.','Actual unchanged-controller replay is required for the derived runtime scene.'])
 rp=dest/'runtime_precision_ledger.json';rp.write_text(json.dumps(report,separators=(',',':'))+'\n');print(json.dumps(dict(scene=ref(sp),ledger=ref(rp),removed=len(records),source_area3_m2=report['removed_original_area3_m2'],seconds=report['elapsed_s']),indent=2))
if __name__=='__main__':main()
