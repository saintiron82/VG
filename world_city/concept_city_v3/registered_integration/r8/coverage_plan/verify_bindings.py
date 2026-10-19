"""Verify the final readable/data deliverable and its concrete source references."""
from build_plan import *
def main():
 failures=[];checked={};files=['whole_city_coverage_plan.json','parcel_candidates.json','native_projection.json','baseline_blocks.json','completion_ledger.json','fixed_family_bulk_contract.json','protected_source_owner_ledger.json','old_plot_envelope_accounting.json','ground_program_units.json','block_015_native_import.json']
 def walk(v,where):
  if isinstance(v,dict):
   if isinstance(v.get('path'),str) and isinstance(v.get('sha256'),str):
    p=ROOT/v['path'];key=(v['path'],v['sha256'])
    if key not in checked:
     actual=sha(p) if p.exists() else 'MISSING';checked[key]=actual
     if actual!=v['sha256']:failures.append({'reference_in':where,'path':v['path'],'expected':v['sha256'],'actual':actual})
   for k,w in v.items():walk(w,where+'.'+k)
  elif isinstance(v,list):
   for i,w in enumerate(v):walk(w,where+f'[{i}]')
 for name in files:walk(load(HERE/name),name)
 plan=load(HERE/'whole_city_coverage_plan.json');parc=load(HERE/'parcel_candidates.json');tests=load(HERE/'test_results.json');native=load(ROOT/plan['native_B15_binding']['layout']['path'])
 exact_ids={h['id']for h in native['holdings']};imported_ids={h['id']for h in parc['holdings']if h['block_id']=='BLOCK_015'}
 checks={'scene_sha_matches':sha(SCENE)==SHA,'source_bookkeeping_passes':tests['failed']==0,'B15_IDs_unchanged':exact_ids==imported_ids,'all_18_blocks_remain_completion_open':len(plan['blocks'])==18 and all(b['actual_scene_complete']is False for b in plan['blocks']),'no_other_block_floor_claimed':all(h['finished_floor_y_m']is None for h in parc['holdings']if h['block_id']!='BLOCK_015'),'all_declared_file_hashes_match':not failures}
 write('final_verification.json',{'schema':'riverstone.r8.coverage_final_verification.v1','scene':ref(SCENE),'checks':checks,'checked_unique_source_bindings':len(checked),'binding_failures':failures,'all_pass':all(checks.values()),'limits':['No new geometry compile or scene mutation performed.','Other-block source native fits, R17 terrain/route validation and actual integrated views remain open.','Protected owner exclusions never count as implemented completion.']})
 print({'checks':checks,'unique_bindings':len(checked),'failures':failures})
if __name__=='__main__':main()
