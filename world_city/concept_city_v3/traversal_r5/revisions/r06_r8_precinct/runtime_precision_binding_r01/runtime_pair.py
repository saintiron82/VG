"""Strict authored-to-runtime proof. No geometry or producer checks are relaxed."""
import hashlib,json
import numpy as np

def canonical(value):
 return hashlib.sha256(json.dumps(value,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def need(condition,message):
 if not condition: raise ValueError(message)

def source_proof(scene,ledger,index_map):
 """Audit all source rows, then return compact expected runtime hashes.

 The caller can release the authored scene before loading the runtime scene.
 """
 need(ledger['schema']=='riverstone.runtime_precision.exact_float32_zero_area.v1','Unsupported runtime ledger schema')
 for field in ['retained_double_vertices_and_order_unchanged','non_surface_fields_unchanged_except_terrain_count_metadata','collision_contracts_unchanged','source_preserved']:
  need(ledger.get(field) is True,'Missing affirmative ledger proof: '+field)
 need(set(scene['surfaces'])==set(index_map)==set(ledger['material_summary']),'Material inventory mismatch')
 removals={}
 for row in ledger['removals']:
  key=(row['material'],row['source_triangle_index']);need(key not in removals,'Duplicate removal key');removals[key]=row
 need(len(removals)==ledger['removed_triangle_count'],'Removal count mismatch')
 expected={};seen=set();source_count=0;runtime_count=0
 for material,flat in scene['surfaces'].items():
  need(len(flat)%3==0,'Malformed source triangle list');count=len(flat)//3;source_count+=count;keep=index_map[material];summary=ledger['material_summary'][material]
  need(all(type(i) is int for i in keep),'Noninteger retained source index')
  need(keep==sorted(set(keep)) and all(0<=i<count for i in keep),'Invalid retained index order or bounds')
  q=np.asarray(flat,dtype=np.float32).reshape(-1,3,3)
  with np.errstate(over='ignore',invalid='ignore'): cross=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0])
  need(bool(np.all(np.isfinite(q))) and bool(np.all(np.isfinite(cross))),'Nonfinite runtime geometry')
  zero=np.all(cross==np.float32(0),axis=1);exact_keep=np.flatnonzero(~zero).tolist()
  need(keep==exact_keep,'Index map does not retain exactly every nonzero runtime triangle')
  removed=np.flatnonzero(zero).tolist()
  need(summary['source_triangles']==count and summary['removed_zero_area']==len(removed) and summary['retained_triangles']==len(keep),'Material count mismatch')
  need(summary['source_array_sha256']==canonical(flat),'Source material array hash mismatch')
  for i in removed:
   key=(material,i);need(key in removals,'Missing exact removal row');seen.add(key);row=removals[key];tri=flat[i*3:i*3+3]
   need(row['source_triangle_xyz_m']==tri and row['source_triangle_sha256']==canonical(tri),'Changed retired source triangle')
   need(row['runtime_float32_vertices_xyz_m']==q[i].tolist() and row['runtime_float32_cross_xyz']==cross[i].tolist(),'False float32 removal proof')
  runtime=[v for i in keep for v in flat[i*3:i*3+3]];digest=canonical(runtime)
  need(summary['runtime_array_sha256']==digest,'Ledger changed a retained triangle')
  expected[material]=digest;runtime_count+=len(keep)
 need(seen==set(removals),'Ledger contains unowned or nonzero removals')
 expected_counts=dict(scene.get('counts',{}));expected_counts['authored_terrain_triangles']=source_count;expected_counts['terrain_triangles']=runtime_count
 return dict(non_surface_sha256=canonical({k:v for k,v in scene.items()if k not in ('surfaces','counts')}),counts=expected_counts,surface_sha256=expected,authored_triangles=source_count,runtime_triangles=runtime_count,removed_triangles=len(removals))

def verify_runtime(scene,proof):
 need(canonical({k:v for k,v in scene.items()if k not in ('surfaces','counts')})==proof['non_surface_sha256'],'Runtime changed native geometry, contracts or other scene fields')
 need(scene.get('counts')==proof['counts'],'Runtime metadata change exceeds exact terrain counts')
 need(set(scene['surfaces'])==set(proof['surface_sha256']),'Runtime material inventory mismatch')
 for material,flat in scene['surfaces'].items():
  need(canonical(flat)==proof['surface_sha256'][material],'Runtime retained triangles differ: '+material)
 return True
