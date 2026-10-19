"""Bind released source routes, while retaining unsupported ownership as held."""
import collections,copy,hashlib,json,math,pathlib,sys
H=pathlib.Path(__file__).resolve().parent
ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
sys.path[:0]=[str(H),str(ROOT)]
import catalog
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.concept_city_v3.assemblies.waterworks.registered_water_completion_r01.approaches_r02 import finite
from world_city.runtime_city.checks import placement as geo
R18=ROOT/'world_city/concept_city_v3/registered_topography/revisions/public_corridors_r18'
def read(p):return json.loads(p.read_bytes())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def write(p,data):p.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def tube(p,q,r=.35):
 L=math.dist(p,q);n=[-(q[1]-p[1])/L,(q[0]-p[0])/L]
 out=[[[v[k]+s*r*n[k]for k in(0,1)]for v,s in[(p,1),(q,1),(q,-1),(p,-1)]]]
 for c in[p,q]:out.append([[c[0]+r/math.cos(math.pi/16)*math.cos(i*math.pi/8),c[1]+r/math.cos(math.pi/16)*math.sin(i*math.pi/8)]for i in range(16)])
 return out
def nearest_hint(pt,chains):
 hits=[]
 for chain in chains:
  for p,q in zip(chain,chain[1:]):
   dx,dz=q[0]-p[0],q[2]-p[2];den=dx*dx+dz*dz
   t=max(0,min(1,((pt[0]-p[0])*dx+(pt[1]-p[2])*dz)/den))if den else 0
   hits.append((math.hypot(pt[0]-p[0]-t*dx,pt[1]-p[2]-t*dz),p[1]+t*(q[1]-p[1])))
 if not hits:raise ValueError('No source floor hint for '+str(pt))
 return min(hits)[1]
