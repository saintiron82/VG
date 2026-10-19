"""Actual native quay/pier deck adjacency; static vessel/river associations."""
from .audit import *
def shared_length(p,q):
 total=0
 for u,v in zip(p,p[1:]+p[:1]):
  d=math.dist(u,v)
  if d<1e-8:continue
  tx,tz=(v[0]-u[0])/d,(v[1]-u[1])/d
  for b,c in zip(q,q[1:]+q[:1]):
   if max(abs((x[0]-u[0])*tz-(x[1]-u[1])*tx)for x in[b,c])>1e-6:continue
   t=[(x[0]-u[0])*tx+(x[1]-u[1])*tz for x in[b,c]];total+=max(0,min(d,max(t))-max(0,min(t)))
 return total

def run():
 s=a.load_scene();nodes=[];boats=[]
 for p in s['common_instances']:
  if p['source_pack']!='port':continue
  ass=s['common_assets'][p['asset_key']];r=json.loads((ROOT/ass['render_path']).read_text())
  if p['id'].startswith(('PORT_QUAY_RUN_','PORT_PIER_')):
   tops=[]
   for group in r['groups']:
    for q in group['quads']:
     vs=[pose(v,p)for v in q]
     if a.normal_y(vs[:3])>1e-8 and max(abs(v[1]-2.2)for v in vs)<1e-8:tops.append([[v[0],v[2]]for v in vs])
   nodes.append(dict(id=p['id'],position_m=p['position_m'],source=ref(ROOT/ass['master_path']),cache=ref(ROOT/ass['render_path']),floor_y_m=2.2,actual_upward_deck_polygons_xz_m=tops,area_m2=sum(g.polygon_area(q)for q in tops)))
  if 'BARGE'in p['id']:
   world=[pose(v,p)for v in [[r['bounds']['min'][0],0,r['bounds']['min'][2]],[r['bounds']['max'][0],0,r['bounds']['min'][2]],[r['bounds']['max'][0],0,r['bounds']['max'][2]],[r['bounds']['min'][0],0,r['bounds']['max'][2]]]];poly=[[v[0],v[2]]for v in world];covered=[];heads=[]
   for j in range(0,len(s['surfaces']['water']),3):
    t=s['surfaces']['water'][j:j+3];q=g.convex_intersection(poly,[[v[0],v[2]]for v in t])
    if g.polygon_area(q)>1e-8:covered.append(a.common.clean(q));heads.extend(a.common.height(a.common.plane(t),v)for v in q)
   boats.append(dict(id=p['id'],position_m=p['position_m'],cache=ref(ROOT/ass['render_path']),full_rig_projected_footprint_m2=g.polygon_area(poly),missing_water_below_projection_m2=sum(g.polygon_area(q)for q in a.common.subtract([poly],covered)),minimum_waterline_minus_static_origin_m=min(heads)-p['position_m'][1],maximum_waterline_minus_static_origin_m=max(heads)-p['position_m'][1],status='Static moored pose; buoyancy, gangway boarding and vessel controller unimplemented.'))
 edges=[]
 for i,n in enumerate(nodes):
  for m in nodes[:i]:
   area=sum(g.polygon_area(g.convex_intersection(p,q))for p in n['actual_upward_deck_polygons_xz_m']for q in m['actual_upward_deck_polygons_xz_m']);length=sum(shared_length(p,q)for p in n['actual_upward_deck_polygons_xz_m']for q in m['actual_upward_deck_polygons_xz_m'])
   if area>1e-7 or length>1e-6:edges.append(dict(a=n['id'],b=m['id'],overlap_area_m2=area,shared_edge_length_m=length))
 write('harbor_interfaces.json',dict(base_scene=ref(a.SCENE_PATH),nodes=nodes,edges=edges,vessels=boats,limits=['Exact native deck graph checks full top faces, not capsule swept clearance or load-bearing engineering.','Deck overlap is reported, never silently deleted or called non-overlap.','Port-to-city road network and main drawbridge north approach are separate canonical road/parent work.']))
 print('nodes',[(r['id'],r['area_m2'])for r in nodes]);print('edges',edges);print('boats',boats)
if __name__=='__main__':run()
