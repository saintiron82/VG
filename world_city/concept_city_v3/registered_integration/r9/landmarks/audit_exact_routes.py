"""Read-only continuous XYZ route-envelope audit of the sealed landmark pack.

Uses actual cached render bounds. This audit does not replay physics or mutate
any collider, source, route, controller, master, cache, or pack.
"""
import importlib.util,json,math,re
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('author',HERE/'build_addendum.py');b=importlib.util.module_from_spec(sp);sp.loader.exec_module(b)
CERT=b.ROOT/'world_city/concept_city_v3/traversal_r5/revisions/r06_r8_precinct/case_input_certification_r04'
SELECTED=CERT/'selected_all493_bound_r02.json';RESULTS=CERT/'certified_results_493_bound_r02.json';CONTROLLER=CERT/'Traversal.gd'
PACK_SHA='605a09ef94105a24b16e5fcd8e90989334cac71ce4d6ed25da4226a3835a4d5d'

def slab_hits(a,z,lo,hi):
 """Exact segment-vs-expanded-box slabs, vectorized; endpoints included."""
 delta=z-a;t0=np.zeros(len(a));t1=np.ones(len(a));possible=np.ones(len(a),dtype=bool)
 for axis in range(3):
  flat=np.abs(delta[:,axis])<1e-12;possible &= ~flat | ((a[:,axis]>=lo[axis])&(a[:,axis]<=hi[axis]))
  denom=np.where(flat,1,delta[:,axis]);u=(lo[axis]-a[:,axis])/denom;v=(hi[axis]-a[:,axis])/denom
  t0=np.maximum(t0,np.where(flat,-np.inf,np.minimum(u,v)));t1=np.minimum(t1,np.where(flat,np.inf,np.maximum(u,v)))
 return np.flatnonzero(possible & (t0<=t1+1e-12))

def inv(points,p):
 d=points-np.array(p['position_m']);c,s=math.cos(p['yaw_rad']),math.sin(p['yaw_rad']);o=d.copy();o[:,0]=c*d[:,0]-s*d[:,2];o[:,2]=s*d[:,0]+c*d[:,2];return o

def segments(routes,results,source):
 a=[];z=[];meta=[]
 for route in routes:
  if source=='selected_route_xyz':ps=route['points'];frames=None
  else:
   r=results[route['id']]['result'];events=[(0,r['spawn_position'])]
   events.extend((p['frame'],p['capsule_center'])for p in r.get('position_samples',[]))
   events.extend((p['walk_physics_frame'],p['position'])for p in r.get('waypoint_reached_frames',[]))
   events.append((r['physics_frames'],r['end_position']));events.sort(key=lambda x:x[0]);events=list(dict((f,p)for f,p in events).items())
   ps=[[p[0],p[1]-.9,p[2]]for f,p in events];frames=[f for f,p in events]
  for i in range(len(ps)-1):
   a.append(ps[i]);z.append(ps[i+1]);meta.append({'route_id':route['id'],'segment_index':i,**({'physics_frame_interval':[frames[i],frames[i+1]]}if frames else {})})
 return np.array(a,dtype=float),np.array(z,dtype=float),meta

