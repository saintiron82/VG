"""Pin a preserved r07 helper for honest independent reproduction of r02."""
import ast,json,hashlib,shutil
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[5];F=H/'candidate_r02';S=F/'source_snapshot'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return dict(path=str(Path(p).relative_to(ROOT)),sha256=sha(p))
old=json.loads((F/'FROZEN.json').read_bytes());dep=next(d for d in old['source_dependencies']if d['path'].endswith('/build_corridors.py'))
src=ROOT/'world_city/concept_city_v3/registered_integration/r9/landward_gates/candidate_r07/source_snapshot/build_corridors.py';assert sha(src)=='c52962e22f80d8171c75dff5fd3988a0526efe1ab30aeb5d49e27f307e7d28f6'
shutil.copy2(src,S/'build_corridors_r07_preserved.py');ctx=H.parent/'context.json';assert sha(ctx)==next(d['sha256']for d in old['source_dependencies']if d['path'].endswith('/context.json'));shutil.copy2(ctx,S/'context_frozen.json')
code=src.read_text();tree=ast.parse(code);names=['xz','area3','plane','ph','up','split3','cut3','Ground'];sections={n.name:ast.get_source_segment(code,n)for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))and n.name in names};assert set(sections)==set(names)
head='''"""Verbatim common helper definitions from preserved r07 (c52962...). Original r02 full producer f9c43... was not preserved. No new clipping/height algorithm."""\nimport math\nfrom world_city.runtime_city.checks import placement as geo\nfrom world_city.concept_city_v3.review_geometry import fan\n''';(S/'finite_helpers_frozen.py').write_text(head+'\n\n'.join(sections[n]for n in names)+'\n')
(S/'reproduce.py').write_text('''"""Replay r02 using preserved r07 common helpers. Refuse output overwrites."""
import sys,json,hashlib,importlib.util
from pathlib import Path
sys.dont_write_bytecode=True
S=Path(__file__).resolve().parent;F=S.parent;ROOT=next(p for p in S.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=json.loads((F/'reproducibility_manifest.json').read_bytes())
for r in m['pinned_files']+m['retained_dependencies']:assert sha(ROOT/r['path'])==r['sha256'],r['path']
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);o=importlib.util.module_from_spec(s);sys.modules[name]=o;s.loader.exec_module(o);return o
module('world_city.concept_city_v3.registered_integration.r9.landward_gates.build_corridors',S/'finite_helpers_frozen.py')
a=module('build_repair',S/'build_repair.py');out=F.parents[1]/'abbey_repair_r02_reproduced';out.mkdir(exist_ok=False);a.H=out;a.ROOT=ROOT;a.C=ROOT/'world_city/concept_city_v3';a.BASE=a.C/'evidence/r8_final110_runtime_r01/scene.json';read=a.read
context=(out.parent/'context.json').resolve()
def pinned_read(p):return read(S/'context_frozen.json')if Path(p).resolve()==context else read(p)
a.read=pinned_read
# Output references retain the canonical frozen deliverable path, while hashes
# are calculated from regenerated files. All writes remain inside the new folder.
def ref(p):
 p=Path(p);q=F/p.name if p.parent==out else p
 return dict(path=str(q.relative_to(ROOT)),sha256=sha(p))
a.ref=ref
original_write=a.write
def write(n,v):
 if n=='surface_patch.json':
  hh=v['source_surface_hashes'];assert set(hh)==set(m['material_hash_serialization_order']);v['source_surface_hashes']={k:hh[k]for k in m['material_hash_serialization_order']}
 original_write(n,v)
a.write=write;a.build();v=module('r02_frozen_validator',S/'validate_repair.py');v.main()
r=a.read(out/'routes.json');r['gate_native_id']='R06_ABBEY_GATE_R05:herb';r['gate_source_id']='ABBEY_NORTH_WORK:main_gate';r['gate_center_xyz_m']=[-259,8,-7.823607];r['gate_clear_width_m']=4;r['ward_source_id']='ABBEY_NORTH_WORK:infirmary:actual_entry';r['ward_door_center_xyz_m']=[-324,8,-16];r['source_plan']=ref(a.C/'registered_source/plan.json');r['supersedes_failed_candidate']=ref(out.parent/'candidate_r01/FROZEN.json');(out/'routes.json').write_text(json.dumps(r,indent=2)+'\\n')
results={}
for n in ['surface_patch.json','pack.json','routes.json','index.json']:
 results[n]={'regenerated_sha256':sha(out/n),'frozen_sha256':sha(F/n),'identical':(out/n).read_bytes()==(F/n).read_bytes()}
(out/'reproduction_result.json').write_text(json.dumps(results,indent=2)+'\\n');print(json.dumps(results,indent=2));assert all(r['identical']for r in results.values()),results
''')
extra=[S/'build_corridors_r07_preserved.py',S/'finite_helpers_frozen.py',S/'context_frozen.json',S/'reproduce.py',S/'build_repair.py',S/'validate_repair.py']
retained=[d for d in old['source_dependencies']if not d['path'].endswith('/build_corridors.py')and not d['path'].endswith('/context.json')];routes=json.loads((F/'routes.json').read_bytes());retained+=[old['base_scene'],routes['source_plan'],ref(H.parent/'candidate_r01/pack.json'),ref(H.parent/'candidate_r01/FROZEN.json'),ref(ROOT/'world_city/concept_city_v3/registered_integration/r9/integration_r02_camera/index.json'),old['prior_failed_view']]
manifest=dict(status='PRESERVED_R07_HELPER_PINNED_REPRODUCTION_PENDING',original_helper_preservation='Original f9c43 full producer was not preserved. No claim of restoring it or proving its complete contents.',unchanged_artifacts=[ref(F/n)for n in ['surface_patch.json','routes.json','index.json','pack.json']],original_recorded_source=dep,preserved_reproduction_source=ref(src),verbatim_reused_definitions={n:hashlib.sha256(sections[n].encode()).hexdigest()for n in names},extraction_policy='Preserved r07 producer copied byte-for-byte; only listed common definitions are loaded, avoiding volatile producer imports. These definitions also match preserved r06 exactly; original f9c43 cannot be directly compared.',pinned_files=[ref(p)for p in extra],retained_dependencies=retained,material_hash_serialization_order=list(json.loads((F/'surface_patch.json').read_bytes())['source_surface_hashes']),serialization_policy='Match frozen material-hash dictionary order because original generator used a Python set. Values and all geometry are independently recomputed. Output path references canonicalized to the unchanged frozen delivery paths; no geometry values are copied from frozen output.',command='PYTHONDONTWRITEBYTECODE=1 python '+str((S/'reproduce.py').relative_to(ROOT)),output_policy='New sibling abbey_repair_r02_reproduced only; frozen outputs and earlier candidates are never overwritten.')
(F/'reproducibility_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('Pinned preserved r07 helper',sha(src))
