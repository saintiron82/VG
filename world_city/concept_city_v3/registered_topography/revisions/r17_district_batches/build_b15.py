"""Compose one accepted district batch against immutable corrected R7 indices."""
import json,time,copy
from . import author as a,compose_fields,public_tails

def read(p):return json.loads(p.read_bytes())
def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def write(p,d):p.write_text(json.dumps(d,separators=(',',':'))+'\n')
def run():
 folder=a.HERE/'b15_composed_r01'
 if folder.exists():raise SystemExit('Preserve prior composed candidate')
 folder.mkdir();t0=time.monotonic();fabric=public_tails.FABRIC;hand=read(fabric/'terrain_handoff.json');layout=read(fabric/'selected_layout.json');access=read(fabric/'access_handoff.json');proof=read(a.HERE/'bulk_b15_r01/source_audit.json');retire=read(a.HERE/'bulk_b15_r01/retirement.json');profile=read(a.HERE/'root06_regrade_r04/profile.json');interfaces=read(a.HERE/'root06_regrade_r04/interfaces.json');acceptance=read(a.HERE/'root06_regrade_r04/acceptance.json');tails=read(a.HERE/'public_tails_r02/handoff.json')['tails']+read(a.HERE/'public_tail_inherited_cap_r01/handoff.json')['tails'];scene=a.load_scene()
 if not proof['passes_source_gate']or not acceptance['passes']or len(tails)!=6:raise ValueError('Source promotion gate not complete')
 owners=[]
 def add(id,p,action,material=None,floor=None,plane=None,kind=None):
  q=a.common.clean(p)
  if not q:return
  d=dict(id=id,polygon_xz_m=q,action=action,kind=kind or action)
  if material is not None:d['material']=material
  if floor is not None:d['floor_y_m']=floor
  if plane is not None:d['plane_y_xz_m']=plane
  owners.append(d)
 for parcel in hand['parcels']:
  for j,p in enumerate(parcel['footing_polygons_xz_m']):add(parcel['id']+':NATIVE:'+str(j),p,'hole',kind='actual_native_footing')
 for j,f in enumerate(profile['triangles']):add(profile['id']+':'+str(j),f['polygon_xz_m'],'field','ground_stone',plane=f['plane_y_xz_m'],kind='continuous_private_public_ramp')
 for tail in tails:
  for j,p in enumerate(tail['polygons_xz_m']):add(tail['id']+':'+str(j),p,'paint','ground_stone',None if tail.get('surface_mode')=='retain_original_source_planes'else tail['floor_y_m'],kind='exact_public_tail')
 for parcel in hand['parcels']:
  for j,p in enumerate(parcel['walk_polygons_xz_m']):add(parcel['id']+':WALK:'+str(j),p,'paint','ground_stone',parcel['floor_y_m'],kind='active_walking')
  for j,p in enumerate(parcel['court_polygons_xz_m']):add(parcel['id']+':COURT:'+str(j),p,'paint','ground_earth',parcel['floor_y_m'],kind='functional_court')
  for j,p in enumerate(parcel['whole_holding_polygons_xz_m']):add(parcel['id']+':GROUND:'+str(j),p,'paint','ground_earth',parcel['floor_y_m'],kind='bounded_holding_ground')
 print('owners',len(owners),flush=True);patch,report=compose_fields.build(scene,owners,retire['body_restorations'],retire['removed_foundation_proxy_ids']);print('tops composed',len(patch['surface_edits']),flush=True)
 keys={(r['material'],r['triangle_index'])for r in patch['surface_edits']}
 for row in interfaces['side_surface_edits']:
  if(row['material'],row['triangle_index'])in keys:raise ValueError('Uncomposed top/side source key')
  patch['surface_edits'].append(row)
 patch['appended_surfaces'].setdefault('bank',[]).extend(v for t in interfaces['appended_retaining_triangles_xyz_m']for v in t)
 patch['source_surface_hashes']={m:a.canonical_sha(scene['surfaces'][m])for m in sorted({r['material']for r in patch['surface_edits']})};patch['id']='R17_BLOCK_015_16_HOLDINGS';patch['status']='SOURCE_ACCEPTED_PENDING_INDEPENDENT_COMPOSITION_AND_RUNTIME';patch['source_references']=[ref(fabric/f)for f in('selected_layout.json','terrain_handoff.json','access_handoff.json','court_equipment.json','native_local.json')]+[ref(a.HERE/p)for p in('bulk_b15_r01/source_audit.json','bulk_b15_r01/retirement.json','public_tails_r02/handoff.json','public_tail_inherited_cap_r01/handoff.json','root06_regrade_r04/profile.json','root06_regrade_r04/interfaces.json','root06_regrade_r04/acceptance.json')]
 report.update(finite_side_source_edits=len(interfaces['side_surface_edits']),new_retaining_triangles=len(interfaces['appended_retaining_triangles_xyz_m']),elapsed_s=time.monotonic()-t0,retired_source_ids=retire['retired_source_ids'],public_root_count=7,maximum_new_triangle_grade=profile['maximum_gradient'],native_hole_count=sum(o['action']=='hole'for o in owners),side_acceptance=ref(a.HERE/'root06_regrade_r04/acceptance.json'))
 # Existing door and court chains remain exact. Only the private root06 terminal
 # is replaced; the other six roots receive bounded source-proved extensions.
 routes=copy.deepcopy(layout['shared_private_routes']);root=next(r for r in routes if r['id']=='B15:R8:LANE:2_5:06');root['superseded_terminal_polyline_xz_m']=root['polyline_xz_m'];start=[sum(v[k]for v in profile['start_edge_xz_m'])/2 for k in(0,1)];stations=[]
 for j in range(0,len(profile['vertices_xz_m']),2):
  p,q=profile['vertices_xz_m'][j:j+2];stations.append([(p[0]+q[0])/2,(profile['heights_m'][j]+profile['heights_m'][j+1])/2,(p[1]+q[1])/2])
 root['polyline_xyz_m']=[[root['polyline_xz_m'][0][0],root['floor_y_m'],root['polyline_xz_m'][0][1]]]+stations;root['polyline_xz_m']=[[v[0],v[2]]for v in root['polyline_xyz_m']];root['terminal_profile']=ref(a.HERE/'root06_regrade_r04/profile.json');root['terminal_road_id']=profile['road_id'];root['terminal_segment_index']=profile['road_segment_index'];root['status']='EXACT_FINITE_TRIANGLE_PROFILE_SOURCE_ACCEPTED'
 for r in routes:
  if 'polyline_xyz_m'not in r:r['polyline_xyz_m']=[[x,r['floor_y_m'],z]for x,z in r['polyline_xz_m']]
  match=next((t for t in tails if t['source_backbone_id']==r['id']),None)
  if match:r['terminal_tail_id']=match['id'];r['terminal_road_id']=match['road_id']
 route_hand=dict(schema='riverstone.r17.district_route_handoff.v1',base_scene_sha256=a.SCENE_SHA256,source_access=ref(fabric/'access_handoff.json'),door_routes=access['routes'],holdings=layout['holdings'],shared_private_routes=routes,public_root_tails=tails,regenerated_root=profile,retired_source_path_ids=retire['retired_source_path_ids'],retired_actual_door_ids=retire['retired_actual_door_ids'],status='SOURCE_GEOMETRY_ACCEPTED_RUNTIME_PENDING',scope='All 66 cached doorway links, 16 holding entries, 11 shared backbones and seven public roots; private branches join their unchanged earlier backbone at exact source level.',activation=False)
 for name,d in [('scene_patch.json',patch),('composition_report.json',report),('owners.json',dict(owners=owners)),('route_handoff.json',route_hand),('retirement.json',retire)]:write(folder/name,d)
 print('DONE',report['elapsed_s'],'seconds',a.sha(folder/'scene_patch.json'),flush=True)
if __name__=='__main__':run()
