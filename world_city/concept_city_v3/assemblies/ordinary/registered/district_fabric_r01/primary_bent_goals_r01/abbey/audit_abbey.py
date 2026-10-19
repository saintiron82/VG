"""Finite existing-source ribbon proof, including conservative capsule caps/joins."""
from search_abbey import *
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.side_clearance import SideIndex

from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.final_profile_audit_r01 import exact_clip
# Local audit-process overrides only; source modules and geometry remain unchanged.
def exact_subtract(polygons,masks):
 out=list(polygons)
 for mask in masks:
  nxt=[]
  for poly in out:
   overlap=exact_clip.clip(poly,mask)
   if len(overlap)>=3 and geo.polygon_area(overlap)>1e-13:nxt.extend(q for q in exact_clip.difference(poly,mask)if len(q)>=3 and geo.polygon_area(q)>1e-13)
   else:nxt.append(poly)
  out=nxt
  if not out:break
 return out
terrain.clip=lambda a,c:exact_clip.clip(a,c)
terrain.AREA_EPSILON_M2=1e-12
terrain.common.subtract=exact_subtract
class Support:
 def __init__(self,scene,windows,native):self.terrain=terrain.TriangleIndex(scene,windows);self.native=terrain.TriangleIndex({'surfaces':native},windows)
 def covering(self,p):
  # Exact upper envelope of retained rendered tops. Plane crossings are clipped,
  # so an ordering heuristic can never select a buried surface.
  rows=list(self.native.covering(p))+list(self.terrain.covering(p));claimed=[]
  rows.sort(key=lambda r:-sum(terrain.common.height(r['plane_y_xz_m'],q)for q in r['intersection_polygon_xz_m'])/len(r['intersection_polygon_xz_m']))
  for ri,r in enumerate(rows):
   poly=r['intersection_polygon_xz_m'];plane=r['plane_y_xz_m'];minimum=min(terrain.common.height(plane,q)for q in poly);masks=list(claimed)
   for oi,other in enumerate(rows):
    if oi==ri:continue
    op=other['intersection_polygon_xz_m'];otherplane=other['plane_y_xz_m']
    if max(terrain.common.height(otherplane,q)for q in op)<=minimum+1e-9:continue
    delta=[otherplane[k]-plane[k]for k in range(3)]
    vals=[delta[0]*q[0]+delta[1]*q[1]+delta[2]for q in op]
    if max(vals)<=1e-9:continue
    dom=[];prev=op[-1];pv=delta[0]*prev[0]+delta[1]*prev[1]+delta[2]
    for cur in op:
     cv=delta[0]*cur[0]+delta[1]*cur[1]+delta[2]
     if (pv>=0)!=(cv>=0):
      t=pv/(pv-cv);dom.append([prev[k]+t*(cur[k]-prev[k])for k in range(2)])
     if cv>=0:dom.append(cur)
     prev,pv=cur,cv
    if len(dom)>=3 and geo.polygon_area(dom)>1e-12:masks.append(dom)
   for q in terrain.common.subtract([poly],masks):
    if geo.polygon_area(q)>1e-12:yield dict(r,intersection_polygon_xz_m=q);claimed.append(q)
def circle(p,n=32):
 r=.3/math.cos(math.pi/n)
 return[[p[0]+r*math.cos(2*math.pi*j/n),p[1]+r*math.sin(2*math.pi*j/n)]for j in range(n)]
