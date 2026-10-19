"""Postbuild artifact/actual-source proof. Never changes production binding."""
import json,math,sys
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H));import author_r03 as a
p=a.read(a.PLAN);c=a.read(a.CAT);old=a.read(a.BASE_CAT);report=a.read(H/'build_report.json');modules={m['id']:m for m in c['modules']};tests={}
tests['plan_binding']=c['source_plan_sha256']==a.sha(a.PLAN)
tests['all_75_previous_catalog_rows_identical']=c['modules'][:75]==old['modules']
tests['frozen_dependencies_unchanged']=all(a.sha(a.R/path)==sha for path,sha in report['source_dependencies'].items())
module_rows=[]
for m in c['modules']:
 render=a.read(a.R/m['render_path']);quads=[q for g in render['groups'] for q in g['quads']];w,h=m['trim']['width_m'],m['trim']['height_m'];checks={}
 checks['files_sha_bound']=a.sha(a.R/m['render_path'])==m['render_sha256'] and a.sha(a.R/m['master_path'])==m['master_sha256']
 checks['count']=len(quads)==m['quads']
 checks['all_vertices_inside_trim_and_projection']=all(-1e-12<=v[0]<=w+1e-12 and -1e-12<=v[1]<=h+1e-12 and -.037500000001<=v[2]<=1e-12 for q in quads for v in q)
 checks['compiler_outward_normals']=m['checks']['all_quad_normals_outward']
 module_rows.append({'id':m['id'],'checks':checks,'all_pass':all(checks.values())})
asset_rows=[]
for asset in p['assets']:
 faces={(f['group_index'],f['quad_index']):f for f in asset['faces']};source=a.read(a.R/asset['source_render_path']);proven=0
 for placement in asset['placements']:
  f=faces[tuple(placement['source_face_ref'])];assert source['groups'][f['group_index']]['quads'][f['quad_index']]==f['quad'];assert a.digest(f['quad'])==placement['source_face_sha256']
  m=modules[placement['module_key']];tr=placement['transform'];assert tr['basis']==[[1,0,0],[0,0,1],[0,-1,0]]
  corners=[]
  for x in (0,m['trim']['width_m']):
   for y in (0,m['trim']['height_m']):
    corners.append([tr['translation'][0]+x,tr['translation'][1]-.0375,tr['translation'][2]-y])
  b=[a.strict_grid(min(v[0] for v in corners)),a.strict_grid(-max(v[2] for v in corners)),a.strict_grid(max(v[0] for v in corners)),a.strict_grid(-min(v[2] for v in corners))]
  assert all(abs(v[1]-f['plane_y_m'])<1e-12 for v in corners)
  assert a.union_proof(b,[f['rect_uv_integer_cells']])['supported']
  assert a.union_proof(b,[v['rect_uv_integer_cells'] for v in f['operation_owners']])['supported'];proven+=1
 # Coplanar rectangles do not overlap: no duplicate geometry along source owner seams.
 overlaps=[]
 for i,pa in enumerate(asset['placements']):
  for pb in asset['placements'][i+1:]:
   if abs(pa['source_plane_y_m']-pb['source_plane_y_m'])>1e-12:continue
   x,y=pa['bounds_uv_m'],pb['bounds_uv_m'];area=max(0,min(x[2],y[2])-max(x[0],y[0]))*max(0,min(x[3],y[3])-max(x[1],y[1]))
   if area>1e-12:overlaps.append(area)
 asset_rows.append({'asset':asset['asset_key'],'placements_proven':proven,'source_and_semantic_union_uncovered_area_cells2':0,'coplanar_overlap_m2':sum(overlaps),'all_pass':not overlaps})
result={'all_pass':all(tests.values()) and all(m['all_pass'] for m in module_rows) and all(v['all_pass'] for v in asset_rows),'tests':tests,'modules':module_rows,'assets':asset_rows,'source_plan_sha256':a.sha(a.PLAN),'module_catalog_sha256':a.sha(a.CAT),'runtime_activation':False,'collision_change':False}
a.save(H/'candidate_geometry.json',result);print(json.dumps({'all_pass':result['all_pass'],'tests':tests,'modules':len(module_rows),'assets':asset_rows}))
