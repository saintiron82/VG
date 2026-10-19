"""Reproducible recovery source/cache freeze and imported local dependency closure."""
import sys
from pathlib import Path
import recovered_range_factory,plan_coverage,fit_native_buildings,author_grounds,author_productive,compile_compounds,resolve_precinct,route_exterior,test_external_sources
from plan_coverage import *
def main():
 closure=[]
 for module in list(sys.modules.values()):
  f=getattr(module,'__file__',None)
  if not f:continue
  p=Path(f).resolve()
  if p.is_file()and p.suffix=='.py'and p.is_relative_to(ROOT):closure.append(ref(p))
 closure={r['path']:r for r in closure};write(HERE/'import_closure.json',{'schema':'riverstone.local_import_closure.v1','files':[closure[k]for k in sorted(closure)],'scope':'Actual locally imported source files for the recovered range, compound, resolver and route pipeline. Standard-library/package dependencies are outside repository closure.','explicit_data_inputs':[ref(SOURCE),ref(LAND),ref(GARDEN),ref(CITY/'validation/landmark_recovery_r1/recovered_rendered_profiles_r2.json'),ref(ROOT/'world_city/runtime_city/revisions/r2/city_history.r2.candidate.json'),ref(ROOT/'voxel_character/common/assets/house/master.json'),ref(ROOT/'voxel_character/common/assets/fountain/master.json')],'revision02_prompt_caveat':'Original prompt absent from checkpoint. Source points to a clearly labeled reconstruction notice; no byte-identical prompt recovery is claimed.'})
 files=[ref(p)for p in sorted(HERE.rglob('*'))if p.is_file()and'__pycache__'not in p.parts and p.name!='freeze_manifest.json'and'boundary_belts'not in p.parts];pack=load(HERE/'resolved_placements.json');access=load(HERE/'evidence/native_access_replay.json');exterior=load(HERE/'evidence/exterior_source_ribbon_audit.json');assert access['all_pass']and exterior['all_source_ribbons_clear']
 for a in pack['assets']:
  assert ref(ROOT/a['source']['path'])==a['source'];assert ref(ROOT/a['cache']['path'])==a['cache']
 value={'schema':'riverstone.registered_precinct.recovery_freeze.v1','native_pack':ref(HERE/'resolved_placements.json'),'exterior_source_proposal':ref(HERE/'exterior_access_proposal.json'),'import_closure':ref(HERE/'import_closure.json'),'files':files,'checks':{'asset_source_cache_pairs':len(pack['assets']),'all_hashes_match':True,'native_floor_gate_replay':True,'exact_exterior_source_ribbons_clear':True,'actual_scene_placed':False,'actual_viewed':False,'independent_terrain_and_access_accepted':False},'known_open_support':'Southern abbey opaque bearing edges require finite retaining/fill up to5.3m. Source floor14/8 is fixed.','immutable_baseline':'Registered plan and sealed r3 inputs preserved.'};write(HERE/'freeze_manifest.json',value);print(ref(HERE/'freeze_manifest.json'),len(files),len(closure))
if __name__=='__main__':main()
