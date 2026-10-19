import json,math,numpy as np
from pathlib import Path
from .build_corridors import H,ROOT,Ground,xz,ph,ref
from world_city.runtime_city.checks import placement as geo
p=json.load(open(H/'candidate_r07/surface_patch.json'));obs_path=H.parent/'gate_runtime_validation/candidate_r07_ray_observation_r01/evidence/capsule.json';obs=json.load(open(obs_path));rows=[dict(material=m,triangle_index=i//3,triangle=vs[i:i+3])for m,vs in p['appended_surfaces'].items()for i in range(0,len(vs),3)];g=Ground(rows);out=[]
for route in obs['routes']:
 for miss in route.get('ray_miss_diagnostics',[]):
  ray=miss['ray_from'];q=xz(ray);nearest=[]
  for i in g.idx.candidates([[q[0]-.05,q[1]-.05],[q[0]+.05,q[1]+.05]]):
   r=g.rows[i];tri=r['triangle'];f=np.asarray(tri,dtype=np.float32).astype(float).tolist();edges=[geo.point_segment_distance(q,xz(a),xz(b))for a,b in zip(f,f[1:]+f[:1])];inside=geo.point_in_convex_polygon(q,[xz(v)for v in f],0.);d=min(edges)
   if d<.005 or inside:
    a=np.asarray(f,dtype=np.float32);n=np.cross(a[1]-a[0],a[2]-a[0]);nearest.append(dict(material=r['material'],appended_triangle_index=r['triangle_index'],source_triangle_xyz_m=tri,float32_triangle_xyz_m=f,float32_up_normal=n.tolist(),projected_point_inside_float32_triangle=inside,nearest_edge_distance_m=d,edge_distances_m=edges,height_at_ray_xz_m=ph(r['plane'],q)))
  record=dict(route=route['id'],miss=miss,candidate_faces=sorted(nearest,key=lambda r:r['nearest_edge_distance_m']));out.append(record);print(route['id'],miss['frame'],[(r['appended_triangle_index'],r['projected_point_inside_float32_triangle'],r['nearest_edge_distance_m'],r['height_at_ray_xz_m'])for r in record['candidate_faces']])
(H/'candidate_r07/ray_miss_float32_topology.json').write_text(json.dumps(dict(observation=ref(obs_path),patch=ref(H/'candidate_r07/surface_patch.json'),diagnostic_source=ref(Path(__file__)),results=out),separators=(',',':'))+'\n')
