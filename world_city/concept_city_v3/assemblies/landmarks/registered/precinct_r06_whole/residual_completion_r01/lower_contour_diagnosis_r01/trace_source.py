from pathlib import Path
import json,hashlib,numpy as np
OUT=Path(__file__).resolve().parent;ROOT=next(p for p in OUT.parents if(p/'world_city/concept_city_v3').is_dir());CITY=ROOT/'world_city/concept_city_v3';N=OUT.parent/'noble_entry_batch_r02';BP=N/'runtime_precision_r01/activation_binding.json';binding=json.loads(BP.read_text());target=next(r for r in json.loads((OUT/'local_faces.json').read_text())['actual_local_scene_faces']if r['source_face']==['road',8688])['vertices_xyz_m'];key=sorted(tuple(v)for v in target);matches=[]
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def eq(t):return sorted(tuple(v)for v in t)==key
for pi,p in enumerate(binding['patches']):
 path=ROOT/p['path'];d=json.loads(path.read_text());exact=[]
 for ei,e in enumerate(d.get('surface_edits',[])):
  if e['material']!='road':continue
  for ri,t in enumerate(e.get('replacement_triangles_xyz_m',[])):
   if eq(t):exact.append(dict(kind='source_edit_replacement',edit_array_index=ei,replacement_triangle_index=ri,source_edit=e))
 vs=d.get('appended_surfaces',{}).get('road',[])
 for i in range(0,len(vs),3):
  if eq(vs[i:i+3]):exact.append(dict(kind='appended_surface',appended_triangle_index=i//3))
 if exact:matches.append(dict(binding_patch_index=pi,patch=ref(path),patch_id=d['id'],matches=exact));print('MATCH',pi,path,[(e['kind'],e.get('edit_array_index'),e.get('replacement_triangle_index'))for e in exact],flush=True)
report=dict(binding=ref(BP),target_runtime_source_face=['road',8688],target_authored_scene_index=14678,target_vertices_xyz_m=target,matches=matches)
(OUT/'source_lineage.json').write_text(json.dumps(report,indent=2)+'\n');print('DONE',len(matches))