def main():
 assert b.sha(HERE/'pack.json')==PACK_SHA
 pack=json.loads((HERE/'pack.json').read_text());selected=json.loads(SELECTED.read_text());cert=json.loads(RESULTS.read_text());settings=cert['settings'];results={r['id']:r for r in cert['cases']}
 assert len(selected['routes'])==len(results)==493
 assert b.sha(SELECTED)==cert['selected']['sha256']
 assert set(r['id']for r in selected['routes'])==set(results)
 assert all(r['pass_'] for r in results.values())
 assert selected['sources']['scene']['sha256']==pack['base_scene_sha256']==b.BASE_SHA
 assert b.sha(CONTROLLER)==selected['sources']['original_controller']['sha256']
 gd=CONTROLLER.read_text()
 for name,key in [('RADIUS','radius_m'),('HEIGHT','height_m'),('WAYPOINT_TOLERANCE','waypoint_tolerance_m')]:assert float(re.search(r'const '+name+r' := ([0-9.]+)',gd).group(1))==settings[key]
 radius=settings['radius_m'];height=settings['height_m'];margin=settings['safe_margin_m'];tolerance=settings['waypoint_tolerance_m'];snap=settings['floor_snap_length_m'];spawn=.06
 # Circumscribed box around the capsule: larger than actual capsule throughout.
 horizontal=radius+margin+tolerance
 below=snap+margin
 above=height+margin+spawn
 inflation_lo=np.array([horizontal,above,horizontal]);inflation_hi=np.array([horizontal,below,horizontal])
 records=[];totals={};min_vertical_clearance=None
 for source in ('selected_route_xyz','certified_recorded_capsule_trace'):
  a,z,meta=segments(selected['routes'],results,source);totals[source]={'route_count':493,'continuous_segment_count':len(a),'instance_count':len(pack['add_instances']),'segment_instance_comparisons':len(a)*len(pack['add_instances'])};broad=0;refined=0
  for p in pack['add_instances']:
   asset=pack['common_assets'][p['asset_key']];render_path=b.ROOT/asset['render_path'];assert b.sha(render_path)==asset['render_sha256'];bounds=json.loads(render_path.read_text())['bounds'];world=b.bounds_world(bounds,p)
   ids=slab_hits(a,z,np.array(world['min'])-inflation_lo,np.array(world['max'])+inflation_hi)
   broad+=len(ids)
   if len(ids):
    al,zl=inv(a[ids],p),inv(z[ids],p);hits=slab_hits(al,zl,np.array(bounds['min'])-inflation_lo,np.array(bounds['max'])+inflation_hi);refined+=len(hits);hitset=set(hits.tolist())
    for i,idx in enumerate(ids.tolist()):records.append({'source':source,'instance_id':p['id'],**meta[idx],'route_segment_start_feet_xyz_m':a[idx].tolist(),'route_segment_end_feet_xyz_m':z[idx].tolist(),'world_bounds_m':world,'obb_refinement_intersects':i in hitset})
  totals[source].update(world_aabb_candidate_segment_pairs=broad,refined_obb_candidate_segment_pairs=refined)
 # Existing certified approach end pose is a verified street-eye datum.
 route=results['ROAD:CATHEDRAL_APPROACH'];end=route['result']['end_position'];eye=[end[0],end[1]-height/2+1.65,end[2]]
 cam={'r9_cathedral_street_eye':{'position_m':eye,'target_m':[208.55262526930568,68,-210.25986027545778],'eye_height_m':1.65,'fov_degrees':75,'purpose':'Street-level upward view of retained cathedral tower and added four-sided belfry dressings from the certified clear approach endpoint.','source_route':'ROAD:CATHEDRAL_APPROACH','source_case_pass':route['pass_'],'source_run':route['selected_actual_run']}}
 # No pack mutation: a separate optional camera addendum is sufficient.
 camera_doc={'schema':'riverstone.city.visual_addendum.v1','base_scene_sha256':b.BASE_SHA,'common_assets':{},'add_instances':[],'remove_instance_ids':[],'inspection_cameras':cam,'provenance':{'landmark_pack':b.ref(HERE/'pack.json'),'selected_routes':b.ref(SELECTED),'certified_results':b.ref(RESULTS),'camera_basis':'Certified end_position is capsule centre. Subtract half-height then add 1.65 m eye offset.'}}
 b.write(HERE/'camera_addendum_r02.json',camera_doc)
 report={'schema':'riverstone.city.additive_exact_route_bounds_audit.v1','audit_implementation':b.ref(Path(__file__)),'status':'pass'if not any(r['obb_refinement_intersects']for r in records)else 'needs_exact_geometry_refinement','pack':b.ref(HERE/'pack.json'),'selected_routes':b.ref(SELECTED),'certified_results':b.ref(RESULTS),'controller':b.ref(CONTROLLER),'base_scene_sha256':b.BASE_SHA,'controller_settings':settings,'envelope':{'actual_capsule_radius_m':radius,'actual_capsule_height_m':height,'safe_margin_m':margin,'additional_horizontal_waypoint_tolerance_m':tolerance,'horizontal_radius_bound_m':horizontal,'vertical_below_feet_bound_m':below,'vertical_above_feet_bound_m':above,'spawn_offset_bound_m':spawn,'floor_snap_bound_m':snap},'method':'Continuous line-segment slab intersection against Minkowski-expanded actual cached 3D AABBs. Candidates are inverse-yaw transformed into each asset local frame and tested against its expanded native OBB. The box circum-envelope strictly contains the vertical capsule. No point sampling is used for the authored route segments.','coverage':totals,'candidate_rows':records,'unresolved_candidates':[r for r in records if r['obb_refinement_intersects']],'limitations':['This is a conservative static geometric impact audit, not a new Godot movement replay.','Recorded trace positions are checked as continuous segments between stored telemetry/waypoint events, not claimed to be every physics frame.','Authored and recorded route elevations are used directly; no inference from landmark ground datum.'],'camera_addendum':b.ref(HERE/'camera_addendum_r02.json'),'pack_unchanged':b.sha(HERE/'pack.json')==PACK_SHA}
 b.write(HERE/'exact_route_impact_r01.json',report)
 print(json.dumps({k:v for k,v in report.items()if k in ('status','coverage','envelope','unresolved_candidates','pack_unchanged','camera_addendum')},indent=2))
if __name__=='__main__':main()
