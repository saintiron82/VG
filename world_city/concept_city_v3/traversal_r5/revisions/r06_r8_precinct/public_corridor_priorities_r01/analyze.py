"""Read-only failed-road priority and full-width shared-junction inventory."""
import collections,hashlib,json,math,pathlib,sys
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT));B=H.parent;CITY=ROOT/'world_city/concept_city_v3'
from world_city.concept_city_v3.registered_topography.revisions.r01_ownership import author as ownership
from world_city.runtime_city.checks import placement as geo

def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def write(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def diff(a,b):return [a[i]-b[i]for i in range(2)]
def bbox(p):return [min(v[0]for v in p),min(v[1]for v in p),max(v[0]for v in p),max(v[1]for v in p)]
def overlap(a,b):return a[0]<=b[2]and b[0]<=a[2]and a[1]<=b[3]and b[1]<=a[3]
def intersection(a,b,c,d):
 u=diff(b,a);v=diff(d,c);det=cross(u,v)
 if abs(det)<1e-10:return None
 w=diff(c,a);t=cross(w,v)/det;s=cross(w,u)/det
 if min(t,s)>=-1e-9 and max(t,s)<=1+1e-9:return [a[i]+t*u[i]for i in range(2)],t,s
 return None

def main():
 inv=read(B/'primary_inventory/inventory.json');summary=read(B/'network_batch_r01/evidence/summary.json');stations=read(B/'network_contact_stations_r01/failure_stations_faces.json');owners=read(B/'network_failure_owners_r01/failure_owner_ledger.json');plan=read(CITY/'registered_source/plan.json')
 roads={r['id']:r for r in inv['roads']};results={r['road_id']:r for r in summary['road_corridor_results']};failed={rid for rid,r in results.items()if not r['both_directions_pass']};dedicated={'MAIN_BRIDGE','PORT_BRIDGE_TIE'};ground=failed-dedicated
 landmark=set().union(*(set(g['required_road_ids'])for g in inv['primary_network_goals']))&ground
 tier1=['SOUTH_MARKET_AXIS','MARKET_NORTH','MARKET_CONTOUR','UPPER_CONTOUR','WEST_MONASTERY_EDGE','NOBLE_RISE','NORTH_BACK_LANE','CATHEDRAL_APPROACH','CLERGY_EAST_GATE'];assert set(tier1)==landmark
 tier2=[rid for rid in roads if rid in ground and rid not in landmark]
 rows=[]
 for rid in roads:
  if rid not in ground:continue
  cases=[c for c in stations['cases']if c['canonical_test_chain']=='ROAD:'+rid]
  rows.append({'road_id':rid,'width_m':roads[rid]['width_m'],'stage':1 if rid in landmark else 2,'canonical_points_xz_m':roads[rid]['polyline_xz_m'],'failed_cases':[{'id':c['case_id'],'status':c['status'],'source_station_records':[{k:v for k,v in q.items()if k not in ['source_polyline_xz_m','stations']}for q in c['source_road_station_records']],'actual_scene_face_keys':c['all_localized_actual_scene_face_keys'],'native_collider_ids':c['native_collider_ids'],'unlocalized_strict_support_failure':c['unlocalized_strict_support_failure']}for c in cases]})
 # All exact source traffic strips and finite circumscribed round joins. No 2m shoulders.
 pieces=[];index=geo._SpatialIndex(16)
 for rid,r in roads.items():
  n=len(r['polyline_xz_m'])-1
  for i,p in enumerate(ownership.corridor(r['polyline_xz_m'],r['width_m'])):
   rec={'road_id':rid,'kind':'segment'if i<n else 'round_join','source_index':i if i<n else i-n,'polygon_xz_m':p,'bounds':bbox(p)}
   index.add(len(pieces),p);pieces.append(rec)
 endpoint_pairs={tuple(sorted([j['from_road_id'],j['to_road_id']]))for j in inv['endpoint_junction_candidates']}
 pairs={}
 for i,p in enumerate(pieces):
  for j in index.candidates(p['polygon_xz_m']):
   if j<=i:continue
   q=pieces[j]
   if p['road_id']==q['road_id']or not({p['road_id'],q['road_id']}&ground)or not overlap(p['bounds'],q['bounds']):continue
   hit=geo.convex_intersection(p['polygon_xz_m'],q['polygon_xz_m'])
   if len(hit)<3 or geo.polygon_area(hit)<1e-8:continue
   key=tuple(sorted([p['road_id'],q['road_id']]))
   row=pairs.setdefault(key,{'roads':list(key),'a_is_regeneration_candidate':key[0]in ground,'b_is_regeneration_candidate':key[1]in ground,'both_current_corridors_pass':all(results[k]['both_directions_pass']for k in key),'endpoint_inventory_already_mentions_pair':key in endpoint_pairs,'raw_overlap_parts':[]})
   row['raw_overlap_parts'].append({'a':{k:p[k]for k in ['road_id','kind','source_index']},'b':{k:q[k]for k in ['road_id','kind','source_index']},'polygon_xz_m':hit})
 crossings=[];segments=[];si=geo._SpatialIndex(16)
 for rid,r in roads.items():
  for k,(a,b)in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
   si.add(len(segments),[a,b]);segments.append((rid,k,a,b))
 seen=set()
 for i,(rid,k,a,b)in enumerate(segments):
  for j in si.candidates([a,b]):
   if j<=i:continue
   qid,m,c,d=segments[j]
   if rid==qid or not({rid,qid}&ground):continue
   hit=intersection(a,b,c,d)
   if hit is None:continue
   xz,t,u=hit;key=(tuple(sorted([rid,qid])),round(xz[0],7),round(xz[1],7))
   if key in seen:continue
   seen.add(key);dy=None;ys=[]
   for rr,seg,f in [(roads[rid],k,t),(roads[qid],m,u)]:
    hints=rr['source_xyz_hint'];ys.append(None if not hints else hints[seg][1]+f*(hints[seg+1][1]-hints[seg][1]))
   if all(y is not None for y in ys):dy=abs(ys[0]-ys[1])
   crossings.append({'roads':[rid,qid],'source_segments':[k,m],'segment_fractions':[t,u],'xz_m':xz,'linear_source_hint_y_m':ys,'linear_source_hint_difference_m':dy,'endpoint_of_both':min(t,1-t)<1e-7 and min(u,1-u)<1e-7,'status':'SHARED_JUNCTION_NEEDS_ONE_EXACT_FULL_WIDTH_PROFILE; source-hint difference is diagnostic only, not actual-scene seam proof'})
 bnd=[p for p in pairs.values()if p['a_is_regeneration_candidate']!=p['b_is_regeneration_candidate']]
 original={r['id']:r for r in plan['roads']};changed=[rid for rid,r in roads.items()if rid in original and r['polyline_xz_m']!=original[rid]['polyline_xz_m']]
 out={'schema':'riverstone.public_corridor_regeneration_priorities.v1','status':'READ_ONLY_MINIMAL_REPAIR_INVENTORY_NOT_NEW_PROFILE_OR_TRAVERSAL_PASS','sources':{'inventory':ref(B/'primary_inventory/inventory.json'),'batch_summary':ref(B/'network_batch_r01/evidence/summary.json'),'all_failure_stations':ref(B/'network_contact_stations_r01/failure_stations_faces.json'),'failure_owners':ref(B/'network_failure_owners_r01/failure_owner_ledger.json'),'registered_plan':ref(CITY/'registered_source/plan.json'),'corridor_implementation':ref(pathlib.Path(ownership.__file__)),'accepted_actual_north_replay':ref(B/'north_connector_r02/freeze_manifest.json')},'ground_corridors':rows,'minimum_failed_canonical_roads':sorted(failed),'minimum_public_ground_corridors':sorted(ground),'stage1_primary_landmark_spine':tier1,'stage2_district_perimeter_access':tier2,'dedicated_interfaces':[{'road_id':'MAIN_BRIDGE','policy':'Do not rebuild old source alignment. Preserve accepted actual north74 triangles, south8+apron19, native closed leaves and hinges, barrier states; continue actual north crosssection into SOUTH_MARKET_AXIS.'},{'road_id':'PORT_BRIDGE_TIE','policy':'Retain main bridge and quay datums. Current native fixed-deck obstruction and strict support loss need dedicated finite interface; its15% local service criterion is separately declared.'}],'retained_passing_road_count':sum(r['both_directions_pass']for r in results.values()),'raw_pairwise_overlap_count':len(pairs),'repair_to_retained_road_pair_count':len(bnd),'full_width_shared_domains':list(pairs.values()),'pairs_missing_from_endpoint_only_inventory':[p['roads']for p in pairs.values()if not p['endpoint_inventory_already_mentions_pair']],'centreline_crossings':crossings,'canonical_r14_alignments_differing_from_raw_plan':changed,'cross_road_constraints':['One finite road-union owner and shared triangulation per overlap, including round joins and all branches; centreline heights alone do not fix full-width junctions.','Preserve actual native body holes, building/compound floors and gate lips; original private walls and gate solids cannot be deleted to fit a road.','Bind E1/E2 public fill to the exact missing2.241436832m2 plus old private remainder3.4506525543m2; inherited12.552% E1 triangle remains a separately reported old defect.','All existing public-facing ramp/landing seams are fixed actual XYZ constraints: seven merchant approaches,15 working-range branches, noble ramps, recovered institutional ramps/landings, training, reservoir, port and park.','Water domains and vertical banks remain finite barriers. NORTH_BACK_LANE_REVERSE already went below water; fix the crossing/grade relationship explicitly, never fill the channel under a road label.','Do not extend frozen broad native-hole masks over roads without proving native top coverage; preserve exact actual top triangles and collision contracts.','Shared road-to-retained-ground edges require both height continuity and finite retaining ownership. No tiny sliver, backface, duplicate coplanar patch, unsupported edge or abrupt graded fan is accepted.','Use emitted triangle planes and full-width gradients, not dry-field analytic derivative alone; original actual failures include.2683m and.1511m jumps plus150.655% local fan.','The75 original endpoint junction candidates and all newly listed interior full-width intersections require turn/reverse replay after composition. No road-centerline pass certifies a junction.'],'scope':'Minimal set means the16 currently failed public-ground road IDs, not proof that untested public turns or later native additions are correct. The first9 are the failed shared spine needed by the seven named primary goals. Seven additional failed district/perimeter routes remain required for whole-network completion.'}
 write(H/'priorities.json',out)
 print(json.dumps({'report':ref(H/'priorities.json'),'failed_ground':len(ground),'first_spine':tier1,'remaining':tier2,'full_width_pairs':len(pairs),'repair_to_retained_pairs':len(bnd),'pairs_missing_from_endpoint_inventory':out['pairs_missing_from_endpoint_only_inventory'],'centerline_crossings':len(crossings),'max_source_hint_difference_m':max((q['linear_source_hint_difference_m']or 0)for q in crossings),'changed_canonical_alignment':changed}))
if __name__=='__main__':main()
