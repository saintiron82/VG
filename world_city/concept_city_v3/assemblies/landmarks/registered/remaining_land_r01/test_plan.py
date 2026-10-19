from plan import *
import hashlib,time

def main():
 start=time.monotonic();d=load(HERE/'remaining_land_plan.json');r=np.load(HERE/'review_masks.npz');labels=np.load(HERE/'program_raster.npz');acc=load(HERE/'access_review.json');terrain=load(HERE/'terrain_screen.json');checks=[]
 def check(name,ok,details=None):
  checks.append({'name':name,'passed':bool(ok),'details':details});assert ok,(name,details)
 check('all_bound_inputs_unchanged',all(ref(ROOT/q['path'])==q for q in d['inputs']['source_refs']))
 check('final_merchant_19_reserved',d['inputs']['merchant_count']==19)
 check('access_binds_exact_plan',acc['plan']==ref(HERE/'remaining_land_plan.json'))
 check('terrain_binds_exact_plan',terrain['plan']==ref(HERE/'remaining_land_plan.json'))
 check('zero_native_compiles_and_placements',d['summary']['native_assets_compiled']==0 and d['summary']['scene_placements_added']==0)
 all_used=np.zeros(SHAPE,bool);area_by_site={k:0 for k in ['BLOCK_003','BLOCK_005','BLOCK_015','SITE_CLERGY','SITE_MONASTERY']};zone_masks={}
 for zone in d['zones']:
  zmask=np.zeros(SHAPE,bool)
  for hold in zone['contiguous_holdings']:
   hm=np.zeros(SHAPE,bool);area=0
   for p in hold['polygon_parts_xz_m']:
    xmin=min(q[0]for q in p);xmax=max(q[0]for q in p);zmin=min(q[1]for q in p);zmax=max(q[1]for q in p);ix0=round((xmin-BOUNDS[0])/PITCH);ix1=round((xmax-BOUNDS[0])/PITCH);iz0=round((zmin-BOUNDS[1])/PITCH);iz1=round((zmax-BOUNDS[1])/PITCH);sl=np.s_[iz0:iz1,ix0:ix1]
    assert np.all(r[zone['site_id']][sl]) and not hm[sl].any();hm[sl]=True;area+=geo.polygon_area(p)
   assert ndimage.label(hm)[1]==1 and abs(area-hold['area_m2'])<1e-6 and not(zmask&hm).any();zmask|=hm
  check(zone['id']+':connected_nonoverlapping_owner_safe',not(all_used&zmask).any()and abs(zmask.sum()*PITCH**2-zone['area_m2'])<1e-6)
  all_used|=zmask;zone_masks[zone['id']]=zmask;area_by_site[zone['site_id']]+=zone['area_m2']
 parcel_seen=np.zeros(SHAPE,bool)
 for b in d['range_parcels']:
  q=mask([b['parcel_with_clearance_xz_m']],2,False);check(b['id']+':true_dimension_parcel_inside_holding',np.all(zone_masks[b['zone_id']][q])and not(parcel_seen&q).any());parcel_seen|=q
 for x in d['unresolved_remainder']:
  total=r[x['site_id']].sum()*PITCH**2;check(x['site_id']+':all_available_ground_accounted',abs(area_by_site[x['site_id']]+x['area_m2']-total)<1e-6)
 check('every_holding_has_explicit_access_status',len(acc['connections'])==d['summary']['contiguous_holdings']and all(q['status']in['unresolved','plan_grid_connected_profile_unresolved']for q in acc['connections']))
 check('unresolved_routes_keep_blocker',all(q.get('blocker')for q in acc['connections']if q['status']=='unresolved'))
 check('no_tentative_floor_claim',all(q['floor_y_m']is None for q in terrain['ranges']))
 kinds=sorted(set(s['owner_kind']for q in terrain['ranges']for s in q['samples']));check('range_samples_avoid_water_and_native_holes',all(s['render_land']and s['owner_kind']not in ['water','water_hole','road','replacement_road','door_landing','door_approach']for q in terrain['ranges']for s in q['samples']),kinds)
 check('all_234_terrain_screen_samples_present',terrain['summary']['point_samples']==len(d['range_parcels'])*9)
 result={'schema':'riverstone.remaining_land.tests.v1','plan':ref(HERE/'remaining_land_plan.json'),'checks':checks,'passed':len(checks),'failed':0,'elapsed_seconds':time.monotonic()-start,'limitations':'Source polygon/grid proof only; no native collision, support, controller, route-grade, or actual-view approval.'};write(HERE/'test_results.json',result);print('PASS',len(checks),'checks',round(result['elapsed_seconds'],2),'seconds')
if __name__=='__main__':main()
