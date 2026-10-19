"""Source coverage inventory. Every new route remains pending actual-scene physics."""
import pathlib,json,hashlib,math,copy
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());C=ROOT/'world_city/concept_city_v3'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def write(p,d):
 with p.open('x')as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def projection(p,a,b):
 v=[b[i]-a[i]for i in range(2)];t=max(0,min(1,sum((p[i]-a[i])*v[i]for i in range(2))/sum(x*x for x in v)));q=[a[i]+t*v[i]for i in range(2)];return math.dist(p,q),q,t
def main():
 paths={'plan':C/'registered_source/plan.json','terrain':C/'registered_topography/revisions/r14_precinct_merchant/contract.json','country':C/'registered_topography/road_extensions/south_country_r1/contract.json','bulk':C/'registered_integration/r8/coverage_plan/fixed_family_bulk_contract.json','parcels':C/'registered_integration/r8/coverage_plan/parcel_candidates.json','noble':C/'assemblies/property/registered/r1/generated/access_overlay.json','landmark_profiles':C/'validation/landmark_recovery_r1/recovered_rendered_profiles_r2.json','training':C/'assemblies/landscape/registered/training/resolved_placements.json'}
 d={k:read(p)for k,p in paths.items()};sources={k:ref(p)for k,p in paths.items()};roads={r['id']:copy.deepcopy(r)for r in d['plan']['roads']}
 for rid,r in d['terrain']['road_profiles'].items():roads[rid]=copy.deepcopy(r)
 for r in d['terrain']['replaced_roads']:roads[r['id']]=copy.deepcopy(r)
 co=d['country'];roads[co['route_id']]={'id':co['route_id'],'polyline_xz_m':[[v[0],v[2]]for v in co['centerline_xyz_m']],'resolved_world_xyz_m':co['centerline_xyz_m'],'width_m':co['width_m'],'kind':'finite_country_extension'}
 records=[]
 for rid,r in roads.items():
  records.append({'id':rid,'width_m':r['width_m'],'polyline_xz_m':r['polyline_xz_m'],'source_xyz_hint':r.get('resolved_world_xyz_m'),'block_id':r.get('block_id'),'connects_road_ids':r.get('connects_road_ids',[]),'kind':r.get('kind'),'status':'PENDING_COMPLETE_ROAD_BOTH_DIRECTIONS','height_policy':'Hints only. Spawn is resolved against the actual current finite scene/native geometry; no path support is synthesized.'})
 blocks=[]
 for b in d['plan']['blocks']:
  rid=b['interior_path_ids'][0]if b['interior_path_ids']else None
  hs=[h for h in d['parcels']['holdings']if h['block_id']==b['id']]
  item={'block_id':b['id'],'status':'PENDING_ENTRANCE_AND_PUBLIC_NETWORK_PHYSICS','boundary_road_ids':b['boundary_road_ids'],'new_source_holding_ids':[h['id']for h in hs],'source_plot_count_is_not_acceptance_authority':True}
  if rid:item.update(entry_kind='existing_inferred_alley',road_id=rid,entry_endpoints_xz_m=[roads[rid]['polyline_xz_m'][0],roads[rid]['polyline_xz_m'][-1]],candidate_route_xz_m=roads[rid]['polyline_xz_m'])
  elif hs:
   h=hs[0];item.update(entry_kind='new_shared_frontage_candidate',holding_id=h['id'],road_id=h['street_road_id'],candidate_route_xz_m=list(reversed(h['street_connection_polyline_xz_m'])),width_m=h['gate_width_m'],runtime_scene_required=True)
  else:item.update(entry_kind='public_civic_market',road_id='MARKET_PROCESSION',candidate_route_xz_m=roads['MARKET_PROCESSION']['polyline_xz_m'],width_m=roads['MARKET_PROCESSION']['width_m'],intent='Traverse the exact current fountain bypass and market entry; no residential plot inferred.')
  if b['id']=='BLOCK_015':item['pending_replacement']='District fabric/R17 final accepted route handoff required; old alley remains a public-road regression only.'
  blocks.append(item)
 # Explicit endpoint-to-strip candidate joins; do not silently bridge a gap.
 junctions=[]
 for rid,r in roads.items():
  for end,point in [(0,r['polyline_xz_m'][0]),(-1,r['polyline_xz_m'][-1])]:
   best=[]
   for qid,q in roads.items():
    if qid==rid:continue
    for i,(a,b)in enumerate(zip(q['polyline_xz_m'],q['polyline_xz_m'][1:])):
     distance,qpoint,t=projection(point,a,b)
     if distance<=q['width_m']/2-.3 and (0<t<1 or distance<1e-6):best.append((distance,qid,i,qpoint,t))
   if best:
    distance,qid,i,qpoint,t=min(best)
    junctions.append({'id':f'JOIN:{rid}:{end}:{qid}:{i}','from_road_id':rid,'endpoint_index':end,'to_road_id':qid,'target_segment_index':i,'polyline_xz_m':[point,qpoint],'distance_m':distance,'radius_m':.3,'geometric_basis':'Endpoint lies within target finite segment strip eroded laterally by capsule radius; endpoint caps accepted only for coincident coordinates. This does not prove vertical support or native clearance.','status':'PENDING_ACTUAL_JUNCTION_REPLAY'})
 gates=[dict(g,status='PENDING_ACTUAL_NATIVE_THROAT_BOTH_DIRECTIONS',native_placement_id='FORT_GATE:'+g['id'])for g in d['plan']['gates']]
 nobles=[{'id':r['gate']['id'],'property_id':r['property_id'],'road_id':r['external_candidate']['road_id'],'polyline_xz_m':[r['external_candidate']['road_center_connection_xz_m']]+list(reversed(r['external_candidate']['external_centerline_xz_m']))+[r['gate']['inside_point_xz_m']],'width_m':r['external_candidate']['clear_width_m'],'status':'PENDING_ACTUAL_PUBLIC_TO_GATE_REPLAY'}for r in d['noble']['records']]
 goals=[{'id':'SOUTH_COUNTRY_TO_MARKET','required_road_ids':['SOUTH_COUNTRY_ROAD','MAIN_BRIDGE','SOUTH_MARKET_AXIS','MARKET_PROCESSION']},{'id':'PORT_TO_MARKET','required_road_ids':['PORT_QUAY','PORT_BRIDGE_TIE','MAIN_BRIDGE','SOUTH_MARKET_AXIS','MARKET_PROCESSION']},{'id':'MARKET_TO_CASTLE','required_road_ids':['MARKET_NORTH','UPPER_CONTOUR','CASTLE_APPROACH'],'private_endpoint_status':'Recovered finite profile exists; original route IDs unavailable, need finite route extraction to actual main opening.'},{'id':'MARKET_TO_CATHEDRAL','required_road_ids':['MARKET_NORTH','UPPER_CONTOUR','CATHEDRAL_APPROACH','CLERGY_EAST_GATE'],'private_endpoint_status':'Recovered finite profiles exist; exact exterior main-opening branch needs route extraction.'},{'id':'MARKET_TO_ABBEY','required_road_ids':['MARKET_CONTOUR','WEST_MONASTERY_EDGE'],'private_endpoint_status':'Recovered finite profiles exist; rear chapel route remains explicitly missing.'},{'id':'MARKET_TO_NOBLE','required_road_ids':['MARKET_NORTH','UPPER_CONTOUR','NOBLE_RISE','NORTH_BACK_LANE','NORTH_WATERKEEPER'],'native_gate_ids':[r['id']for r in nobles]},{'id':'MARKET_TO_TRAINING','required_road_ids':['MARKET_NORTH','UPPER_CONTOUR','CASTLE_APPROACH'],'native_gate_id':d['training']['gate_proposals'][0]['id'],'private_endpoint_status':'Actual 0.125 m native treads and gate must be tested; geometric fine-top proof is not a controller pass.'}]
 out={'schema':'riverstone.primary_exterior_coverage_inventory.v1','status':'SOURCE_INVENTORY_PENDING_ACTUAL_BATCH','sources':sources,'roads':records,'road_count':len(records),'blocks':blocks,'block_count':len(blocks),'public_gates':gates,'noble_gates':nobles,'endpoint_junction_candidates':junctions,'primary_network_goals':goals,'landmark_missing_route':'monastery_registered:rear_chapel_connection:main_entry','required_distinct_bridge_tests':['Closed native leaf and hinge deck passage both directions','Secured native barrier panels: 0.5 m gap must block radius0.3 m capsule','Neither static test establishes live actor occupancy/operations integration'],'prior_pass_scope':['R6 corrected18cases cover seven short merchant exterior chains plus southern bridge terminal/country route and controls.','R7 36cases cover15closed-door standing lips andtwo courts, both directions, pluscontrols.','R8 stair proxy18cases cover only declaredstair/productive routes with sixcontrols.'],'acceptance':['Original radius0.3m/height1.8m no-step controller,60Hz,45degreefloorangle','Zero positive floor-state and short support-ray misses','Actual current nearby native meshes and finite scene triangles; no support infill','Every result binds exactscene/contract/native hashes; finalscene replays required']}
 write(H/'inventory.json',out)
 print(json.dumps({'roads':len(records),'blocks':len(blocks),'junctions':len(junctions),'source_hashes':sources,'inventory':ref(H/'inventory.json')}))
if __name__=='__main__':main()
