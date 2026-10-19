"""Apply the same finished roof grammar to all wholly supported facility groups.
Source-only expansion; never calls compile_master. Reuses two frozen priority inputs.
"""
import collections,copy,gc,json,resource,time
from pathlib import Path
import author_facility_roofs as a
import finish_roofs as f
OUT=f.OUT/'all_supported'

def ordered_finish(d,source,rules,covering):
 master=f.finish(d,source,rules,covering);comps={c['id']:c for c in master['components']};ranks={i['id']:j for j,i in enumerate(source['instances'])};oprank={(c['id'],op['id']):j for c in source['components'] for j,op in enumerate(c['operations'])}
 def rank(ins):
  prov=comps[ins['component']]['metadata']['provenance'];sid=ins['metadata']['source_identity']['instance'];return (ranks[sid],min(oprank[(prov['source_component'],op)] for op in prov['source_operations']))
 master['instances'].sort(key=rank);master['metadata']['source_paint_precedence']='Stable original component-instance order, then source operation order. Adjacent bands merge only on identical plane/material domains; generated rows retain stable order.'
 return master

def main():
 start=time.perf_counter();rules=f.limited();OUT.mkdir(parents=True,exist_ok=True);bundle=f.layers.load_master(f.OUT/'shape_support_descriptors.v2.json.gz');mapping=a.read(a.MAP);priority=a.read(f.OUT/'layered_compile_catalog.json');priority_by={(r['asset_key'],r['covering']):r for r in priority['assets']};oldcontracts={r['asset_key']:r for r in a.read(a.HERE/'replacement_contracts.json')['assets']};records=[];pending=[];contracts=[];errors=[];counts=collections.Counter()
 cached=a.read(OUT/'layered_compile_catalog.json')['assets'] if (OUT/'layered_compile_catalog.json').exists() else []
 cached_by={(r['native_asset_key'],r['covering']):r for r in cached}
 for key,d in bundle['assets'].items():
  if d['pending'] or d['suppression']['unsafe_material_groups']:
   pending.append({'asset_key':key,'pending_operations':d['pending'],'unsafe_material_groups':d['suppression']['unsafe_material_groups'],'required_extension_by_kind':sorted({{'lathe':'radial conical shell and radial tile/shingle grammar; exact taper and cap','box':'semantic ownership of nonridge roof/ornament and flat slab edge rule','extrusion':'extract thin hip skin from solid triangle; preserve exact terminal hip cuts'}.get(p['shape_kind'],'explicit shape interpretation') for p in d['pending']}),'replacement_allowed':False});continue
  source=a.read(a.ROOT/d['source_master_path']);counts['supported_native_assets']+=1;variants=['roof_tile']+(['wood_shingle'] if any('wood_brown' in pal for pal in d['palette_id_counts']) else [])
  for covering in variants:
   if (key,covering) in priority_by:
    record=copy.deepcopy(priority_by[(key,covering)]);record['native_asset_key']=key;record['status']='FROZEN_PRIORITY_SOURCE_NOT_FULLY_COMPILED';record['source_priority_catalog']=a.ref(f.OUT/'layered_compile_catalog.json');records.append(record);counts['frozen_priority_masters_reused']+=1;continue
   prior=cached_by.get((key,covering))
   if prior and a.shared.sha(a.ROOT/prior['emitted_master_path'])==prior['emitted_master_sha256'] and a.shared.sha(a.ROOT/prior['source_master_path'])==prior['source_sha256']:
    records.append(copy.deepcopy(prior));counts['existing_hash_verified_source_variants_reused']+=1;counts.update(prior['structure_validation']['checks']);continue
   try:
    near=ordered_finish(d,source,rules,covering);flat=f.flatten(near);check=f.structure(flat,d,require_layered=False)
    if check['failures']:raise ValueError(check['failures'][:6])
    variant_key=key if covering=='roof_tile' else key+'__wood_shingle';mp=OUT/'masters'/(variant_key+'.finished.master.json.gz');f.gzwrite(mp,flat)
    if f.disk()>rules['budgets']['total_bytes_limit']:raise ValueError('additional_disk_budget_exceeded')
    record={'asset_key':variant_key,'native_asset_key':key,'covering':covering,'emitted_master_path':a.rel(mp),'emitted_master_sha256':a.shared.sha(mp),'source_master_path':d['source_master_path'],'source_sha256':d['source_master_sha256'],'source_render_path':d['source_render_path'],'source_render_sha256':d['source_render_sha256'],'source_descriptor_bundle':a.ref(f.OUT/'shape_support_descriptors.v2.json.gz'),'replacement_allowed':False,'source_authoring_complete_for_all_roof_groups':True,'whole_group_material_ids':d['suppression']['safe_material_groups_when_full_matching_near_resource_ready'],'structure_validation':check,'components':len(flat['components']),'operations':sum(len(c['operations']) for c in flat['components']),'source_terminal_cuts_retained':len(flat['assembly_cuts']),'compressed_bytes':mp.stat().st_size,'uncompiled':True,'status':'FINISHED_SOURCE_STRUCTURE_CHECKED_NOT_FULLY_COMPILED','palette_selection':{'explicit_wood_palette_ids':[p for p in d['palette_id_counts'] if 'wood_brown' in p],'color_alone_never_selects_covering':True},'intersection_policy':'Original component-instance/paint order and exact scoped terminal cuts retained. Whole-roof valley/cap visual acceptance remains pending.'};records.append(record);counts['new_finished_variants']+=1;counts['new_operations']+=record['operations'];counts['new_compressed_bytes']+=record['compressed_bytes'];counts.update(check['checks']);print(json.dumps({'asset':variant_key,'operations':record['operations'],'gzip_bytes':record['compressed_bytes'],'cuts':record['source_terminal_cuts_retained']}),flush=True)
   except (ValueError,KeyError) as e:
    errors.append({'asset_key':key,'covering':covering,'error':str(e)});print(json.dumps({'failed':key,'covering':covering,'reason':str(e)}),flush=True)
   finally:
    near=None;flat=None;gc.collect()
  contract=copy.deepcopy(oldcontracts[key]);contract['source_authoring_complete_for_all_roof_groups']=True;contract['replacement_contract_supported_for_all_roof_groups']=True;contract['pending_shape_operations']=[];contract['replacement_contract_supported_material_ids']=d['suppression']['safe_material_groups_when_full_matching_near_resource_ready'];contract['current_blocker']='No complete compiled near resources or whole-roof/runtime visual verification yet.'
  for g in contract['render_groups']:
   g['group_replacement_supported']=g['material_id'] in contract['replacement_contract_supported_material_ids'];g['unsupported_refs']=[];g['replacement_allowed']=False;g['represented_roof_operations']=[{'component':p['component'],'operation':op,'role':'finished_tile_plane_with_source_cuts_and_eave_verge_detail'} for p in d['planes'] if p['material']==g['material_id'] for op in p['source_operations']]+[{'component':r['component'],'operation':r['operation']['id'],'role':'segmented_ridge_caps_within_original_box'} for r in d['retained_ridge_boxes'] if r['operation']['material']==g['material_id']]
  contract['exact_terminal_component_cuts']=d['preserved_terminal_component_cuts'];contract['finished_variants']=[{'asset_key':r['asset_key'],'covering':r['covering'],'emitted_master_path':r['emitted_master_path'],'emitted_master_sha256':r['emitted_master_sha256']} for r in records if r['native_asset_key']==key];contracts.append(contract)
 a.write(OUT/'layered_compile_catalog.json',{'schema':'riverstone.facility_roof.layered_input_catalog.v3','assets':records,'native_asset_count':len({r['native_asset_key'] for r in records}),'variant_count':len(records),'priority_two_asset_catalog':a.ref(f.OUT/'layered_compile_catalog.json'),'rules':a.ref(f.RULES),'author':a.ref(Path(__file__)),'finish_adapter':a.ref(Path(f.__file__)),'plane_adapter':a.ref(Path(a.__file__)),'shared_compiler_path':'world_city/concept_city_v3/near_detail_r01/city_upgrade/house_rules/layered_compile.py','runtime_activation':False,'full_compile_performed':False,'errors':errors})
 a.write(OUT/'replacement_contracts.v3.json',{'schema':'riverstone.facility_roof.replacement_contracts.v3','assets':contracts,'replacement_allowed':False,'runtime_activation':False,'whole_group_only':True,'source_coverage_is_not_runtime_completion':True})
 a.write(OUT/'pending_extensions.json',{'schema':'riverstone.facility_roof.pending_extensions.v3','assets':pending,'pending_operation_count':sum(len(p['pending_operations']) for p in pending),'source_geometry_preserved':True,'required_geometry_extensions':['Solid triangular hip -> thin surface shells, exact existing hip cuts, hip ridge/end caps.','Conical/lathe spire -> radial shell/tile grammar and apex cap inside original profile; requires existing common lathe or supported faceted extrusion representation and bounded compiler approval.','Nonridge box -> verify original gallery roof/cap ownership, then flat cover and fascia rule; do not suppress shared nonroof slot.'],'shared_acceptance':['Original envelope, semantic colors and openings retained.','Exhaustive original material/group provenance.','Small source/near ROI containment and scoped-cut equivalence.','Full bounded compile and runtime atomic replacement later, only within approved storage/performance budgets.'],'do_not_claim_57_source_assets_complete_city':True})
 counts['variant_records']=len(records);counts['pending_assets']=len(pending);counts['pending_operations']=sum(len(p['pending_operations']) for p in pending);counts['directory_bytes']=f.disk();counts['additional_bytes']=f.disk()-rules['budgets']['baseline_bytes'];report={'schema':'riverstone.facility_roof.expansion_report.v3','status':'PASS_SOURCE_AUTHORING_ONLY' if not errors else 'PARTIAL_WITH_ERRORS','counts':dict(counts),'errors':errors,'seconds':time.perf_counter()-start,'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'full_asset_compiles':0,'runtime_activation':False,'source_coverage_is_not_runtime_completion':True,'before_after_core_evidence':a.ref(f.OUT/'compiler_pre_cell_bounds_evidence.json')};a.write(OUT/'expansion_report.json',report);print(json.dumps(report));return bool(errors)

if __name__=='__main__':raise SystemExit(main())
