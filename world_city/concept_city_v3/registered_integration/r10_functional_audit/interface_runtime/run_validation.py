#!/usr/bin/env python3
"""Run new bounded gate evidence; refuse overwrites and source drift."""
import argparse,hashlib,json,os,pathlib,subprocess,time
H=pathlib.Path(__file__).resolve().parent
ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def sha(p):
 with pathlib.Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--prepared',type=pathlib.Path,required=True);ap.add_argument('--kind',choices=['capsule','cart','both'],default='both');ap.add_argument('--tag',required=True);args=ap.parse_args();p=args.prepared.resolve();d=json.loads(p.read_bytes());assert p.is_relative_to(H);base=p.parent
 refs={str(pathlib.Path(v['path'])):v['sha256']for v in d['sources'].values()};refs.update({str(ROOT/k):v for k,v in d['implementation_hashes'].items()});refs[str(p)]=sha(p)
 for path,digest in refs.items():assert sha(path)==digest,'Source changed: '+path
 assert sha(base/'Traversal.gd')==sha(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd'),'Controller altered'
 assert sha(base/'RenderData.gd')==sha(ROOT/'voxel_character/common/preview/RenderData.gd'),'Common loader altered'
 out=base/'evidence'/args.tag;out.mkdir();env=dict(os.environ,GODOT_SILENCE_ROOT_WARNING='1')
 for key,leaf in [('XDG_CACHE_HOME','cache'),('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config')]:v=base/'.runtime'/leaf;v.mkdir(parents=True,exist_ok=True);env[key]=str(v)
 runs=[]
 for kind in ['capsule','cart']if args.kind=='both'else[args.kind]:
  report=out/(kind+'.json');log=out/(kind+'.log');scene='Traversal.tscn'if kind=='capsule'else'CartClearance.tscn';cmd=['godot','--headless','--disable-render-loop','--fixed-fps','60','--path',str(base),'res://'+scene,'--','--prepared='+str(p),'--report='+str(report)];start=time.monotonic()
  with log.open('x')as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
  changed=[path for path,digest in refs.items()if sha(path)!=digest];result=json.loads(report.read_bytes())if report.exists()else{'status':'missing_report'}
  runs.append({'kind':kind,'exit_code':r.returncode,'elapsed_s':time.monotonic()-start,'command':cmd,'report_path':str(report),'report_sha256':sha(report)if report.exists()else None,'log_sha256':sha(log),'status':result['status'],'summary':result.get('summary'),'changed_sources':changed})
  (out/'run_manifest.json').write_text(json.dumps({'prepared_path':str(p),'prepared_sha256':sha(p),'runs':runs},indent=2)+'\n');print(json.dumps(runs[-1],indent=2),flush=True)
  assert not changed,'Sources changed during replay'
 return 0 if all(r['exit_code']==0 and r['status']=='pass'for r in runs)else 2
if __name__=='__main__':raise SystemExit(main())
