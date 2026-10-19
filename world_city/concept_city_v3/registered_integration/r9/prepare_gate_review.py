"""Stage one immutable Godot review from a producer-frozen gate candidate.
No scene duplication and no terrain sampling. Runtime QA remains a separate ledger.
"""
import argparse, hashlib, json, shutil, shlex, math
from pathlib import Path
R=Path(__file__).resolve().parents[4]
C=R/'world_city/concept_city_v3'
BASE=C/'evidence/r8_final110_runtime_r01/scene.json'
ADD=C/'assemblies/ordinary/registered/district_fabric_r01/primary_bent_goals_r01/castle/surface_patch.json'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n')
def stage(candidate,out):
 candidate=(R/candidate).resolve();out=(R/out).resolve()
 assert candidate.is_relative_to(R) and out.is_relative_to(C/'evidence')
 frozen=json.loads((candidate/'FROZEN.json').read_text())
 for name,digest in frozen['files'].items():
  assert sha(candidate/name)==digest, 'Frozen input changed: '+name
 assert not out.exists(), 'Preserve earlier review'
 out.mkdir(parents=True)
 routes=json.loads((candidate/'routes.json').read_text())
 cameras=json.loads((C/'registered_integration/r9/gate_view_candidate_r01/camera_pack.json').read_text())
 for route in routes['routes']:
  if 'gate_waypoint_index'not in route:continue
  side=route['group'].lower();gate=route['points'][route['gate_waypoint_index']];after=route['points'][route['gate_waypoint_index']+1:]
  if not after:continue
  eye=min(after,key=lambda v:abs(math.hypot(v[0]-gate[0],v[2]-gate[2])-25))
  cameras['inspection_cameras']['r9_'+side+'_gate_eye']={'position_m':[eye[0],eye[1]+1.65,eye[2]],'target_m':[gate[0],gate[1]+3,gate[2]],'eye_height_m':1.65,'source_route':route['id'],'purpose':'Current frozen approach waypoint +1.65m eye, looking at actual gate.'}
 cameras['provenance']={'frozen_gate_route_path':str((candidate/'routes.json').relative_to(R)),'sha256':sha(candidate/'routes.json'),'camera_limits':'Eye heights use current frozen route waypoints; actual support is independently runtime-tested.'}
 write(out/'camera_pack.json',cameras)
 index=json.loads((candidate/'index.json').read_text())
 index['packs'].append({'path':str((out/'camera_pack.json').relative_to(R)),'sha256':sha(out/'camera_pack.json')})
 write(out/'index.json',index)
 src=out/'source';src.mkdir()
 for p in (C/'preview_r9').iterdir():
  if p.is_file() and p.suffix in ('.gd','.tscn','.godot'):shutil.copy2(p,src/p.name)
 inputs={str(p.relative_to(R)):sha(p)for p in [BASE,ADD,candidate/'surface_patch.json',out/'index.json',candidate/'FROZEN.json']}
 for ref in index['packs']:inputs[ref['path']]=sha(R/ref['path'])
 inputs.update({str(p.relative_to(R)):sha(p)for p in src.iterdir()if p.is_file()})
 write(out/'runtime_source_binding.json',{'status':'STAGED_NOT_EXECUTED','source_sha256':inputs,'frozen_candidate':str(candidate.relative_to(R)),'limits':['Actual native source snapshot for this review','Gate runtime and cart verification must be read from independent frozen QA results','Old493 results apply to old source, not whole new city']})
 common=['/opt/godot/4.6.3/Godot_v4.6.3-stable_linux.x86_64','--path',str(src),'--audio-driver','Dummy','--rendering-method','gl_compatibility']
 args=['--manifest='+str(BASE),'--repo-root='+str(R),'--visual-pack-index='+str(out/'index.json'),'--finite-surface-patch='+str(candidate/'surface_patch.json'),'--finite-surface-patch-sha256='+sha(candidate/'surface_patch.json'),'--terrain-addendum='+str(ADD),'--terrain-addendum-sha256='+sha(ADD),'--lighting=r9','--material-profile=baseline','--hide-hud']
 for mode in ('headless','capture'):
  command=common+(['--headless']if mode=='headless'else['--resolution','1280x853'])+['--']+args
  if mode=='headless':command+=['--headless-check','--report='+str(out/'headless.json')]
  else:command+=['--canvas-width=1536','--canvas-height=1024','--capture-views=registered,r9_west_gate_oblique,r9_east_gate_oblique,r9_west_gate_eye,r9_east_gate_eye','--capture-dir='+str(out),'--report='+str(out/'runtime.json')]
  script='#!/bin/sh\nset -eu\nexport HOME=/workspace/shared/city-r9-home\nexport XDG_CONFIG_HOME="$HOME/.config" XDG_CACHE_HOME="$HOME/.cache" XDG_DATA_HOME="$HOME/.local/share" LIBGL_ALWAYS_SOFTWARE=1\n'
  script+='test ! -e '+shlex.quote(str(out/('headless.json'if mode=='headless'else'registered.png')))+'\nset +e\n'
  script+=' '.join(map(shlex.quote,command))+' > '+shlex.quote(str(out/(mode+'.log')))+' 2>&1\nstatus=$?\nprintf "%s\\n" "$status" > '+shlex.quote(str(out/(mode+'_exit.txt')))+'\nexit "$status"\n'
  (out/(mode+'.sh')).write_text(script)
 print(out)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--output',required=True);a=p.parse_args();stage(a.candidate,a.output)
