"""Correct the one north-contract waypoint hint; preserve all geometry/controllers."""
import json,pathlib,hashlib,numpy as np,copy
O=pathlib.Path(__file__).resolve().parent;ROOT=O.parents[5];P=O/'replay_r01'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
BASE=P/'prepared_bound_r02.json';CAP=P/'evidence/runtime_r02/capsule.json';CONTRACT=ROOT/'world_city/concept_city_v3/traversal_r5/revisions/r06_r8_precinct/primary_goals_authored_r01/geometry/contract_NORTH_APPROACH_R04_CONTINUOUS_ROAD_GOAL:PORT_TO_MARKET.json'
before=read(BASE);d=copy.deepcopy(before);tri=np.array(read(CONTRACT)['triangles']);cap={r['id']:r for r in read(CAP)['routes']}
def at(x,z):
 hits=[]
 for i,t in enumerate(tri):
  a,b,c=t;M=np.array([[b[0]-a[0],c[0]-a[0]],[b[2]-a[2],c[2]-a[2]]])
  if abs(np.linalg.det(M))<1e-12:continue
  u,v=np.linalg.solve(M,[x-a[0],z-a[2]])
  if min(u,v,1-u-v)>=-1e-7:hits.append({'triangle_index':i,'y_m':float(a[1]+u*(b[1]-a[1])+v*(c[1]-a[1]))})
 return max(hits,key=lambda h:h['y_m']) if hits else None
ledger=[]
for r in d['routes']:
 if r['id'].startswith('NEGATIVE_'):continue
 changes=[]
 for i,p in enumerate(r['points']):
  # Exact existing authored north-transition waypoint only. No new points or XZ shift.
  if abs(p[0]-119.59834894318314)>1e-10 or abs(p[2]-419.36416610734005)>1e-10:continue
  h=at(p[0],p[2]);assert h and abs(p[1]-1)<1e-10 and abs(h['y_m']-1.75)<1e-10
  evidence=[]
  for s in cap[r['id']]['position_samples']:
   pos=s['capsule_center'];dist=float(np.linalg.norm(np.array(pos)[[0,2]]-np.array(p)[[0,2]]))
   if dist>3:continue
   exact=at(pos[0],pos[2]);assert exact
   evidence.append({'frame':s['frame'],'actual_xz_m':[pos[0],pos[2]],'distance_from_waypoint_m':dist,'observed_ground_y_m':s['ground_y_m'],'support_id':s['support_id'],'exact_contract_height_at_sample_m':exact['y_m'],'observed_minus_contract_m':s['ground_y_m']-exact['y_m']})
  assert evidence and max(abs(s['observed_minus_contract_m'])for s in evidence)<.0001
  old=p.copy();p[1]=h['y_m'];changes.append({'index':i,'original_xyz_hint_m':old,'corrected_xyz_hint_m':p.copy(),'delta_y_m':p[1]-old[1],'method':'Exact already-bound contract height at unchanged XZ, independently corroborated by adjacent original capsule ground observations.','contract_face':h,'runtime_observations':evidence})
 assert len(changes)==1
 r['length_m']=float(np.linalg.norm(np.diff(np.array(r['points']),axis=0),axis=1).sum());ledger.append({'id':r['id'],'changed_waypoints':changes,'unchanged_xz':True,'unchanged_waypoint_count':True})
assert d['assets']==before['assets'] and d['placements']==before['placements'] and d['buildings']==before['buildings'] and d['cart_fixture']==before['cart_fixture'] and d['implementation_hashes']==before['implementation_hashes']
for name,p in [('height_hint_correction_script',pathlib.Path(__file__)),('original_prepared_input',BASE),('original_capsule_ground_report',CAP),('existing_north_contract',CONTRACT)]:d['sources'][name]={'path':str(p),'sha256':sha(p)}
d['height_hint_correction']={'ledger_path':str(O/'height_correction_ledger.json'),'original_input_sha256':sha(BASE),'scope':'One waypoint Y 1.0 -> 1.75 in each of four directional vectors. Exact XZ, count, geometry, contracts, controller, ray range, cart dimensions and thresholds unchanged.'}
d['assumptions']=[x for x in d['assumptions'] if not x.startswith('Full chains have not')];d['assumptions'].append('Original four long capsule directions passed. Original four cart failures retained separately; this is a source-bound one-waypoint height-hint correction replay.')
out={'schema':'riverstone.r10.port_height_hint_correction.v1','sources':{k:v for k,v in d['sources'].items()if k in ['original_prepared_input','original_capsule_ground_report','existing_north_contract']},'changes':ledger,'geometry_and_controller_unchanged':True,'ray_start_offset_m':.75,'ray_end_offset_m':-1.5,'cart_underbody_clearance_m':.15}
(O/'height_correction_ledger.json').write_text(json.dumps(out,indent=2)+'\n');d['sources']['height_correction_ledger']={'path':str(O/'height_correction_ledger.json'),'sha256':sha(O/'height_correction_ledger.json')}
(P/'prepared_height_corrected_r03.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'cases':len(ledger),'changes_per_case':[len(x['changed_waypoints'])for x in ledger],'output':str(P/'prepared_height_corrected_r03.json')},indent=2))
