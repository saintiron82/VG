"""Report every shared original-triangle conflict before full scene assembly."""
import json,time,sys,collections
from pathlib import Path
from .build_scene import a,HERE,verify
from .compose_finite_patches import compound_row
def main(binding_path,output_path):
 start=time.monotonic();b=a.load(binding_path);scene=verify(b['base_scene']);groups=collections.defaultdict(list)
 for ref in b['patches']:
  patch=verify(ref)
  for row in patch['surface_edits']:groups[(row['material'],row['triangle_index'])].append((patch['id'],row))
 shared={k:v for k,v in groups.items()if len(v)>1};errors=[]
 for i,(key,rows)in enumerate(shared.items()):
  try:compound_row(scene,key,rows,b.get('finite_physical_side_retirement_union',False))
  except ValueError as exc:errors.append(dict(material=key[0],triangle_index=key[1],patch_ids=[r[0]for r in rows],error=str(exc)))
  if i%500==0:print('shared',i,'/',len(shared),'errors',len(errors),'seconds',time.monotonic()-start,flush=True)
 result=dict(binding=dict(path=str(Path(binding_path).resolve().relative_to(a.ROOT)),sha256=a.sha(binding_path)),shared_source_triangles=len(shared),errors=errors,elapsed_s=time.monotonic()-start)
 Path(output_path).write_text(json.dumps(result,indent=2)+'\n');print('COMPLETE',len(errors),'errors',flush=True)
if __name__=='__main__':main(*sys.argv[1:])
