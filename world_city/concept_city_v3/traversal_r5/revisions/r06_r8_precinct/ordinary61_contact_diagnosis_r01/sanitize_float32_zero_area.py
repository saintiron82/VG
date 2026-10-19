"""Exact runtime-precision triangle sanitation, without a geometric area cutoff."""
import json,hashlib,time,resource,math
from pathlib import Path
import numpy as np
H=Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').exists());SOURCE=ROOT/'world_city/concept_city_v3/evidence/r8_district_61_assembly_preflight_r01/scene.json';EXPECTED='643851e9554c335fc5af4f1e1b6b51af19d3e67b4b1bc578c091539f29a29299'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x):return hashlib.sha256(json.dumps(x,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def sanitize(scene):
 ledger=[];summary={};index_map={}
 for mat,flat in scene['surfaces'].items():
  t64=np.array(flat,dtype=np.float64).reshape(-1,3,3);t32=t64.astype(np.float32);u=t32[:,1]-t32[:,0];v=t32[:,2]-t32[:,0];cross=np.cross(u,v);zero=np.all(cross==np.float32(0),axis=1)
  # Non-finite vectors are a separate hard error, never a deletion predicate.
  assert np.all(np.isfinite(t32))and np.all(np.isfinite(cross))
  indices=np.flatnonzero(zero).tolist();removed=set(indices);kept=[i for i in range(len(t64))if i not in removed];index_map[mat]=kept
  double_cross=np.cross(t64[:,1]-t64[:,0],t64[:,2]-t64[:,0]);areas3=np.linalg.norm(double_cross,axis=1)/2;areasxz=np.abs(double_cross[:,1])/2
  for i in indices:
   tri=flat[i*3:i*3+3];q=t32[i].tolist();ledger.append(dict(material=mat,original_triangle_index=i,source_triangle_sha256=canonical(tri),source_triangle_xyz_m=tri,runtime_float32_vertices_xyz_m=q,runtime_float32_cross_xyz=cross[i].tolist(),runtime_unique_vertex_count=len({tuple(x)for x in q}),original_area3_m2=float(areas3[i]),original_projected_area_m2=float(areasxz[i]),replacement_triangles_xyz_m=[]))
  summary[mat]=dict(source_triangle_count=len(t64),exact_float32_zero_area_count=len(indices),retained_triangle_count=len(kept),removed_high_precision_area3_m2=math.fsum(float(areas3[i])for i in indices),removed_high_precision_projected_area_m2=math.fsum(float(areasxz[i])for i in indices),source_array_sha256=canonical(flat),retained_array_sha256=canonical([v for i in kept for v in flat[i*3:i*3+3]]))
  scene['surfaces'][mat]=[v for i in kept for v in flat[i*3:i*3+3]]
 return ledger,summary,index_map

def main():
 start=time.monotonic();assert sha(SOURCE)==EXPECTED;scene=json.loads(SOURCE.read_bytes());non_surface_hash=canonical({k:v for k,v in scene.items()if k!='surfaces'});ledger,summary,index_map=sanitize(scene)
 assert all((r['material'],r['original_triangle_index'])in{(x['material'],x['original_triangle_index'])for x in ledger}for r in [dict(material='road',original_triangle_index=3618),dict(material='road',original_triangle_index=10119)])
 assert canonical({k:v for k,v in scene.items()if k!='surfaces'})==non_surface_hash
 OUT=H/'float32_zero_area_r01';OUT.mkdir(exist_ok=True);sp=OUT/'scene.json'
 with sp.open('w')as f:json.dump(scene,f,separators=(',',':'),allow_nan=False)
 # Full nonzero test on final arrays; exact comparison, no epsilon.
 for flat in scene['surfaces'].values():
  t=np.array(flat,dtype=np.float32).reshape(-1,3,3);c=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);assert not np.any(np.all(c==np.float32(0),axis=1))
 mp=OUT/'retained_source_index_map.json';mp.write_text(json.dumps(index_map,separators=(',',':'))+'\n')
 out=dict(schema='riverstone.actual_scene.float32_zero_area_sanitation.v1',status='EXACT_DEGENERATE_TRIANGLE_REMOVAL_PENDING_CONTROLLER_REGRESSION',source=ref(SOURCE),derived_scene=ref(sp),retained_source_index_map=ref(mp),implementation=ref(Path(__file__)),predicate='Cast each XYZ coordinate to IEEE754 float32; perform float32 vector subtraction and cross product; remove if and only if all3 cross-product components equal exact zero. No minimum-area/width threshold.',material_summary=summary,removals=ledger,non_surface_fields_sha256=non_surface_hash,non_surface_fields_identical=True,retained_triangle_order_and_original_double_vertices_identical=True,known_failed_faces_confirmed=[['road',3618],['road',10119]],removed_triangle_count=len(ledger),removed_high_precision_area3_m2=math.fsum(r['original_area3_m2']for r in ledger),removed_high_precision_projected_area_m2=math.fsum(r['original_projected_area_m2']for r in ledger),elapsed_s=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,limits=['Native cache meshes and collision contracts are unchanged.','Every triangle with nonzero float32 cross product is retained even if tiny or steep.','Original high-precision scene remains preserved. Physical effect must be established by the same-controller isolated replay.'])
 p=OUT/'removal_ledger.json';p.write_text(json.dumps(out,separators=(',',':'))+'\n');print(ref(p));print(ref(sp));print('removed',len(ledger),'area3',out['removed_high_precision_area3_m2'],'seconds',out['elapsed_s']);print({k:v['exact_float32_zero_area_count']for k,v in summary.items()})
if __name__=='__main__':main()
