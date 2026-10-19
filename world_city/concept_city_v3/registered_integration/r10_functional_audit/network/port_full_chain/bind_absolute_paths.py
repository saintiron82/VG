"""Normalize source-reference paths for Godot project-relative runtime; hashes unchanged."""
import pathlib,json,hashlib
O=pathlib.Path(__file__).resolve().parent;ROOT=O.parent.parents[4];P=O/'replay_r01';d=json.loads((P/'prepared.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();mapping={}
for k,v in d['sources'].items():
 p=pathlib.Path(v['path']);p=p if p.is_absolute() else ROOT/p;assert sha(p)==v['sha256'];mapping[k]={'original_path':v['path'],'absolute_path':str(p),'sha256_unchanged':v['sha256']};v['path']=str(p)
d['sources']['absolute_bind_helper']={'path':str(pathlib.Path(__file__)),'sha256':sha(pathlib.Path(__file__))};d['path_normalization_provenance']={'original_prepared_sha256':sha(P/'prepared.json'),'only_change':'Source reference path resolution; geometry, routes, controllers and hashes unchanged.','mapping':mapping};(P/'prepared_bound_r02.json').write_text(json.dumps(d,indent=2)+'\n');print('All source paths now absolute and same hashes verified')
