"""Stage shared private-route groups across all 14 unactivated districts."""
import json,time,collections,math
from .screen import HERE,write
from .. import author as a,public_tails

def run():
 start=time.monotonic();layouts=[json.loads((p/'combined_source_layout.json').read_bytes())for p in(HERE,a.HERE/'remaining_level_r01')];holdings=[h for l in layouts for h in l['holdings']];parent={h['id']:h['id']for h in holdings};rows=[];idx=a.geo._SpatialIndex(16)
 def root(x):
  while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
  return x
 def join(x,y):
  x,y=root(x),root(y)
  if x!=y:parent[max(x,y)]=min(x,y)
 for h in holdings:
  for p in h['external_route_polygons_xz_m']:
   for j in idx.candidates(p):
    other,q=rows[j]
    if other==h['id']:continue
    hit=a.clip(p,q)
    if hit and a.geo.polygon_area(hit)>1e-7:join(h['id'],other)
   idx.add(len(rows),p);rows.append((h['id'],p))
 # A route entering a different owned court must share that court's datum.
 for h in holdings:
  for j in idx.candidates(h['holding_polygon_xz_m']):
   other,q=rows[j]
   if other==h['id']:continue
   hit=a.clip(h['holding_polygon_xz_m'],q)
   if hit and a.geo.polygon_area(hit)>1e-7:join(h['id'],other)
 traffic=[];ti=a.geo._SpatialIndex(16)
 for r in json.loads(a.PLAN_PATH.read_bytes())['roads']:
  for p in[a.geo.road_ribbon(u,v,r['width_m'])for u,v in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])]+[public_tails.circle(q,r['width_m']/2)for q in r['polyline_xz_m'][1:-1]]:ti.add(len(traffic),p);traffic.append(p)
 groups=collections.defaultdict(list)
 for h in holdings:groups[root(h['id'])].append(h)
 result=[]
 for key,hs in sorted(groups.items()):
  parts=[]
  for h in hs:
   for p in h['external_route_polygons_xz_m']:parts.extend(a.common.subtract([p],[traffic[j]for j in sorted(ti.candidates(p))]))
  domains=a.common.disjoint_union(parts)
  result.append(dict(id='PRIVATE_GROUP:'+key,holding_ids=[h['id']for h in hs],source_private_route_polygons_xz_m=domains,private_area_m2=sum(a.geo.polygon_area(p)for p in domains),gate_fixed_regions=[dict(id=h['id']+':COURT_DATUM',polygon_xz_m=h['holding_polygon_xz_m'],plane_y_xz_m=[0,0,h['floor_y_m']])for h in hs],gate_targets=[dict(holding_id=h['id'],point_xz_m=h['gate_position_xz_m'],floor_y_m=h['floor_y_m'])for h in hs],source_holding_records=hs,status='TOPOLOGY_PREPARATION_ONLY_PUBLIC_FIELD_PENDING'))
 out=dict(schema='riverstone.r17.shared_private_profile_groups.v1',base_scene_sha256=a.SCENE_SHA256,source_references=[dict(path=str((p/'combined_source_layout.json').relative_to(a.ROOT)),sha256=a.sha(p/'combined_source_layout.json'))for p in(HERE,a.HERE/'remaining_level_r01')],groups=result,summary=dict(holdings=len(holdings),groups=len(result),multi_holding_groups=sum(len(r['holding_ids'])>1 for r in result),private_area_m2=sum(r['private_area_m2']for r in result),elapsed_s=time.monotonic()-start),policy='Canonical traffic remains public. Final private domains must also subtract the exact accepted R18 public/junction domains; shared public edge knots will be added only after its actual triangles pass. All shared private branches use a single field.',activation=False)
 write('shared_private_groups.json',out);print(out['summary'],flush=True)
if __name__=='__main__':run()
