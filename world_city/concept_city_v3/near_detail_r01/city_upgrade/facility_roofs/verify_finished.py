"""Recheck all v2 source hashes and authored structures without asset compilation."""
import collections,json,resource,time
from pathlib import Path
import author_facility_roofs as a
import finish_roofs as f

def main():
 start=time.perf_counter();rules=f.limited();cat=a.read(f.OUT/'layered_compile_catalog.json');support=a.read(f.OUT/'shape_support_catalog.json');bundle=f.layers.load_master(a.ROOT/support['descriptors']['path']);counts=collections.Counter();failures=[]
 for name in ['rules','author','common_plane_author','layered_compile']:
  ref=cat[name]
  if a.shared.sha(a.ROOT/ref['path'])!=ref['sha256']:failures.append(['catalog_dependency_hash_changed',name])
 for key,d in bundle['assets'].items():
  for kind in ['master','render']:
   if a.shared.sha(a.ROOT/d['source_'+kind+'_path'])!=d['source_'+kind+'_sha256']:failures.append([key,'original_'+kind+'_changed'])
  counts['original_master_render_pairs_rehashed']+=1;counts['supported_merged_planes']+=len(d['planes']);counts['pending_shape_operations']+=len(d['pending']);counts['retained_terminal_component_cuts']+=sum(len(c) for c in d['preserved_terminal_component_cuts'].values())
  if not d['pending'] and not d['suppression']['unsafe_material_groups']:counts['all_material_groups_source_describable']+=1
 for record in cat['assets']:
  path=a.ROOT/record['emitted_master_path']
  if a.shared.sha(path)!=record['emitted_master_sha256']:failures.append([record['asset_key'],'finished_master_hash_changed'])
  master=f.layers.load_master(path);d=a.read(a.ROOT/record['descriptor']['path']);result=f.structure(master,d);failures+=result['failures'];counts.update(result['checks']);counts['finished_full_roof_source_masters']+=1
  if master['materials']!=a.read(a.ROOT/record['source_master_path'])['materials']:failures.append([record['asset_key'],'materials_changed'])
  if record['replacement_allowed'] or not record['uncompiled']:failures.append([record['asset_key'],'unsupported_activation_claim'])
 report=a.read(f.OUT/'roi_validation.json');hip=a.read(f.OUT/'hip_cut_roi_validation.json');counts['bounded_finish_roi_compiles']=len(report['reports']);counts['bounded_real_hip_roi_compiles']=1
 for r in report['reports']:
  if r['status']!='PASS_SMALL_ROI' or r['outside_original_cells'] or not r['near_cells'] or max(r['near_candidate_cells'],r['reference_candidate_cells'])>rules['budgets']['roi_candidate_cells']:failures.append([r['asset_key'],'roi_contract_failed'])
 if hip['outside_original_roof_cells'] or not hip['cells_removed_by_exact_original_cut'] or hip['status']!='PASS_SMALL_ROI_EXACT_CUT':failures.append(['hip_cut_evidence_failed'])
 size=f.disk();counts['artifact_bytes_before_report']=size;counts['additional_bytes_from_baseline']=size-rules['budgets']['baseline_bytes']
 if size>rules['budgets']['total_bytes_limit']:failures.append(['additional_disk_budget_exceeded'])
 tests=(a.HERE/'test_results.txt').read_text()
 if 'Ran 16 tests' not in tests or not tests.rstrip().endswith('OK'):failures.append(['regression_tests_missing'])
 counts['passing_regression_tests']=16;counts['full_asset_compiles']=0
 out={'schema':'riverstone.facility_roof.finished_validation.v2','status':'PASS_SOURCE_STRUCTURE_AND_SMALL_ROIS' if not failures else 'FAIL','checks':dict(counts),'failures':failures,'seconds':time.perf_counter()-start,'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'memory_limit_bytes':rules['budgets']['memory_limit_bytes'],'catalog':a.ref(f.OUT/'layered_compile_catalog.json'),'replacement_contracts':a.ref(f.OUT/'replacement_contracts.v2.json'),'roi_evidence':a.ref(f.OUT/'roi_validation.json'),'hip_roi_evidence':a.ref(f.OUT/'hip_cut_roi_validation.json'),'tests':a.ref(a.HERE/'test_results.txt'),'cpu_geometry_preview':a.ref(f.OUT/'actual_roi_geometry.png'),'all_original_sources_unchanged':not any('original_' in str(x) and '_changed' in str(x) for x in failures),'runtime_activation':False,'not_verified':['Full roof chunk compilation','Whole roof intersections and valley/cap interfaces','Runtime atomic original-group suppression','Streaming and performance','In-engine visual acceptance','Solid triangular hips, lathe spires, nonridge boxes','Hip join-cap finishing beyond original exact cut geometry']}
 a.write(f.OUT/'validation_report.v2.json',out);print(json.dumps({'status':out['status'],'checks':dict(counts),'failures':failures,'max_rss_bytes':out['max_rss_bytes']}));return bool(failures)

if __name__=='__main__':raise SystemExit(main())
