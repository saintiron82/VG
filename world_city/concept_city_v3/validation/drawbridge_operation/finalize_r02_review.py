"""Bind the independently executed r02 physical fixture, retaining r01 failure."""
import json,pathlib,hashlib
HERE=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in HERE.parents if (p/'world_city').is_dir());OP=ROOT/'world_city/concept_city_v3/assemblies/waterworks/registered_bridge/drawbridge_candidate/operation_r01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
seals=[(OP/'freeze_manifest.json','ae2b2a6509292e5bad841e32ab2ca9ca2b5bb33941db6dbecedd8eff709aeb5e'),(OP/'runtime_fixture/freeze_manifest.json','30614a51cfeee49ee7f8fdc958d814be7858e5a3d3b90fc34063b573c8b013be'),(OP/'runtime_fixture/revisions/r02/freeze_manifest.json','fd6fd9e1e557d32f0bd195b32bc9d2b6e35fc6e41bd304a96b134e6ff594566f')]
checks=[]
for f,h in seals:
 assert sha(f)==h
 for r in json.loads(f.read_text())['files']:
  p=f.parent/r['path'];assert sha(p)==r['sha256'];checks.append(ref(p))
snap=HERE/'runtime_reconstructed_02'
for r in json.loads((snap/'snapshot_sources.json').read_text()):assert sha(ROOT/r['source'])==sha(ROOT/r['copy'])==r['sha256']
p=snap/'independent_runtime_report.json';result=json.loads(p.read_text());assert result['valid'] and len(result['checks'])==32 and result['ticks']==846
failure=HERE/'runtime_reconstructed_01/independent_runtime_report.json';old=json.loads(failure.read_text());assert not old['valid'] and len(old['failures'])==2
report={'schema':'riverstone.independent.runtime_r02_bound_review.v1','status':'pass_bounded_closed_world_physics_fixture','seals':[ref(f) for f,h in seals],'sealed_file_checks':checks,'independent_runtime_report':ref(p),'independent_runtime_script':ref(snap/'IndependentRuntime.gd'),'run_log':ref(snap/'run.log'),'copied_source_bindings':ref(snap/'snapshot_sources.json'),'preserved_r01_failure':ref(failure),'independent_core_review':ref(HERE/'bound_review_ae2b2a650929.json'),'checks':result['checks'],'physics_ticks':846,'findings':['The full24m rig at originZ38 keeps NAVIGATION_DRAIN and90° leaves for220 ticks; reversal remains inside the open channel.','Full outer-corridor exit removes bidirectional exceptions before lowering/reopening. Subsequent reverse motion physically collides with the closed admission gate.','The analogous road-incumbentX16 window holds ROAD_DRAIN until full outer exit; then road re-entry physically collides.','A vessel under the closed span halts stable ROAD_OPEN. Unregistered StaticBody3D presence is detected by direct query outside the fixture subtree.','Query saturation, unauthorized exceptions, reduced rig shapes, changed collision masks and repeated physics-frame observations fail closed.'],'limits':['Fixture uses conservative full-rig CharacterBody3D boxes and actual admission colliders; native bridge colliders are not installed.','Closed-world actor registry and direct shape queries are not a live city population integration.','Continuous actor trajectories, speed/stopping-distance guarantees, vehicle dynamics and structural mechanics remain unverified.','Original r01 reverse-entry failure is retained; its earlier successful author suite did not cover the window.','Hinge-cover hoist/carriage supports remain absent from visible mechanical art.'],'checker':ref(pathlib.Path(__file__))}
out=HERE/'bound_runtime_r02_fd6fd9e1e557.json';out.write_text(json.dumps(report,indent=2)+'\n');print(ref(out))
