"""Pin every volatile input and replay into a new folder without altering frozen outputs."""
import json,hashlib,shutil
from pathlib import Path
H=Path(__file__).resolve().parent;F=H/'candidate_r01';S=F/'source_snapshot';ROOT=H.parents[5]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return dict(path=str(Path(p).relative_to(ROOT)),sha256=sha(p))
m= json.loads((F/'FROZEN.json').read_bytes());obs=ROOT/'world_city/concept_city_v3/registered_integration/r10_functional_audit/network/observed_route_observation_mapping.json';expected=next(r['sha256']for r in m['source_dependencies']if r['path']==str(obs.relative_to(ROOT)));assert sha(obs)==expected;shutil.copy2(obs,S/'public_observations_frozen.json')
(S/'reproduce.py').write_text('''"""Reproduce clergy r01 from exact pinned sources with canonical reference paths."""
import json,sys,hashlib,types
from pathlib import Path
sys.dont_write_bytecode=True
S=Path(__file__).resolve().parent;F=S.parent;H=F.parent;ROOT=next(p for p in S.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=json.loads((F/'reproducibility_manifest.json').read_bytes())
for r in m['pinned_files']+m['retained_dependencies']:assert sha(ROOT/r['path'])==r['sha256'],r['path']
a=types.ModuleType('clergy_frozen_replay');a.__file__=str(H/'build_candidate_r01.py');a.PINNED_S=S
code=(S/'build_candidate_r01.py').read_text();old="S=H.parent/'abbey_repair_r03/candidate_r03/source_snapshot'";assert code.count(old)==1;code=code.replace(old,'S=PINNED_S');exec(compile(code,str(S/'build_candidate_r01.py'),'exec'),a.__dict__)
out=H.parent/'clergy_public_access_reproduced';out.mkdir(exist_ok=False);a.H=out;read=a.read
context=(out.parent/'context.json').resolve();obs=(a.C/'registered_integration/r10_functional_audit/network/observed_route_observation_mapping.json').resolve()
def pinned_read(p):
 p=Path(p).resolve()
 if p==context:return read(S/'context_frozen.json')
 if p==obs:return read(S/'public_observations_frozen.json')
 if p==out/'exploration_r02.json':return read(S/'exploration_r02.json')
 return read(p)
def ref(p):
 p=Path(p);canonical=F/p.name if p.parent==out else p
 return dict(path=str(canonical.relative_to(ROOT)),sha256=sha(p))
a.read=pinned_read;a.ref=ref;a.main();results={}
for n in ['surface_patch.json','pack.json','routes.json','index.json']:
 results[n]=dict(regenerated_sha256=sha(out/n),frozen_sha256=sha(F/n),identical=(out/n).read_bytes()==(F/n).read_bytes())
(out/'reproduction_result.json').write_text(json.dumps(results,indent=2)+'\\n');print(json.dumps(results,indent=2));assert all(r['identical']for r in results.values()),results
''')
retained=[r for r in m['source_dependencies']if r['path']!=str(obs.relative_to(ROOT))]+[m['base_scene']]
manifest=dict(status='PINNED_REPRODUCTION_PENDING',pinned_files=[ref(p)for p in S.iterdir()if p.is_file()],retained_dependencies=retained,original_frozen_files=m['files'],serialization_policy='Only runtime input/output paths are remapped: use the exact copied helper/context/observation data; canonical output references point to unchanged frozen deliverables. No geometry values are copied from output.',command='PYTHONDONTWRITEBYTECODE=1 python '+str((S/'reproduce.py').relative_to(ROOT)))
(F/'reproducibility_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
