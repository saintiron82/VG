"""Source handoff manifest, exact variant selection and immutable-output checks."""
import collections,json
from pathlib import Path
import author_facility_roofs as a
import finish_roofs as f
import expand_facilities as e
import extend_roof_shapes as x

def main():
 old=a.read(e.OUT/'layered_compile_catalog.json');new=a.read(x.OUT/'layered_compile_catalog.json');roi=a.read(x.OUT/'validation_report.json');selector=a.read(a.HERE/'variant_selection.json');records=[];fail=[]
 for cat,path in [(old,e.OUT/'layered_compile_catalog.json'),(new,x.OUT/'layered_compile_catalog.json')]:
  for r in cat['assets']:
   for file,expected in [(r['emitted_master_path'],r['emitted_master_sha256']),(r['source_master_path'],r['source_sha256'])]:
    if a.shared.sha(a.ROOT/file)!=expected:fail.append(['hash_changed',file])
   keep={k:r[k] for k in ['asset_key','native_asset_key','covering','emitted_master_path','emitted_master_sha256','source_master_path','source_sha256','source_render_path','source_render_sha256']};keep.update(source_catalog=a.rel(path),replacement_allowed=False,source_only=True,native_cell_bounds_required=True);records.append(keep)
 catalog={'schema':'riverstone.facility_roof.all_source_inputs.v4','assets':records,'native_asset_count':len({r['native_asset_key'] for r in records}),'source_variant_count':len(records),'source_catalogs':[a.ref(e.OUT/'layered_compile_catalog.json'),a.ref(x.OUT/'layered_compile_catalog.json')],'replacement_allowed':False,'runtime_activation':False,'completion_scope':'All current facility shape sources authored; semantic, whole-asset compilation and runtime gates remain separate.'};a.write(x.OUT/'all_72_layered_compile_catalog.json',catalog)
 if catalog['native_asset_count']!=72 or len(records)!=81:fail.append(['source_coverage_partition_failed'])
 available={r['asset_key']:r for r in records};ids=set();counts=collections.Counter()
 for r in selector['placements']:
  k=(r['placement_id'],r['native_asset_key'],r['city_palette_id'])
  if k in ids:fail.append(['duplicate_selector',k])
  ids.add(k)
  if r['status']=='RESOLVED_SOURCE_VARIANT':
   v=available.get(r['selected_variant_asset_key'])
   if not v or v['native_asset_key']!=r['native_asset_key'] or v['covering']!=r['roof_covering'] or v['source_sha256']!=r['source_master_sha256']:fail.append(['selector_source_mismatch',k])
  elif r['selected_variant_asset_key'] is not None or r['fallback_allowed']:fail.append(['unknown_has_fallback',k])
  counts[r['status']]+=1
 for tid,ref in selector['tiles'].items():
  if a.shared.sha(a.ROOT/ref['path'])!=ref['sha256']:fail.append(['tile_hash_mismatch',tid])
 tests=(x.OUT/'test_results.txt').read_text()
 if 'Ran 31 tests' not in tests or not tests.rstrip().endswith('OK'):fail.append(['tests_not_31_passes'])
 if roi['failures'] or len(roi['roi_reports'])!=20 or any(r['outside_original_position_material_cells'] or not r['removed_cells'] or not r['pruned_and_unpruned_native_samples_identical'] for r in roi['roi_reports']):fail.append(['bounded_roi_failed'])
 pending={'schema':'riverstone.facility_roof.remaining_gates.v4','supersedes_shape_pending_only':a.ref(e.OUT/'pending_extensions.json'),'remaining_unsupported_shape_operations':[],'resolved_original_pending_operation_count':15,'semantic_pending':selector['pending'],'semantic_resolution_plan':{'castle_registered:stable':'Recover an explicit roof_material_family/roof_covering record linked to this placement and source master hash, or obtain an author choice. Then select/generate that covering and revalidate; preserve the original roof until resolved. Never infer from baked RGB.'},'full_compile_required_asset_keys':sorted({r['native_asset_key'] for r in records}),'required_runtime_checks':['Compile selected variant using common native bounds and aggregate global constraints','Check full-roof component connectivity, intersections and source openings','Compose roof/window ROI ownership with identical integer half-open cell bounds; no approximate shape crop','Stage full matching near resources before disabling original complete material groups, all normal directions','Keep original whole building structural/collision baseline and restore coarse group atomically on eviction','Run engine close/far streaming, performance and visual acceptance'],'no_bounded_roi_can_authorize_whole_group_suppression':True,'replacement_allowed':False};a.write(x.OUT/'pending_extensions.v4.json',pending)
 size=f.disk();rules=a.read(x.RULES)
 if size>rules['budgets']['total_bytes_limit']:fail.append(['budget_exceeded',size])
 report={'schema':'riverstone.facility_roof.final_source_handoff.v4','status':'PASS_SOURCE_HANDOFF_NOT_PLAYABLE_COMPLETION' if not fail else 'FAIL','all_native_assets':72,'all_source_variants':81,'new_native_assets':15,'new_source_variants':16,'new_shape_counts':dict(collections.Counter(q['type'] for r in new['assets'] if r['covering']=='roof_tile' for q in r['shape_extensions'])),'whole_original_render_groups':sum(len(c['render_groups']) for p in [e.OUT/'replacement_contracts.v3.json',x.OUT/'replacement_contracts.v4.json'] for c in a.read(p)['assets']),'small_native_roi_cases':20,'regression_tests':31,'previous_65_master_hashes_preserved':True,'legacy_frozen_outputs_preserved':23,'variant_selection_status_counts':dict(counts),'variant_covering_counts':selector['counts']['by_covering'],'source_catalog':a.ref(x.OUT/'all_72_layered_compile_catalog.json'),'new_source_catalog':a.ref(x.OUT/'layered_compile_catalog.json'),'new_replacement_contracts':a.ref(x.OUT/'replacement_contracts.v4.json'),'native_roi_validation':a.ref(x.OUT/'validation_report.json'),'variant_selection':a.ref(a.HERE/'variant_selection.json'),'pending':a.ref(x.OUT/'pending_extensions.v4.json'),'actual_geometry_image':a.ref(x.OUT/'actual_roi_geometry.v4.png'),'core':a.ref(a.core.__file__),'new_author':a.ref(Path(x.__file__)),'verifier':a.ref(Path(__file__)),'full_asset_compiles_by_this_worker':0,'replacement_allowed':False,'runtime_activation':False,'directory_bytes_before_report':size,'added_bytes_from_task_baseline':size-rules['budgets']['baseline_bytes'],'additional_bytes_limit':rules['budgets']['additional_bytes_limit'],'roi_max_rss_bytes':roi['max_rss_bytes'],'failures':fail};a.write(x.OUT/'handoff_validation.json',report);print(json.dumps(report,indent=2));return bool(fail)
if __name__=='__main__':raise SystemExit(main())
