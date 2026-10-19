"""Lossless evidence retention for transient common-cell render compilation."""
from contextlib import contextmanager
import gzip
import json
from pathlib import Path
import platform
import zlib


@contextmanager
def cell_stream(path,render_only):
    if render_only:yield None
    else:
        with gzip.open(path,'wt',encoding='utf-8',compresslevel=5) as stream:yield stream


def preserve_replay_sources(a,here,asset_key,master_path,source_path,catalog_path,rules_path,code_paths):
    directory=here/'replay_code';directory.mkdir(exist_ok=True);files={}
    for role,path in code_paths.items():
        path=Path(path);sha=a.sha(path);snapshot=directory/(role+'_'+sha[:16]+path.suffix)
        if not snapshot.exists():snapshot.write_bytes(path.read_bytes())
        if a.sha(snapshot)!=sha:raise ValueError('Replay code snapshot hash mismatch')
        files[role]={'original_path':str(path.resolve().relative_to(a.ROOT)),'snapshot_path':str(snapshot.relative_to(a.ROOT)),'sha256':sha}
    return {'schema':'riverstone.house_detail.replay_contract.v1','asset_key':asset_key,
            'inputs':{role:{'path':str(Path(path).resolve().relative_to(a.ROOT)),'sha256':a.sha(path)} for role,path in
                      {'authored_master':master_path,'source_master':source_path,'catalog':catalog_path,'layer_rules':rules_path}.items()},
            'code_snapshots':files,'python_version':platform.python_version(),'zlib_version':zlib.ZLIB_VERSION,
            'command':['python',str((here/'layered_compile.py').relative_to(a.ROOT)),asset_key,'--catalog',str(Path(catalog_path).resolve().relative_to(a.ROOT)),'--rules',str(Path(rules_path).resolve().relative_to(a.ROOT)),'--render-only','--output-dir','<NEW_EMPTY_OUTPUT_DIRECTORY>'],
            'reproduction':'Restore the saved code versions at their original paths in an isolated copy, verify all input hashes, then run the command. Original source operations are actually sampled again; no retained voxel payload is required.',
            'equality_contract':'Fine occupancy/semantic and exposed face fingerprints must equal stats. Gzip byte identity across different zlib versions is not assumed.'}
