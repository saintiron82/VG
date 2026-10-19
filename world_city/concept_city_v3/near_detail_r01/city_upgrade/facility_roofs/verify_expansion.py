"""Final hash, provenance, cut-scope and compiler-input audit; no asset compile."""
import collections,gc,json,resource,time
import author_facility_roofs as a
import finish_roofs as f
import expand_facilities as e

def close(t,u):return all(abs(t['translation'][j]-u['translation'][j])<1e-8 for j in range(3)) and all(abs(t['basis'][j][k]-u['basis'][j][k])<1e-8 for j in range(3) for k in range(3))
def main():
 start=time.perf_counter();rules=f.limited();cat=a.read(e.OUT/'layered_compile_catalog.json');contracts=a.read(e.OUT/'replacement_contracts.v3.json');pending=a.read(e.OUT/'pending_extensions.json');pre=a.read(f.OUT/'compiler_pre_cell_bounds_evidence.json');native=a.read(f.OUT/'post_cell_bounds/validation.json');counts=collections.Counter();fail=[];elig=[];ops=0
 for r in cat['assets']:
  key=r['asset_key'];m=f.layers.load_master(a.ROOT/r['emitted_master_path']);source=a.read(a.ROOT/r['source_master_path'])
  if a.shared.sha(a.ROOT/r['emitted_master_path'])!=r['emitted_master_sha256'] or a.shared.sha(a.ROOT/r['source_master_path'])!=r['source_sha256']:fail.append([key,'master_hash_mismatch'])
  if a.shared.sha(a.ROOT/r['source_render_path'])!=r['source_render_sha256']:fail.append([key,'render_hash_mismatch'])
  a.core.validate_master(m,.05);counts['master_schema_revalidated']+=1;counts['source_operations_in_finished_variants']+=sum(len(c['operations']) for c in m['components'])
  if m['materials']!=source['materials']:fail.append([key,'palette_changed'])
  if r['replacement_allowed'] or not r['uncompiled']:fail.append([key,'unsupported_runtime_claim'])
  if r['structure_validation'].get('compiler_pending'):
   f.layers.SpatialSource(m,.05,range_only=True);basis='native range_only SpatialSource instantiated; matching proper-rigid ROI passed';counts['legacy_rotation_pending_resolved_by_native_bounds']+=1
  else:basis='Earlier stricter SpatialSource structure acceptance; current common schema revalidated and native bounds ABI checked'
  eligibility={'asset_key':key,'native_asset_key':r['native_asset_key'],'covering':r['covering'],'status':'SUPPORTED_SOURCE_INPUT_NOT_FULLY_COMPILED','required_path':'SpatialSource(range_only=True).bounded_master + core.compile_master(cell_bounds=...)','basis':basis,'emitted_master_sha256':r['emitted_master_sha256']};elig.append(eligibility);r['native_cell_bounds_input_status']=eligibility['status'];r['legacy_rotation_guard_is_not_current_blocker']=bool(r['structure_validation'].get('compiler_pending'))
  world=a.instance_transforms(source);original_cuts={(c['id'],o['id']):o for c in source['components'] for o in c['operations'] if o['action']=='cut'};by_component={c['id']:c for c in m['components']};identity={i['id']:by_component[i['component']]['metadata']['shared_row_source'].get('instance_metadata',{}).get('source_identity') for i in m['instances']}
  for cut in m['assembly_cuts']:
   meta=cut['metadata'];src=original_cuts[(meta['source_component'],meta['source_cut_id'])]
   if meta['source_cut']!=src or cut['shape']!=src['shape'] or not close(cut['transform'],a.core.compose(world[meta['source_instance']],a.core.transform(src.get('transform')))):fail.append([key,'cut_shape_or_transform_changed',cut['id']])
   for iid in cut['selector']['instance']:
    row=identity[iid]
    if row['component']!=meta['source_component'] or row['instance']!=meta['source_instance'] or not a.core.selector_matches(src.get('selector',{}),{'part':row['part'],'material':row['material']}):fail.append([key,'cut_ownership_changed',cut['id'],iid])
   counts['scoped_original_cuts_reverified']+=1
  m=None;source=None;gc.collect()
 for contract in contracts['assets']:
  source=a.read(a.ROOT/contract['source_master']['path']);render=a.read(a.ROOT/contract['source_render']['path'])
  for group in contract['render_groups']:
   g=render['groups'][group['source_render_group_index']];original={(c['id'],o['id']) for c in source['components'] for o in c['operations'] if o.get('action')=='paint' and o.get('material')==group['material_id']};represented={(x['component'],x['operation']) for x in group['represented_roof_operations']}
   if g['material']!=group['material_id'] or a.core.digest(g)!=group['source_group_sha256_canonical'] or len(g['quads'])!=group['source_quad_count'] or original!=represented:fail.append([contract['asset_key'],'whole_material_group_provenance_mismatch',group['material_id']])
   counts['original_render_groups_exhaustively_matched']+=1
 for ref in pre['frozen_outputs']:
  if a.shared.sha(a.ROOT/ref['path'])!=ref['sha256']:fail.append(['prior_output_changed',ref['path']])
 counts['frozen_pre_change_outputs_preserved']=len(pre['frozen_outputs']);counts['native_facilities']=len({r['native_asset_key'] for r in cat['assets']});counts['finished_source_variants']=len(cat['assets']);counts['pending_assets']=len(pending['assets']);counts['pending_operations']=pending['pending_operation_count'];counts['native_bounded_roi_cases']=len(native['reports']);counts['full_asset_compiles']=0
 if counts['native_facilities']!=57 or counts['pending_assets']!=15 or counts['pending_operations']!=15:fail.append(['coverage_partition_mismatch'])
 if any(r['outside_original_solid_cells'] or not r['pruned_and_unpruned_native_samples_identical'] for r in native['reports']):fail.append(['native_roi_failed'])
 tests=(e.OUT/'test_results.txt').read_text()
 if 'Ran 18 tests' not in tests or not tests.rstrip().endswith('OK'):fail.append(['regression_results_missing'])
 counts['passing_regression_tests']=18
 eligibility={'schema':'riverstone.facility_roof.native_input_eligibility.v3','assets':elig,'core':a.ref(a.core.__file__),'layered_engine':a.ref(f.layers.__file__),'roi_evidence':a.ref(f.OUT/'post_cell_bounds/validation.json'),'runtime_activation':False,'full_compile_performed':False};a.write(e.OUT/'compiler_eligibility.cell_bounds.json',eligibility);cat['native_cell_bounds_eligibility']=a.ref(e.OUT/'compiler_eligibility.cell_bounds.json');cat['current_compiler_inputs_supported']=True;cat['runtime_activation']=False;a.write(e.OUT/'layered_compile_catalog.json',cat)
 counts['directory_bytes_before_report']=f.disk();counts['additional_bytes_from_baseline']=f.disk()-rules['budgets']['baseline_bytes']
 if f.disk()>rules['budgets']['total_bytes_limit']:fail.append(['disk_budget_exceeded'])
 report={'schema':'riverstone.facility_roof.expansion_validation.v3','status':'PASS_FINISHED_SOURCE_INPUTS_NOT_PLAYABLE_COMPLETION' if not fail else 'FAIL','checks':dict(counts),'failures':fail,'seconds':time.perf_counter()-start,'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'memory_limit_bytes':rules['budgets']['memory_limit_bytes'],'catalog':a.ref(e.OUT/'layered_compile_catalog.json'),'eligibility':a.ref(e.OUT/'compiler_eligibility.cell_bounds.json'),'replacement_contracts':a.ref(e.OUT/'replacement_contracts.v3.json'),'pending':a.ref(e.OUT/'pending_extensions.json'),'runtime_activation':False,'source_coverage_is_not_runtime_completion':True,'not_verified':['Full roof chunk compilation','Whole-roof valley, hip-edge and intersection cap visual finish','Atomic original-group suppression in runtime','Close/far streaming and performance','In-engine acceptance','Unsupported solid hips, lathe spires, nonridge boxes']};a.write(e.OUT/'validation_report.json',report);print(json.dumps({'status':report['status'],'checks':dict(counts),'failures':fail,'max_rss_bytes':report['max_rss_bytes']}));return bool(fail)

if __name__=='__main__':raise SystemExit(main())
