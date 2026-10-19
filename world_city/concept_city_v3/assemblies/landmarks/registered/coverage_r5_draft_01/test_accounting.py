"""Bounded interval and ledger consistency tests; no geometry compilation."""
from account_coverage import *
import random

def main():
 r=load(HERE/'coverage_accounting.json');proof=load(HERE/'asset_projection_proofs.json');size=load(HERE/'ordinary_size_audit.json');assert r['native_projection_proofs']==ref(HERE/'asset_projection_proofs.json');assert size['native_projections']==ref(HERE/'asset_projection_proofs.json');assert r['input_candidate_snapshot']==proof['input']==size['candidate_snapshot'];checks=[]
 random.seed(8031)
 for i in range(24):
  x=random.uniform(-400,400);z=random.uniform(-400,400);w=random.uniform(.15,35);d=random.uniform(.15,35);yaw=random.uniform(0,math.pi);poly=geo.transformed_aabb_xz_m({'min':[-w/2,0,-d/2],'max':[w/2,1,d/2]},[x,0,z],yaw);layer=layer_from([poly]);truth=w*d;lo=count(layer[0]);ce=count(layer[1]);hi=count(layer[2]);assert lo-1e-7<=truth<=hi+1e-7;assert lo<=ce<=hi;checks.append({'case':i,'exact_area_m2':truth,'lower_m2':lo,'center_m2':ce,'upper_m2':hi})
 for b in r['ordinary_blocks']:
  for key in('native_roof_projection','native_occupied_structural_body_projection'):
   m=b[key];assert m['area_lower_bound_m2']<=m['center_sample_area_m2']<=m['area_upper_bound_m2'];assert m['coverage_lower']<=m['coverage_center']<=m['coverage_upper']+1e-7
  m=b['ordinary_review_domain'];assert m['area_lower_bound_m2']<=m['center_sample_area_m2']<=m['area_upper_bound_m2'];assert m['unroofed_center_area_m2']>=0
 for s in r['precincts']:
  rows=s['assigned_nonoverlapping_center_areas']+[s['unresolved_native_land']]
  assert abs(sum(x['center_sample_area_m2']for x in rows)-s['raster_domain_center_m2'])<1e-8
  for x in rows:assert x['area_lower_bound_m2']<=x['center_sample_area_m2']<=x['area_upper_bound_m2']
 assert len(r['ordinary_blocks'])==18 and len(size['rows'])==540 and len(size['prioritized_replacement_review'])==8
 assert proof['summary']['market_canopy_instances']==104 and proof['summary']['roof_bearing_assets']==101
 assert len(proof['summary']['unresolved_cover_assets'])==1
 write(HERE/'test_results.json',{'schema':'riverstone.coverage_accounting.tests.v1','accounting':ref(HERE/'coverage_accounting.json'),'ordinary_sizes':ref(HERE/'ordinary_size_audit.json'),'random_rotated_rectangle_interval_cases':checks,'all_interval_order_and_category_partition_checks_pass':True,'all_18_blocks_present':True,'all_540_retained_ordinary_instances_present':True,'market_canopies_included':104,'unresolved_cover_count':1,'geometry_compiler_runs':0});print('24 interval fixtures and all block, precinct and size-ledger checks pass.')
if __name__=='__main__':main()
