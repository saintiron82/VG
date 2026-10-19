"""One observed replay, with exact collision hashes and logging-only controller diff."""
import pathlib,json,hashlib,os,subprocess,time
O=pathlib.Path(__file__).resolve().parent;R=O/'ray_diagnostic_r01';P=R/'prepared_bound_r02.json';d=json.loads(P.read_text());sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
refs={v['path']:v['sha256'] for v in d['sources'].values()};refs.update({str(R/'Traversal.gd'):d['diagnostic_provenance']['diagnostic_controller_sha256'],str(R/'Traversal.original.gd'):d['diagnostic_provenance']['original_controller_sha256'],str(P):sha(P)})
for k,v in d['assets'].items():
 if isinstance(v,dict) and 'path' in v and 'sha256' in v: refs[v['path']]=v['sha256']
for p,h in refs.items():assert sha(p)==h,p
out=R/'evidence'/'diagnostic_r02';out.mkdir();env=dict(os.environ,GODOT_SILENCE_ROOT_WARNING='1')
for k,n in [('XDG_CACHE_HOME','cache'),('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config')]:q=R/'.runtime'/n;q.mkdir(parents=True,exist_ok=True);env[k]=str(q)
cmd=['godot','--headless','--disable-render-loop','--fixed-fps','60','--path',str(R),'res://Traversal.tscn','--','--prepared='+str(P),'--report='+str(out/'capsule.json')];t=time.monotonic()
with (out/'capsule.log').open('x') as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
changed=[p for p,h in refs.items() if sha(p)!=h];m={'command':cmd,'exit_code':r.returncode,'elapsed_s':time.monotonic()-t,'verified_sources':refs,'changed_sources':changed,'observation_only':True,'not_replacement_certificate':True,'report_sha256':sha(out/'capsule.json') if (out/'capsule.json').exists() else None};(out/'run_manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps({'exit_code':r.returncode,'changed_sources':changed,'report':str(out/'capsule.json')}));assert not changed
