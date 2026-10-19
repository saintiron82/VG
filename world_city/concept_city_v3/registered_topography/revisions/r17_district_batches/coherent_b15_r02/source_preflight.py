"""Exact coherent B15 source budget and shared public reservations."""
import json,time,math
from .. import author as a,native_clearance,public_tails
HERE=a.HERE/'coherent_b15_r02';FABRIC=public_tails.FABRIC/'coherent_regrade_r01/BLOCK_015'
def read(n):return json.loads((FABRIC/n).read_bytes())
def write(n,d):
 p=HERE/n
 if p.exists():raise ValueError('Preserve '+str(p))
 p.write_text(json.dumps(d,separators=(',',':'))+'\n')
def run():
 t=time.monotonic();layout=read('selected_layout.json');hand=read('terrain_handoff.json');graph=read('route_graph.json');plan=json.loads(a.PLAN_PATH.read_bytes());scene=a.load_scene();nodes={r['id']:r for r in graph['nodes']};roads={r['id']:r for r in plan['roads']};windows=[p for r in hand['parcels']for key in('whole_holding_polygons_xz_m','walk_polygons_xz_m')for p in r.get(key,[])];index=a.TriangleIndex(scene,windows);roots=[]
 for root in graph['proposed_public_roots']:
  node=nodes[root['node_id']];rd=roads[root['public_road_id']];p,q=rd['polyline_xz_m'][root['public_segment']:root['public_segment']+2];lane=a.geo.road_ribbon(p,q,rd['width_m']);end=root['public_center_anchor']['point_xz_m'];start=node['polyline_xz_m'][-1];width=node['width_m'];tail=a.common.disjoint_union([a.geo.road_ribbon(start,end,width),public_tails.circle(start,width/2),public_tails.circle(end,min(width,rd['width_m'])/2)]);polys=a.common.disjoint_union(node['polygons_xz_m']+tail);seam=[]
  for poly in polys:
   q=a.clip(poly,lane)
   if q:
    for r in index.covering(q):
     if r['material']not in('road','alley'):continue
     ys=[a.common.height(r['plane_y_xz_m'],v)for v in r['intersection_polygon_xz_m']];seam.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],polygon_xz_m=r['intersection_polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'],min_y_m=min(ys),max_y_m=max(ys),grade=math.hypot(*r['plane_y_xz_m'][:2])))
  floor=root['proposed_floor_y_m'];delta=max([max(abs(s['min_y_m']-floor),abs(s['max_y_m']-floor))for s in seam]+[0]);roots.append(dict(root,source_node=node,extension_polygons_xz_m=tail,extended_polyline_xyz_m=[[start[0],floor,start[1]],[end[0],root['public_center_anchor']['y_m'],end[1]]],public_source_pieces=seam,maximum_public_floor_delta_m=delta,maximum_public_triangle_grade=max([s['grade']for s in seam]+[0]),status='FIXED_LEVEL_PUBLIC_SEAM'if delta<1e-7 and seam else'REQUIRES_FINITE_PROFILE',fixed_boundary_reservation=True));print(root['node_id'],roots[-1]['status'],delta,roots[-1]['maximum_public_triangle_grade'],flush=True)
 native=native_clearance.check(layout);write('native_clearance.json',native);print('native',native['summary'],flush=True)
 write('public_root_screen.json',dict(schema='riverstone.r17.coherent_public_roots.v1',base_scene_sha256=a.SCENE_SHA256,sources=[dict(path=str((FABRIC/n).relative_to(a.ROOT)),sha256=a.sha(FABRIC/n))for n in('selected_layout.json','terrain_handoff.json','route_graph.json')],roots=roots,elapsed_s=time.monotonic()-t,activation=False))
if __name__=='__main__':run()
