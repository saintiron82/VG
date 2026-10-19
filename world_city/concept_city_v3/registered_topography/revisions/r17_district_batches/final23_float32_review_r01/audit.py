"""Bounded precision diagnostic; no scene or sealed producer mutation."""
import json,struct
from pathlib import Path
from .. import author as a
from ..coherent_final24_r02.prepare import ref
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'coherent_final24_r02/top_scene_patch_r01.json'
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def ny(t):
 u=[t[1][k]-t[0][k]for k in range(3)];v=[t[2][k]-t[0][k]for k in range(3)];return u[2]*v[0]-u[0]*v[2]
def run():
 p=json.loads(SOURCE.read_bytes());rows=[]
 for r in p['surface_edits']:
  for i,t in enumerate(r['replacement_triangles_xyz_m']):rows.append((dict(kind='replacement',material=r['material'],source_triangle_index=r['triangle_index'],replacement_triangle_index=i),t))
 for m,vs in p['appended_surfaces'].items():
  if m!='bank':
   for i in range(len(vs)//3):rows.append((dict(kind='appended',material=m,appended_triangle_index=i),vs[3*i:3*i+3]))
 cases=[];counts=dict(triangles=len(rows),positive_source=0,negative_source=0,zero_source=0,float32_negative_nonzero=0,float32_exact_zero=0,float32_positive=0)
 for key,t in rows:
  n=ny(t);ft=[[f32(x)for x in v]for v in t];nf=ny(ft);counts['positive_source'if n>0 else 'negative_source'if n<0 else 'zero_source']+=1;counts['float32_negative_nonzero'if nf<0 else 'float32_exact_zero'if nf==0 else 'float32_positive']+=1
  if nf<=0:cases.append(dict(**key,source_triangle_sha256=a.canonical_sha(t),vertices_xyz_m=t,float32_vertices_xyz_m=ft,source_normal_y=n,float32_normal_y=nf,classification='NONZERO_FLOAT32_INVERSION'if nf<0 else'EXACT_FLOAT32_PROJECTED_COLLAPSE'))
 report=dict(schema='riverstone.final23.float32_top_winding_diagnostic.v1',source=ref(SOURCE),summary=counts,cases=cases,policy='Diagnostic only. IEEE754 float32 vertex positions, then exact arithmetic on represented values. No face deletion, coordinate change, tolerance or area threshold.',activation=False)
 (HERE/'report.json').write_text(json.dumps(report,separators=(',',':'),allow_nan=False)+'\n');print(counts,flush=True);print(ref(HERE/'report.json'),flush=True)
if __name__=='__main__':run()
