"""Replay actual reservoir sources, test dry service and protected draw cavity."""
import collections
from .audit import *
from voxel_character.common import coordinate_planes,render_data
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import frozen_r6 as f
from world_city.concept_city_v3.registered_integration.r8.runtime_contracts import append_water_extensions

def run():
 s=a.load_scene();data={};records=[]
 for p in s['common_instances']:
  if p['source_pack']!='reservoir':continue
  asset=s['common_assets'][p['asset_key']];mp=ROOT/asset['master_path'];rp=ROOT/asset['render_path'];master=json.loads(mp.read_text());c=coordinate_planes.compile_master(master,{'pitch':.2},max_candidate_cells=600000,max_output_cells=200000);r=render_data.make_render_data(c);assert c['valid'];assert r==json.loads(rp.read_text());data[p['id']]=dict(p=p,c=c,r=r,cells={tuple(q[:3])for q in c['cells']},master=master);records.append(dict(id=p['id'],source=ref(mp),cache=ref(rp),cells=len(c['cells']),quads=r['quad_count'],source_replay_matches=True));print(p['id'],len(c['cells']),flush=True)
 def occupied(id,v):
  d=data[id];p=d['p'];x,y,z=p['position_m'];yaw=p['yaw_rad'];dx,dz=v[0]-x,v[2]-z;local=[math.cos(yaw)*dx-math.sin(yaw)*dz,v[1]-y,math.sin(yaw)*dx+math.cos(yaw)*dz];origin=d['c']['grid_origin'];idx=tuple(math.floor((v-origin[i])/.2+1e-7)for i,v in enumerate(local));return idx in d['cells']
 bed=data['RESERVOIR_BED'];bank=data['RESERVOIR_BANKS'];assert bed['p']['position_m']==bank['p']['position_m'];assert bed['c']['grid_origin']==bank['c']['grid_origin'];allcells=bed['cells']|bank['cells'];seen={next(iter(bed['cells']))};todo=collections.deque(seen)
 while todo:
  x,y,z=todo.popleft()
  for q in[(x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)]:
   if q in allcells and q not in seen:seen.add(q);todo.append(q)
 assert seen==allcells
 bore=[]
 for zi in range(61):
  for x in[-36.2,-36,-35.8]:
   for y in[15.2,15.6,16.0]:
    v=[x,y,-344+zi*.1]
    for id in['RESERVOIR_BANKS','RESERVOIR_PROTECTED_CONDUIT','RESERVOIR_DRAWPOINT']:assert not occupied(id,v),(id,v)
    bore.append(v)
 p=data['RESERVOIR_DRAWPOINT']['p'];x,ground,z=p['position_m'];head=15.5;radius=.55
 for xi in range(-11,12):
  for zi in range(-11,12):
   dx,dz=xi*.05,zi*.05
   if math.hypot(dx,dz)<=radius+1e-9:assert not occupied(p['id'],[x+dx,head,z+dz]);assert occupied(p['id'],[x+dx,13.5,z+dz])
 poly=[[x+radius*math.cos(2*math.pi*i/16),z+radius*math.sin(2*math.pi*i/16)]for i in range(16)];vertices=[v for t in f.fan_upward([[q[0],head,q[1]]for q in poly])for v in t];extension=dict(base_water_sha256=a.canonical_sha(s['surfaces']['water']),owner_ids=[p['id']],collision=False,append_vertices_xyz_m=vertices,policy='Finite stored-water surface inside existing protected draw shaft, at R14 COVERED_CISTERN head. Existing river, canals and reservoir surface values remain untouched; no flow simulation.')
 write('water_extension.json',extension);out=append_water_extensions(s,s,[extension]);assert out['surfaces']['water'][:len(s['surfaces']['water'])]==s['surfaces']['water']
 service=data['RESERVOIR_SERVICE_CIRCUIT_RECOVERY'];cistern=data['RESERVOIR_DRAWPOINT'];origin=[service['p']['position_m'][i]+service['c']['grid_origin'][i]for i in range(3)];floor=set();obstacles=set()
 for d in[service,cistern]:
  for cx,cy,cz in d['cells']:
   v=pose([d['c']['grid_origin'][0]+(cx+.5)*.2,d['c']['grid_origin'][1]+(cy+.5)*.2,d['c']['grid_origin'][2]+(cz+.5)*.2],d['p']);q=(round((v[0]-origin[0])/.2-.5),round((v[2]-origin[2])/.2-.5))
   if abs(v[1]-17.9)<1e-7 and(cx,cy+1,cz)not in d['cells']:floor.add(q)
   if 18.01<v[1]<19.8:obstacles.add(q)
 offsets=[(x,z)for x in range(-2,3)for z in range(-2,3)if x*x+z*z<=4];walk={q for q in floor if all((q[0]+dx,q[1]+dz)in floor and(q[0]+dx,q[1]+dz)not in obstacles for dx,dz in offsets)}
 def nearest(p):return min(walk,key=lambda q:math.hypot(origin[0]+(q[0]+.5)*.2-p[0],origin[2]+(q[1]+.5)*.2-p[1]))
 start=nearest([-33.4,-335.7167708839214]);seen={start};todo=collections.deque(seen)
 while todo:
  x,z=todo.popleft()
  for q in[(x-1,z),(x+1,z),(x,z-1),(x,z+1)]:
   if q in walk and q not in seen:seen.add(q);todo.append(q)
 targets=[]
 for b in service['master']['extensions']['bridges']:
  point=[b['center_xyz_m'][0],b['center_xyz_m'][2]];q=nearest(point);targets.append(dict(id=b['id'],native_floor_cell=list(q),reachable=q in seen));assert q in seen
 write('reservoir_native_audit.json',dict(base_scene=ref(a.SCENE_PATH),native_sources=records,bed_and_bank_connected_cells=len(allcells),closed_bottom_under_new_stored_water=True,protected_bore_sample_count=len(bore),protected_bore_samples_empty=True,stored_water=dict(head_y_m=head,radius_m=radius,owner_id=p['id'],actual_position_m=p['position_m'],extension=ref(HERE/'water_extension.json')),maintenance_service=dict(two_source_native_floor_graph=True,radius_m=.4,total_walk_cells=len(walk),reachable_walk_cells=len(seen),both_existing_crossings_reachable=targets),limits=['Native-source geometry replay only; isolated two-source floor graph does not prove collision clearance against all surrounding native/terrain solids.','Actual external city road approach and integrated capsule traversal are separate acceptance gates.','Reservoir storage, spring yield, head losses, treatment and flood capacity are not simulated.']))
 print('PASS reservoir native geometry and stored-water disk',flush=True)
if __name__=='__main__':run()
