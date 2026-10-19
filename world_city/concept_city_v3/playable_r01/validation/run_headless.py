#!/usr/bin/env python3
"""Run one validation process with explicit writable XDG paths and unique evidence."""
import argparse,datetime,json,os,pathlib,subprocess,sys,tempfile
p=argparse.ArgumentParser();p.add_argument('--suite',choices=['routes','failclosed'],default='routes');p.add_argument('--mode',choices=['follow','replay'],default='follow');p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--input',type=pathlib.Path);p.add_argument('--case');p.add_argument('--repo-root',type=pathlib.Path);a=p.parse_args()
root=pathlib.Path(__file__).resolve().parent.parent;out=a.out.resolve()
if out.exists():raise SystemExit('Refusing existing evidence directory '+str(out))
if a.mode=='replay' and not a.input:raise SystemExit('--input required for replay')
out.mkdir(parents=True);home=pathlib.Path(tempfile.mkdtemp(prefix='lily-city-validation-'))
env=os.environ.copy();env['HOME']=str(home)
for var,name in [('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config'),('XDG_CACHE_HOME','cache'),('XDG_STATE_HOME','state'),('XDG_RUNTIME_DIR','runtime')]:
 d=home/name;d.mkdir(mode=0o700);env[var]=str(d)
cmd=['godot','--headless','--path',str(root),'--fixed-fps','60','validation/LilyCityValidation.tscn' if a.suite=='routes' else 'validation/FailClosedValidation.tscn','--','--mode='+a.mode,'--out='+str(out)]
if a.input:cmd.append('--input='+str(a.input.resolve()))
if a.case:cmd.append('--case='+a.case)
if a.repo_root:cmd.append('--repo-root='+str(a.repo_root.resolve()))
metadata={'command':cmd,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sandbox_environment':{k:env[k] for k in ['HOME','XDG_DATA_HOME','XDG_CONFIG_HOME','XDG_CACHE_HOME','XDG_STATE_HOME','XDG_RUNTIME_DIR']}}
(out/'invocation.json').write_text(json.dumps(metadata,indent=2)+'\n')
with (out/'run.log').open('w') as log:result=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
metadata.update(exit_code=result.returncode,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(out/'completion.json').write_text(json.dumps(metadata,indent=2)+'\n')
print((out/'run.log').read_text());sys.exit(result.returncode)
