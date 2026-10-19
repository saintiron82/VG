"""Source-bound actual native/public side interfaces. This does not change geometry."""
import pathlib,json,hashlib,sys,math,numpy as np
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT));from world_city.concept_city_v3.registered_topography.revisions.r01_ownership.author import corridor
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as g
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
CITY=ROOT/'world_city/concept_city_v3';R=CITY/'traversal_r5/revisions/r06_r8_precinct/public_network_r18_runtime_r01';read=lambda p:json.loads(p.read_bytes());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();ref=lambda p:dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def write(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2);f.write('\n')
def main():
 d=read(R/'prepared_runtime.json');profile=read(H.parent/'north_approach_r03/profile.json');B=np.array(profile['bridge_frame']['basis']);T=np.array(profile['bridge_frame']['translation']);to_world=lambda q:(np.array(q)@B.T+T).tolist();to_local=lambda q:((np.array(q)-T)@B).tolist();worldpoly=lambda p:[[v[0],v[2]]for q in p for v in[to_world([q[0],0,q[1]])]]
 plan=read(CITY/'registered_source/plan.json');roads={r['id']:r for r in plan['roads']};out=[]
 for name,side in [('EAST_WALL_SERVICE',-1),('SOUTH_WALL_SERVICE',1)]:
  road=roads[name];route=next(q for q in d['routes']if q['id']=='ROAD:'+name);p=road['polyline_xz_m'][-4:];polys=list(corridor(p,road['width_m']));local=[[[v[0],v[2]]for q in poly for v in[to_local([q[0],0,q[1]])]]for poly in polys];native_polys=[[[v[0],v[2]]for v in r['triangle_local_xyz_m']]for r in profile['triangles']];cut=g.subtract(g.union(local),native_polys);seams=[]
  def interval(u,v,poly):
   area=sum(p[0]*q[1]-q[0]*p[1]for p,q in zip(poly,poly[1:]+poly[:1]));sign=1 if area>0 else -1;lo=0.;hi=1.
   for aa,bb in zip(poly,poly[1:]+poly[:1]):
    f=lambda p:sign*((bb[0]-aa[0])*(p[1]-aa[1])-(bb[1]-aa[1])*(p[0]-aa[0]));fu=f(u);fv=f(v)
    if fu<0 and fv<0:return None
    if fu<0:lo=max(lo,fu/(fu-fv))
    elif fv<0:hi=min(hi,fu/(fu-fv))
   return(lo,hi)if hi>lo+1e-10 else None
  sections=profile['sections_local_xyz_m'];idx=0 if side<0 else -1
  for si,(aa,bb)in enumerate(zip(sections,sections[1:])):
   u=aa[idx];v=bb[idx];uv=[[u[0],u[2]],[v[0],v[2]]];ranges=sorted(t for poly in local if(t:=interval(*uv,poly)));merged=[]
   for lo,hi in ranges:
    if merged and lo<=merged[-1][1]+1e-10:merged[-1][1]=max(hi,merged[-1][1])
    else:merged.append([lo,hi])
   for lo,hi in merged:
    vs=[to_world([u[k]+f*(v[k]-u[k])for k in range(3)])for f in[lo,hi]];seams.append(dict(native_profile_section=si,vertices_xyz_m=vs,native_local_vertices_xyz_m=[[u[k]+f*(v[k]-u[k])for k in range(3)]for f in[lo,hi]]))
  assetkey=d['placements'][route['placement_ids'][0]]['asset_key'];asset=d['assets'][assetkey];data=read(ROOT/asset['render_path']);wpolys=[worldpoly(q)for q in cut];window=a.bounds([p for q in wpolys for p in q]);near=[]
  for key,t in zip(data['source_face_indices'],data['triangles']):
   poly=[[v[0],v[2]]for v in t]
   if a.intersects(a.bounds(poly),window):near.append(dict(runtime_source_key=key,collision_triangle_xyz_m=t,collision_triangle_sha256=a.canonical_sha(t)))
  native=[]
  for pid in ['BRIDGE_MAIN_RIVER:NORTH_SUPPORTED_CAUSEWAY']:
   po=d['placements'][pid];na=d['assets'][po['asset_key']];cache=read(ROOT/na['render_path'])
   for gi,group in enumerate(cache['groups']):
    for qi,q in enumerate(group['quads']):
     poly=[[v[0],v[2]]for v in q];bb=a.bounds(poly)
     if any(a.intersects(bb,a.bounds(z))for z in cut):native.append(dict(instance=pid,group_index=gi,quad_index=qi,local_quad_xyz_m=q,world_quad_xyz_m=[to_world(v)for v in q],cache=na))
  out.append(dict(id=name,source_width_m=road['width_m'],source_polyline_tail_xz_m=p,full_road_ribbon_polygons_xz_m=polys,finite_public_side_polygons_xz_m=wpolys,native_boundary_local_z_m=side*3,native_boundary_segments=seams,current_runtime_source_faces=near,actual_native_support_quads_in_window=native,route_ids=[route['id'],route['id']+'_REVERSE'],road_start_cross_section_hint='Use the first selected polyline tail knot and retain its actual public source planes; endpoint round-cap is part of named road footprint.',required_checks=['Preserve all fixed native boundary heights and local native support protrusions.','Regrade actual road floor only inside its declared 4 m ribbon, with exact full-width outer public seam.','Native support extends beyond the 6 m floor edge and remains collidable; verify each actual support quad stays below the new finite approach.','The current runtime source faces are evidence only; final source producer retirement must bind its corresponding authored source rows.']))
 write(H/'north_side_interfaces.json',dict(schema='riverstone.actual_north_bridge_side_interfaces.v1',scene=d['sources']['scene'],prepared=ref(R/'prepared_runtime.json'),native_profile=ref(H.parent/'north_approach_r03/profile.json'),native_contract=ref(H.parent/'north_approach_r03/collision_r04/collision_contract.json'),native_pack=ref(H.parent/'north_approach_r03/resolved_placements.json'),source_plan=ref(CITY/'registered_source/plan.json'),original_failure_handoff=ref(R/'evidence/wall_port_failure_handoff_r01.json'),interfaces=out,status='ACTUAL_INTERFACE_SURVEY_ONLY_REPAIR_PENDING'))
 print(json.dumps(dict(handoff=ref(H/'north_side_interfaces.json'),interfaces=[dict(id=x['id'],polygons=len(x['finite_public_side_polygons_xz_m']),seam_segments=len(x['native_boundary_segments']),source_faces=len(x['current_runtime_source_faces']))for x in out])))
if __name__=='__main__':main()
