"""Change only relocation identity to obey the existing addendum adapters."""
import json,hashlib,shutil,copy,sys
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;ROOT=H.parents[5];sys.path.insert(0,str(ROOT));OLD=H/'candidate_r01';CANON=H/'candidate_r02';SOURCE_ID='FIELD_SITE_CLERGY_035:12:bed:1';NEW_ID=SOURCE_ID+':R10_RELOCATED'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def ref(p,canonical=None):return dict(path=str((canonical or p).relative_to(ROOT)),sha256=sha(p))
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def produce(out):
 old=read(OLD/'FROZEN.json')
 for n,h in old['files'].items():assert sha(OLD/n)==h,n
 out.mkdir(exist_ok=False)
 for n in ['surface_patch.json','ground_ownership.json','source_tests.json','exact_patch_audit.json','numeric_filter_ledger.json']:shutil.copy2(OLD/n,out/n)
 pack=read(OLD/'pack.json');assert pack['remove_instance_ids']==[SOURCE_ID]and pack['add_instances'][0]['id']==SOURCE_ID;pack['add_instances'][0]['id']=NEW_ID;rr=pack['instance_relocations'][0];rr['replacement_instance']['id']=NEW_ID;rr['source_id']=SOURCE_ID;rr['replacement_id']=NEW_ID;write(out/'pack.json',pack)
 # The transform does not touch any terrain, path coordinates, poses, dimensions,
 # assets, palettes, or access policy. Reference paths point at the canonical pack.
 idx=read(OLD/'index.json');idx['packs'][-1]=ref(out/'pack.json',CANON/'pack.json');write(out/'index.json',idx);routes=read(OLD/'routes.json');routes['finite_patch']=ref(out/'surface_patch.json',CANON/'surface_patch.json');routes['visual_index']=ref(out/'index.json',CANON/'index.json');write(out/'routes.json',routes)
 assert (out/'surface_patch.json').read_bytes()==(OLD/'surface_patch.json').read_bytes();assert routes['routes']==read(OLD/'routes.json')['routes'];check=copy.deepcopy(pack);check['add_instances'][0]['id']=SOURCE_ID;check['instance_relocations'][0]['replacement_instance']['id']=SOURCE_ID;del check['instance_relocations'][0]['source_id'];del check['instance_relocations'][0]['replacement_id'];assert check==read(OLD/'pack.json')
 return out

def main():
 out=produce(CANON);old=read(OLD/'FROZEN.json')
 # Execute the actual unchanged production Python adapter on the full real stack.
 from world_city.concept_city_v3.registered_integration.r9 import integrate_packs as adapter
 paths=[r['path']for r in read(OLD/'index.json')['packs'][:-1]];fail=None
 try:adapter.integrate(paths+[str((OLD/'pack.json').relative_to(ROOT))],str((H/'adapter_r01_expected_failure').relative_to(ROOT)))
 except ValueError as e:fail=str(e)
 assert fail=='Duplicate instance '+SOURCE_ID,fail
 adapter.integrate(paths+[str((out/'pack.json').relative_to(ROOT))],str((H/'adapter_r02_pass').relative_to(ROOT)))
 # Match the adapter's delayed-retirement behavior for a final identity check.
 base=read(adapter.BASE);ids={i['id']for i in base['common_instances']};removes=set();adds=[]
 for name in paths+[str((out/'pack.json').relative_to(ROOT))]:
  pk=read(ROOT/name)
  for i in pk.get('remove_instance_ids',[]):assert i in ids and i not in removes;removes.add(i)
  for i in pk.get('add_instances',[]):assert i['id']not in ids;ids.add(i['id']);adds.append(i)
 resolved=[i for i in base['common_instances']if i['id']not in removes]+[i for i in adds if i['id']not in removes];found=[i for i in resolved if i['id']==NEW_ID];assert len(found)==1 and found[0]['position_m']==[184.5,14.,-149.5];assert not any(i['id']==SOURCE_ID for i in resolved)
 report=dict(status='ACTUAL_PYTHON_ADAPTER_REGRESSION_PASS_GD_RUNTIME_PENDING',old_candidate=ref(OLD/'FROZEN.json'),old_actual_error=fail,producer_audit_error='The r01 producer simulated removal with dict.pop before adding, but production Python/GD adapters reserve the original ID through validation and retire instances only after all packs pass.',new_source_id=SOURCE_ID,new_instance_id=NEW_ID,resolved_source_id_count=0,resolved_new_id_count=1,terrain_bytes_unchanged=True,route_vectors_unchanged=True,poses_assets_palettes_unchanged=True,actual_python_adapter=ref(Path(adapter.__file__)),actual_python_composition=ref(H/'adapter_r02_pass/composition.json'),gd_adapter_read_only_contract=ref(ROOT/'world_city/concept_city_v3/preview_r9/VisualAddendum.gd'),gd_adapter_executed=False)
 write(out/'adapter_regression.json',report);snap=out/'source_snapshot';snap.mkdir();shutil.copy2(Path(__file__),snap/'build_relocation_id_r02.py');shutil.copy2(Path(adapter.__file__),snap/'integrate_packs_source.py');shutil.copy2(ROOT/'world_city/concept_city_v3/preview_r9/VisualAddendum.gd',snap/'VisualAddendum_source.gd')
 # Reproduce the identity-only transform into a separate directory.
 replay=produce(H/'candidate_r02_reproduced');rr={n:dict(regenerated_sha256=sha(replay/n),frozen_sha256=sha(out/n),identical=(replay/n).read_bytes()==(out/n).read_bytes())for n in ['surface_patch.json','pack.json','index.json','routes.json']};assert all(r['identical']for r in rr.values());write(out/'reproducibility_manifest.json',dict(status='FOUR_DELIVERABLES_BYTE_IDENTICAL',source_r01_frozen=ref(OLD/'FROZEN.json'),results=rr,method='Identity-only deterministic transform of the hash-verified preserved r01. The r01 terrain producer already has independent pinned regeneration evidence.',reproduction_call='Import source_snapshot/build_relocation_id_r02.py with __file__ context set to this producer folder; call produce(new_absent_directory). Canonical reference paths remain candidate_r02.'))
 frozen=dict(status='FROZEN_ACTUAL_PYTHON_COMPOSITION_PASS_RUNTIME_AND_VIEW_PENDING',base_scene=old['base_scene'],files={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()},source_dependencies=[ref(OLD/'FROZEN.json'),ref(H/'build_relocation_id_r02.py'),ref(Path(adapter.__file__)),ref(ROOT/'world_city/concept_city_v3/preview_r9/VisualAddendum.gd')]);write(out/'FROZEN.json',frozen);print(json.dumps(dict(candidate=str(out.relative_to(ROOT)),refs={n:ref(out/n)for n in ['surface_patch.json','pack.json','index.json','routes.json']},regression=report),indent=2))
if __name__=='__main__':main()
