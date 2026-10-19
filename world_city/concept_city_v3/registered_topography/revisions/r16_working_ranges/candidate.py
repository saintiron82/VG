"""Bounded R16 composition on actual R6 planes, with exact native exclusions."""
import copy,json,math
from collections import defaultdict,Counter
from . import author as a,frozen_r6 as f
HERE=a.HERE
PROFILE=HERE/'public_interfaces/r6_candidate/level_profile_handoff.json'
PROFILE_SHA='b83e38d8505e9e90c1e7dea2d59163e5771c9f05b65b1c7829ec528f5c916304'
COURT=a.SOURCE/'court_phase01/terrain_handoff.json'
COURT_SHA='9f3a0c615ad31685c963c10a0f3ff89a3dcd5828ec6c47613d633d60f1b6c976'
COURT_PACK=a.SOURCE/'court_phase01/resolved_placements.json'
COURT_PACK_SHA='0404e5374536a9dddde7784f621f58da1a17bd0192bad01a2cb03af18a00177b'

def source_inputs():
 if a.sha(PROFILE)!=PROFILE_SHA:raise ValueError('Changed sealed public profile')
 if a.sha(COURT)!=COURT_SHA or a.sha(COURT_PACK)!=COURT_PACK_SHA:raise ValueError('Changed court native handoff')
 profile=json.loads(PROFILE.read_bytes());court=json.loads(COURT.read_bytes());connector=json.loads((HERE/'court_connector.json').read_bytes())
 if any(r['base_scene_sha256']!=f.SCENE_SHA256 for r in [profile,connector]):raise ValueError('Changed profile base')
 assert not profile['protected_owner_conflicts'] and not profile['source_height_conflicts']
 assert not profile['affected_old_side_masks'] and not profile['retaining_sides']
 return profile,court,connector

def owner_records(profile,court,connector):
 owners=[dict(r,action='hole') for r in a.native_holes()]
 for r in court['native_bearing_owners']:
  if r['requires_finite_terrain_cut']:owners.append(dict(r,kind='actual_court_native_bearing_hole',action='hole',render_land=False))
 owners.extend(dict(r,action='paint') for r in a.court_regions())
 for i,p in enumerate(connector['polygon_regions_xz_m']):owners.append(dict(id='BANK_COURT_CONNECTOR:'+str(i),polygon_xz_m=p,kind='retained_plane_court_connector',action='paint',material='ground_stone'))
 owners.extend(dict(r,kind='retained_plane_moved_public_lane',action='profile') for r in profile['regions'])
 return owners

