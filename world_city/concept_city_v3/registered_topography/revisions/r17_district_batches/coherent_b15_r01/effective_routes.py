"""Explicit finite supersession of obsolete public terminal branches."""
import json,math,time,collections
from .. import author as a,side_clearance
from .source_preflight import HERE,FABRIC,read,write

def trim_before(poly,edge,reference):
 p,q=edge;sign=1 if a.geo._cross(p,q,reference)>=0 else-1
 r=side_clearance.halfspace([[v[0],0,v[1]]for v in poly],lambda v:sign*a.geo._cross(p,q,[v[0],v[2]]))
 return a.common.clean([[v[0],v[2]]for v in r])

def build():
 hand=read('terrain_handoff.json');graph=read('route_graph.json');screen=json.loads((HERE/'public_root_screen.json').read_bytes());profiles=json.loads((HERE/'terminal_profiles_r03.json').read_bytes());moves=json.loads((HERE/'terminal_reservations_r02.json').read_bytes());add=json.loads((FABRIC.parent/'backbone_dryside_addendum_r01.json').read_bytes());changes={r['source_node_id']:r['profile']for r in profiles['results']};changes.update({r['source_node_id']:r['chosen']for r in moves['roots']if r['chosen']});nodes=[];retired=[]
 for n0 in graph['nodes']:
  n=dict(n0)
  if n['id']==add['replacement_route']['id']:n.update(add['replacement_route'])
  if n['id']in changes:
   ch=changes[n['id']];edge=ch['private_start_edge_xz_m'];oldpolys=n['polygons_xz_m'];kept=[q for p in oldpolys if(q:=trim_before(p,edge,n['polyline_xz_m'][0]))];retiredpolys=a.common.subtract(oldpolys,kept+[ch['polygon_xz_m']]);n['polygons_xz_m']=kept+[ch['polygon_xz_m']];start=[sum(v[k]for v in edge)/2 for k in(0,1)];end=ch.get('public_edge_xz_m')or[[v[0],v[2]]for v in ch['public_seam_xyz_m']];finish=[sum(v[k]for v in end)/2 for k in(0,1)];line=n['polyline_xz_m'][:-1]+[start,finish];n['polyline_xz_m']=line;n['terminal_profile']=ch;n['active_floor_policy']='Exact finite profile takes priority; old downstream pad fragments are nonwalking verge.';retired.append(dict(source_node_id=n['id'],inactive_terminal_polygons_xz_m=retiredpolys,private_start_edge_xz_m=edge,new_public_edge_xz_m=end,source_profile_path='terminal_profiles_r03.json'if'triangles'in ch else'terminal_reservations_r02.json'))
  else:
   root=next((r for r in screen['roots']if r['node_id']==n['id']),None)
   if root:n['polygons_xz_m']+=root['extension_polygons_xz_m'];n['polyline_xz_m']+=[root['public_center_anchor']['point_xz_m']]
  nodes.append(n)
 return dict(schema='riverstone.r17.coherent_routes.v1',base_scene_sha256=a.SCENE_SHA256,source_route_graph_sha256=a.sha(FABRIC/'route_graph.json'),dry_side_addendum_sha256=a.sha(FABRIC.parent/'backbone_dryside_addendum_r01.json'),door_routes=hand['door_routes'],nodes=nodes,court_route_chains=hand['court_route_chains'],terminal_supersessions=retired,accepted_new_profile_grade_limit=.12,public_continuation_policy='Retained public triangles retain their measured baseline status; this handoff proves finite private routes and exact shared end profiles, not the whole public network.',activation=False)

def run():
 t=time.monotonic();data=build();scene=a.load_scene();patch=json.loads((HERE/'candidate_scene_patch.json').read_bytes());owners=json.loads((HERE/'owners.json').read_bytes())['owners'];windows=[p for n in data['nodes']for p in n['polygons_xz_m']];old=a.TriangleIndex(scene,windows);edits={(r['material'],r['triangle_index']):r for r in patch['surface_edits']};local=dict(surfaces={})
 for r in old.rows+side_clearance.SideIndex(scene,windows).rows:
  ts=edits.get((r['material'],r['triangle_index']),{}).get('replacement_triangles_xyz_m',[r['vertices_xyz_m']]);local['surfaces'].setdefault(r['material'],[]).extend(v for tr in ts for v in tr)
 for m,vs in patch['appended_surfaces'].items():local['surfaces'].setdefault(m,[]).extend(vs)
 index=a.TriangleIndex(local,windows);holes=[o['polygon_xz_m']for o in owners if o['action']=='hole'];hi=a.geo._SpatialIndex(16)
 for i,p in enumerate(holes):hi.add(i,p)
 checks=[];walk=[];inherited=[]
 for n in data['nodes']:
  for j,p in enumerate(n['polygons_xz_m']):
   for k,q in enumerate(a.common.subtract([p],[holes[i]for i in hi.candidates(p)])):
    proof=a.audit_polygon(index,q);bad=[r for r in proof['source_pieces']if r['actual_triangle_grade']>.12000001];newbad=[r for r in bad if r['material']not in('road','alley')];inherited.extend(dict(node_id=n['id'],**r)for r in bad if r['material']in('road','alley'));checks.append(dict(node_id=n['id'],polygon_index=j,missing_area_m2=proof['missing_area_m2'],overlap_area_m2=proof['excess_area_m2'],new_grade_failures=newbad))
    for r in proof['source_pieces']:walk.append(dict(id=n['id'],polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m']))
 side=side_clearance.SideIndex(local,windows).audit(walk);wi=a.geo._SpatialIndex(16)
 for i,o in enumerate(walk):wi.add(i,o['polygon_xz_m'])
 # Retaining edges are permitted along the finite outer boundary. Reject an
 # actual vertical face if its interior projection lies inside any walk polygon.
 intrusions=[]
 for r in side['contacts']:
  poly=r['intersection_vertices_xyz_m'];m=[sum(v[k]for v in poly)/len(poly)for k in(0,2)];inside=False
  for i in wi.candidates([m]):
   o=walk[i];p=o['polygon_xz_m'];sgn=1 if a.geo.signed_polygon_area(p)>0 else-1
   if all(sgn*a.geo._cross(u,v,m)>1e-8*max(math.dist(u,v),1.)for u,v in zip(p,p[1:]+p[:1])):inside=True;break
  if inside:intrusions.append(r)
 failures=[r for r in checks if r['missing_area_m2']>1e-7 or r['overlap_area_m2']>1e-7 or r['new_grade_failures']];result=dict(scene_patch_sha256=a.sha(HERE/'candidate_scene_patch.json'),route_nodes=len(data['nodes']),door_routes=len(data['door_routes']),checks=len(checks),failures=failures,baseline_public_grade_exceedances=inherited,raw_side_contacts=len(side['contacts']),interior_side_contacts=intrusions,elapsed_s=time.monotonic()-t,status='PASS_LOCAL_FIELDS'if not(failures or intrusions)else'FAILED',activation=False)
 write('route_handoff_candidate.json',data);write('effective_route_audit_r01.json',result);write('effective_route_side_contacts_r01.json',side);print('result',result['status'],'fails',len(failures),'walls',len(intrusions),'inherited',len(inherited),'time',result['elapsed_s'],flush=True)
if __name__=='__main__':run()
