"""Read-only event observer around an unchanged, hash-bound capsule controller."""
import argparse, hashlib, json, os, pathlib, resource, subprocess, time
H=pathlib.Path(__file__).resolve().parent
ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p): return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def write(p,v):
 with p.open('x') as f: json.dump(v,f,indent=2);f.write('\n')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--prepared',type=pathlib.Path,default=H.parent/'ordinary61_diagnostic_r01/prepared_runtime.json');parser.add_argument('--cases',default='BLOCK_002:R8_C003:PUBLIC_ENTRY');parser.add_argument('--name',default='c003_original');args=parser.parse_args()
 prepared=args.prepared.resolve();d=json.loads(prepared.read_bytes());cases=args.cases.split(',');assert set(cases)<=set(r['id'] for r in d['routes'])
 assert (H/'Traversal.gd').read_bytes()==(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd').read_bytes()
 assert (H/'RenderData.gd').read_bytes()==(ROOT/'voxel_character/common/preview/RenderData.gd').read_bytes()
 assert (H/'project.godot').read_bytes()==(H.parent.parent/'ordinary61_diagnostic_r01/project.godot').read_bytes()
 for source in d['sources'].values(): assert sha(pathlib.Path(source['path']))==source['sha256']
 for path,digest in d['implementation_hashes'].items(): assert sha(ROOT/path)==digest
 evidence=H/'evidence'/args.name;evidence.mkdir();report=evidence/'replay.json';events=evidence/'observer_events.jsonl';log=evidence/'replay.log'
 env=dict(os.environ,GODOT_SILENCE_ROOT_WARNING='1',XDG_CACHE_HOME=str(H/'.runtime/cache'),XDG_DATA_HOME=str(H/'.runtime/data'),XDG_CONFIG_HOME=str(H/'.runtime/config'))
 command=['godot','--headless','--disable-render-loop','--fixed-fps','60','--path',str(H),'res://Traversal.tscn','--','--prepared='+str(prepared),'--report='+str(report),'--observer='+str(events),'--routes='+args.cases]
 manifest=dict(schema='riverstone.read_only_traversal_observer_run.v1',prepared=ref(prepared),scene=d['sources']['scene'],cases=cases,implementation={p.name:ref(p)for p in [H/'Traversal.gd',H/'RenderData.gd',H/'ReadOnlyObserver.gd',H/'Traversal.tscn',H/'project.godot',H/'run_observer.py']},original_controller=ref(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd'),original_loader=ref(ROOT/'voxel_character/common/preview/RenderData.gd'),command=command,limits=['Controller, loader and physics settings byte-identical. Observer child reads after controller priority zero at priority ten.','Observer does not mutate body, velocity, transforms, route, world, result, thresholds or acceptance.','Repeat support ray is explicitly diagnostic; its result is not the original controller local variable. Slide contact APIs expose shape index, not triangle face index.'])
 write(evidence/'run_manifest.json',manifest);start=time.monotonic()
 with log.open('x') as f: result=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,env=env)
 metrics=dict(exit_code=result.returncode,wall_seconds=time.monotonic()-start,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
 write(evidence/'metrics.json',metrics);print(json.dumps(metrics));raise SystemExit(0 if result.returncode in [0,2] else result.returncode)
if __name__=='__main__': main()
