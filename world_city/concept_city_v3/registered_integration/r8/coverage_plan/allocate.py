"""Route-first, reusable parcel grammar and complete land-use ledger for all blocks."""
from build_plan import *

# District-scale jobs, not house-at-a-time batches.
BATCHES=[
 ('R8_A_LOWER_CANAL',['BLOCK_015'],'Complete both canal-bank work/residential fabrics, rear domestic courts and continuous tow/service access.'),
 ('R8_B_EAST_WORKING',['BLOCK_007','BLOCK_013'],'Complete two eastern working blocks around retained native attached rows; connect real workyards and household courts.'),
 ('R8_C_MARKET_MERCHANT',['BLOCK_002','BLOCK_004','BLOCK_008','BLOCK_010','BLOCK_011'],'Continuous shop/residence fronts and private merchant work courts. Activate or reconcile the twelve pending merchant holdings.'),
 ('R8_D_SOUTH_GATE',['BLOCK_014','BLOCK_016','BLOCK_017','BLOCK_018'],'Finish southern trade streets and attached lodging/service courts, leaving gate and wall inspection routes open.'),
 ('R8_E_UPPER_SERVICE',['BLOCK_000','BLOCK_001','BLOCK_006'],'Finish selective upper-service fronts and private kitchen gardens without suburban detached-row spacing.'),
 ('R8_F_PRECINCT_MARGINS',['BLOCK_003','BLOCK_005'],'Productive/private grounds, selective service courts and continuous wall/water maintenance access around protected precincts.'),
 ('R8_G_MARKET_RETAIN',['BLOCK_012'],'Retain the protected civic/market floor; close logistics and circulation checks, with no ordinary infill.')]
GRAMMARS=[
 {'id':'ATTACHED_DOUBLE_RANGE_30_10','holding_m':[34.,28.],'building_parts_local':[rect(-15,3,15,13),rect(-15,-13,15,-3)],'role':'domestic_work_court','range_count':2,'native_builder_size_m':[30,26],'private_court_clear_dimensions_m':[30,6],'side_passage_clear_width_m':2},
 {'id':'CRAFT_U_30_28','holding_m':[32.,30.],'building_parts_local':[rect(-15,4,15,14),rect(-15,-14,-7,4),rect(7,-14,15,4)],'role':'work_court','range_count':3,'native_builder_size_m':[30,28]},
 {'id':'DOMESTIC_L_24_25','holding_m':[26.,27.],'building_parts_local':[rect(-12,3.5,12,12.5),rect(-12,-12.5,-4,3.5)],'role':'domestic_court','range_count':2,'native_builder_size_m':[24,25]},
 {'id':'COMPACT_L_17_22','holding_m':[19.,23.],'building_parts_local':[rect(-8.5,3,8.5,11),rect(-8.5,-11,-1.5,3)],'role':'domestic_court','range_count':2,'native_builder_size_m':[17,22]},
 {'id':'FRONT_RANGE_30_10','holding_m':[32.,20.],'building_parts_local':[rect(-15,0,15,10)],'role':'work_court','range_count':1,'native_builder_size_m':[30,10]},
 {'id':'NARROW_RANGE_24_9','holding_m':[26.,18.],'building_parts_local':[rect(-12,-1,12,8)],'role':'domestic_court','range_count':1,'native_builder_size_m':[24,9]}]

def frame(cx,cz,w,d,yaw):return xform(rect(-w/2,-d/2,w/2,d/2),{'position_m':[cx,0,cz],'yaw_rad':yaw})
def cell(x,z):return (int((z-BOUNDS[1])/PITCH),int((x-BOUNDS[0])/PITCH))
def thin_points(line,step=8):
 accum=0.;out=[]
 for a,b in zip(line,line[1:]):
  length=math.dist(a,b)
  if length<1e-8:continue
  u=((b[0]-a[0])/length,(b[1]-a[1])/length)
  while accum<length:
   out.append(([a[0]+accum*u[0],a[1]+accum*u[1]],u));accum+=step
  accum-=length
 return out

