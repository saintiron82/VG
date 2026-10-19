"""Atomic final23 activation and transitive hash-only dependency rebinding."""
import pathlib,json,copy
from world_city.concept_city_v3.registered_integration.r6 import apply_packs as a,merge_patches as m
D=pathlib.Path(__file__).resolve().parent

def ref(p):return dict(path=a.rel(p),sha256=a.sha(p))
def read(r):return a.load(a.ROOT/r['path'],r['sha256'])
def main():
 bp=D/'noble_cap_bridge_binding.json';b=a.load(bp);hp=a.CITY/'registered_topography/revisions/r17_district_batches/coherent_final24_r02/integration_handoff.json';h=a.load(hp);assert h['source_main_binding']==ref(bp)
 old=[read(r)for r in b['patches']];patches=copy.deepcopy(old);out=D/'final23_activation_r01';assert not out.exists();out.mkdir()
 for row in h['replace_producers']:
  i=row['producer_index'];assert b['patches'][i]==row['original'];patches[i]=read(row['replacement']);b['patches'][i]=row['replacement']
 by={p['id']:p for p in patches};original={p['id']:m.canonical_sha(p)for p in old};changes=[]
 for p in patches:
  for key,value in p.get('requires_patch_canonical_sha256',{}).items():assert value==original[key],(p['id'],key)
 # Dependency graph must be acyclic, otherwise its content hashes cannot close.
 pending=set(by);done=set()
 while pending:
  ready=[key for key in pending if set(by[key].get('requires_patch_canonical_sha256',{}))<=done]
  if not ready:raise ValueError('Cyclic source-hash prerequisites')
  for key in ready:
   p=by[key]
   for dep,was in list(p.get('requires_patch_canonical_sha256',{}).items()):
    now=m.canonical_sha(by[dep]);p['requires_patch_canonical_sha256'][dep]=now
    if was!=now:changes.append(dict(producer=key,dependency=dep,old=was,new=now))
   done.add(key);pending.remove(key)
 for i,(was,now)in enumerate(zip(old,patches)):
  if now==read(b['patches'][i]):continue
  q=out/f'producer_{i:02d}.json';q.write_text(json.dumps(now,separators=(',',':'))+'\n');b['patches'][i]=ref(q)
 b['patches']+=h['append_patches']
 for r in h['append_native_packs']:read(r);b['packs'].append(dict(r,name='final23_whole_holdings_and_step'))
 b['collision_contracts']+=h['append_collision_contracts']
 for r in h['append_patches']+h['append_collision_contracts']:read(r)
 cp=D/'review_cameras.json';c=a.load(cp)
 for k,v in c['cameras'].items():assert k not in b['review_cameras'];b['review_cameras'][k]=v
 b['evidence'] += [ref(hp),h['contract'],h['physical_owners'],h['routes'],h['source_index_composition'],h['generated_bank_row_ledger'],ref(a.ROOT/h['freeze_manifest_path']),ref(cp)]
 b['source_stage']='All110 ordinary holdings adopted, plus one protected hall domain. Final23, step, B17, noble cap and fixed-span support activated. Bridge side-join closure and final combined acceptance remain pending.'
 b['limits']=['Whole-city exterior/layout candidate; final actual images and composed-controller replay are required.','110 adopted ordinary holdings are not a building or voxel count.','One unbuilt B008 proposal is superseded by the retained protected market hall and service ground.','Interiors, city NPC/economy, wallwalk and microtexture polish are separate implementation scope.','Bridge occupancy operation remains a closed-world registered-actor fixture; full live city traffic is not implemented.']
 q=out/'dependency_rebinding.json';q.write_text(json.dumps(dict(source_binding=ref(bp),handoff=ref(hp),changes=changes,policy='Only explicit dependency hashes changed; all producer geometry other than the two sealed replacements remains exact.'),indent=2)+'\n');b['evidence'].append(ref(q))
 q=out/'activation_binding.json';q.write_text(json.dumps(b,indent=2)+'\n');print(ref(q),len(b['patches']),len(b['packs']),len(b['collision_contracts']),len(changes),flush=True)
if __name__=='__main__':main()
