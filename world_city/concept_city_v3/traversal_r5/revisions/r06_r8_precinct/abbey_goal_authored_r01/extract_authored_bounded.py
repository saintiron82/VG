import json,pathlib,resource,subprocess,sys,time
H=pathlib.Path(__file__).resolve().parent;R=next(p for p in H.parents if(p/'voxel_character').is_dir());D=R/'world_city/concept_city_v3';limit=3*1024**3
args=[sys.executable,str(H/'prepare.py'),'--scene',str((D/'evidence/r8_final110_layout_review_r05/scene.json').relative_to(R)),'--scene-sha','29466dbc33d5926895c236e2f62f6a1f7554614a5f794cb37571555baff27d85','--binding',str((D/'registered_integration/r8/final_exterior_candidate_r01/whole_city_activation_r03/activation_binding.json').relative_to(R)),'--routes',str((H.parent/'primary_goals_extension_r01/route_catalog_491_r02.json').relative_to(R))]
def bounded():resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
start=time.monotonic()
with(H/'evidence/preparation.log').open('x')as f:p=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,preexec_fn=bounded,cwd=R)
out=dict(command=args,exit_code=p.returncode,elapsed_s=time.monotonic()-start,address_space_limit_bytes=limit,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
with(H/'evidence/extraction_metrics.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(out));raise SystemExit(p.returncode)
