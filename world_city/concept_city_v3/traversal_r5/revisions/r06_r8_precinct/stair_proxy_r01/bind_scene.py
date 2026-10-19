"""Pure, fail-closed binding for the tested native-stair collision representation.
No scene is written by this module. The caller owns the new composed scene.
"""
import copy, hashlib, json, pathlib, math
HERE=pathlib.Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'voxel_character').is_dir())
BASE_SHA='4113a70f323b5481a118eb4c70f0511ace0741e14cb9fbfb1b3031843b303769'
CONTRACT_SHA='b6649ab28d25707b4c181eeb1c8966f10c9c58b1af5533e3098cac9cc7aeaea9'
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(pathlib.Path(p).read_bytes())
def validate_contract():
    path=HERE/'collision_contract.json'
    assert sha(path)==CONTRACT_SHA, 'Contract changed'
    c=read(path)
    for key in ['native_source','replacement_local_mesh']:
        assert sha(ROOT/c[key]['path'])==c[key]['sha256'], key
    mesh=read(ROOT/c['replacement_local_mesh']['path'])
    assert len(mesh['triangles'])==len(c['add_triangles_world_xyz_m'])==388
    t=c['replacement_transform']; co=math.cos(t['yaw_rad']); si=math.sin(t['yaw_rad']); o=t['position_m']
    expected=[[[co*v[0]+si*v[2]+o[0],v[1]+o[1],-si*v[0]+co*v[2]+o[2]] for v in tri] for tri in mesh['triangles']]
    assert expected==c['add_triangles_world_xyz_m'], 'World/local triangle mismatch'
    return c

def bind_exact_base(scene_path):
    """Return a new scene with one appended collision contract; preserve all visuals."""
    assert sha(scene_path)==BASE_SHA, 'Requires exact tested bank-repaired scene'
    scene=read(scene_path); c=validate_contract(); pid=c['native_placement_id']
    rows=[p for p in scene['common_instances'] if p['id']==pid]
    assert len(rows)==1
    p=rows[0]
    assert p['position_m']==c['replacement_transform']['position_m']
    assert p['yaw_rad']==c['replacement_transform']['yaw_rad']
    assert p.get('scale',[1,1,1])==[1,1,1]
    assert scene['common_assets'][p['asset_key']]['render_sha256']==c['native_source']['sha256']
    assert not any(q['id']==c['id'] for q in scene.get('collision_contracts',[]))
    assert not any(pid in q.get('disable_native_mesh_collider_ids',[]) for q in scene.get('collision_contracts',[]))
    result=dict(scene)
    result['collision_contracts']=copy.deepcopy(scene.get('collision_contracts',[]))+[c]
    assert all(result[k]==v for k,v in scene.items() if k!='collision_contracts')
    assert result['collision_contracts'][:-1]==scene.get('collision_contracts',[])
    return result