def main():
 start=time.monotonic();p=load(CITY/'registered_source/plan.json');base=load(HERE/'baseline_blocks.json');proj=load(HERE/'native_projection.json');r=np.load(HERE/'baseline_masks.npz');dom=r['block_labels'];blocks=base['blocks'];inst=proj['instances'];source=load(SCENE)
 # Preserve all nineteen reviewed merchant frames. The twelve absent in actual
 # R7 stay explicitly source-only, not silently "built".
 merchant_path=CITY/'assemblies/property/registered/merchant_fabric_r02/effective_eligibility.json';merchant=load(merchant_path);hand=load(CITY/'assemblies/property/registered/merchant_fabric_r02/terrain_handoff.json');special_polys=[];special_rows=[];actual_ids={q['id']for q in source['common_instances']}
 for q in merchant['properties']:
  exists=any(i.startswith(q['id']+':')for i in actual_ids)
  ps=[q['polygon_xz_m'],q['external_gate_link']['polygon_xz_m']]
  for route in q['internal_routes']:ps+=route['ribbon_polygons_xz_m']+route['round_join_polygons_xz_m']
  h=next(x for x in hand['properties']if x['property_id']==q['id']);ps+=h['retained_lower_ground']['polygons_xz_m'];special_polys+=ps
  special_rows.append({'id':q['id'],'block_id':q['block_id'],'polygon_parts_xz_m':ps,'status':'actual_R7'if exists else'pending_reviewed_source_not_implemented','retire_on_activation_only':q['source_retired_native_ids']})
 phase02_path=CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase02/resolved_placements.json'
 phase02=load(phase02_path)
 for q in phase02['holdings']:
  special_polys+=q['polygon_parts_xz_m']
 for q in phase02.get('internal_routes',[]):special_polys+=q['ribbon_polygons_xz_m']
 collar_path=CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase02/collar_design.json'
 collar=load(collar_path);special_polys.append(collar['polygon_xz_m'])
 special=mask(special_polys,True)
 hard=r['spaces']|r['estates']|r['retained_native']|r['retained_access']|r['wall']|special
 wetservice=buffer(r['water'],4.0)
 # First reserve the complete walking-side strips. They are source circulation
 # reservations, not a claim that these new strips have a traversable surface.
 publicside=buffer(r['road'],1.0)&~r['water']&~hard
 safe=(dom>0)&~hard&~wetservice&~publicside&~r['road']
 # Safety clearance is additional to the raster approximation. Existing ordinary
 # detached occupancy is intentionally not a hard mask; every overlap is named.
 safe=ndimage.distance_transform_edt(safe)>=1.0
 newlabels=np.zeros(SHAPE,np.int32);newroof=np.zeros(SHAPE,bool);courts=np.zeros(SHAPE,bool);routes=[];holdings=[]
 road_by={q['id']:q for q in p['roads']};block_by={q['block_id']:j+1 for j,q in enumerate(blocks)}
 # Tow/service reservation covers both banks rather than isolated objects.
 canal_ids=['CRAFT_CANAL_VISIBLE','EAST_CHANNEL_VISIBLE']
 for ch in p['water_reservations']['channels']:
  if ch['id']not in canal_ids:continue
  routes.append({'id':'R8_TOW_'+ch['id'],'role':'two_bank_tow_and_service','center_water_polyline_xz_m':ch['polyline_xz_m'],'wet_width_m':ch['width_m'],'dry_no_build_width_each_bank_m':4.0,'required_clear_walk_width_m':3.5,'status':'reserved_before_buildings; bank sides remain separate unless a verified existing bridge connects them','native_grade_approval':False,'new_bridge_permission':False})
 for batchid,bids,why in BATCHES:
  for bid in bids:
   bi=block_by[bid];bm=dom==bi
   if bid=='BLOCK_012':continue
   if bid=='BLOCK_015':
    frozen=load(HERE/'b15_tight_source_diagnostic_NOT_AUTHORITATIVE.json')
    for h in frozen['holdings']:
     hm=mask([h['holding_polygon_xz_m']]);br=mask(h['building_envelope_parts_xz_m']);holdings.append(h);newlabels[hm]=len(holdings);newroof|=br;courts|=hm&~br;safe[buffer(hm,1.0)]=False
    routes += [q for q in frozen['routes']if q.get('block_id')==bid]
    print('FROZEN B15 SOURCE DIAGNOSTIC',len(frozen['holdings']),'native builder owns accepted layout',flush=True)
    continue
   allowed=safe&bm
   # Upper noble/wall margins have fewer selective service rows; the parcel
   # programs below still account for all their gardens and maintenance ground.
   maxholds=999 if bid not in ('BLOCK_001','BLOCK_003','BLOCK_005')else({'BLOCK_001':8,'BLOCK_003':20,'BLOCK_005':28}[bid])
   eligible=[road_by[rid]for rid in blocks[bi-1]['boundary_road_ids']+([bid+':ALLEY']if bid+':ALLEY'in road_by else[])if rid in road_by]
   # Internal alleys first make genuine rear/private court frontage possible.
   eligible.sort(key=lambda q:(0 if ':ALLEY'in q['id']else 1,q['id']))
   count=0
   for grammar in GRAMMARS:
    if grammar['id']=='ATTACHED_DOUBLE_RANGE_30_10' and bid in ('BLOCK_000','BLOCK_001','BLOCK_003','BLOCK_005','BLOCK_006','BLOCK_015'):continue
    if count>=maxholds:break
    w,d=grammar['holding_m']
    for road in eligible:
     if count>=maxholds:break
     for pt,u in thin_points(road['polyline_xz_m'],3.):
      if count>=maxholds:break
      for side in (1,-1):
       # Local +Z faces the public route; local -Z points into the holding.
       inward=(-u[1]*side,u[0]*side);outward=(-inward[0],-inward[1]);yaw=math.atan2(outward[0],outward[1])
       offset=road['width_m']/2+2.0+d/2;cx=pt[0]+inward[0]*offset;cz=pt[1]+inward[1]*offset
       iz,ix=cell(cx,cz)
       if not(0<=iz<NZ and 0<=ix<NX and allowed[iz,ix]):continue
       poly=frame(cx,cz,w,d,yaw);hm=mask([poly]);n=int(hm.sum())
       if n<.96*w*d or not np.all(allowed[hm]):continue
       # Full-width private gate link is reserved before any native envelope.
       gate=[cx+outward[0]*d/2,cz+outward[1]*d/2]
       if grammar['id']=='ATTACHED_DOUBLE_RANGE_30_10':gate=[gate[0]+math.cos(yaw)*16,gate[1]-math.sin(yaw)*16]
       line=[gate,pt];entry=mask(ribbon(line,3.5))
       forbidden=hard|r['water']
       if np.any(entry&forbidden)or np.any(entry&(newlabels>0)):continue
       iid=f'{bid}:R8_P{count+1:03d}';group_id=len(holdings)+1;tf={'position_m':[cx,0,cz],'yaw_rad':yaw};bps=[xform(q,tf)for q in grammar['building_parts_local']];br=mask(bps)
       assert not np.any(br&~hm)
       retired=[]
       for i in inst:
        if i['source_pack']!='ordinary':continue
        # First reject distant bounds, then actual native projected footprint.
        if math.dist([cx,cz],[i['position_m'][0],i['position_m'][2]])>max(w,d)+25:continue
        if any(np.any(mask([q])&(hm|entry))for q in i['native_owner_parts_xz_m']):retired.append(i['id'])
       holdings.append({'id':iid,'batch_id':batchid,'block_id':bid,'grammar_id':grammar['id'],'role':grammar['role'],'origin_xz_m':[cx,cz],'yaw_rad':yaw,'holding_dimensions_m':[w,d],'holding_polygon_xz_m':poly,'building_envelope_parts_xz_m':bps,'source_building_envelope_area_m2':sum(geo.polygon_area(q)for q in bps),'attached_range_count':grammar['range_count'],'gate_position_xz_m':gate,'gate_width_m':(2.0 if grammar['id']=='ATTACHED_DOUBLE_RANGE_30_10'else 3.5),'street_road_id':road['id'],'street_connection_polyline_xz_m':line,'route_ribbon_polygons_xz_m':ribbon(line,3.5),'private_court_polygon_parts_xz_m':parts(hm&~br),'planned_court_area_grid_m2':area(hm&~br),'retire_native_instance_ids':retired,'finished_floor_y_m':None,'status':'source_candidate_not_compiled; requires exact native/terrain/route acceptance','building_rule':'True-dimension attached L/U/range. No mesh scaling. Range units share party walls; courtyard stays private except named gate passage.','private_use_required':['domestic cooking/washing/drying and kitchen plot'if grammar['role']=='domestic_court'else'trade-specific working apron, covered storage and cart turn','screened waste/fuel enclosure off the walking line','real boundary and gate, not ornamental props'],'completion_gate':['Exact native projected roof and bottom-bearing ownership inside accepted parcel','Native door and full 3.5 m gate route to named preserved road; no props or thresholds obstruct it','Private court and productive/work uses implemented from this source partition','Retire every listed old native instance atomically with its replacement and obsolete private entry']})
       newlabels[hm]=group_id;newroof|=br;courts|=hm&~br
       allowed[buffer(hm,1.0)|entry]=False
       safe[buffer(hm,1.0)|entry]=False
       routes.append({'id':iid+':ENTRY','block_id':bid,'holding_id':iid,'role':'private_gate_to_preserved_public_road','width_m':3.5,'polyline_xz_m':line,'ribbon_polygons_xz_m':ribbon(line,3.5),'source_road_id':road['id'],'native_grade_approval':False})
       count+=1
   write((bid.lower()+'_route_parcels.json')if bid!='BLOCK_015'else'b15_tight_source_diagnostic_NOT_AUTHORITATIVE.json',{'block_id':bid,'scene':ref(SCENE),'holdings':[q for q in holdings if q['block_id']==bid],'routes':[q for q in routes if q.get('block_id')==bid or q['id'].startswith('R8_TOW')],'special_reserved_polygon_parts_xz_m':parts(special&bm),'available_after_route_reservations_polygon_parts_xz_m':parts(safe&bm),'method':'1m planning source, exact native/floor acceptance pending; roads and dry canal4m bands reserved first'})
   print('ALLOC',bid,count,'holdings',area(newlabels*bm>0),flush=True)
 # Reject whole source replacement groups that would lose native roof area.
 # Shared old native IDs couple replacements: evaluate these atomically rather
 # than double-counting their retirement in separate holdings.
 groups=[];remaining=set(range(len(holdings)));idsets=[set(h['retire_native_instance_ids'])for h in holdings]
 while remaining:
  q=remaining.pop();group={q};ids=set(idsets[q]);changed=True
  while changed:
   changed=False
   for j in list(remaining):
    if ids&idsets[j]:group.add(j);ids|=idsets[j];remaining.remove(j);changed=True
  groups.append((group,ids))
 rejects=[];remove=set();native_by={i['id']:i for i in inst}
 for group,ids in groups:
  if any(holdings[j]['block_id']=='BLOCK_015'for j in group):continue
  oldm=mask([poly for i in ids for poly in native_by[i]['roof_parts_xz_m']]);newm=mask([poly for j in group for poly in holdings[j]['building_envelope_parts_xz_m']])
  if area(newm)+.01<area(oldm):
   remove|=group;rejects.append({'holding_ids':[holdings[j]['id']for j in sorted(group)],'retired_native_roof_m2':area(oldm),'proposed_roof_m2':area(newm),'reason':'Reject unexplained native roof regression; retain old geometry until denser coherent deep plot is authored.'})
 if remove:
  holdings=[h for j,h in enumerate(holdings)if j not in remove];keep={h['id']for h in holdings};routes=[q for q in routes if not q.get('holding_id')or q['holding_id']in keep];newlabels[:]=0;newroof[:]=False;courts[:]=False
  for j,h in enumerate(holdings,1):
   hm=mask([h['holding_polygon_xz_m']]);br=mask(h['building_envelope_parts_xz_m']);newlabels[hm]=j;newroof|=br;courts|=hm&~br
 write('rejected_roof_regression_groups.json',{'groups':rejects,'retained_actual_native_geometry':True,'new_replacement_required':True})
 # Global retirement identities never create untracked ghosts or stale door paths.
 retirement_ids=sorted({i for q in holdings for i in q['retire_native_instance_ids']});retire_set=set(retirement_ids);retired=np.zeros(SHAPE,bool);retained_ordinary=np.zeros(SHAPE,bool)
 for q in inst:
  if q['source_pack']=='ordinary':
   target=retired if q['id']in retire_set else retained_ordinary
   for poly in q['roof_parts_xz_m']:add(target,poly)
 entrymask=mask([q for r0 in routes for q in r0.get('ribbon_polygons_xz_m',[])])
 # Full land-use partition. Every sample is accounted. Unassigned is real and
 # never replaced by an unsupported "green"/"complete" label.
 categories=[('protected_institution_estate',r['spaces']|r['estates']),('water_and_4m_bank_service',wetservice),('protected_wall_service',r['wall']),('preserved_public_road',r['road']),('retained_native_special_owner',r['retained_native']|r['retained_access']),('reviewed_merchant_source_pending_or_retained',special),('reserved_public_walk_and_private_entry',publicside|entrymask),('proposed_attached_building_envelope',newroof),('proposed_private_court',courts),('retained_detached_native_roof_pending_frontage_review',retained_ordinary)]
 land=np.zeros(SHAPE,np.uint8);classrows=[];left=(dom>0)
 for code,(name,m)in enumerate(categories,1):take=left&m;land[take]=code;left&=~take;classrows.append({'code':code,'category':name,'area_m2':area(take),'geometry_status':'proposed_source'if name.startswith(('proposed','reserved','reviewed'))else'actual_or_protected'})
 # Assign private land to a named new/retained property only when a short clear
 # route from its court exists. Other ground stays explicit unresolved land.
 seeds=(newlabels>0)|retained_ordinary;dist,inds=ndimage.distance_transform_edt(~seeds,return_indices=True);near_label=newlabels[tuple(inds)];garden=left&(dist<=6)&(near_label>0);land[garden]=11;left&=~garden;classrows.append({'code':11,'category':'proposed_private_productive_or_work_ground','area_m2':area(garden),'geometry_status':'source_use_only; exact boundary and access must be authored'})
 # Purposeful precinct/wall margin programs are finite source reservations,
 # not proof of actual crops or maintenance access. These remain task items.
 margin=left&np.isin(dom,[block_by[x]for x in ('BLOCK_001','BLOCK_003','BLOCK_005')]);land[margin]=12;left&=~margin;classrows.append({'code':12,'category':'proposed_precinct_margin_productive_service_ground','area_m2':area(margin),'geometry_status':'source_only_requires_contiguous_productive_enclosures_and_service_access'})
 # Retained detached household backlands remain an explicit consolidated retrofit
 # parcel. Adjacent blank ground does not count as an implemented garden.
 dist_old=ndimage.distance_transform_edt(~retained_ordinary);oldground=left&(dist_old<=8);land[oldground]=13;left&=~oldground;classrows.append({'code':13,'category':'retained_household_plot_reconfigure_ground','area_m2':area(oldground),'geometry_status':'unimplemented household garden/work/court retrofit; existing house alone does not complete it'})
 land[left]=14;classrows.append({'code':14,'category':'unassigned_requires_parcel_or_access_decision','area_m2':area(left),'geometry_status':'explicit_unfinished'})
 after_roof=(r['roof']&~retired)|newroof
 density_domain=(dom>0)&~(r['spaces']|r['estates']|wetservice|r['wall']|r['road'])
 blockout=[]
 for bi,b in enumerate(blocks,1):
  bm=dom==bi;rows=[{'category':c['category'],'area_m2':area(bm&(land==c['code'])),'code':c['code']}for c in classrows];assert sum(q['area_m2']for q in rows)==area(bm)
  hs=[q for q in holdings if q['block_id']==b['block_id']];un=area(left&bm);status='protected_civic_market_keep'if b['block_id']=='BLOCK_012'else'full_source_partition_with_explicit_unfinished_work'
  blockout.append({**{k:v for k,v in b.items()if k!='ordinary_replanning_polygon_parts_xz_m'},'status':status,'batch_id':next(a for a,ids,_ in BATCHES if b['block_id']in ids),'land_use_partition':rows,'candidate_holding_ids':[q['id']for q in hs],'proposed_attached_envelope_m2':sum(q['source_building_envelope_area_m2']for q in hs),'retire_native_instance_ids':sorted({i for q in hs for i in q['retire_native_instance_ids']}),'unassigned_m2':un,'source_plan_complete':False if un>0 else True,'roof_gain_review':{'actual_R7_screened_roof_m2':area(bm&r['roof']),'actual_R7_retirement_roof_m2':area(bm&retired),'proposed_roof_union_m2':area(bm&newroof),'prospective_roof_union_m2':area(bm&after_roof),'net_roof_gain_m2':area(bm&after_roof)-area(bm&r['roof']),'ordinary_density_denominator_m2':area(bm&density_domain),'ordinary_current_native_roof_fraction':area(bm&density_domain&r['roof'])/max(1,area(bm&density_domain)),'ordinary_prospective_roof_fraction':area(bm&density_domain&after_roof)/max(1,area(bm&density_domain)),'design_prior_target_fraction':[.40,.60]if b['block_id']in('BLOCK_007','BLOCK_013','BLOCK_015')else[.35,.50],'target_is_game_design_prior_not_measured_historical_ratio':True},'actual_scene_complete':False,'completion_criteria':{'unassigned_area_m2_max':0,'unassigned_component_over_25m2_max':0,'named_property_or_public_owner_fraction_min':1.0,'new_holding_gate_route_pass_fraction_min':1.0,'protected_road_water_special_owner_change_max':0,'source_reservation_counted_as_actual_complete':False,'eligible_rebuilt_street_frontage_attached_fraction_min':.65,'permeability_rule':'Keep 2 m clear walking routes and 3.5 m service/gate approaches, crossings only on verified existing bridges. Close every access gap explicitly.','land_use_rule':'Every private plot includes actual domestic/work/productive ground and boundaries; ceremonial/market and maintenance open land requires named function and connected route.','visual_gate':'Review registered whole-city camera plus district oblique and two eye-level route views before calling this block complete.'}})
 np.savez_compressed(HERE/'allocation_masks.npz',land_use=land,holdings=newlabels,proposed_roof=newroof,proposed_court=courts,retired_roof=retired,retained_ordinary_roof=retained_ordinary,private_ground=garden,unassigned=left,pitch=PITCH,bounds=BOUNDS)
 for b in blocks:
  if b['block_id']=='BLOCK_015':continue
  bid=b['block_id'];bi=block_by[bid];bm=dom==bi
  free_final=bm&~hard&~wetservice&~publicside&~r['road']&~buffer(newlabels>0,1.0)&~entrymask
  write(bid.lower()+'_route_parcels.json',{'block_id':bid,'scene':ref(SCENE),'holdings':[q for q in holdings if q['block_id']==bid],'routes':[q for q in routes if q.get('block_id')==bid],'special_reserved_polygon_parts_xz_m':parts(special&bm),'available_after_route_reservations_polygon_parts_xz_m':parts(free_final),'source_only':True,'no_unexplained_native_roof_regression':True})
 write('parcel_candidates.json',{'schema':'riverstone.r8.route_first_parcel_candidates.v1','scene':ref(SCENE),'status':'source candidates only; no geometry compiled','grammars':GRAMMARS,'holdings':holdings,'routes':routes,'reviewed_merchant_holdings':special_rows,'retirement_ledger':[{'native_instance_id':i,'replacement_holding_ids':[q['id']for q in holdings if i in q['retire_native_instance_ids']],'retire_source_private_path_ids':[q['id']for q in p['paths']if q.get('owner_building_id')==i],'condition':'Atomic actual replacement; do not delete while this remains a source proposal.'}for i in retirement_ids]})
 write('whole_city_coverage_plan.json',{'schema':'riverstone.r8.whole_city_coverage_plan.v1','status':'all eighteen blocks accounted; source proposals distinguished from actual scene; explicit unresolved land remains','scene':ref(SCENE),'source_plan':ref(CITY/'registered_source/plan.json'),'baseline':ref(HERE/'baseline_blocks.json'),'native_projection':ref(HERE/'native_projection.json'),'parcel_candidates':ref(HERE/'parcel_candidates.json'),'prior_remaining_land_plan':ref(CITY/'assemblies/landmarks/registered/remaining_land_r01/remaining_land_plan.json'),'method':{'planning_pitch_m':PITCH,'max_point_to_cell_corner_m':math.sqrt(2)/2,'roof_measure':'Native local horizontal exterior roof/canopy projection; current actual instances only. World category sums are center-sampled, not exact vector area.','unused_old_plot_policy':'All ordinary B_REG plot envelopes reopened; native IDs retire only in explicit replacement groups. No old design building counts imply completed land.','route_first':True,'whole_city_terrain_recompute':False,'new_geometry_compiled':False,'actual_completion_claim':False},'batches':[{'id':a,'block_ids':b,'objective':c,'holding_ids':[q['id']for q in holdings if q['batch_id']==a],'block_count':len(b),'estimated_attached_ranges':sum(q['attached_range_count']for q in holdings if q['batch_id']==a),'sequence':['Review full source land partition and retirement groups','Seal walking/service/tow route reservations','Resolve exact terrain bands/support as a district batch','Dimension-author reusable native L/U/range grammar','Validate exact native footprint/doors/full-width routes and actual integrated view','Close all residual components and actual-use checks']}for a,b,c in BATCHES],'categories':classrows,'blocks':blockout,'summary':{'ordinary_block_faces':len(blockout),'candidate_holdings':len(holdings),'proposed_attached_ranges':sum(q['attached_range_count']for q in holdings),'proposed_building_envelope_area_m2':sum(q['source_building_envelope_area_m2']for q in holdings),'ordinary_detached_retirement_candidates':len(retirement_ids),'actual_detached_instances':base['summary']['actual_detached_instances'],'unassigned_area_m2':area(left),'reviewed_merchant_holdings':len(special_rows),'reviewed_merchant_not_in_actual_R7':sum(q['status'].startswith('pending')for q in special_rows),'seconds':time.monotonic()-start}})
 print('SUMMARY',len(holdings),len(retirement_ids),area(left),flush=True)

if __name__=='__main__':main()
