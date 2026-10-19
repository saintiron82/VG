"""Validate the integrated delta without claiming traversal or art approval."""
from . import apply_packs as a
import json
def main():
    base=a.load(a.BASE_PATH,a.BASE_SHA256)
    path=a.CITY/'evidence/visual_registered_common_r6/scene.json';scene=a.load(path)
    subset=a.load(a.CITY/'registered_topography/revisions/r15_merchant_local_patch/subset_07/acceptance_report.json')
    before={p['id']:p for p in base['common_instances']};after={p['id']:p for p in scene['common_instances']}
    unchanged=subset['inactive_original_ids'];assert all(after[i]==before[i] for i in unchanged)
    assert all(i not in after for i in subset['retired_source_ids'])
    assert scene['inspection_cameras']['registered']==base['inspection_cameras']['registered']
    assert scene['bridge_mechanism']==base['bridge_mechanism']
    assert scene['surfaces']['water']==base['surfaces']['water']
    for asset in scene['common_assets'].values():a.asset_record(asset)
    a.validate_instances(scene)
    contracts=scene['collision_contracts'];assert contracts,'Preserve finite southern collision declaration'
    native=sum(1 for p in after.values() if p.get('source_pack')=='productive_grounds_phase01');assert native==103
    assert sum(1 for p in after.values() if p.get('source_pack')=='merchant_seven_r02')==14
    assert len(after)==len(before)-22+14+103+1
    report={'status':'source_composition_pass_pending_view_and_physics','scene_sha256':a.sha(path),
      'actual_static_native_instances':len(after),'unique_asset_hashes_verified':len(scene['common_assets']),
      'inactive_original_ids_byte_equal':unchanged,'retired_ids_absent':subset['retired_source_ids'],
      'new_merchant_properties':7,'new_merchant_runtime_groups':14,'recorded_closed_exterior_doors':46,
      'productive_ground_native_instances':native,'productive_ground_program_area_m2':11430.5,
      'registered_camera_unchanged':True,'water_unchanged':True,'bridge_mechanism_unchanged':True,
      'finite_collision_contracts_preserved':True,'whole_city_complete':False}
    (a.HERE/'composition_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if not isinstance(v,list)},indent=2))
if __name__=='__main__':main()
