import json,sys,math,importlib.util
from pathlib import Path
import numpy as np
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;ROOT=H.parents[5];sys.path.insert(0,str(ROOT))
p=H/'candidate_r02/source_snapshot/finite_helpers_frozen.py';s=importlib.util.spec_from_file_location('fh',p);hh=importlib.util.module_from_spec(s);s.loader.exec_module(hh)
from world_city.runtime_city.checks import placement as g
C=ROOT/'world_city/concept_city_v3';R=C/'registered_integration/r10_functional_audit/interface_runtime/replay_r02';data=json.loads((R/'geometry/ABBEY_ADMISSION.json').read_bytes());p=[-245.438766479492,-6.33718156814575];out=[]
for i,(t,r)in enumerate(zip(data['triangles'],data['source_face_indices'])):
 pp=[[v[0],v[2]]for v in t];d=0 if g.point_in_convex_polygon(p,pp,1e-8) and g.polygon_area(pp)>1e-12 else min(g.point_segment_distance(p,a,b)for a,b in zip(pp,pp[1:]+pp[:1]))
 if d>.36 or max(v[1]for v in t)<7.2 or min(v[1]for v in t)>8.8:continue
 a=np.array(t);nn=np.cross(a[1]-a[0],a[2]-a[0]);norm=nn/np.linalg.norm(nn);rec=dict(collision_triangle_index=i,source=r,distance_xz_m=d,normal_xyz=norm.tolist(),triangle=t)
 if abs(norm[1])>1e-8:
  pl=hh.plane(t);rec['plane_height_at_center']=hh.ph(pl,p);rec['gradient']=math.hypot(pl[0],pl[1])
 out.append(rec)
j=dict(failed_capsule_center=[p[0],8.68399143218994,p[1]],radius_m=.3,footprint_probe_radius_m=.36,nearby_triangles=out,local_origin_proof=data['local_origin_proof']);(H/'runtime_footprint_diagnosis.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j,indent=2))
