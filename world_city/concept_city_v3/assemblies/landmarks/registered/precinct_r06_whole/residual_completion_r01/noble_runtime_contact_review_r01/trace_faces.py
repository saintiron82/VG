from pathlib import Path
import json,hashlib
OUT=Path(__file__).resolve().parent;ROOT=next(p for p in OUT.parents if(p/'world_city/concept_city_v3').is_dir());N=OUT.parent/'noble_entry_batch_r02';bp=N/'runtime_precision_r01/activation_binding.json';binding=json.loads(bp.read_text());diag=json.loads((OUT/'contact_face_diagnosis.json').read_text());targets={}
def key(t):return tuple(sorted(tuple(v)for v in t))
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
for case in diag['cases']:
 for s in case['contacts']:
  for r in s['matching_faces']:
   k=key(r['vertices_xyz_m']);targets.setdefault(k,dict(runtime_source_face=r['source_face'],runtime_collider_face=r['collider_face_index'],vertices_xyz_m=r['vertices_xyz_m'],cases=[],matches=[]));targets[k]['cases'].append(case['id'])
for pi,rr in enumerate(binding['patches']):
 p=ROOT/rr['path'];d=json.loads(p.read_text())
 for ei,e in enumerate(d.get('surface_edits',[])):
  if e['material']not in ('ground_stone','bank'):continue
  for ti,t in enumerate(e.get('replacement_triangles_xyz_m',[])):
   k=key(t)
   if k in targets:targets[k]['matches'].append(dict(binding_patch_index=pi,patch=rr,patch_id=d['id'],kind='source_edit_replacement',edit_array_index=ei,source_material=e['material'],source_triangle_index=e['triangle_index'],replacement_triangle_index=ti))
 for mat in ('ground_stone','bank'):
  vs=d.get('appended_surfaces',{}).get(mat,[])
  for i in range(0,len(vs),3):
   k=key(vs[i:i+3])
   if k in targets:targets[k]['matches'].append(dict(binding_patch_index=pi,patch=rr,patch_id=d['id'],kind='appended_surface',material=mat,appended_triangle_index=i//3))
rows=list(targets.values());p=OUT/'exact_contact_source_lineage.json';p.write_text(json.dumps(dict(binding=ref(bp),diagnosis=ref(OUT/'contact_face_diagnosis.json'),triangles=rows),indent=2)+'\n')
for r in rows:print(r['runtime_source_face'],[(m['binding_patch_index'],m['kind'],m.get('appended_triangle_index'))for m in r['matches']])
print(ref(p))