def main():
 t=time.monotonic();d=load(O/'search_result.json');grid=np.load(O/'search_grid.npz');pts=d['polyline_xz_m'];assert pts
 bounds=d['bounds_xz_m'];step=d['grid_step_m'];dist=grid['distance'];
 def los(a,c):
  ps=np.linspace(a,c,max(2,math.ceil(math.dist(a,c)/.08)+1));ix=np.rint((ps[:,0]-bounds[0])/step).astype(int);iz=np.rint((ps[:,1]-bounds[1])/step).astype(int)
  return bool(np.all(dist[iz,ix]>=.49))
 simple=[pts[0]];i=0
 while i<len(pts)-1:
  j=len(pts)-1
  while j>i+1 and not los(pts[i],pts[j]):j-=1
  simple.append(pts[j]);i=j
 # Exact public source cut beyond the original junction's defective cap.
 road=next(r for r in load(CAT)['routes']if r['id']==d['road_id']);si=10;cut_t=.15
 q=[road['points_xyz_m'][si][k]+cut_t*(road['points_xyz_m'][si+1][k]-road['points_xyz_m'][si][k])for k in range(3)]
 simple[0]=[q[0],q[2]];d['road_cut']=dict(segment_index=si,t=cut_t,point_xyz_m=q)
 # Reuse the source-only local detour around exposed road-junction defects.
 if '--detour'in sys.argv and (O/'road_seam_candidate.json').exists():
  seam=load(O/'road_seam_candidate.json')
  if seam['status']=='CANDIDATE':simple=seam['polyline_xz_m']+simple[1:];d['road_cut']=seam['road_cut']
 # Approach the opening along its actual outward-facing normal in the final metre.
 e=d['entrance'];near=[e['threshold_world_xyz_m'][i]-1.6*e['forward_into_asset_world'][i]for i in[0,2]]
 if los(simple[-2],near)and los(near,simple[-1]):simple.insert(-1,near)
 polys=[]
 for i,(a,c)in enumerate(zip(simple,simple[1:])):
  segments=np.linspace(a,c,max(2,math.ceil(math.dist(a,c)/2)+1)).tolist()
  polys.extend(dict(id='SEG:'+str(i)+':'+str(j),kind='finite_segment_strip',polygon_xz_m=q)for j,q in enumerate(b.ribbon(segments,.6)))
 threshold=[e['threshold_world_xyz_m'][i]for i in[0,2]]
 polys.append(dict(id='DOOR_THRESHOLD_WITNESS',kind='exterior_standing_to_actual_door_threshold',polygon_xz_m=b.ribbon([simple[-1],threshold],.6)[0]))
 polys.append(dict(id='DOOR_THRESHOLD_CAP',kind='circumscribed_32gon_threshold_end',polygon_xz_m=circle(threshold)))
 polys += [dict(id='CAP:'+str(i),kind='circumscribed_32gon_capsule_join_or_end',polygon_xz_m=circle(p))for i,p in enumerate(simple)]
 wins=[r['polygon_xz_m']for r in polys];scene=load(SC);geometry=load(O/'source_geometry.json');native={};bindings=[];native_triangle_refs={};cache={}
 for p in geometry['native_bindings']:
  if not any(geo.intersection_area(b.xform(b.rect(*(lambda bb:[bb['min'][0],bb['min'][2],bb['max'][0],bb['max'][2]])(load(ROOT/p['cache']['path'])['bounds'])),p),w)>1e-8 for w in wins):continue
  mesh=cache.setdefault(p['cache']['path'],load(ROOT/p['cache']['path']));p['actual_world_bounds_polygon_xz_m']=b.xform(b.rect(mesh['bounds']['min'][0],mesh['bounds']['min'][2],mesh['bounds']['max'][0],mesh['bounds']['max'][2]),p);bindings.append({k:v for k,v in p.items()if k not in('body_polygons_xz_m','floor_polygons_xz_m')});vs=[];refs=[]
  for gi,g in enumerate(mesh['groups']):
   for qi,q in enumerate(g['quads']):
    if max(v[1]for v in q)-min(v[1]for v in q)>1e-8:continue
    fy=q[0][1]+p['position_m'][1]
    if abs(fy-8)>1e-7:continue
    ny=(q[1][2]-q[0][2])*(q[2][0]-q[0][0])-(q[1][0]-q[0][0])*(q[2][2]-q[0][2])
    if ny<=0:continue
    poly=b.xform([[v[0],v[2]]for v in q],p)
    for tri in terrain.fan_upward([[x,fy,z]for x,z in poly]):
     refs.append(dict(native_instance_id=p['id'],cache=p['cache'],group_index=gi,group_material=g['material'],quad_index=qi,source_quad_sha256=terrain.canonical_sha(q),local_source_quad_xyz_m=q,world_triangle_xyz_m=tri));vs.extend(tri)
  if vs:native['native:'+p['id']]=vs;native_triangle_refs['native:'+p['id']]=refs
 print('simplified',len(simple),'points',simple,'native',len(bindings),flush=True)
 idx=Support(scene,wins,native);print('support indexed',len(idx.terrain.rows),len(idx.native.rows),time.monotonic()-t,flush=True);side=SideIndex(scene,wins);print('sides indexed',len(side.rows),time.monotonic()-t,flush=True);owners=[];checks=[];contacts=[];slab_cache={}
 for part in polys:
  check=terrain.audit_polygon(idx,part['polygon_xz_m'],None,grade_limit=.12);checks.append(dict(**part,**check));print('support',part['id'],len(check['source_pieces']),time.monotonic()-t,flush=True)
  fmin=min((r['min_y_m']for r in check['source_pieces']),default=8);fmax=max((r['max_y_m']for r in check['source_pieces']),default=8)
  for pi,r in enumerate(check['source_pieces']):
   owners.append(dict(id=part['id']+':'+str(pi),polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m']))
   for p in bindings:
    if geo.intersection_area(r['polygon_xz_m'],p['actual_world_bounds_polygon_xz_m'])<=1e-8:continue
    mesh=cache[p['cache']['path']];lo=fmin-p['position_m'][1]+.01;hi=fmax-p['position_m'][1]+2.2;key=(p['id'],round(lo,9),round(hi,9))
    if key not in slab_cache:slab_cache[key]=[b.xform(q,p)for q in slab_rectangles(mesh,lo,hi)]
    for bi,q in enumerate(slab_cache[key]):
     ar=geo.intersection_area(r['polygon_xz_m'],q)
     if ar>1e-8:contacts.append(dict(ribbon_part=part['id'],floor_piece=pi,native_id=p['id'],body_piece=bi,area_m2=ar,floor_y_interval_m=[r['min_y_m'],r['max_y_m']],slab_y_interval_m=[lo+p['position_m'][1],hi+p['position_m'][1]]))
  print(part['id'],'missing',check['missing_area_m2'],'excess',check['excess_area_m2'],'grade',check['max_actual_triangle_grade'],'contacts',len(contacts),flush=True)
 bank=side.audit(owners);used={};upper_conflicts=[]
 for owner in owners:
  floor_min=min(terrain.common.height(owner['plane_y_xz_m'],q)for q in owner['polygon_xz_m'])
  for ri in idx.terrain.index.candidates(owner['polygon_xz_m']):
   rr=idx.terrain.rows[ri]
   if max(v[1]for v in rr['vertices_xyz_m'])<=floor_min+1e-7:continue
   qq=exact_clip.clip(owner['polygon_xz_m'],rr['polygon_xz_m'])
   if not qq or geo.polygon_area(qq)<=1e-8:continue
   delta=max(terrain.common.height(rr['plane_y_xz_m'],q)-terrain.common.height(owner['plane_y_xz_m'],q)for q in qq)
   if delta>1e-7:upper_conflicts.append(dict(owner_id=owner['id'],material=rr['material'],triangle_index=rr['triangle_index'],source_triangle_sha256=rr['source_triangle_sha256'],max_surface_above_selected_floor_m=delta,polygon_xz_m=qq))
 for c in checks:
  for r in c['source_pieces']:
   if r['material'].startswith('native:'):used[(r['material'],r['triangle_index'])]=native_triangle_refs[r['material']][r['triangle_index']]
 # Resolve each route waypoint against actual native-first top triangles.
 xyz=[]
 for p in simple:
  candidates=[]
  for index in[idx.native,idx.terrain]:
   for j in index.index.candidates(circle(p)):
    r=index.rows[j]
    if geo.point_in_convex_polygon(p,r['polygon_xz_m'],1e-7):candidates.append(terrain.common.height(r['plane_y_xz_m'],p))
   if candidates:break
  assert candidates,p
  xyz.append([p[0],max(candidates),p[1]])
 passed=all(c['passes_existing_surface']for c in checks)and not contacts and not bank['contacts']and not upper_conflicts
 summary=dict(status='FINITE_RIBBON_PASS_RUNTIME_UNTESTED'if passed else'FINITE_RIBBON_BLOCKED',passed=passed,segment_count=len(simple)-1,waypoint_count=len(simple),ribbon_piece_count=len(polys),missing_area_sum_m2=sum(c['missing_area_m2']for c in checks),excess_area_sum_m2=sum(c['excess_area_m2']for c in checks),max_actual_triangle_grade=max(c['max_actual_triangle_grade']for c in checks),native_contacts=len(contacts),bank_contacts=len(bank['contacts']),higher_actual_surface_conflicts=len(upper_conflicts),native_instances=len(bindings),native_source_triangles_used=len(used),scene_boxes_count=len(scene['boxes']),route_length_m=sum(math.dist(a,c)for a,c in zip(simple,simple[1:])),threshold_witness_xyz_m=e['threshold_world_xyz_m'],seconds=time.monotonic()-t)
 out=dict(schema='riverstone.abbey_existing_bent_route_proof.v1',scene=ref(SC),entrance_pack=ref(PK),route_catalog=ref(CAT),source_road_id=d['road_id'],road_cut=d['road_cut'],opening=e,polyline_xyz_m=xyz,width_m=.6,capsule_radius_m=.3,headroom_m=2.2,clear_volume_floor_contact_allowance_m=.01,capsule_coverage='Every 0.6 m segment rectangle plus every joint/end circumscribed 32-gon with inradius 0.3 m conservatively covers the full swept circular capsule footprint.',summary=summary,exact_clipping_helper=ref(Path(exact_clip.__file__)),native_bindings=bindings,native_floor_source_refs=list(used.values()),support_selection='Exact pointwise upper envelope of actual native and terrain tops. Source-plane dominance regions are clipped before subtracting; no index-order or level-only ownership assumption. Every chosen piece is independently checked for hidden higher geometry.',upper_actual_surface_conflicts=upper_conflicts,support_checks=checks,native_contacts=contacts,terrain_side_checks=bank,limitations=['Read-only existing final scene; no new terrain/native geometry or controller changes.','Finite geometry proof only; unchanged player/NPC controller replay and actual scene visual review not run.'])
 write('abbey_bent_route_proof.json',out);write('abbey_bent_route_summary.json',{k:v for k,v in out.items()if k not in('support_checks','native_floor_source_refs','terrain_side_checks','native_contacts','upper_actual_surface_conflicts')});print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
