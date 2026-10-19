"""Finite R7 promotion over the actually reviewed and replayed R6 scene.

Only hash-bound producer patches and existing common cache packs are composed.
No city-wide terrain generation, implicit fill or separate engine is used.
"""
import copy,json,sys,time
from pathlib import Path
from ..r6 import apply_packs as a, merge_patches
from ...registered_topography.revisions.r15_merchant_local_patch import frozen
from . import surface_guard

HERE=Path(__file__).resolve().parent
BASE_SHA='6e441b9ca417db63dccbb0bbccd48aa59e6a2a62079cdeeb3e5440d78f654844'

def verified(row):return a.load(a.source_file(row['path']),row['sha256'])

def build(binding):
    if binding.get('status')!='sources_reviewed_ready_for_visual':
        raise ValueError('Producer acceptance has not authorized this binding')
    if binding['base_scene']['sha256']!=BASE_SHA:
        raise ValueError('Not the corrected and replayed R6 base')
    scene=verified(binding['base_scene'])
    for row in binding['producer_evidence']:verified(row)
    if not binding['patches'] or not binding['packs']:
        raise ValueError('Expected both owned ground and native additions')
    patches=[verified(row) for row in binding['patches']]
    # Reject wrong winding at the author/source boundary, before composition.
    source_guards=[surface_guard.audit_patch(p) for p in patches]
    merged=merge_patches.merge(patches,base_scene_sha256=BASE_SHA)
    merged['id']='R7_COMPOSED_LOCAL_EDITS'
    merge_patches.validate_against_scene(scene,merged)
    result=frozen.apply_edits(scene,merged)
    # The reused pure applier's legacy provenance constant describes R5.
    # Its actual index/hash checks above bind this operation to corrected R6.
    result['local_terrain_patch']['base_scene_sha256']=BASE_SHA
    ledgers=[]
    for row in binding['packs']:
        pack=verified(row)
        result,ledger=a.apply_pack(result,pack,row['name'],dict(path=row['path'],sha256=row['sha256']))
        ledgers.append(ledger)
        if pack.get('collision_contracts'):
            result['collision_contracts']=copy.deepcopy(result.get('collision_contracts',[]))+copy.deepcopy(pack['collision_contracts'])
    result['materials']=copy.deepcopy(result['materials'])
    for key,value in binding.get('new_materials',{}).items():
        if key in result['materials'] and result['materials'][key]!=value:
            raise ValueError('Existing material recolor would leak: '+key)
        result['materials'][key]=value
    if set(result['surfaces'])-set(result['materials']):raise ValueError('Unknown terrain material')
    result['inspection_cameras']=copy.deepcopy(result['inspection_cameras'])
    for name,camera in binding.get('review_cameras',{}).items():
        if name in result['inspection_cameras']:raise ValueError('Do not overwrite an earlier camera')
        result['inspection_cameras'][name]=copy.deepcopy(camera)
    result['counts']=dict(result['counts'])
    result['counts'].update(common_instances=len(result['common_instances']),
        actual_remaining_proxy_boxes=len(result['boxes']),support_proxies=len(result['boxes']),
        terrain_triangles=sum(len(v)//3 for v in result['surfaces'].values()),
        r7_local_patches=len(patches))
    used={p['asset_key'] for p in result['common_instances']}|set(result['bridge_mechanism']['asset_keys'])
    result['common_assets']={k:v for k,v in result['common_assets'].items() if k in used}
    result['counts']['common_unique_assets']=len(used)
    a.validate_instances(result)
    guard=surface_guard.audit_scene(result)
    assert result['inspection_cameras']['registered']==scene['inspection_cameras']['registered']
    assert result['bridge_mechanism']==scene['bridge_mechanism']
    assert result['surfaces']['water']==scene['surfaces']['water']
    assert result['collision_contracts'][:len(scene['collision_contracts'])]==scene['collision_contracts']
    result['status']='r7_finite_native_candidate_pending_actual_review'
    result['limits']=copy.deepcopy(binding['limits'])
    result['r7_provenance']=dict(binding_sha256=a.digest(binding),base_scene=binding['base_scene'],
        producer_evidence=binding['producer_evidence'],pack_ledgers=ledgers,
        source_patch_guards=[{k:v for k,v in g.items() if k!='reports'} for g in source_guards],
        final_terrain_winding={k:v for k,v in guard.items() if k!='reports'},
        whole_city_complete=False,registered_camera_unchanged=True)
    return result,merged,guard

def main(binding_path,destination):
    dest=Path(destination);dest.mkdir(parents=True,exist_ok=True)
    path=dest/'scene.json'
    if path.exists():raise ValueError('Preserve prior scenes')
    start=time.monotonic();binding=a.load(binding_path);scene,patch,guard=build(binding)
    path.write_text(json.dumps(scene,separators=(',',':'),allow_nan=False)+'\n')
    for name,data in [('patch.json',patch),('surface_guard.json',guard)]:
        (dest/name).write_text(json.dumps(data,separators=(',',':'),allow_nan=False)+'\n')
    report=dict(scene=dict(path=a.rel(path),sha256=a.sha(path)),counts=scene['counts'],
        binding=dict(path=a.rel(binding_path),sha256=a.sha(binding_path)),seconds=time.monotonic()-start,
        status='native_candidate_pending_actual_render_and_physics',whole_city_complete=False)
    (dest/'build_record.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main(*sys.argv[1:])
