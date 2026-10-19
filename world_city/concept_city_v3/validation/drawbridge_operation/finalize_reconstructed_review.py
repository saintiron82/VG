"""Bind actually executed independent proofs to the reconstructed seals."""
import json,pathlib,hashlib
HERE=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in HERE.parents if (p/'world_city').is_dir());OP=ROOT/'world_city/concept_city_v3/assemblies/waterworks/registered_bridge/drawbridge_candidate/operation_r01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
core=OP/'freeze_manifest.json';runtime=OP/'runtime_fixture/freeze_manifest.json'
assert sha(core)=='ae2b2a6509292e5bad841e32ab2ca9ca2b5bb33941db6dbecedd8eff709aeb5e'
assert sha(runtime)=='30614a51cfeee49ee7f8fdc958d814be7858e5a3d3b90fc34063b573c8b013be'
checks=[]
for f in [core,runtime]:
 for r in json.loads(f.read_text())['files']:
  p=f.parent/r['path'];checks.append({'source':str(p.relative_to(ROOT)),'expected':r['sha256'],'actual':sha(p)});assert sha(p)==r['sha256']
for name in ['godot_reconstructed_01','runtime_reconstructed_01']:
 for r in json.loads((HERE/name/'snapshot_sources.json').read_text()):
  p=ROOT/r.get('copied',r.get('copy'));assert sha(p)==r['sha256']==sha(ROOT/r['source'])
p=HERE/'operation_f92488af13c4_a5b935239b6a.json';py=json.loads(p.read_text())
for f,h in py['sources'].items():assert sha(ROOT/f)==h
assert py['passing_count']==52 and not py['uncovered_motion_enclosures']
gd=HERE/'godot_reconstructed_01/independent_godot_report.json';g=json.loads(gd.read_text());assert g['valid'] and g['cases']==50 and g['frames']==354
assert sha(HERE/'operation_f92488af13c4_a5b935239b6a.fixtures.json')==sha(HERE/'godot_reconstructed_01/independent_vectors.json')
rt=HERE/'runtime_reconstructed_01/independent_runtime_report.json';r=json.loads(rt.read_text());assert not r['valid'] and len(r['failures'])==2
report={'schema':'riverstone.reconstructed_operation.independent_bound_review.v1','status':'controller_parity_pass_runtime_r01_FAILED_incumbent_reentry','core_seal':ref(core),'runtime_seal':ref(runtime),'sealed_file_checks':checks,'python_report':ref(p),'godot_report':ref(gd),'runtime_report':ref(rt),'runtime_checker':ref(HERE/'runtime_reconstructed_01/IndependentRuntime.gd'),'case_counts':{'python':52,'godot':50,'godot_frames':354,'runtime_ticks':r['ticks']},'runtime_failures':r['failures'],'limits':['Core tests use explicit simulated sensing.','Physical fixture has actual conservative full-rig CharacterBody3D and admission blockers, but no native bridge colliders or city actor integration.','r01 must remain held; a separately sealed repair requires new independent tests.','All pre-restoration post-backup reports remain historical and are not used.'],'checker':ref(pathlib.Path(__file__))}
p=HERE/'bound_review_ae2b2a650929.json';p.write_text(json.dumps(report,indent=2)+'\n');print(p,sha(p))
