"""Reject only sub-quantization fragments with explicit area-error bounds.
Every retired fragment is retained verbatim in the correction ledger. No
well-resolved triangle is dropped, re-wound, nudged, or moved off its source.
"""
import json,math
import numpy as np
from pathlib import Path
from .build_corridors import sha,ref,area3
H=Path(__file__).parent;p=H/'surface_patch.json';d=json.loads(p.read_bytes());before=sha(p);removed=[]
def keep(t,where,source=None):
 a=np.asarray(t,dtype=np.float64);f=a.astype(np.float32);n=np.cross(f[1]-f[0],f[2]-f[0]);reason=None
 if not np.any(n):reason='float32 zero triangle'
 elif source is not None:
  s=np.asarray(source,dtype=np.float32);sn=np.cross(s[1]-s[0],s[2]-s[0])
  if np.dot(sn,n)<=0:reason='float32 source-normal orientation lost'
 elif where['material']!='bank'and n[1]<=0:reason='float32 upward projection lost'
 if reason is None:return True
 # Perturbing vertices by at most e can change a triangle's area by no more
 # than perimeter*e + 3*e^2 (a conservative swept-edge area bound).
 e=float(np.linalg.norm(f.astype(np.float64)-a,axis=1).max());perimeter=sum(math.dist(t[i],t[(i+1)%3])for i in range(3));bound=perimeter*e+3*e*e;area=area3(t)
 measure=area;measure_kind='3D triangle area'
 if source is None and where['material']!='bank':
  # A top face can become vertical after XZ quantization while retaining a
  # tiny normal in X/Y. Its walkable footprint, rather than its sloped area,
  # must be representable. Bound that projection with the same swept-edge proof.
  measure=abs(float(np.cross(a[1]-a[0],a[2]-a[0])[1]))/2;measure_kind='XZ walkable footprint area'
  q=a[:,[0,2]];fq=f.astype(np.float64)[:,[0,2]];e=float(np.linalg.norm(fq-q,axis=1).max());perimeter=sum(float(np.linalg.norm(q[i]-q[(i+1)%3]))for i in range(3));bound=perimeter*e+3*e*e
 assert measure<=bound+1e-12,('Not a sub-quantization fragment',where,measure,bound)
 assert area<.001,('Fragment exceeds explicit local correction bound',where,area)
 removed.append(dict(where,reason=reason,triangle_xyz_m=t,world_float32_xyz_m=f.tolist(),double_area_m2=area,quantization_measure=measure_kind,quantization_measure_area_m2=measure,max_vertex_quantization_error_m=e,area_perturbation_bound_m2=bound));return False
for e in d['surface_edits']:
 e['replacement_triangles_xyz_m']=[t for i,t in enumerate(e['replacement_triangles_xyz_m'])if keep(t,dict(kind='replacement',material=e['material'],source_triangle_index=e['triangle_index'],replacement_index=i),e['source_triangle_xyz_m'])]
for mat,verts in d['appended_surfaces'].items():
 d['appended_surfaces'][mat]=[v for i in range(0,len(verts),3)if keep(verts[i:i+3],dict(kind='appended',material=mat,appended_triangle_index=i//3))for v in verts[i:i+3]]
d['float32_fragment_correction']=dict(policy='Only renderer-invalid sub-quantization fragments are retired. Each replacement 3D area or appended walkable XZ footprint <= perimeter*maximum vertex float32 rounding displacement + 3*displacement squared; every discarded 3D area <0.001 m2. Exact original vertices and proof remain in correction ledger.',count=len(removed),summed_double_area_m2=sum(v['double_area_m2']for v in removed));d['summary']['appended_triangles']=sum(len(v)//3 for v in d['appended_surfaces'].values());p.write_text(json.dumps(d,separators=(',',':'))+'\n');(H/'float32_filter_report.json').write_text(json.dumps(dict(input_patch_sha256=before,output_patch=ref(p),removed=removed),separators=(',',':'))+'\n');print('Corrected',len(removed),'fragments, summed area',d['float32_fragment_correction']['summed_double_area_m2'])