def build(scene):
 profile,court,connector=source_inputs();owners=owner_records(profile,court,connector);index=f.SurfaceIndex(scene,windows=[f.bounds(r['polygon_xz_m']) for r in owners],margin=0)
 oi=a.geo._SpatialIndex(8)
 for i,r in enumerate(owners):oi.add(i,r['polygon_xz_m'])
 edits=[];appended=defaultdict(list);removed=defaultdict(float);per_source=[]
 for r in index.records:
  active=[owners[i] for i in sorted(oi.candidates(r['polygon_xz_m'])) if a.clean(a.geo.convex_intersection(r['polygon_xz_m'],owners[i]['polygon_xz_m']))]
  if not active:continue
  parts=[r['polygon_xz_m']];source_removed=0
  for owner in active:
   remaining=[]
   for p in parts:
    q=a.clean(a.geo.convex_intersection(p,owner['polygon_xz_m']))
    if not q:remaining.append(p);continue
    area=a.geo.polygon_area(q);removed[owner['id']]+=area;source_removed+=area
    if owner['action']=='paint':appended[owner['material']].extend(v for t in f.fan_upward(f.lift(q,r['plane_y_xz_m'])) for v in t)
    remaining.extend(a.subtract([p],[owner['polygon_xz_m']]))
   parts=remaining
  replacement=[t for p in parts for t in f.fan_upward(f.lift(p,r['plane_y_xz_m']))]
  retained_area=sum(f.normal_y(t)/2 for t in replacement)
  assert abs(retained_area+source_removed-a.geo.polygon_area(r['polygon_xz_m']))<1e-7
  edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],replacement_triangles_xyz_m=replacement))
  per_source.append(dict(material=r['material'],triangle_index=r['triangle_index'],original_area_m2=a.geo.polygon_area(r['polygon_xz_m']),retained_area_m2=retained_area,reowned_area_m2=source_removed))
 # Use the independently checked source profile vertices verbatim.
 for r in profile['triangles']:
  t=r['vertices_xyz_m'];assert f.normal_y(t)>0
  src=r['source_r6'];actual=scene['surfaces'][src['material']][src['triangle_index']*3:src['triangle_index']*3+3]
  assert f.canonical_sha(actual)==src['source_triangle_sha256'] and actual==src['vertices_xyz_m']
  appended[r['material']].extend(t)
 profile_removed=sum(removed[r['id']] for r in profile['regions']);assert abs(profile_removed-profile['proof']['union_area_m2'])<1e-7
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R16_WORKING_RANGES_LEVEL_JOINS',status='CANDIDATE_SOURCE_GEOMETRY_PENDING_ACTUAL_R7_REVIEW',base_scene_sha256=f.SCENE_SHA256,source_surface_hashes={m:f.canonical_sha(scene['surfaces'][m]) for m in sorted({r['material'] for r in edits})},surface_edits=edits,appended_surfaces=dict(appended),removed_foundation_proxy_ids=[])
 assert all(f.normal_y(t)>0 for r in edits for t in r['replacement_triangles_xyz_m'])
 assert all(f.normal_y(vs[i:i+3])>0 for vs in appended.values() for i in range(0,len(vs),3))
 report=dict(status='PASS_BOUNDED_COMPOSED_SOURCE_PLANES_AND_ORIENTATION',base_scene_sha256=f.SCENE_SHA256,source_triangle_edit_count=len(edits),appended_triangle_counts={k:len(v)//3 for k,v in appended.items()},source_area_partition=per_source,owner_removed_area_m2=dict(removed),native_footing_hole_count=len(a.native_holes()),court_native_hole_count=sum(r['requires_finite_terrain_cut'] for r in court['native_bearing_owners']),court_native_cut_area_m2=sum(removed[r['id']] for r in court['native_bearing_owners'] if r['requires_finite_terrain_cut']),public_profile_area_m2=profile_removed,all_new_top_normals_positive=True,all_new_height_planes_unchanged=True,old_bank_and_water_arrays_unchanged=True,new_support_compile_cells=0,retired_native_and_foundation_ids=[],scope='Only finite native holes and material ownership change. All retained/recolored source planes and profile XYZ values are preserved. Native instance composition and capsule acceptance remain parent/validator duties.')
 return patch,report,owners

def route_handoff(profile,connector):
 source=a.read('terrain_handoff.json');externals=[]
 for r in profile['routes']:
  o=copy.deepcopy(r);o['polyline_xyz_m']=[[x,2.5,z] for x,z in r['polyline_xz_m']];o['public_endpoint_xyz_m']=[r['terminal_moved_to_xz_m'][0],2.5,r['terminal_moved_to_xz_m'][1]];externals.append(o)
 def dedup(points):
  out=[]
  for p in points:
   if not out or math.dist(out[-1],p)>1e-9:out.append(p)
  return out
 def prefix_to(points,target):
  for i,(p,q) in enumerate(zip(points,points[1:])):
   dx,dz=q[0]-p[0],q[1]-p[1];den=dx*dx+dz*dz
   if den<1e-16:continue
   t=((target[0]-p[0])*dx+(target[1]-p[1])*dz)/den
   if -1e-8<=t<=1+1e-8 and math.dist([p[0]+t*dx,p[1]+t*dz],target)<1e-7:return dedup(points[:i+1]+[target])
  raise ValueError('Court join does not lie on the declared native branch')
 ext={r['id']:r for r in externals};doors={r['id']:r for r in source['exact_native_door_leaves']};native=[]
 for r in source['internal_walkspaces']:
  d=doors[r['door_id']];external=ext[r['connects_route_id']];branch=list(reversed(r['polyline_xz_m']));assert math.dist(external['polyline_xz_m'][0],branch[0])<1e-7
  full=dedup(list(reversed(external['polyline_xz_m']))+branch)
  native.append(dict(id=r['id'],door_id=r['door_id'],holding_id=r['holding_id'],parcel_id=r['parcel_id'],width_m=r['width_m'],actual_door_xyz_m=d['actual_door_xyz_m'],threshold_lip_xyz_m=[d['threshold_lip_xz_m'][0],2.5,d['threshold_lip_xz_m'][1]],connects_route_id=r['connects_route_id'],branch_polyline_xyz_m=[[x,2.5,z] for x,z in r['polyline_xz_m']],public_to_lip_polyline_xyz_m=[[x,2.5,z] for x,z in full],portal_status=d['portal_status']))
 courts=[]
 for c in source['source_courts']:
  if c['id']=='BANK_DRY_WORK_COURT':
   external=ext[connector['connects_route_id']];full=dedup(list(reversed(external['polyline_xz_m']))+connector['polyline_xz_m']);join=connector['id']
  else:
   link=c['access_link']['polyline_xz_m'];target=link[-1];matches=[]
   for r in source['internal_walkspaces']:
    if r['holding_id']!=c['holding_id']:continue
    try:part=prefix_to(list(reversed(r['polyline_xz_m'])),target)
    except ValueError:continue
    matches.append((len(part),r,part))
   _,r,part=min(matches,key=lambda row:row[0]);external=ext[r['connects_route_id']];full=dedup(list(reversed(external['polyline_xz_m']))+part+list(reversed(link)));join=r['id']
  courts.append(dict(id=c['id'],holding_id=c['holding_id'],width_m=c['access_link']['width_m'],polygon_xz_m=c['polygon_xz_m'],floor_y_m=2.5,public_to_court_polyline_xyz_m=[[x,2.5,z] for x,z in full],joins_native_route_or_connector=join,connects_route_id=external['id']))
 for record in native:record['polyline_xyz_m']=record['public_to_lip_polyline_xyz_m']
 for record in courts:record['polyline_xyz_m']=record['public_to_court_polyline_xyz_m']
 return dict(schema='riverstone.r16.actual_route_handoff.v1',status='SOURCE_GEOMETRY_CANDIDATE_PHYSICS_PENDING',base_scene_sha256=f.SCENE_SHA256,external_routes=externals,native_door_routes=native,court_links=courts,profile_ref=dict(path=str(PROFILE.relative_to(a.ROOT)),sha256=a.sha(PROFILE)),bank_court_connector_ref=dict(path=str((HERE/'court_connector.json').relative_to(a.ROOT)),sha256=a.sha(HERE/'court_connector.json')),full_width_profiles=profile['full_width_profiles'],boundary_seam_ledger=profile['boundary_seam_ledger'],expected_case_count=36,closed_native_doors_not_traversed=True)

def main():
 scene=f.load_scene();patch,report,owners=build(scene);profile,court,connector=source_inputs();routes=route_handoff(profile,connector)
 outputs=[('scene_patch.json',patch),('producer_report.json',report),('route_handoff.json',routes)]
 for name,d in outputs:
  path=HERE/name
  if path.exists():raise ValueError('Refusing to overwrite '+name)
  path.write_text(json.dumps(d,separators=(',',':'))+'\n');print(name,a.sha(path),flush=True)
if __name__=='__main__':main()
