"""Import the fabric owner's frozen B15 candidate, without changing any native ID.
Run only after receiving the owner's final path/hash. No compilation or scene edit.
"""
from build_plan import *
import argparse

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--layout',required=True);ap.add_argument('--sha256',required=True);args=ap.parse_args();path=ROOT/args.layout;assert sha(path)==args.sha256;d=load(path);plan=load(HERE/'whole_city_coverage_plan.json');parc=load(HERE/'parcel_candidates.json');r=np.load(HERE/'baseline_masks.npz');old=np.load(HERE/'allocation_masks.npz');oldland=old['land_use'];proj=load(HERE/'native_projection.json');sp=load(CITY/'registered_source/plan.json');bi=next(i+1 for i,b in enumerate(plan['blocks'])if b['block_id']=='BLOCK_015');bm=r['block_labels']==bi
 native_path=ROOT/d['native_local']['path'];assert sha(native_path)==d['native_local']['sha256'];native=load(native_path);actual_ids={i['id']for i in load(SCENE)['common_instances']};assert set(d['retired_source_ids'])<=actual_ids
 holdings=[h for h in parc['holdings']if h['block_id']!='BLOCK_015'];routes=[q for q in parc['routes']if q.get('block_id')!='BLOCK_015'];accepted=[]
 for h in d['holdings']:
  pp=[x for x in d['placements']if x.get('holding_id')==h['id']];assert pp
  roof=[poly for x in pp for poly in x['native_roof_polygons_xz_m']];placement=pp[0];hm=mask([h['holding_polygon_xz_m']]);nm=mask(roof)
  # Native candidates must not consume any protected owner category. Report an
  # exception rather than clipping actual native geometry to make it pass.
  forbidden=bm&np.isin(oldland,[1,2,3,4,5,6]);bad=area(nm&forbidden)
  assert bad==0,(h['id'],'native candidate overlaps protected source plan at1m center sample',bad)
  accepted.append({'id':h['id'],'batch_id':'R8_A_LOWER_CANAL','block_id':'BLOCK_015','grammar_id':placement['asset_key'],'role':placement.get('role','native_attached_court'),'origin_xz_m':[placement['position_m'][0],placement['position_m'][2]],'yaw_rad':placement['yaw_rad'],'holding_polygon_xz_m':h['holding_polygon_xz_m'],'building_envelope_parts_xz_m':roof,'native_roof_parts_xz_m':roof,'native_placement_ids':[x['id']for x in pp],'source_building_envelope_area_m2':sum(x['roof_area_m2']for x in pp),'attached_range_count':(3 if 'craft_U' in placement['asset_key'] else 2 if '_L' in placement['asset_key'] else 1),'gate_position_xz_m':h['gate_position_xz_m'],'gate_width_m':h['external_width_m'],'street_road_id':'fabric_reserved_backbone; see immutable external/shared route evidence','street_connection_polyline_xz_m':h['external_route'],'route_ribbon_polygons_xz_m':h['external_route_polygons_xz_m'],'private_court_polygon_parts_xz_m':h['core_court_polygons_xz_m'],'planned_court_area_grid_m2':area(hm&~nm),'retire_native_instance_ids':h['retired_source_ids'],'finished_floor_y_m':h['floor_y_m'],'status':'compiled_native_candidate; not yet actual_R7_scene','source_binding':ref(path),'native_local':ref(native_path),'completion_gate':['Use immutable native IDs and exact accepted support/route snapshot from district fabric owner.','Retire old ordinary geometry and restore accepted terrain holes atomically.','Actual integrated view and route gate still required before block completion.']})
  routes.append({'id':h['id']+':ENTRY','block_id':'BLOCK_015','holding_id':h['id'],'role':'native_candidate_private_access','width_m':h['external_width_m'],'polyline_xz_m':h['external_route'],'ribbon_polygons_xz_m':h['external_route_polygons_xz_m'],'native_grade_approval':'see frozen R17 district evidence, not inferred by this import'})
 for q in d.get('shared_private_routes',[]):routes.append({'id':q['id'],'block_id':'BLOCK_015','role':q['role'],'width_m':q['width_m'],'polyline_xz_m':q['polyline_xz_m'],'ribbon_polygons_xz_m':q['polygons_xz_m'],'source_binding':ref(path),'native_grade_approval':'see frozen R17 district evidence'})
 holdings+=accepted;parc['holdings']=holdings;parc['routes']=routes;parc['native_B15_binding']={'layout':ref(path),'native_local':ref(native_path),'builder_summary':d['summary'],'source_owner':'district_fabric_r01','source_ids_unchanged':True,'actual_R7_unmodified':True}
 retirement_ids=sorted(set(i for h in holdings for i in h['retire_native_instance_ids'])|set(d['retired_source_ids']));parc['retirement_ledger']=[{'native_instance_id':i,'replacement_holding_ids':[h['id']for h in holdings if i in h['retire_native_instance_ids']],'retire_source_private_path_ids':[q['id']for q in sp['paths']if q.get('owner_building_id')==i],'condition':'Atomic accepted district replacement; never delete from R7 merely because source plan exists.'}for i in retirement_ids]
 write('parcel_candidates.json',parc)
 newlabels=np.zeros(SHAPE,np.int32);newroof=np.zeros(SHAPE,bool);courts=np.zeros(SHAPE,bool)
 for j,h in enumerate(holdings,1):
  hm=mask([h['holding_polygon_xz_m']]);nm=mask(h['building_envelope_parts_xz_m']);newlabels[hm]=j;newroof|=nm;courts|=hm&~nm
 retired=np.zeros(SHAPE,bool);retained=np.zeros(SHAPE,bool)
 for i in proj['instances']:
  if i['source_pack']!='ordinary':continue
  target=retired if i['id']in retirement_ids else retained
  for poly in i['roof_parts_xz_m']:add(target,poly)
 land=np.where(np.isin(oldland,[1,2,3,4,5,6]),oldland,0).astype(np.uint8);left=(r['block_labels']>0)&(land==0);publicside=buffer(r['road'],1)&~r['water']&~np.isin(oldland,[1,2,3,4,5,6]);entry=mask([poly for q in routes for poly in q.get('ribbon_polygons_xz_m',[])])
 for code,m in[(7,publicside|entry),(8,newroof),(9,courts),(10,retained)]:take=left&m;land[take]=code;left&=~take
 seeds=(newlabels>0)|retained;distance,inds=ndimage.distance_transform_edt(~seeds,return_indices=True);near=newlabels[tuple(inds)];garden=left&(distance<=6)&(near>0);land[garden]=11;left&=~garden
 upper=[i+1 for i,b in enumerate(plan['blocks'])if b['block_id']in('BLOCK_001','BLOCK_003','BLOCK_005')];margin=left&np.isin(r['block_labels'],upper);land[margin]=12;left&=~margin;oldground=left&(ndimage.distance_transform_edt(~retained)<=8);land[oldground]=13;left&=~oldground;land[left]=14
 after=(r['roof']&~retired)|newroof;density=(r['block_labels']>0)&~(r['spaces']|r['estates']|buffer(r['water'],4)|r['wall']|r['road'])
 for cat in plan['categories']:cat['area_m2']=area(land==cat['code'])
 for j,b in enumerate(plan['blocks'],1):
  bb=r['block_labels']==j;hs=[h for h in holdings if h['block_id']==b['block_id']];b['land_use_partition']=[{'category':c['category'],'area_m2':area(bb&(land==c['code'])),'code':c['code'],'status':'excluded_only_not_complete'if c['code']==1 else'actual_or_source_status_in_category_definition'}for c in plan['categories']];b['candidate_holding_ids']=[h['id']for h in hs];b['proposed_attached_envelope_m2']=sum(h['source_building_envelope_area_m2']for h in hs);b['retire_native_instance_ids']=sorted({i for h in hs for i in h['retire_native_instance_ids']});b['unassigned_m2']=area(bb&left);b['source_plan_complete']=False;b['actual_scene_complete']=False
  g=b['roof_gain_review'];den=area(bb&density);g.update(actual_R7_retirement_roof_m2=area(bb&retired),proposed_roof_union_m2=area(bb&newroof),prospective_roof_union_m2=area(bb&after),net_roof_gain_m2=area(bb&after)-area(bb&r['roof']),ordinary_prospective_roof_fraction=area(bb&density&after)/max(1,den));g['remaining_roof_capacity_to_lower_prior_m2']=max(0,den*g['design_prior_target_fraction'][0]-area(bb&density&after));g['no_roof_regression_pass']=g['net_roof_gain_m2']>=0
  if b['block_id']=='BLOCK_015':b['native_candidate_binding']=ref(path);b['native_candidate_summary']=d['summary'];b['native_candidate_status']='compiled exact footprints with frozen owner evidence; actual scene completion still false'
 for batch in plan['batches']:batch['holding_ids']=[h['id']for h in holdings if h['batch_id']==batch['id']]
 plan['parcel_candidates']=ref(HERE/'parcel_candidates.json');plan['native_B15_binding']=parc['native_B15_binding'];plan['summary'].update(candidate_holdings=len(holdings),proposed_attached_ranges=sum(h['attached_range_count'] for h in holdings),proposed_building_envelope_area_m2=sum(h['source_building_envelope_area_m2']for h in holdings),ordinary_detached_retirement_candidates=len(retirement_ids),unassigned_area_m2=area(left),net_native_roof_gain_source_diagnostic_m2=sum(b['roof_gain_review']['net_roof_gain_m2']for b in plan['blocks']),remaining_roof_capacity_to_lower_prior_m2=sum(b['roof_gain_review']['remaining_roof_capacity_to_lower_prior_m2']for b in plan['blocks']));plan['status']='B15 frozen native candidate imported without changing IDs; remaining blocks source planning; no actual completion claim';write('whole_city_coverage_plan.json',plan)
 np.savez_compressed(HERE/'allocation_masks.npz',land_use=land,holdings=newlabels,proposed_roof=newroof,proposed_court=courts,retired_roof=retired,retained_ordinary_roof=retained,private_ground=garden,unassigned=left,pitch=PITCH,bounds=BOUNDS)
 write('block_015_native_import.json',{'scene':ref(SCENE),'layout':ref(path),'native_local':ref(native_path),'builder_summary':d['summary'],'holdings':accepted,'retirement_ids':d['retired_source_ids'],'source_ids_preserved':True,'new_geometry_compiled_by_this_import':False,'actual_scene_modified':False})
 print({'imported_holdings':len(accepted),'binding':ref(path),'builder_net_roof_gain_m2':d['summary']['net_ordinary_roof_gain_m2'],'plan_summary':plan['summary']})
if __name__=='__main__':main()
