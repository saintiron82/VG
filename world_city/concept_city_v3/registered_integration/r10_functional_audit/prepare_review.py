"""Freeze actual Godot review source and exact functional-candidate inputs."""
import argparse,hashlib,json,shlex,shutil,math
from pathlib import Path
R=Path(__file__).resolve().parents[4];C=R/'world_city/concept_city_v3';H=Path(__file__).resolve().parent
BASE=C/'evidence/r8_final110_runtime_r01/scene.json';ADD=C/'assemblies/ordinary/registered/district_fabric_r01/primary_bent_goals_r01/castle/surface_patch.json'
def sha(p):
 with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main(candidate,out,institution_routes=None,views=None,gate_candidate=None):
 candidate=(R/candidate).resolve();out=(R/out).resolve();assert candidate.is_relative_to(R)and out.is_relative_to(C/'evidence')and not out.exists()
 ledger=json.loads((candidate/'candidate_ledger.json').read_text());assert sha(candidate/'index.json')==ledger['visual_index_sha256'];assert sha(candidate/'surface_patch.json')==ledger['surface_patch_sha256']
 out.mkdir(parents=True);src=out/'source';src.mkdir()
 for p in (C/'preview_r9').iterdir():
  if p.is_file()and p.suffix in ('.gd','.tscn','.godot'):shutil.copy2(p,src/p.name)
 cameras={};camera_sources=[]
 institution_routes=institution_routes or ['world_city/concept_city_v3/registered_integration/r10_functional_audit/institution_entries/candidate_r01/routes.json']
 if isinstance(institution_routes,str):institution_routes=[institution_routes]
 institution_paths=[(R/name).resolve()for name in institution_routes]
 assert all(p.is_relative_to(R)for p in institution_paths)
 water_path=H/'public_water/frozen_r01/routes.json'
 for institution_path in institution_paths:
  for row in json.loads(institution_path.read_text())['cameras']:
   assert row['id']not in cameras,'Duplicate institution camera'
   cameras[row['id']]={'position_m':row['position'],'target_m':row['target']}
 for row in json.loads(water_path.read_text())['routes']:
  side=row['id'].split(':')[1];a=row['points_xyz_m'][0];b=row['points_xyz_m'][-1]
  cameras['r10_public_draw_'+side+'_eye']={'position_m':[a[0],a[1]+1.65,a[2]],'target_m':[b[0],b[1]+1,b[2]],'eye_height_m':1.65}
 if gate_candidate:
  gate=(R/gate_candidate).resolve();assert gate.is_relative_to(R)
  frozen=json.loads((gate/'FROZEN.json').read_text())
  for name,digest in frozen['files'].items():assert sha(gate/name)==digest,'Changed frozen gate input: '+name
  template=C/'registered_integration/r9/gate_view_candidate_r01/camera_pack.json'
  cameras.update(json.loads(template.read_text())['inspection_cameras'])
  for row in json.loads((gate/'routes.json').read_text())['routes']:
   if 'gate_waypoint_index'not in row:continue
   gate_point=row['points'][row['gate_waypoint_index']];after=row['points'][row['gate_waypoint_index']+1:]
   if not after:continue
   eye=min(after,key=lambda v:abs(math.hypot(v[0]-gate_point[0],v[2]-gate_point[2])-25))
   cameras['r9_'+row['group'].lower()+'_gate_eye']={'position_m':[eye[0],eye[1]+1.65,eye[2]],'target_m':[gate_point[0],gate_point[1]+3,gate_point[2]],'eye_height_m':1.65,'source_route':row['id']}
  camera_sources += [template,gate/'FROZEN.json',gate/'routes.json']
 write(out/'camera_pack.json',{'schema':'riverstone.city.visual_addendum.v1','base_scene_sha256':ledger['base_scene_sha256'],'common_assets':{},'add_instances':[],'remove_instance_ids':[],'inspection_cameras':cameras})
 index=json.loads((candidate/'index.json').read_text());index['packs'].append({'path':str((out/'camera_pack.json').relative_to(R)),'sha256':sha(out/'camera_pack.json')});write(out/'index.json',index)
 author=out/'prepare_review_snapshot.py';shutil.copy2(Path(__file__).resolve(),author)
 inputs=[BASE,ADD,candidate/'candidate_ledger.json',candidate/'surface_patch.json',out/'index.json',water_path,author]+institution_paths+camera_sources+[R/r['path']for r in index['packs']]+list(src.iterdir())
 write(out/'runtime_source_binding.json',{'status':'STAGED_NOT_EXECUTED','source_sha256':{str(p.relative_to(R)):sha(p)for p in inputs},'candidate':str(candidate.relative_to(R)),'limits':['Actual runtime/visual review is distinct from static source validation','Each gate/institution version retains its own source, route, and runtime acceptance ledger','No whole-city operation, water quality/flow, household interior or NPC claim']})
 common=['/opt/godot/4.6.3/Godot_v4.6.3-stable_linux.x86_64','--path',str(src),'--audio-driver','Dummy','--rendering-method','gl_compatibility']
 args=['--manifest='+str(BASE),'--repo-root='+str(R),'--visual-pack-index='+str(out/'index.json'),'--finite-surface-patch='+str(candidate/'surface_patch.json'),'--finite-surface-patch-sha256='+sha(candidate/'surface_patch.json'),'--terrain-addendum='+str(ADD),'--terrain-addendum-sha256='+sha(ADD),'--lighting=r9','--material-profile=baseline','--hide-hud']
 views=views or 'registered,r10_public_draw_2,r10_public_draw_6,r10_public_draw_2_eye,r10_public_draw_6_eye,R10_ABBEY_PUBLIC_GATE_EYE,R10_ABBEY_WARD_APPROACH'
 for mode in ('headless','capture'):
  command=common+(['--headless']if mode=='headless'else['--resolution','1280x853'])+['--']+args
  if mode=='headless':command+=['--headless-check','--report='+str(out/'headless.json')]
  else:command+=['--canvas-width=1536','--canvas-height=1024','--capture-views='+views,'--capture-dir='+str(out),'--report='+str(out/'runtime.json')]
  script='#!/bin/sh\nset -eu\nexport HOME=/workspace/shared/city-r9-home\nexport XDG_CONFIG_HOME="$HOME/.config" XDG_CACHE_HOME="$HOME/.cache" XDG_DATA_HOME="$HOME/.local/share" LIBGL_ALWAYS_SOFTWARE=1\n'
  script+='test ! -e '+shlex.quote(str(out/('headless.json'if mode=='headless'else views.split(',')[0]+'.png')))+'\nset +e\n'
  script+=' '.join(map(shlex.quote,command))+' > '+shlex.quote(str(out/(mode+'.log')))+' 2>&1\nstatus=$?\nprintf "%s\\n" "$status" > '+shlex.quote(str(out/(mode+'_exit.txt')))+'\nexit "$status"\n';(out/(mode+'.sh')).write_text(script)
 print(out)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--output',required=True);p.add_argument('--institution-routes',action='append');p.add_argument('--views');p.add_argument('--gate-candidate');a=p.parse_args();main(a.candidate,a.output,a.institution_routes,a.views,a.gate_candidate)
