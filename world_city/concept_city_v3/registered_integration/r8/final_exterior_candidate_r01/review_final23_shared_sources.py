"""Read-only enumeration of exact final23 source-row composition conflicts."""
import json,time,collections,pathlib
from world_city.concept_city_v3.registered_integration.r8.compose_finite_patches import compound_row
from world_city.concept_city_v3.registered_integration.r6 import apply_packs as a
D=pathlib.Path(__file__).resolve().parent
bp=D/'port_atomic_activation_r02/activation_binding.json';b=a.load(bp);scene=a.load(a.ROOT/b['base_scene']['path'],b['base_scene']['sha256']);groups=collections.defaultdict(list);patchrefs={}
for ref in b['patches']:
 p=a.load(a.ROOT/ref['path'],ref['sha256']);patchrefs[p['id']]=ref
 for row in p['surface_edits']:groups[row['material'],row['triangle_index']].append((p['id'],row))
rows=[(key,rs)for key,rs in groups.items()if len(rs)>1 and any('FINAL24'in pid for pid,_ in rs)];errors=[];ok=0;start=time.monotonic();print('shared final23 rows',len(rows),flush=True)
for key,rs in rows:
 try:compound_row(scene,key,rs,b.get('finite_physical_side_retirement_union',False));ok+=1
 except ValueError as e:
  errors.append(dict(material=key[0],triangle_index=key[1],error=str(e),producers=[dict(id=pid,ref=patchrefs[pid],replacement_count=len(row['replacement_triangles_xyz_m']))for pid,row in rs],source_triangle_xyz_m=scene['surfaces'][key[0]][key[1]*3:key[1]*3+3]));print('FAIL',key,str(e),flush=True)
report=dict(binding=dict(path=a.rel(bp),sha256=a.sha(bp)),shared_rows=len(rows),passing=ok,errors=errors,seconds=time.monotonic()-start,policy='Read only exact source composition; no geometry edits or relaxed thresholds.')
p=D/'final23_shared_source_conflicts_r01.json';p.write_text(json.dumps(report,indent=2)+'\n');print(a.rel(p),a.sha(p),len(errors),flush=True)
