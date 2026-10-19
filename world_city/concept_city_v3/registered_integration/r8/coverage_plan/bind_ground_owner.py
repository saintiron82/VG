"""Keep B15 residual authoring under the native district owner's frozen ledger."""
from build_plan import *
def main():
 plan=load(HERE/'whole_city_coverage_plan.json');grounds=load(HERE/'ground_program_units.json');path=CITY/'assemblies/ordinary/registered/district_fabric_r01/land_use_ledger.json';d=load(path)
 if plan.get('native_B15_binding'):
  assert d['layout']==plan['native_B15_binding']['layout']
  for u in grounds['units']:
   if u['block_id']=='BLOCK_015':u.update(allocation_authority=ref(path),status='whole_city_diagnostic_only; native district owner resolves residuals',independent_B15_authoring_allowed=False)
  grounds['B15_authoritative_ground_accounting']=ref(path);grounds['B15_actual_completion_claim']=False
  write('ground_program_units.json',grounds);plan['ground_program_units']=ref(HERE/'ground_program_units.json');plan['native_B15_binding']['ground_accounting']=ref(path)
  for b in plan['blocks']:
   if b['block_id']=='BLOCK_015':b['ground_accounting_owner']=ref(path)
  write('whole_city_coverage_plan.json',plan)
  tests=load(HERE/'test_results.json');tests['limits']=[q.replace('Source native dimensions for new deep/range recipes need common-compiler verification before placement.','Source capacity envelopes must be refit with the seven existing compiled family masks before placement.')for q in tests['limits']];write('test_results.json',tests)
  print({'B15_ground_owner':ref(path),'B15_independent_ground_authorship':False})
if __name__=='__main__':main()
