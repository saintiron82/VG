"""Source-bound B15 public seam and route handoff; no scene activation."""
import json,math
from .. import author as a
from .source_preflight import HERE,FABRIC,read,write

def run():
 data=json.loads((HERE/'route_handoff_candidate.json').read_bytes());graph=read('route_graph.json');screen=json.loads((HERE/'public_root_screen.json').read_bytes());nodes={n['id']:n for n in data['nodes']};scene=a.load_scene();idx=a.TriangleIndex(scene,[p for n in data['nodes']for p in n['polygons_xz_m']]);seams=[]
 def height(n,p):
  pr=n.get('terminal_profile',{})
  for tr in pr.get('triangles',[]):
   if a.geo.point_in_convex_polygon(p,tr['polygon_xz_m'],1e-8):return a.common.height(tr['plane_y_xz_m'],p)
  return n['floor_y_m']
 for n in data['nodes']:
  line=n['polyline_xz_m'];pr=n.get('terminal_profile')
  if pr:
   start=[sum(v[k]for v in pr['private_start_edge_xz_m'])/2 for k in(0,1)];end=pr.get('public_edge_xz_m')or[[v[0],v[2]]for v in pr['public_seam_xyz_m']];finish=[sum(v[k]for v in end)/2 for k in(0,1)];steps=max(1,math.ceil(math.dist(start,finish)/.25));line=line[:-2]+[[start[k]+s/steps*(finish[k]-start[k])for k in(0,1)]for s in range(steps+1)];n['polyline_xz_m']=line
  n['polyline_xyz_m']=[[p[0],height(n,p),p[1]]for p in line];n['active_endpoint_xyz_m']=n['polyline_xyz_m'][-1]
 for r in screen['roots']:
  n=nodes[r['node_id']];pr=n.get('terminal_profile');seams.append(dict(id=r['node_id'],public_road_id=pr['road_id']if pr else r['public_road_id'],public_segment=pr['road_segment_index']if pr else r['public_segment'],floor_y_m=n['floor_y_m'],reservation_polygons_xz_m=[pr['polygon_xz_m']]if pr else r['extension_polygons_xz_m'],public_seam_knots_xyz_m=(pr.get('public_seam_knots_xyz_m')or pr.get('public_seam_xyz_m'))if pr else None,shared_profile_triangles=pr.get('triangles',[])if pr else[],retained_public_source_pieces=pr['public_source_triangles']if pr else r['public_source_pieces'],active_endpoint_xyz_m=n['active_endpoint_xyz_m'],new_field_maximum_gradient=pr.get('maximum_gradient',pr.get('maximum_new_grade',0.))if pr else 0.,policy='R18 preserves this exact finite entry profile and its public seam. Coplanar road portions keep public travel semantics with one visible owner.'))
 data['edges']=graph['edges'];data['implementation_tier']='Exact finite source routes and actual native thresholds; integrated capsule replay is pending.';data['status']='SOURCE_REVIEWED_PENDING_INTEGRATION';data['court_route_chains']=[dict(r,public_root=dict(r['public_root'],superseded_anchor_metadata=True,effective_node_id=r['public_root']['node_id']),route_lookup='nodes by route_ids_to_public; terminal supersessions are authoritative')for r in data['court_route_chains']];write('route_handoff.json',data);write('fixed_public_seams.json',dict(schema='riverstone.r17.fixed_public_entries.v1',base_scene_sha256=a.SCENE_SHA256,roots=seams,count=len(seams),supersedes='../coherent_b15_r01/fixed_public_seams_candidate.json',activation=False));print('routes',len(data['door_routes']),'seams',len(seams))
if __name__=='__main__':run()
