"""Read-only final patched surface support diagnostic; preserve prior evidence."""
import json
import sys
sys.dont_write_bytecode=True
import author as a
from inspect_farm_roads import H,poly_for,xz
from world_city.concept_city_v3.registered_integration.r9.landward_gates.build_corridors import Ground

p=H/'surface_patch.json';patch_ref=a.ref(p);patch=json.loads(p.read_text());edits={(v['material'],v['triangle_index']):v for v in patch['surface_edits']};rows=[]
for r in json.loads((H/'local_source_faces.json').read_text()):
 e=edits.get((r['material'],r['triangle_index']))
 if e is None:rows.append(r)
 else:
  assert r['triangle']==e['source_triangle_xyz_m']
  rows.extend({'material':r['material'],'triangle_index':r['triangle_index'],'triangle':t}for t in e['replacement_triangles_xyz_m'])
for mat,verts in patch['appended_surfaces'].items():
 rows.extend({'material':mat,'triangle_index':j//3,'triangle':verts[j:j+3]}for j in range(0,len(verts),3))
ground=Ground(rows);farm_ref=a.ref(H/'farm_pack.json');farm=json.loads((H/'farm_pack.json').read_text());result=[]
for i in farm['add_instances']:
 if not i['id'].startswith('R9_WEST_PUBLIC_SEPARATOR'):continue
 b=farm['common_assets'][i['asset_key']]['bounds'];points=[xz(i['position_m'])]+poly_for(i,b);samples=[]
 for point in points:
  try:y=ground.at(point)
  except ValueError:y=None
  samples.append({'point_xz_m':point,'final_surface_y_m':y,'separator_bottom_y_m':i['position_m'][1]+b['min'][1],'bottom_minus_surface_m':None if y is None else i['position_m'][1]+b['min'][1]-y})
 result.append({'id':i['id'],'position_m':i['position_m'],'samples':samples,'max_absolute_support_delta_m':max(abs(s['bottom_minus_surface_m'])for s in samples if s['bottom_minus_surface_m'] is not None)})
report={'schema':'riverstone.city.separator_final_support_diagnostic.v1','inputs':{'surface_patch':patch_ref,'farm_pack':farm_ref},'scope':'Exact final source replacement/appended triangle heights at separator center and native footprint corners, independent of original-terrain fallback. Native r09 top comparison is retained in farm_road_diagnostic_r01.json.','separators':result,'failures_over_0_01m':[r for r in result if r['max_absolute_support_delta_m']>.01]}
out=a.HERE/'separator_final_support_r01.json';assert not out.exists();a.write(out.name,report)
assert a.sha(p)==patch_ref['sha256']and a.sha(H/'farm_pack.json')==farm_ref['sha256'],'Producer changed during inspection'
print(json.dumps({'failures':len(report['failures_over_0_01m']),'rows':[{'id':r['id'],'center_delta_m':r['samples'][0]['bottom_minus_surface_m'],'max_abs_delta_m':r['max_absolute_support_delta_m']}for r in report['failures_over_0_01m']]},indent=2))
