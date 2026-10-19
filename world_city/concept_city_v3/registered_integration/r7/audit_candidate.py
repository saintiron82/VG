"""Independent composition invariants for the bounded R7 candidate."""
import json,sys
from pathlib import Path
from ..r6 import apply_packs as a
from .surface_guard import audit_scene

def audit(base,scene,binding):
    old={p['id']:p for p in base['common_instances']}
    actual={p['id']:p for p in scene['common_instances']}
    additions={};retired=set();new_asset_keys=set()
    for row in binding['packs']:
        pack=a.load(a.source_file(row['path']),row['sha256'])
        retired.update(pack.get('replaced_placement_ids',[]))
        additions.update({p['id']:p for p in pack['placements']})
        new_asset_keys.update(pack['assets'])
    assert set(actual)==(set(old)-retired)|set(additions)
    for identity,p in old.items():
        if identity not in retired:assert actual[identity]==p,identity
    for identity,p in additions.items():
        for key in ('asset_key','position_m','yaw_rad','scale','palette_id','palette_override'):
            if key in p:assert actual[identity][key]==p[key],(identity,key)
    for key in new_asset_keys:a.asset_record(scene['common_assets'][key])
    assert scene['inspection_cameras']['registered']==base['inspection_cameras']['registered']
    assert scene['bridge_mechanism']==base['bridge_mechanism']
    assert scene['surfaces']['water']==base['surfaces']['water']
    assert scene['collision_contracts'][:len(base['collision_contracts'])]==base['collision_contracts']
    for key,value in base['materials'].items():assert scene['materials'][key]==value,key
    guard=audit_scene(scene)
    return dict(status='pass_bounded_candidate_source',retained_native_instances=len(old)-len(retired),
        added_native_instances=len(additions),retired_native_instances=len(retired),
        common_new_asset_keys=len(new_asset_keys),all_base_native_transforms_and_palettes_unchanged=True,
        registered_camera_and_water_and_bridge_unchanged=True,original_collision_contracts_unchanged=True,
        terrain_upward_guard={k:v for k,v in guard.items() if k!='reports'},
        limits='Source equality is not actual-view or traversal approval; native instance counts include props and are not household counts.')

def main(binding_path,scene_path):
    binding=a.load(binding_path);base=a.load(a.source_file(binding['base_scene']['path']),binding['base_scene']['sha256'])
    scene=a.load(scene_path);report=audit(base,scene,binding)
    report['scene_sha256']=a.sha(scene_path)
    Path(scene_path).with_name('candidate_source_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main(*sys.argv[1:])
