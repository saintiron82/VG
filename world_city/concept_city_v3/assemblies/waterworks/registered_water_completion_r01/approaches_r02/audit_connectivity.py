"""Exact same-height shared-edge graph for the finite approach/deck network."""
import json,math,collections
from . import select_profiles as s,finite
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.runtime_city.checks import placement as g
HERE=s.HERE

def run():
 doc=json.loads((HERE/'fields.json').read_text());profiles=doc['profiles'];fields=[dict(t,owner_id=p['id'])for p in profiles for t in p['triangles']];bridges=json.loads((HERE.parent/'crossing_interfaces.json').read_text())['crossings'];ix=g._SpatialIndex(8);adj=collections.defaultdict(set);bad=[];edges=[]
 for i,t in enumerate(fields):ix.add(i,t['polygon_xz_m'])
 for i,t in enumerate(fields):
  for u,v in zip(t['polygon_xz_m'],t['polygon_xz_m'][1:]+t['polygon_xz_m'][:1]):
   L=math.dist(u,v)
   if L<1e-9:continue
   for j in ix.candidates([u,v]):
    if j<=i:continue
    other=fields[j];span=finite.interval(u,v,other['polygon_xz_m'])
    if not span or L*(span[1]-span[0])<1e-7:continue
    points=[[u[k]+x*(v[k]-u[k])for k in(0,1)]for x in span];delta=max(abs(a.common.height(t['plane_y_xz_m'],p)-a.common.height(other['plane_y_xz_m'],p))for p in points)
    if delta>1e-6:bad.append(dict(first=i,second=j,length_m=L*(span[1]-span[0]),maximum_seam_delta_m=delta));continue
    adj[i].add(j);adj[j].add(i);edges.append(dict(first=i,second=j,length_m=L*(span[1]-span[0]),maximum_seam_delta_m=delta))
 for k,b in enumerate(bridges):
  node=len(fields)+k
  for seam in b['approach_seams']:
   e=[[v[0],v[2]]for v in seam['xyz_m']];L=math.dist(*e)
   for i in ix.candidates(e):
    t=fields[i];span=finite.interval(*e,t['polygon_xz_m'])
    if not span or L*(span[1]-span[0])<1e-7:continue
    pts=[[e[0][j]+u*(e[1][j]-e[0][j])for j in(0,1)]for u in span];delta=max(abs(a.common.height(t['plane_y_xz_m'],p)-b['deck_top_y_m'])for p in pts)
    if delta>1e-6:bad.append(dict(first=i,native=b['id'],maximum_seam_delta_m=delta));continue
    adj[i].add(node);adj[node].add(i)
 remaining=set(range(len(fields)+len(bridges)));components=[]
 while remaining:
  seed=min(remaining);remaining.remove(seed);members={seed};queue=[seed]
  while queue:
   node=queue.pop()
   for j in adj[node]&remaining:remaining.remove(j);members.add(j);queue.append(j)
  components.append(dict(triangle_count=sum(i<len(fields)for i in members),triangle_area_m2=sum(g.polygon_area(fields[i]['polygon_xz_m'])for i in members if i<len(fields)),field_ids=sorted({fields[i]['owner_id']for i in members if i<len(fields)}),native_bridges=sorted(bridges[i-len(fields)]['id']for i in members if i>=len(fields)),node_indices=sorted(members)))
 expected=[{'MARKET_NORTH','NORTH_BACK_LANE'},{'EAST_RADIAL','EAST_WALL_SERVICE'}];passed=not bad and len(components)==2 and all(any(set(c['native_bridges'])==x for c in components)for x in expected)
 # Every accepted named-road ribbon piece inside the bounded approach interval
 # must be owned by a road field or the exact native deck, without road slivers.
 masks=[q for p in profiles for q in p['polygons_xz_m']]+[b['native_ownership_polygon_xz_m']for b in bridges];semantic=[]
 for p in profiles:
  for i,q in enumerate(p.get('named_road_semantic_parts_xz_m',[])):
   miss=sum(g.polygon_area(x)for x in finite.subtract([q],masks));semantic.append(dict(field_id=p['id'],piece=i,unowned_named_road_area_m2=miss))
 passed=passed and all(r['unowned_named_road_area_m2']<1e-7 for r in semantic)
 s.write('connectivity_audit.json',dict(schema='riverstone.water_approach_edge_connectivity.r02',base_scene_sha256=a.SCENE_SHA256,fields_sha256=a.sha(HERE/'fields.json'),status='PASS'if passed else'FAIL',components=components,shared_edge_count=len(edges),maximum_shared_edge_delta_m=max((e['maximum_seam_delta_m']for e in edges),default=0),incompatible_edges=bad,named_road_coverage=semantic,continuation_limit='These are two local crossing networks. Parent R18 must bind the five exact outer public profiles to the canonical city network; this graph does not claim that continuation or controller traversal.'))
 print('CONNECTIVITY',passed,[(c['triangle_count'],c['native_bridges'])for c in components],'bad',len(bad),'unowned',max((r['unowned_named_road_area_m2']for r in semantic),default=0),flush=True)
if __name__=='__main__':run()
