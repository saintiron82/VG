"""Candidate-side geometry diagnostics only. No cistern is placed."""
import json,pathlib,math,hashlib
import numpy as np
O=pathlib.Path(__file__).resolve().parent;ROOT=O.parents[4];B=ROOT/'world_city/concept_city_v3';S=B/'registered_integration/r9/population_audit/selected_scene_metadata.json';A=B/'registered_integration/r9/landward_gates/asset_bounds.json';ins={i['id']:i for i in json.load(open(S))['common_instances']};bounds=json.load(open(A));index=json.load(open(B/'registered_integration/r9/integration_r02/index.json'))
for ref in index['packs']:
 p=json.load(open(ROOT/ref['path']))
 for k,v in p.get('common_assets',{}).items():bounds[k]=v['bounds']
 for x in p.get('remove_instance_ids',[]):ins.pop(x,None)
 for x in p.get('add_instances',[]):ins[x['id']]=x
 for x in p.get('replace_instances',[]):ins[x['id']]=dict(ins[x['id']],asset_key=x['asset_key'])
plan=json.load(open(B/'registered_source/plan.json'));roads={r['id']:r for r in plan['roads']};mapping={r['id']:r for r in json.load(open(O/'observed_route_observation_mapping.json'))};sites=json.load(open(O/'observed_facility_location_candidates.json'))['selected']
def poly(bb,pos,yaw):
 xz=np.array([[bb[sx][0],bb[sz][2]] for sx,sz in [('min','min'),('max','min'),('max','max'),('min','max')]]);c,s=math.cos(yaw),math.sin(yaw);return xz@np.array([[c,-s],[s,c]])+np.array(pos)[[0,2]]
def overlap(a,b):
 for q in (a,b):
  for u,v in zip(q,np.roll(q,-1,axis=0)):
   edge=v-u;normal=np.array([-edge[1],edge[0]]);aa=a@normal;bb=b@normal
   if max(aa)<=min(bb)+1e-8 or max(bb)<=min(aa)+1e-8:return False
 return True
obstacles=[]
for i in ins.values():
 bb=bounds[i['asset_key']];p=np.array(i['position_m']);q=poly(bb,p,i.get('yaw_rad',0));obstacles.append((i['id'],q,p[1]+bb['min'][1],p[1]+bb['max'][1]))
rows=[]
for s in sites:
 q=np.array(mapping[s['road']]['observed_graph_points_xyz_m']);p=np.array(s['point_m']);j=int(np.linalg.norm(q[:,[0,2]]-p[[0,2]],axis=1).argmin());a=q[max(0,j-1)];b=q[min(len(q)-1,j+1)];t=(b-a)[[0,2]];t=t/np.linalg.norm(t);normal=np.array([-t[1],t[0]]);width=roads[s['road'][5:]]['width_m'];candidates=[]
 for side in [-1,1]:
  for setback in [.5,1.5,3.5]:
   for shift in [0,-5,5,-10,10,-20,20,-30,30]:
    xz=p[[0,2]]+t*shift+normal*side*(width/2+2+setback);point=[float(xz[0]),float(p[1]),float(xz[1])];bb={'min':[-2,-2.6,-2],'max':[2,4.2,2]};yaw=math.atan2(t[0],t[1]);rect=poly(bb,point,yaw);hits=[oid for oid,poly2,lo,hi in obstacles if hi>point[1]+.25 and lo<point[1]+4.2 and overlap(rect,poly2)]
    candidates.append({'provisional_platform_xyz_m':point,'yaw_rad':yaw,'along_route_shift_m':shift,'side':side,'side_setback_from_design_road_edge_m':setback,'branch_geometric_length_m':float(width/2+2+setback),'native_above_ground_obb_collision_ids':hits,'above_ground_bound_screen_clear':not hits,'clearance_scope':'Conservative retained native oriented bounds above platform+0.25m only. Not mesh/shaft/terrain/road-ownership/water certification.'})
 clear=[x for x in candidates if not x['native_above_ground_obb_collision_ids']];clear.sort(key=lambda x:(abs(x['along_route_shift_m']),x['side_setback_from_design_road_edge_m']))
 rows.append({'site':s['addition_count'],'road':s['road'],'station_xyz_m':s['point_m'],'design_road_width_m':width,'road_tangent_xz':t.tolist(),'side_normal_xz':normal.tolist(),'public_side_pocket_area_m2':16,'native_master':'world_city/concept_city_v3/assemblies/waterworks/registered_services_r01/masters/closed_cistern.json','candidate_count':len(candidates),'clear_native_above_ground_bound_candidates':len(clear),'preferred_bound_only_candidates':clear[:4],'all_candidates':candidates,'status':'NOT_PLACED: platform Y remains station Y; actual terrain and excavation must be resolved','required_checks':['Actual support/side geometry and2.6m shaft excavation','Protected road width and2m public branch ownership','Water/bank/channel separation and dry drainage route','Current full-native triangle collision, visual integrity, capsule approach/turn','Hydraulic source branch and quality remain unverified']})
(O/'facility_site_handoff.json').write_text(json.dumps({'schema':'riverstone.public_cistern_side_pocket_screen.v1','sites':rows,'limits':['Side-pocket alternatives do not alter the optimal-station graph or count as actual access.','Native OBB clear is conservative above-ground geometry only; source ground/foundation/water/excavation checks remain required.','All provisional Y values equal the selected road station elevation, not sampled pocket terrain.','No side pocket is assumed public merely because it borders a public road.']},indent=2)+'\n')
print([(r['site'],r['clear_native_above_ground_bound_candidates'],r['preferred_bound_only_candidates'][:1]) for r in rows])
