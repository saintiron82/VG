import json,hashlib
from pathlib import Path
from .runtime_winding import HERE,f32,normal,canonical_sha
from .. import author as a
from ..coherent_final24_r02.prepare import ref

def write(name,obj):
 p=HERE/name;assert not p.exists();p.write_text(json.dumps(obj,separators=(',',':'),allow_nan=False)+'\n')
def run():
 review=HERE.parent/'final23_float32_review_r01';original=HERE.parent/'coherent_final24_r02/top_scene_patch_r01.json';p=json.loads((review/'top_scene_patch_retriangulated.json').read_bytes());ledger=json.loads((review/'source_retriangulation_ledger.json').read_bytes());write('source_retriangulation_ledger.json',ledger);p['precision_source_continuation']['ledger']=ref(HERE/'source_retriangulation_ledger.json');p['precision_source_continuation'].pop('ledger_path',None);write('top_scene_patch.json',p);cases=[];vertical=[];zero=[]
 def inspect(key,t):
  ft=[[f32(x)for x in v]for v in t];n=normal(ft)
  row=dict(producer_row=key,material=key['material'],source_triangle_sha256=canonical_sha(t),precise_source_vertices_xyz_m=t,runtime_before_vertices_xyz_m=ft,float32_normal_xyz=n)
  if n[1]<0:cases.append(dict(row,id='FINAL23_PRECISION:'+str(len(cases)),runtime_after_vertices_xyz_m=[ft[0],ft[2],ft[1]]))
  elif n[1]==0:
   (zero if all(x==0 for x in n)else vertical).append(row)
 for r in p['surface_edits']:
  for i,t in enumerate(r['replacement_triangles_xyz_m']):inspect(dict(kind='replacement',material=r['material'],source_triangle_index=r['triangle_index'],replacement_triangle_index=i),t)
 for m,vs in p['appended_surfaces'].items():
  for i in range(len(vs)//3):inspect(dict(kind='appended',material=m,appended_triangle_index=i),vs[3*i:3*i+3])
 assert len(cases)==10 and len(vertical)==7 and len(zero)==40
 write('runtime_winding_contract.json',dict(schema='riverstone.final23.recognized_runtime_winding.v1',source_producer=ref(HERE/'top_scene_patch.json'),original_precise_source=ref(original),cases=cases,retained_nonzero_vertical_faces=vertical,exact_3d_zero_faces=zero,policy='Ten expressly approved, exact source-row-bound runtime winding corrections. Quantized geometric vertex sets are unchanged. No unrecognized face is flipped. The seven nonzero vertical faces are retained. This rendering precision exception does not prove upward physical support; precise source ownership and actual runtime replay remain separate.',activation=False))
 print('Prepared10 runtime inversions, retained7 vertical faces,40 exact3Dzero diagnostics',flush=True)
if __name__=='__main__':run()
