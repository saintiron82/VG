"""Bind sealed local producers to the frozen R5 scene; no world resampling."""
from . import apply_packs as a
import json

def ref(path):
    p=a.CITY/path
    return {'path':a.rel(p),'sha256':a.sha(p)}

def main():
    target=a.HERE/'review_binding.json'
    if target.exists():raise ValueError('Preserve a prior review binding')
    prefix='assemblies/landmarks/registered/precinct_r05_ground/'
    gardens=prefix+'phase01/'
    subset='registered_topography/revisions/r15_merchant_local_patch/subset_07/'
    evidence=[subset+'acceptance_report.json',subset+'freeze_manifest.json',
      prefix+'local_frame_r01/corner_repair_r01/tests.json',
      prefix+'local_frame_r01/corner_repair_r01/terrain_patch/test_results.json',
      'traversal_r5/revisions/r02/evidence/capsule_continuous_cover.json',
      'traversal_r5/revisions/r02/freeze_manifest.json',
      gardens+'native_tests.json',gardens+'ground_tests.json',gardens+'freeze_manifest.json']
    for n in (subset+'freeze_manifest.json',):
        for f in a.load(a.CITY/n)['files']:
            assert a.sha(a.ROOT/f['path'])==f['sha256'],f['path']
    acceptance=a.load(a.CITY/subset/'acceptance_report.json')
    assert len(acceptance['accepted_property_ids'])==7
    assert acceptance['support_placement_count']==0
    assert a.load(a.CITY/gardens/'native_tests.json')['all_native_gate_and_boundary_route_checks_pass']
    data={'schema':'riverstone.r6_review_binding.v1','status':'sources_reviewed_ready_for_visual',
      'base_scene':ref('evidence/visual_registered_common_r5/bridge_scene.json'),
      'patch_apply':ref('registered_topography/revisions/r15_merchant_local_patch/frozen.py'),
      'patches':[ref('traversal_r5/revisions/r02/scene_patch.json'),
                 ref(subset+'scene_patch.json'),ref(gardens+'combined_clergy_ground_patch.json')],
      'packs':[{'name':'southern_repair_r02',**ref('registered_integration/r6/southern_repair_pack.json')},
               {'name':'clergy_local_frame_r01',**ref('registered_integration/r6/clergy_repair_pack.json')},
               {'name':'merchant_seven_r02',**ref(subset+'merchant_pack.json')},
               {'name':'productive_grounds_phase01',**ref(gardens+'resolved_placements.json')}],
      'producer_evidence':[ref(p) for p in evidence],
      'new_materials':{},
      'limits':['Seven of19 merchant candidates active; remaining12 retain unchanged R5 buildings.',
        'Four level productive holdings occupy11430.5m2. Two stepped grounds remain deferred.',
        'Whole-city exterior coverage and concept fidelity remain incomplete; this is a local integrated iteration.',
        'Actual R6 image and composed traversal review pending. Static source checks are not character or cart clearance.',
        'Southern continuous collision is a declared finite proxy matching a visible native cover within0.02681m.',
        'The stored external_gate_links are proposal provenance, not extra runtime surfaces; accepted profiles are already in the terrain patch.',
        'Bridge moving-span guards remain separately tested fixture behavior; no whole-city NPC traffic simulation is asserted.',
        'Actual captures use software OpenGL; load times are not target-hardware performance.']}
    target.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(ref('registered_integration/r6/review_binding.json')))
if __name__=='__main__':main()