def main():
 source_path=R18/'resolved_route_catalog_r01.json';src=read(source_path);source_ref=ref(source_path)
 inv_path=H.parent/'primary_inventory/inventory.json';inv=read(inv_path);roads={r['id']:r for r in inv['roads']}
 field_path=R18/'finite_field_candidate_r04_common.json';field=read(field_path);records=field['records'];ix=a.geo._SpatialIndex(4)
 for k,row in enumerate(records):ix.add(k,row['polygon_xz_m'])
 local=read(H/'bound_local_controls.json');entries=read(H/'bound_entry_controls.json');old_path=H.parent/'network_batch_r01/prepared_runtime.json';old={r['id']:r for r in read(old_path)['routes']};localmap={r['id']:r for r in local['routes']}
 def owners(pt):
  hits=[]
  for k in ix.candidates([pt]):
   r=records[k];p=r['polygon_xz_m'];sign=1 if geo.signed_polygon_area(p)>0 else-1
   if all(sign*geo._cross(u,v,pt)>=-1e-9*max(math.dist(u,v),1e-12)for u,v in zip(p,p[1:]+p[:1])):hits.append(r)
  return hits
 def points(row):
  chains=[]
  if row['id']in old:chains.append(old[row['id']]['points'])
  chains.extend(roads[r]['source_xyz_hint']for r in row['source_road_ids']if r in roads and roads[r].get('source_xyz_hint'))
  if any(x in row['source_road_ids']for x in['MAIN_BRIDGE','SOUTH_COUNTRY_ROAD']):chains.extend(r['points_xyz_m']for r in local['routes']if r['case_class']in['native_bridge','bridge_approach'])
  out=[]
  for pt in row['polyline_xz_m']:
   hits=owners(pt);y=math.fsum(a.common.height(r['plane_y_xz_m'],pt)for r in hits)/len(hits)if hits else nearest_hint(pt,chains)
   value=[pt[0],y,pt[1]]
   if not out or math.dist(value,out[-1])>=1e-8:out.append(value)
  return out
 private={r['id']for r in inv['roads']if r['kind']=='inferred_connected_block_alley'}
 old_result_path=H.parent/'network_batch_r01/evidence/network_initial.json';old_result=read(old_result_path);resultmap={r['id']:r for r in old_result['routes']};srcmap={r['id']:r for r in src['routes']};reconciled=[]
 for roadid in sorted(private):
  rid='ROAD:'+roadid;forward=old[rid];reverse=old[rid+'_REVERSE'];candidate=srcmap[rid]
  same=[[p[0],p[2]]for p in forward['points']]==candidate['polyline_xz_m']and reverse['points']==list(reversed(forward['points']))
  passed=all(resultmap[k]['pass']for k in[rid,rid+'_REVERSE'])
  reconciled.append(dict(road_id=roadid,case_ids=[rid,rid+'_REVERSE'],exact_old_forward_and_reverse_xz_match=same,prior_both_directions_passed=passed,prior_statuses=[resultmap[k]['status']for k in[rid,rid+'_REVERSE']],prior_scene=read(old_path)['sources']['scene'],current_status='accepted_for_unchanged_chain_regression'if same and passed else'held_unmatched_or_unverified',current_geometry_limit='Prior traversal proves this exact chain on the bound old scene. Current district replacement may alter support or obstacles, so final-scene replay is still required.'))
 verified_private={r['road_id']for r in reconciled if r['exact_old_forward_and_reverse_xz_match']and r['prior_both_directions_passed']}
 write(H/'prior_alley_reconciliation.json',dict(schema='riverstone.prior_actual_alley_reconciliation.r18.v1',old_prepared=ref(old_path),old_actual_result=ref(old_result_path),current_source_catalog=source_ref,rows=reconciled,correction='The initial broad holds relied on inventory kind alone and overlooked all 26 exact prior actual passes. Matching chains are retained as regression controls. New junction candidates have no such prior pass and remain held.'))
 routes=copy.deepcopy(local['routes'])+copy.deepcopy(entries['routes']);ids={r['id']for r in routes};held_chains=[];held_turns=[]
 for row in src['routes']+src['junction_routes']:
  isturn='source_candidate_id'in row
  if any(r in private and(isturn or r not in verified_private)for r in row['source_road_ids']):
   (held_turns if isturn else held_chains).append(dict(id=row['id'],status='held',reason='Inferred old private alley has no released current public owner proof. Released holding entries are bound separately; no retirement is inferred.',source=source_ref));continue
  if row['id']in ids:continue
  cls='junction_turn'if isturn else'precinct_entry'if row['id'].startswith(('NOBLE:','GATE:'))else'native_bridge'if row['id']=='ROAD:MAIN_BRIDGE'else'public_corridor'
  prior=any(r in verified_private for r in row['source_road_ids']);provenance=[source_ref,ref(inv_path),ref(field_path)]+([ref(old_result_path),ref(H/'prior_alley_reconciliation.json')]if prior else[])
  routes.append(dict(id=row['id'],case_class=cls,points_xyz_m=points(row),source_road_ids=row['source_road_ids'],source_width_m=row.get('source_width_m'),test_scope='Exact source-bound XZ chain, actual composed-scene standing height and collision required; both directions. '+('Exact prior actual passed chain retained for current-scene regression. 'if prior else'')+row.get('geometry_basis','Finite named public junction turn.'),provenance=provenance,resolved_geometry_proof=ref(H/'prior_alley_reconciliation.json')if prior else source_ref,bidirectional=True,bridge_state='ROAD_OPEN',source_geometry_basis='PRIOR_ACTUAL_PASSED_EXACT_XZ_CHAIN'if prior else row.get('geometry_basis','SOURCE_INTERIOR_JUNCTION'),hint_height_policy='R18 finite plane where covered; otherwise nearest bound source road/native vector. Actual standing Y is resolved anew from the integrated collision mesh.'));ids.add(row['id'])
 lookup={r['id']:r for r in routes}
 # The two joins below are exact shared native standing points. No invented
 # connector or nearest-network snap is permitted in the continuous goal.
 south=list(reversed(lookup['AUTHORITATIVE_SOUTH_TERMINAL_COUNTRY']['points_xyz_m']));bridge=list(reversed(lookup['ROAD:MAIN_BRIDGE']['points_xyz_m']));north=lookup['NATIVE_NORTH_TERMINAL_TO_MARKET']['points_xyz_m']
 assert math.dist([south[-1][0],south[-1][2]],[bridge[0][0],bridge[0][2]])<1e-8
 join=next(k for k,p in enumerate(north)if math.dist([bridge[-1][0],bridge[-1][2]],[p[0],p[2]])<1e-8)
 goalid='GOAL:SOUTH_COUNTRY_TO_MARKET'
 routes.append(dict(id=goalid,case_class='public_corridor',points_xyz_m=south+bridge[1:]+north[join+1:],source_road_ids=['SOUTH_COUNTRY_ROAD','MAIN_BRIDGE','SOUTH_MARKET_AXIS','MARKET_PROCESSION'],test_scope='Continuous exact country-to-market chain through the accepted south standing point, native bridge axis, north connector and fountain bypass, both directions.',provenance=[source_ref,ref(H/'bound_local_controls.json')],resolved_geometry_proof=source_ref,bidirectional=True,bridge_state='ROAD_OPEN',exact_shared_join_tolerance_m=1e-8))
 coverage=dict(ordinary_entries=copy.deepcopy(entries['coverage']),required_ordinary_entries_ids=[r['id']for r in entries['coverage']]);coverage['required_public_roads_ids']=sorted(roads);coverage['public_roads']=[]
 for rid in sorted(roads):
  row=dict(id=rid,status='held'if rid in private-verified_private else'accepted')
  if rid in private-verified_private:row.update(reason='Old inferred private alley is not an exact match to a prior actual passed chain; accepted ordinary entries are tested separately.',source=ref(H/'prior_alley_reconciliation.json'))
  else:row.update(route_ids=['ROAD:'+rid],acceptance_scope='Eligible source-bound motion control; physics acceptance remains pending.')
  coverage['public_roads'].append(row)
 coverage['required_primary_network_goals_ids']=[r['id']for r in inv['primary_network_goals']];coverage['primary_network_goals']=[]
 for row in inv['primary_network_goals']:
  if row['id']=='SOUTH_COUNTRY_TO_MARKET':item=dict(id=row['id'],status='accepted',route_ids=[goalid])
  else:item=dict(id=row['id'],status='held',reason='Road and junction component controls are included, but an exact continuous route to every required endpoint is not supplied. '+row.get('private_endpoint_status','Native gate/port continuation still needs an exact full-chain handoff.'),source=ref(inv_path),component_route_ids=['ROAD:'+r for r in row['required_road_ids']])
  coverage['primary_network_goals'].append(item)
 # Every exception piece remains visible. One representative full-capsule
 # probe per source triangle is admitted only when finite R18 owners cover it.
 bysource=collections.defaultdict(list)
 for row in src['grade_exception_controls']:bysource[row['source_triangle_index']].append(row)
 probes=[]
 for si,pieces in sorted(bysource.items()):
  trials=[];selected=None
  for piece in sorted(pieces,key=lambda p:p['area_m2'],reverse=True):
   caps=tube(*piece['crossing_candidate_xz_m']);ownerids=set();missing=0
   for cap in caps:
    nearby=[records[k]for k in ix.candidates(cap)];ownerids.update(r['id']for r in nearby);gaps=finite.subtract([cap],[r['polygon_xz_m']for r in nearby]);missing+=sum(geo.polygon_area(p)for p in gaps)
   trial=dict(piece_id=piece['id'],unsupported_tube_area_m2=missing,owner_ids=sorted(ownerids),tube_polygons_xz_m=caps);trials.append(trial)
   if missing<1e-7:selected=(piece,trial);break
  ledger=dict(source_triangle_index=si,piece_ids=[p['id']for p in pieces],piece_count=len(pieces),source_design_gradients=sorted({p['gradient']for p in pieces}),trials=trials,status='held',reason='No representative radius-0.35m tube is fully covered by the bound R18 public field; retained/native support has not been promoted by inference.')
  if selected:
   piece,trial=selected;rid='DESIGN_GRADE_SOURCE_'+str(si);p=piece['crossing_candidate_xz_m'];q=records[next(k for k,r in enumerate(records)if r['id']==piece['owner_id'])];xyz=[[v[0],a.common.height(q['plane_y_xz_m'],v),v[1]]for v in p]
   routes.append(dict(id=rid,case_class='design_grade_probe',points_xyz_m=xyz,source_road_ids=[],source_plane_owner_ids=trial['owner_ids'],design_exception_source_triangle_index=si,source_exception_piece_ids=ledger['piece_ids'],test_scope='One local full-capsule-supported control across an explicit design-grade exception source. Physics result does not erase the design-grade exception.',provenance=[source_ref,ref(field_path)],resolved_geometry_proof=ref(field_path),bidirectional=True,bridge_state='ROAD_OPEN'))
   ledger.update(status='accepted',route_ids=[rid],reason='Representative radius-0.35m tube is supported by exact finite R18 owners. Actual activation and physics are still required.')
  probes.append(ledger)
 sources=dict(primary_inventory=ref(inv_path),resolved_r18_routes=source_ref,r18_finite_owners=ref(field_path),r18_active23_seal=ref(R18/'finite_candidate_active23_seal_r01.json'),previous_complete_network=ref(old_path),previous_actual_network_result=ref(old_result_path),prior_alley_reconciliation=ref(H/'prior_alley_reconciliation.json'),bound_local_controls=ref(H/'bound_local_controls.json'),bound_entry_controls=ref(H/'bound_entry_controls.json'),**entries['sources'])
 b15pack=read(catalog.source(entries['sources']['b15_replay']))['sources']['native_pack'];sources['b15_native_pack']=ref(catalog.source(b15pack));required_packs=entries['required_native_packs']+[sources['b15_native_pack']]
 out=dict(schema='riverstone.resolved_public_replay_catalog.r18.v1',status='READY_FOR_ACTUAL_SCENE_REPLAY',sources=sources,routes=routes,activation_requirements=dict(native_packs=required_packs,finite_public_field=ref(field_path)),coverage=coverage,source_candidate_accounting=dict(prior_actual_alley_reconciliation=ref(H/'prior_alley_reconciliation.json'),held_old_private_chains=held_chains,held_private_junctions=held_turns,ordinary_block_inventory=src['blocks'],grade_exception_piece_count=len(src['grade_exception_controls']),grade_exception_source_triangle_count=len(bysource),grade_exception_probes=probes),limits=['Accepted means released for actual-scene measurement, never a static or physics pass.','All 13 exact prior actual passed alley chains are retained for current-scene regression; their 37 new junction candidates remain held without current ownership/continuation proof. No retirement is inferred.','Only the ready 23 holding entries plus the sealed 22 B15 entries are accepted; the other 55 candidates are held.','Six primary endpoint goals remain explicitly held even if their component roads pass.','Design-grade exception counts distinguish 102 finite pieces from 43 original source triangles; a passing local probe cannot erase the source design target exception.'])
 expanded=catalog.validate(out);write(H/'route_catalog.json',out);write(H/'catalog_binding_report.json',dict(catalog=ref(H/'route_catalog.json'),forward_records=len(routes),expanded_cases=len(expanded),case_classes=dict(collections.Counter(r['case_class']for r in expanded)),accepted_grade_source_probes=sum(p['status']=='accepted'for p in probes),held_grade_source_probes=sum(p['status']=='held'for p in probes),held_private_chains=len(held_chains),held_private_turns=len(held_turns),status='SOURCE_BOUND_AWAITING_EXACT_JOINT_SCENE'))
 print(json.dumps(read(H/'catalog_binding_report.json'),indent=2))
if __name__=='__main__':main()
