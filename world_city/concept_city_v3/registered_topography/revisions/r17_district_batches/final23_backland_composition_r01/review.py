"""Same exact compound-row test as parent's all-row diagnostic, new outputs."""
import json,time,collections
from .author import HERE,ref,load,write
from .. import author as a
from .....registered_integration.r8.compose_finite_patches import compound_row

def run():
 path=HERE/'activation_binding.json';b=json.loads(path.read_bytes());scene=a.load_scene();groups=collections.defaultdict(list);refs={}
 for r in b['patches']:
  p=load(r);refs[p['id']]=r
  for row in p['surface_edits']:groups[row['material'],row['triangle_index']].append((p['id'],row))
 rows=[(k,rs)for k,rs in groups.items()if len(rs)>1 and any('FINAL24'in pid for pid,_ in rs)];errors=[];ok=0;start=time.monotonic();print('Review',len(rows),'shared rows',flush=True)
 for key,rs in rows:
  try:compound_row(scene,key,rs,b.get('finite_physical_side_retirement_union',False));ok+=1
  except ValueError as error:errors.append(dict(material=key[0],triangle_index=key[1],error=str(error),producers=[dict(id=pid,ref=refs[pid])for pid,row in rs]));print('FAIL',key,str(error),flush=True)
 write('shared_source_review.json',dict(binding=ref(path),shared_rows=len(rows),passing=ok,errors=errors,passed=not errors,seconds=time.monotonic()-start,checker=ref(a.CITY/'registered_integration/r8/compose_finite_patches.py'),policy='Unchanged exact compound_row acceptance. Every shared final23 row is checked; no threshold relaxation.'));print('Complete',ok,len(errors),flush=True)
if __name__=='__main__':run()
