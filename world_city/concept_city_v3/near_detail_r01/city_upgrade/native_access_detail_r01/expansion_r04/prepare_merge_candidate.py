"""Data-only append candidate; never writes the production runtime catalog."""
from pathlib import Path
import copy,json,sys
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H));import author_r04 as b
b.limits();a=b.a
old=b.read(a.PLAN);delta=b.read(b.PLAN);oc=b.read(a.CAT);dc=b.read(b.CAT);proof=b.read(H/'candidate_geometry.json');gp=b.read(H/'godot_mesh_report.json');assert proof['all_pass'] and gp['all_pass']
assert oc['source_plan_sha256']==b.sha(a.PLAN) and dc['source_plan_sha256']==b.sha(b.PLAN)
assert old['source_city_index_sha256']==delta['source_city_index_sha256']==b.sha(b.IP)
assert not ({r['asset_key'] for r in old['assets']}&{r['asset_key'] for r in delta['assets']})
modules=copy.deepcopy(oc['modules']);byid={r['id']:r for r in modules}
for row in dc['modules']:
 if row['id'] in byid:assert byid[row['id']]==row,'Same key with changed module bytes is rejected'
 else:modules.append(copy.deepcopy(row));byid[row['id']]=row
for row in modules:
 assert b.sha(b.R/row['master_path'])==row['master_sha256'] and b.sha(b.R/row['render_path'])==row['render_sha256']
assets=copy.deepcopy(old['assets'])+copy.deepcopy(delta['assets']);demand={d['id']:d for d in old['module_demand']}
for d in delta['module_demand']:
 if d['id'] in demand:assert demand[d['id']]==d
 demand[d['id']]=d
assert all(p['module_key'] in byid for a in assets for p in a['placements'])
plan={'schema':old['schema'],'revision':'r03_plus_expansion_r04_candidate','source_city_index_sha256':b.sha(b.IP),'assets':assets,'module_demand':list(demand.values()),'maximum_additional_visual_offset_from_source_m':.0375,'source_collision_note':old['source_collision_note'],'runtime_activation':False,'whole_city_upgrade_complete':False,'merge_provenance':{'previous_plan':b.ref(a.PLAN),'previous_modules':b.ref(a.CAT),'delta_plan':b.ref(b.PLAN),'delta_modules':b.ref(b.CAT),'delta_geometry_validation':b.ref(H/'candidate_geometry.json'),'delta_godot_mesh_validation':b.ref(H/'godot_mesh_report.json'),'scope_ledger':b.ref(b.LEDGER),'merge_script':b.ref(Path(__file__)),'asset_merge':'append disjoint asset keys only','module_merge':'reuse exact identical rows by id, reject all changed duplicates','previous_asset_rows_exactly_preserved':True}}
pp=H/'combined/source_plan_r03_plus_r04.json';cp=H/'combined/module_catalog_r03_plus_r04.json';b.save(pp,plan)
cat=copy.deepcopy(dc);cat.update(revision='r03_plus_expansion_r04_candidate',source_plan_sha256=b.sha(pp),modules=modules);cat['incremental_reuse']={'old_modules_preserved':len(oc['modules']),'new_trim_modules':len(modules)-len(oc['modules']),'geometry_files_duplicated':0};b.save(cp,cat)
prod=b.C/'playable_detail_r01/native_access_catalog.json';config=b.read(prod);assert config['source_plan_sha256']==b.sha(a.PLAN) and config['module_catalog_sha256']==b.sha(a.CAT),'Existing active baseline changed; review before merge'
config.update(source_plan_path=str(pp.relative_to(b.R)),source_plan_sha256=b.sha(pp),module_catalog_path=str(cp.relative_to(b.R)),module_catalog_sha256=b.sha(cp),binding_revision='candidate_r03_plus_four_static_bridges_r04');b.save(H/'combined/runtime_catalog_candidate.json',config)
assert len(assets)==6 and len(modules)==145 and sum(len(a['placements']) for a in assets)==652
assert assets[:2]==old['assets'] and modules[:84]==oc['modules'];assert b.sha(prod)==dc['source_dependencies'][str(prod.relative_to(b.R))]
report={'all_pass':True,'combined_plan':b.ref(pp),'combined_modules':b.ref(cp),'runtime_catalog_candidate':b.ref(H/'combined/runtime_catalog_candidate.json'),'production_catalog_unchanged':b.ref(prod),'prior_assets_exactly_preserved':2,'prior_placements_exactly_preserved':226,'prior_modules_exactly_preserved':84,'new_assets':4,'new_placements':426,'new_trim_modules':61,'total_assets':6,'total_placements':652,'total_modules':145,'new_geometry_files_duplicated':0,'runtime_promoted':False,'remaining_gate':'Parent actual original-scene integration, cap120 truncation/collider identity review; no new walk route claim'};b.save(H/'merge_validation.json',report);assert b.output_bytes()<b.LIMIT;print(json.dumps(report))
