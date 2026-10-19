"""Immutable producer handoff. Refuses to overwrite a frozen revision."""
import shutil,math
from .author import *
from .select_sites import at_arc

def runtime_routes():
 selected=load(H/'selected_sites.json');routes=load(H/'routes.json');mapping={r['id']:r for r in load(N/'observed_route_observation_mapping.json')};out=[]
 for row,rr in zip(selected['sites'],routes['routes']):
  sid='R10_PUBLIC_DRAW:'+str(row['site']);path=mapping[row['road']]['observed_graph_points_xyz_m'];center=row['station_xyz_m'];arc=0;near=(float('inf'),0)
  for aa,bb in zip(path,path[1:]):
   v=[bb[i]-aa[i]for i in range(3)];L=math.sqrt(sum(t*t for t in v));f=max(0,min(1,sum((center[i]-aa[i])*v[i]for i in range(3))/(L*L)));p=[aa[i]+f*v[i]for i in range(3)];dist=math.dist(p,center)
   if dist<near[0]:near=dist,arc+f*L
   arc+=L
  def point(offset):return at_arc(path,max(0,min(arc,near[1]+offset)))[0]
  def add(kind,points,width):out.append(dict(id=sid+':'+kind,group='public_water_'+str(row['site']),points=points,points_xyz_m=points,source_road_ids=[row['road']],clear_width_m=width,source_width_m=width,public_target_id=row['road']+':OBSERVED_ARC_STATION',supported_terminal_id=sid+':USE_STANDING_POINT'if kind!='OLD_ROAD_THROUGH'else row['road'],placement_ids=[sid],native_collider_ids=[sid],minimum_allowed_feet_y_m=row['position_m'][1]-.05,bidirectional=True,test_scope='Pedestrian capsule support/clearance only, unchanged0.3m radius1.8m height. No cart, fluid or interaction system.'))
  add('PUBLIC_APPROACH',rr['points_xyz_m'],2)
  c,s=math.cos(row['yaw_rad']),math.sin(row['yaw_rad'])
  for side in [-1,1]:add('BOUNDED_LATERAL_'+str(side),[[p[0]+side*.65*c,p[1],p[2]-side*.65*s]for p in rr['points_xyz_m']],.6)
  # Include original observed vertices in the +/-6m interval, not a shortcut chord.
  through=[point(-6)];distance=0
  for aa,bb in zip(path,path[1:]):
   distance+=math.dist(aa,bb)
   if near[1]-6<distance<near[1]+6:through.append(bb)
  through.append(point(6));add('OLD_ROAD_THROUGH',through,row['design_road_width_m'])
  for side in [-1,1]:add('ROAD_TURN_'+str(side),[point(side*4)]+rr['points_xyz_m'],2)
 write('runtime_routes.json',dict(schema='riverstone.r10.public_water_runtime_candidates.v1',status='NOT_REPLAYED',base_scene=ref(S),base_scene_sha256=SHA,source_observed_routes=ref(N/'observed_route_observation_mapping.json'),routes=out,unique_routes=len(out),directional_cases=2*len(out),required_integration='Gate final pack + this native pack + finite surface patch + institution entry patch, after duplicate original-source face rejection.',native_policy='Retain all relevant original/common colliders and new exact RenderData. No omitted walls, infinite ground, snapping or substitute height plane.'))

def main():
 validation=load(H/'validation.json');assert validation['status']=='PASS_STATIC_SOURCE_NATIVE_AND_FINITE_SURFACE';assert validation['pack']['sha256']==sha(H/'pack.json');assert validation['surface_patch']['sha256']==sha(H/'surface_patch.json')
 runtime_routes();dst=H/'frozen_r01';assert not dst.exists(),'Never overwrite a frozen handoff';dst.mkdir()
 files=['pack.json','surface_patch.json','water_extension.json','parcel_ownership_overlay.json','routes.json','runtime_routes.json','selected_sites.json','validation.json','compile_report.json','storage_geometry.json','service_head_ledger.json','masters/aboveground_drawhouse.json','cache/aboveground_drawhouse.render.json','README.md']
 for name in files:
  target=dst/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(H/name,target)
 for name in ['author.py','select_sites.py','test_pack.py','freeze.py']:
  target=dst/'generator_snapshot'/name;target.parent.mkdir(exist_ok=True);shutil.copy2(H/name,target)
 p=load(dst/'pack.json')
 for asset in p['common_assets'].values():
  asset['master_path']=str((dst/'masters/aboveground_drawhouse.json').relative_to(R));asset['render_path']=str((dst/'cache/aboveground_drawhouse.render.json').relative_to(R))
 for key,name in [('local_surface_patch','surface_patch.json'),('water_extension','water_extension.json'),('parcel_ownership_overlay','parcel_ownership_overlay.json')]:p[key]=ref(dst/name)
 (dst/'pack.json').write_text(json.dumps(p,indent=2)+'\n')
 v=load(dst/'validation.json');v['pack']=ref(dst/'pack.json');v['surface_patch']=ref(dst/'surface_patch.json');v['frozen_ref_rebase']='Only pack reference paths changed from validated source. Native master/render payload, placements, terrain patch, ownership and routes are identical.';(dst/'validation.json').write_text(json.dumps(v,indent=2)+'\n')
 manifest=dict(schema='riverstone.r10.public_water_frozen_handoff.v1',status='FROZEN_STATIC_PASS_RUNTIME_AND_ACTUAL_VISUAL_PENDING',base_scene=ref(S),source_plan=ref(B/'registered_source/plan.json'),selected_r9_index=ref(B/'registered_integration/r9/integration_r02/index.json'),files=[ref(p)for p in sorted(dst.rglob('*'))if p.is_file()],native_instance_ids=[p['id']for p in load(dst/'pack.json')['add_instances']],edited_source_faces=[dict(material=r['material'],triangle_index=r['triangle_index'])for r in load(dst/'surface_patch.json')['surface_edits']],integration=['Compose visual pack with final gate and abbey candidate packs.','Apply surface_patch.json (includes local stored/bowl water); water_extension.json is ledger-only, never append it twice.','Carry parcel_ownership_overlay.json as the explicit P_REG_0668 boundary change.','Reject repeated original source triangle IDs with other finite patches.','Replay runtime_routes.json and then inspect both r10_public_draw_* cameras.'],replay='12 unique source-authored probes,24 directions; not yet run.',expansion='Live select_sites.py accepts a comma-separated subset1..6. Other four sites remain unplaced and must pass the same finite ground/native/road/property gates. Freeze a new revision after any change.')
 (dst/'freeze_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(frozen=str(dst.relative_to(R)),manifest_sha256=sha(dst/'freeze_manifest.json'),pack_sha256=sha(dst/'pack.json'),surface_patch_sha256=sha(dst/'surface_patch.json'),routes_sha256=sha(dst/'routes.json')),indent=2))
if __name__=='__main__':main()
