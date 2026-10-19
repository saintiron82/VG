"""Bounded float32 audit of actual composed remainder and clipped paint output."""
import json,collections
from pathlib import Path
from .. import author as a
from ..coherent_final24_r02.prepare import ref,load
from ..final23_precision_continuation_r01.runtime_winding import normal,f32,canonical_sha
from .....registered_integration.r8.compose_finite_patches import compound_row
HERE=Path(__file__).resolve().parent

def run():
 B=HERE.parent/'final23_backland_composition_r01';b=json.loads((B/'activation_binding.json').read_bytes());ledger=json.loads((B/'ownership_ledger.json').read_bytes());keys={(r['material'],r['triangle_index'])for r in ledger['source_rows']};groups=collections.defaultdict(list)
 for ref0 in b['patches']:
  p=load(ref0)
  for r in p['surface_edits']:
   if(r['material'],r['triangle_index'])in keys:groups[r['material'],r['triangle_index']].append((p['id'],r))
 scene=a.load_scene();counts=collections.Counter();cases=[];rows=[]
 def inspect(t,origin):
  ft=[[f32(x)for x in v]for v in t];n=normal(ft);state='negative_nonzero'if n[1]<0 else'positive'if n[1]>0 else'exact_3d_zero'if all(x==0 for x in n)else'nonzero_vertical';counts[origin['kind']+':'+state]+=1
  if state!='positive':cases.append(dict(origin=origin,source_triangle_sha256=canonical_sha(t),source_vertices_xyz_m=t,float32_vertices_xyz_m=ft,float32_normal_xyz=n,classification=state))
 for key,rs in groups.items():
  out,proof=compound_row(scene,key,rs,b.get('finite_physical_side_retirement_union',False));rows.append(dict(material=key[0],triangle_index=key[1],replacement_count=len(out['replacement_triangles_xyz_m']),composition_proof=proof))
  for i,t in enumerate(out['replacement_triangles_xyz_m']):inspect(t,dict(kind='actual_composed_source_remainder',material=key[0],source_triangle_index=key[1],composed_replacement_triangle_index=i))
 for r in ledger['appended_rows']:
  for i,t in enumerate(r['replacement_triangles_xyz_m']):inspect(t,dict(kind='new_backland_paint_remainder',material=r['material'],original_backland_appended_triangle_index=r['source_appended_triangle_index'],new_backland_triangle_index=r['derived_first_triangle_index']+i))
 report=dict(source_binding=ref(B/'activation_binding.json'),source_ownership_ledger=ref(B/'ownership_ledger.json'),source_rows=rows,counts=dict(counts),cases=cases,passed_no_nonzero_negative=not any(r['classification']=='negative_nonzero'for r in cases),policy='Exact IEEE754 float32 diagnostic of the 119 actual compound-row outputs and 294 newly clipped paint rows. No geometry changes or new runtime exceptions. Intermediate source restoration faces are not incorrectly counted as final geometry.')
 (HERE/'report.json').write_text(json.dumps(report,separators=(',',':'),allow_nan=False)+'\n');print(dict(counts),flush=True);print(ref(HERE/'report.json'),flush=True)
if __name__=='__main__':run()
