"""Export-only exact edge-adjacency cull for the sealed r10/r13 interfaces.
Shared opposite edges with the same owner or a native-hole neighbor cannot
produce a rendered retaining interface. Unmatched/ambiguous edges retain the
original two-sided owner queries. No geometry quantization is introduced.
"""
import math,hashlib,json,collections
from world_city.concept_city_v3.registered_topography.revisions.r10_density_reservoir import author as base
STATS=collections.Counter()
def retaining_interfaces(bounds,records):
 edges={}
 for r in records:
  p=r['polygon_xz_m']
  for a,b in zip(p,p[1:]+p[:1]):
   if math.dist(a,b)<1e-7:continue
   key=tuple(sorted(tuple(round(v,7) for v in q) for q in (a,b)))
   edges.setdefault(key,[]).append((r,a,b))
 out=[]
 for key,entries in edges.items():
  r,a,b=entries[0];STATS['unique_edges']+=1
  if len(entries)==2:
   s,c,d=entries[1]
   # Geometric opposite sides must agree at actual endpoints, not only rounded keys.
   opposite=math.dist(a,d)<1e-9 and math.dist(b,c)<1e-9
   if opposite and (r['owner_id']==s['owner_id'] or not r.get('render_land',True) or not s.get('render_land',True)):
    STATS['proven_shared_skips']+=1;continue
  L=math.dist(a,b);m=[(a[k]+b[k])/2 for k in (0,1)];n=[-(b[1]-a[1])/L*1e-5,(b[0]-a[0])/L*1e-5]
  os=[base.owner_at(*(m[k]+s*n[k] for k in (0,1))) for s in (1,-1)];STATS['fallback_owner_queries']+=2
  if os[0]['owner_id']==os[1]['owner_id'] or any(not o.get('render_land',True) for o in os):continue
  ys=[[base.surface_height_at(dict(o,review_tile_bounds_xz_m=bounds),*q) for q in (a,b)] for o in os]
  if max(abs(ys[0][i]-ys[1][i]) for i in (0,1))<1e-6:continue
  out.append(dict(id='R10_INTERFACE_'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:18],left_owner_id=os[0]['owner_id'],right_owner_id=os[1]['owner_id'],vertices_xyz_m=[[a[0],ys[0][0],a[1]],[b[0],ys[0][1],b[1]],[b[0],ys[1][1],b[1]],[a[0],ys[1][0],a[1]]],material_hint='stone',thickness_m=.3,collision_semantics='visible finite cut/fill closure; no capsule approval'))
 return out
