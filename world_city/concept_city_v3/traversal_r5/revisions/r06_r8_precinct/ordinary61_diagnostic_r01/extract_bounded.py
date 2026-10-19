import json,pathlib,resource,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent;R=next(p for p in H.parents if(p/'voxel_character').is_dir());D=R/'world_city/concept_city_v3';limit=3*1024**3
args=[sys.executable,str(H/'prepare.py'),'--scene',str((D/'evidence/r8_district_61_assembly_preflight_r01/scene.json').relative_to(R)),'--scene-sha','643851e9554c335fc5af4f1e1b6b51af19d3e67b4b1bc578c091539f29a29299','--binding',str((D/'registered_integration/r8/nonvisual61_binding_1115.json').relative_to(R)),'--routes',str((H/'route_catalog_bound_r02.json').relative_to(R))]
def bounded():resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
start=time.monotonic()
with(H/'evidence/preparation.log').open('x')as f:p=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,preexec_fn=bounded,cwd=R)
out=dict(command=args,exit_code=p.returncode,elapsed_s=time.monotonic()-start,address_space_limit_bytes=limit,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
with(H/'evidence/extraction_metrics.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(out));raise SystemExit(p.returncode)
