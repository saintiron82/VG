from build_plan import *

def main():
 p=load(CITY/'registered_source/plan.json');scene=load(SCENE);r=np.load(HERE/'baseline_masks.npz');domain=r['block_labels']>0;ids={i['id']for i in scene['common_instances']};owner_sources=[dict(q,owner_kind='noble_estate')for q in p['plots']if q['land_use']=='enclosed_noble_compound']+[dict(q,owner_kind='institutional_or_public_space')for q in p['spaces']]
 owner_sources.sort(key=lambda q:(0 if q['id']in('SITE_CEMETERY','SITE_CLOISTER')else 1,q['area_m2']))
 phases=[]
 for key in ('phase01','phase02'):
  path=CITY/f'assemblies/landmarks/registered/precinct_r05_ground/{key}/resolved_placements.json';d=load(path)
  phases.append((key,path,d))
 precinct_path=CITY/'assemblies/landmarks/registered/precinct_r04/coverage_plan.json';precinct=load(precinct_path);landscape_path=CITY/'assemblies/landscape/registered/resolved_placements.json';landscape=load(landscape_path)
 used=np.zeros(SHAPE,bool);rows=[]
 for q in owner_sources:
  om=mask([q['polygon_xz_m']],True);exclusive=om&~used;used|=om;members=[]
  for i in scene['common_instances']:
   x,y,z=i['position_m'];iz=int((z-BOUNDS[1])/PITCH);ix=int((x-BOUNDS[0])/PITCH)
   if 0<=iz<NZ and 0<=ix<NX and om[iz,ix]:members.append({'id':i['id'],'source_pack':i['source_pack']})
  ph=[]
  for key,path,d in phases:
   for h in d['holdings']:
    hm=mask(h['polygon_parts_xz_m']);over=area(om&hm)
    if not over:continue
    present=[i for i in ids if i.startswith(h['id']+':')];ph.append({'phase':key,'holding_id':h['id'],'source_holding_area_m2':h['area_m2'],'owner_intersection_grid_m2':over,'actual_R7_component_ids':present,'source':ref(path),'status':'actual_R7_component_evidence_only_not_whole_owner_completion'if present else'staged_not_in_actual_R7'})
  old=next((s for s in precinct['sites']if s['id']==q['id']),None);ground_refs=[]
  for site in landscape['sites']:
   if 'polygon_xz_m'in site and np.any(mask([site['polygon_xz_m']],True)&om):ground_refs.append({'id':site.get('id'),'source':ref(landscape_path),'status':'finite_garden_ground_reference; source overlap is not whole-owner coverage'})
  rows.append({'source_owner_id':q['id'],'owner_kind':q['owner_kind'],'polygon_xz_m':q['polygon_xz_m'],'source_exact_polygon_area_m2':q['area_m2'],'raw_within_registered_block_faces_grid_m2':area(om&domain),'exclusive_ordinary_exclusion_grid_m2':area(exclusive&domain),'exclusive_whole_owner_grid_m2':area(exclusive),'by_registered_block_grid_m2':{b['id']:area(exclusive&(r['block_labels']==j+1))for j,b in enumerate(p['blocks'])if np.any(exclusive&(r['block_labels']==j+1))},'status':'EXCLUDED_FROM_ORDINARY_REPLANNING_NOT_CERTIFIED_COMPLETE','whole_owner_complete':False,'actual_component_association':{'method':'current actual R7 placement origin inside source polygon; semantic owner membership and covered area need separate verification','components':members,'counts_by_pack':dict(collections.Counter(x['source_pack']for x in members))},'productive_phase_references':ph,'existing_garden_ground_references':ground_refs,'precinct_r04_source_program':None if old is None else{'source':ref(precinct_path),'remaining_source_subareas_area_m2':old.get('remaining_source_subareas_area_m2'),'source_only_subarea_ids':[x['id']for x in old.get('remaining_subareas',[])],'status':'source program; do not count as actual completed land'},'intentionally_open_ground_policy':'Castle/training courts, ceremony, enclosed noble gardens and service lawns may remain open only with a named function, route and actual facility/boundary evidence; generic precinct polygon is not completion.'})
 result={'schema':'riverstone.r8.protected_source_owner_ledger.v1','scene':ref(SCENE),'registered_plan':ref(CITY/'registered_source/plan.json'),'owners':rows,'method':{'raw_area':'Exact source polygon area; overlaps are retained and must not be summed as exclusive area.','exclusive_area':'1m center-sampled ownership priority: cemetery/cloister subowners first, then ascending source polygon area. Every protected sample belongs to exactly one reported owner; no native completion claim.','footprint_limit':'Actual instance association by origin is not native footprint coverage. This ledger intentionally leaves nonordinary function/ground completion open.'},'summary':{'owners':len(rows),'exclusive_protected_area_within_block_faces_m2':sum(q['exclusive_ordinary_exclusion_grid_m2']for q in rows),'source_overlap_warning':True,'automatically_completed_area_m2':0,'all_owners_actual_completion_requires_review':True},'protected_native_special_owner_exclusions_separate':{'note':'Existing ordinary-density/merchant/working-range native footprints are separately reported in the ordinary block ledger. Their retained presence also does not certify entire plot use.'}}
 assert result['summary']['exclusive_protected_area_within_block_faces_m2']==area(domain&(r['spaces']|r['estates']))
 write('protected_source_owner_ledger.json',result)
 plan=load(HERE/'whole_city_coverage_plan.json');plan['protected_source_owner_ledger']=ref(HERE/'protected_source_owner_ledger.json')
 for c in plan['categories']:
  if c['category']=='protected_institution_estate':c['completion_status']='excluded_from_ordinary_replanning; not automatically finished';c['automatically_completed_area_m2']=0
 for b in plan['blocks']:
  for c in b['land_use_partition']:
   if c['category']=='protected_institution_estate':c['status']='excluded_only_not_complete'
 write('whole_city_coverage_plan.json',plan)
 print(json.dumps(result['summary']));print([(q['source_owner_id'],q['exclusive_ordinary_exclusion_grid_m2'])for q in rows])
if __name__=='__main__':main()
