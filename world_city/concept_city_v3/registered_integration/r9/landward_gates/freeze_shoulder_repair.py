"""Freeze the bounded side-only r10 candidate; never rewrite old candidates."""
import json,hashlib,shutil,sys,subprocess
from pathlib import Path
from .build_corridors import H,ROOT,ref

def load(p):return json.loads(p.read_bytes())
def write(p,d):
 with p.open('x')as f:json.dump(d,f,separators=(',',':'),allow_nan=False);f.write('\n')
def main():
 out=H/'candidate_r10';stage=H/'shoulder_repair_r10_staging';old=H/'candidate_r09';assert not out.exists()
 assert load(stage/'side_geometry_audit.json')['status']=='PASS_SOURCE_ONLY'
 report=stage/'float32_preflight_final.json'
 subprocess.run([sys.executable,str(H.parent/'gate_runtime_validation/validate_float32.py'),'--patch',str(stage/'surface_patch.json'),'--report',str(report)],check=True)
 out.mkdir()
 for name in ['surface_patch.json','repair_report.json','wall_ledger.json','side_geometry_audit.json']:
  shutil.copyfile(stage/name,out/name)
 shutil.copyfile(report,out/'float32_preflight.json')
 shutil.copyfile(H/'shoulder_visual_diagnosis_r09.json',out/'source_diagnosis.json')
 # All common assets/native packs continue to reference the frozen r09 sources.
 index=load(old/'index.json');write(out/'index.json',index)
 for source,name in [(old/'routes.json','routes.json'),(H/'candidate_r09_boundary_routes_r01/routes.json','boundary_routes.json')]:
  data=load(source);data['finite_patch']=ref(out/'surface_patch.json');data['visual_index']=ref(out/'index.json');write(out/name,data)
  assert data['routes']==load(source)['routes']
 patch=load(out/'surface_patch.json');prior=load(old/'surface_patch.json')
 invariant=dict(previous=ref(old/'surface_patch.json'),candidate=ref(out/'surface_patch.json'),source_edits_identical=patch['surface_edits']==prior['surface_edits'],ownership_identical=patch['ownership']==prior['ownership'],unchanged_material_arrays={m:patch['appended_surfaces'][m]==v for m,v in prior['appended_surfaces'].items()if m!='ground_grass'},native_index_identical=index==load(old/'index.json'),main_route_vectors_identical=True,supplementary_boundary_vectors_identical=True,main_routes=ref(out/'routes.json'),boundary_routes=ref(out/'boundary_routes.json'),changed_geometry='Only bounded widened-forecourt ground_grass and explicit bank closure faces. No road, ground_earth, retained source fragment, native instance, route or fixture changes.',runtime_status='Actual integrated r09 26+26 PASS preserved. Side geometry changes require final visual validation and QA-approved runtime reuse or replay; r10 runtime not claimed.')
 write(out/'unchanged_support_ledger.json',invariant)
 snap=out/'source_snapshot';snap.mkdir();files=[]
 for name in ['repair_gate_shoulders.py','audit_shoulder_repair.py','freeze_shoulder_repair.py']:
  shutil.copyfile(H/name,snap/name);files.append(dict(source=ref(H/name),snapshot=ref(snap/name)))
 write(snap/'manifest.json',dict(schema='riverstone.source_snapshot.v1',files=files,original_candidate=ref(old/'FROZEN.json'),original_patch=ref(old/'surface_patch.json'),geometry_helpers=[ref(H/'build_corridors.py'),ref(ROOT/'world_city/runtime_city/checks/placement.py'),ref(ROOT/'world_city/concept_city_v3/review_geometry.py')],inputs=[ref(H/'local_source_faces.json')],commands=['python -m world_city.concept_city_v3.registered_integration.r9.landward_gates.repair_gate_shoulders','python -m world_city.concept_city_v3.registered_integration.r9.landward_gates.audit_shoulder_repair','python -m world_city.concept_city_v3.registered_integration.r9.landward_gates.freeze_shoulder_repair'],scope='Gate forecourt side-only reversible revision; no entire scene export.'))
 (out/'README.md').write_text('''# Gate forecourt side repair r10\n\nr09 actual integration_r03 passed 26 capsule and 26 geometric cart cases.\nThe subsequent same-eye visual review found real side cracks. r09 remains\nimmutable, including its passing runtime and failing visual evidence.\n\nThis candidate only repairs the widened forecourt grass strips, using shared\nroad-section heights and explicit vertical bank faces at the unchanged source\nterrain boundary. It is a narrow level setback with retaining walls, not a\ncontinuous earth slope forced across incompatible source heights. Maximum\nretaining-wall height is 3.8385 m. Side walls are not public crossing paths.\n\nAll public road arrays, original terrain source edits, farm tops, native packs,\nmain routes, boundary routes, and cart fixture are unchanged. Source checks\nare in side_geometry_audit.json and unchanged_support_ledger.json.\n\nNew top surfaces have no float32 shared-XZ height conflicts; their maximum\nactual triangle gradient is 9.8404%. No retaining-wall interval touches the\nroad boundary. Outside the explicitly repaired forecourt strips, old source\nshoulders can retain their old discontinuities. No wider city repair is claimed.\n\nActual Godot same-eye visual review is required. New bank faces change local\ncollision crops, so runtime reuse or affected replay must be decided by QA.\nThis candidate does not yet carry a visual or runtime pass.\n''')
 write(out/'FROZEN.json',dict(status='IMMUTABLE_SOURCE_CANDIDATE_VISUAL_RUNTIME_PENDING',files={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(out.iterdir())if p.is_file()},source_snapshot=ref(snap/'manifest.json')))
 print(json.dumps(dict(patch=ref(out/'surface_patch.json'),routes=ref(out/'routes.json'),boundary_routes=ref(out/'boundary_routes.json'),index=ref(out/'index.json'))))
if __name__=='__main__':main()
