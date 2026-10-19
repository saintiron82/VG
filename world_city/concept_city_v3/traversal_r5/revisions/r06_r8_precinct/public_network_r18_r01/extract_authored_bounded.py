import json,pathlib,resource,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent;R=next(p for p in H.parents if(p/'voxel_character').is_dir());D=R/'world_city/concept_city_v3';limit=3*1024**3
args=[sys.executable,str(H/'prepare.py'),'--scene',str((D/'evidence/r8_district_61_noble_r02_authored/scene.json').relative_to(R)),'--scene-sha','661bb8fa764d181936312602f0196800fc3d534d42d7277a56c6d72e833748c1','--binding',str((D/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_entry_batch_r02/activation_binding.json').relative_to(R)),'--routes',str((H/'route_catalog_61_noble_r06.json').relative_to(R))]
def bounded():resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
start=time.monotonic()
with(H/'evidence/preparation.log').open('x')as f:p=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,preexec_fn=bounded,cwd=R)
out=dict(command=args,exit_code=p.returncode,elapsed_s=time.monotonic()-start,address_space_limit_bytes=limit,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
with(H/'evidence/extraction_metrics.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(out));raise SystemExit(p.returncode)
