"""Rebind transitive producer digests after explicit ownership replacements."""
import copy,json,pathlib
from world_city.concept_city_v3.registered_integration.r6 import apply_packs as a,merge_patches as m
D=pathlib.Path(__file__).resolve().parent
ref=lambda p:dict(path=a.rel(p),sha256=a.sha(p))
def main():
 bp=D/'whole_city_activation_r01/activation_binding.json';b=a.load(bp);old=[a.load(a.ROOT/r['path'],r['sha256'])for r in b['patches']];ps=copy.deepcopy(old);by={p['id']:p for p in ps};pending=set(by);done=set();changes=[]
 while pending:
  ready=sorted(k for k in pending if set(by[k].get('requires_patch_canonical_sha256',{}))<=done)
  if not ready:raise ValueError('Cyclic or missing source prerequisites')
  for k in ready:
   p=by[k]
   for dep,was in list(p.get('requires_patch_canonical_sha256',{}).items()):
    now=m.canonical_sha(by[dep]);p['requires_patch_canonical_sha256'][dep]=now
    if was!=now:changes.append(dict(producer=k,dependency=dep,old=was,new=now))
   done.add(k);pending.remove(k)
 out=D/'whole_city_activation_r02';assert not out.exists();out.mkdir()
 for i,(was,now)in enumerate(zip(old,ps)):
  if was==now:continue
  assert {k:v for k,v in was.items()if k!='requires_patch_canonical_sha256'}=={k:v for k,v in now.items()if k!='requires_patch_canonical_sha256'}
  p=out/f'producer_{i:02d}.json';p.write_text(json.dumps(now,separators=(',',':'))+'\n');b['patches'][i]=ref(p)
 for p in ps:
  for dep,h in p.get('requires_patch_canonical_sha256',{}).items():assert m.canonical_sha(by[dep])==h
 lp=out/'dependency_rebinding.json';lp.write_text(json.dumps(dict(source_binding=ref(bp),changes=changes,all_geometry_unchanged=True,all_dependencies_pass=True),indent=2)+'\n');b['evidence'].append(ref(lp));p=out/'activation_binding.json';p.write_text(json.dumps(b,indent=2)+'\n');print(ref(p),len(changes),flush=True)
if __name__=='__main__':main()
