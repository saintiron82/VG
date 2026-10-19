"""Bind the current 110-holding candidate to an explicitly supplied exact scene.

Uses the sealed r01 native checker, but replaces its obsolete R04-derived report
with the current candidate. Never promotes source/grid/material accounting into
an exact final residual-land or traversal certificate.
"""
from . import check_final_city_activation as c
from pathlib import Path
import argparse,copy,time
CANDIDATE=c.g.HERE/'city_completion_candidate_r05/completion_ledger.json'
CANDIDATE_SHA='bdd05a0012723b53b1bb1a92a4abf6ecb19fcc2d420f92da567ce7997e022ff2'
OUT=c.g.HERE/'city_activation_ledger_r01'


def bind_ledger(candidate,audit,manifest_ref,scene_ref,scene_counts):
 ledger=copy.deepcopy(candidate)
 ledger.update(schema='riverstone.ordinary_city.exact_scene_activation_ledger.v2',
  status='EXACT_NATIVE_ACTIVATION_PASS_TERRAIN_TRAVERSAL_AND_MATERIAL_AUDITS_SEPARATE'if audit['passed']else'HELD_NATIVE_ACTIVATION_MISMATCH',
  actual_final_manifest=manifest_ref,actual_final_scene=scene_ref,activation_audit=audit,actual_scene_counts=scene_counts)
 ledger['source_references'].update(source_selected_candidate=c.g.ref(CANDIDATE),activation_checker=c.g.ref(__file__),sealed_native_checker=c.g.ref(c.__file__))
 ledger['summary'].update(actual_scene_bound=True,final_actual_scene_bound=True,native_activation_passed=audit['passed'],exact_checked_old_native_retirements=audit['summary']['all_explicit_old_native_retirements'])
 for b in ledger['blocks']:
  rows=[r for r in audit['holding_rows']if r['block_id']==b['block_id']]
  assert set(b['selected_holding_ids'])=={r['id']for r in rows}
  b.update(actual_activation_scene=scene_ref,exact_native_activation_passed=audit['passed'],actual_native_holding_rows=rows)
  b['remaining_activation_and_traversal_gate_ids']=['G2','G3','G4','G5']if audit['passed']else['G1','G2','G3','G4','G5']
  b['exact_source_projected_area_m2']['final_actual_material_area_m2']=None
  b['exact_source_projected_area_m2']['final_exact_unassigned_land_m2']=None
 for gate in ledger['remaining_gates']:
  if gate['id']=='G1':gate.update(status='EXACT_SCENE_NATIVE_PASS'if audit['passed']else'HELD_NATIVE_MISMATCH',evidence='native_activation_audit.json')
  elif gate['id']=='G5':gate.update(status='SCENE_BOUND_RENDERED_REVIEW_AND_EXACT_RESIDUAL_MEASUREMENT_SEPARATE')
 ledger['residual_material_application']['status']='SEPARATE_FINAL_APPLICATION_REPORT_REQUIRED'
 ledger['activation_limitations']=['Exact scene native identity, pose, asset, palette, source bytes and explicit retirement absence are checked here.',
  'Terrain top/side/support, physical colliders, final route replay and rendered appearance require their own exact-scene reports.',
  'The source candidate areas retain their measurement types. Final exact unassigned land and actual material quantities remain null in this bounded native report.']
 return ledger


def run(manifest_path,manifest_sha,scene_path,scene_sha):
 started=time.monotonic();mp=manifest_path if manifest_path.is_absolute()else c.g.ROOT/manifest_path;sp=scene_path if scene_path.is_absolute()else c.g.ROOT/scene_path
 assert c.g.ref(mp)['sha256']==manifest_sha,'Supplied manifest hash mismatch.'
 assert c.g.ref(sp)['sha256']==scene_sha,'Supplied scene hash mismatch.'
 manifest=c.g.load(mp);sr=c.g.ref(sp);assert sr in list(c.references(manifest)),'Manifest does not bind this exact scene.'
 assert c.g.ref(CANDIDATE)['sha256']==CANDIDATE_SHA,'Current candidate source changed.'
 assert not OUT.exists(),'Never overwrite an exact-scene activation ledger.'
 candidate=c.g.load(CANDIDATE);prior,final,withdrawal,groups,deferred=c.expected_sources();scene=c.g.load(sp)
 audit=c.inspect(scene,groups,withdrawal,deferred,final)
 counts=dict(native_part_and_assembly_instances=len(scene['common_instances']),inherited_planning_building_masses=scene.get('counts',{}).get('building_masses'),not_a_building_count=True)
 ledger=bind_ledger(candidate,audit,c.g.ref(mp),sr,counts)
 OUT.mkdir();c.g.write(OUT/'completion_ledger.json',ledger);c.g.write(OUT/'native_activation_audit.json',audit)
 lines=['# Exact-scene ordinary activation ledger','',ledger['status'],'',
 f"110 adopted whole holdings and 835 backland selections are checked against {sr['path']} (SHA-256 {sr['sha256']}). The 960 m² unbuilt B008 proposal remains explicitly withdrawn in favor of retained hall/service ground.",'',
 f"The audit checks 2,006 distinct selected native parts/assemblies, all 295 old ordinary retirements, the approved step skin, and every excluded/deferred source proposal. Final source batch: 23 holdings, 214 ordinary native objects, one step skin and 69 retirements.",'',
 'Only 22 listed backland subyards have a complete gated enclosure claim. Eight old proposed perimeters remain wholly held (105 panels); three other fixtures are deferred and two panels are intentional entry openings.','',
 'Exact-source holding union is 74,614.973 m²; selected roof union is 40,793.000 m²; the incremental roof gain over explicitly retired R7 roofs is 11,948.250 m². These source areas retain their original layer definitions. Actual final material areas and exact unassigned-land areas are not measured by this native checker.','',
 '## Registered blocks','']
 for b in ledger['blocks']:
  lines.append(f"- {b['block_id']}: {b['selected_holding_count']} adopted holdings; {b['functional_backlands']['selected_native_instances']} selected backland native objects; "+(', '.join(b['selected_holding_ids'])or b['disposition']))
 lines+=['','## Remaining physical evidence','',*['- '+x for x in ledger['activation_limitations']], '','The full JSON carries current functions, exact source areas, sampling estimates, exclusions and G2–G5. Initial coverage, R04 and source candidate bytes remain preserved.']
 (OUT/'COMPLETION_LEDGER.md').write_text('\n'.join(lines)+'\n')
 c.g.write(OUT/'manifest.json',dict(schema='riverstone.ordinary_city.native_activation_manifest.v2',passed=audit['passed'],actual_manifest=c.g.ref(mp),actual_scene=sr,source_candidate=c.g.ref(CANDIDATE),ledger=c.g.ref(OUT/'completion_ledger.json'),audit=c.g.ref(OUT/'native_activation_audit.json'),readable=c.g.ref(OUT/'COMPLETION_LEDGER.md'),checker=c.g.ref(__file__),seconds=time.monotonic()-started))
 print(audit['checks'],flush=True);print(c.g.ref(OUT/'manifest.json'),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',required=True,type=Path);p.add_argument('--manifest-sha',required=True);p.add_argument('--scene',required=True,type=Path);p.add_argument('--scene-sha',required=True);v=p.parse_args();run(v.manifest,v.manifest_sha,v.scene,v.scene_sha)
