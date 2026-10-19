"""Trace real project reads during one normal scene build for disk-bounded smoke.

The complete archive still contains all history. This trace only bounds the
independent extraction used to prove the selected build has no hidden inputs.
"""
import sys,pathlib,json,hashlib,os
ROOT=next(p for p in pathlib.Path(__file__).resolve().parents if(p/'voxel_character').is_dir())
def main(binding,destination):
 reads=set();active=True
 def audit(event,args):
  if not active or event!='open'or not args or not isinstance(args[0],str):return
  mode=args[1]if len(args)>1 else None;flags=args[2]if len(args)>2 else 0
  if isinstance(mode,str)and not('r'in mode or'+'in mode):return
  if mode is None and flags&os.O_WRONLY:return
  try:p=pathlib.Path(args[0]).resolve()
  except(ValueError,TypeError,OSError):return
  if p.is_relative_to(ROOT):reads.add(p)
 sys.addaudithook(audit)
 from .build_scene import main as build,a
 build(binding,destination)
 dest=pathlib.Path(destination).resolve();source=dest/'scene.json'
 # Untouched assets inherited from R7 are not read by placement assembly.
 # Verify and include every actual runtime master/render dependency explicitly.
 scene=json.loads(source.read_bytes())
 for asset in scene['common_assets'].values():a.asset_record(asset)
 active=False
 files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(reads)if p.is_file()and'__pycache__'not in p.parts}
 supplemental=[]
 for p in sorted((ROOT/'world_city/concept_city_v3/preview_r4').rglob('*.json')):
  if '.godot'not in p.parts:supplemental.append(dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 report=dict(schema='riverstone.scene_build_read_closure.v1',authored_scene=dict(path=str(source.relative_to(ROOT)),sha256=hashlib.sha256(source.read_bytes()).hexdigest()),build_binding=dict(path=str(pathlib.Path(binding).resolve().relative_to(ROOT)),sha256=hashlib.sha256(pathlib.Path(binding).read_bytes()).hexdigest()),files=files,additional_runtime_dependencies=supplemental,actual_project_read_count=len(files),policy='Successful normal build input reads plus explicit verification of every actual native master/render dependency. Full archive retains all historical data; independent smoke extracts this closure plus all code/config and project runtime JSON, and denies reads from original repo.')
 (dest/'build_read_closure.json').write_text(json.dumps(report,indent=2)+'\n');print('READ_CLOSURE',len(files),sum((ROOT/n).stat().st_size for n in files),flush=True)
if __name__=='__main__':main(*sys.argv[1:])
