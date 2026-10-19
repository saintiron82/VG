"""Indexed execution of the existing finite retaining-edge construction.

Exact paired continuous interior edges need no retaining face. Bounding boxes
reject only disjoint candidates; all surviving clipping uses the existing
common geometry helpers. This is placement orchestration, not a new mesher.
"""
import math,time
from ...registered_topography.revisions.r17_district_batches.contour_bulk_r01 import compose_districts as c
a=c.a;side_clearance=c.side_clearance
def bounds(p):return(min(v[0]for v in p),min(v[1]for v in p),max(v[0]for v in p),max(v[1]for v in p))
def overlap(b,d):return not(b[2]<d[0]-1e-9 or d[2]<b[0]-1e-9 or b[3]<d[1]-1e-9 or d[3]<b[1]-1e-9)
def key(p,q):return tuple(sorted((tuple(p),tuple(q))))
def width(p):
 values=[max(abs(a.geo._cross(u,v,x))for x in p)/math.dist(u,v)for u,v in zip(p,p[1:]+p[:1])if math.dist(u,v)>1e-12]
 return min(values)if values else 0.
def fine_index(rows):
 idx=a.geo._SpatialIndex(4)
 for i,r in enumerate(rows):idx.add(i,r['polygon_xz_m'])
 return idx
def empty_inward_probe_proof(poly):
 """Prove the existing 10 µm inward query cannot return this owner.

 A separating half-space excludes both endpoints of the entire translated
 edge. Its linearity then excludes every subdivision, not just its midpoint.
 """
 sgn=1 if a.geo.signed_polygon_area(poly)>0 else-1;proof=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  L=math.dist(p,q)
  if L<1e-8:continue
  n=[sgn*(q[1]-p[1])/L,sgn*(p[0]-q[0])/L];shifted=[[x[k]-n[k]*1e-5 for k in(0,1)]for x in(p,q)];witness=None
  for j,(u,v)in enumerate(zip(poly,poly[1:]+poly[:1])):
   length=math.dist(u,v)
   if length<=a.geo.NUMERIC_EPSILON:continue
   upper=max(sgn*a.geo._cross(u,v,x)/length for x in shifted)
   if upper < -1e-10-a.geo.NUMERIC_EPSILON:
    witness=dict(separating_edge=j,maximum_signed_distance_m=upper);break
  if witness is None:return None
  proof.append(dict(edge_xz_m=[p,q],**witness))
 return proof
def interfaces(scene,index,logical,outside_owners=()):
 start=time.monotonic();outside_index=c.owner_index(outside_owners);oi=c.owner_index(logical);ob=[bounds(o['polygon_xz_m'])for o in logical];xb=[bounds(o['polygon_xz_m'])for o in outside_owners];sb=[bounds(o['polygon_xz_m'])for o in index.rows]
 sides=side_clearance.SideIndex(scene,[o['polygon_xz_m']for o in logical]);edits=[];removed=[]
 print('Indexed side rows',len(sides.rows),'seconds',time.monotonic()-start,flush=True)
 for ri,r in enumerate(sides.rows):
  remaining=[r['vertices_xyz_m']];cuts=[];bb=bounds(r['projection_xz_m'])
  for j in sorted(oi.candidates(r['projection_xz_m'])):
   if not overlap(bb,ob[j]):continue
   nextparts=[]
   for p in remaining:
    outside,inside=c.subtract_side(p,logical[j]['polygon_xz_m']);nextparts.extend(outside)
    if inside:cuts.append(inside)
   remaining=nextparts
   if not remaining:break
  ar=sum(side_clearance.area3d(p)for p in cuts)
  if ar>=1e-9:
   replacement=[[p[0],p[k],p[k+1]]for p in remaining for k in range(1,len(p)-1)];before=side_clearance.area3d(r['vertices_xyz_m']);after=sum(side_clearance.area3d(p)for p in replacement)
   if abs(before-after-ar)>1e-6:raise ValueError('Side partition mismatch')
   edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],replacement_triangles_xyz_m=replacement));removed.append(dict(material=r['material'],triangle_index=r['triangle_index'],removed_area_m2=ar))
  if ri and ri%2000==0:print('Retired side progress',ri,'of',len(sides.rows),'seconds',time.monotonic()-start,flush=True)
 # All owners remain in authoritative queries. Skip an owner's edge walk only
 # when a half-space proof excludes every possible original inward probe.
 tiny=[];probe_empty=set()
 for i,o in enumerate(logical):
  w=width(o['polygon_xz_m'])
  if w>1e-9:continue
  proof=empty_inward_probe_proof(o['polygon_xz_m'])
  if proof is not None:
   probe_empty.add(i);tiny.append(dict(id=o['id'],area_m2=a.geo.polygon_area(o['polygon_xz_m']),width_m=w,edge_proofs=proof))
 oi=fine_index(logical);outside_index=fine_index(outside_owners);source_index=fine_index(index.rows);ob=[bounds(o['polygon_xz_m'])for o in logical]
 def owner_at(p):
  bb=(p[0],p[1],p[0],p[1])
  for j in sorted(oi.candidates([p])):
   if overlap(bb,ob[j])and a.geo.point_in_convex_polygon(p,logical[j]['polygon_xz_m'],1e-10):return j,logical[j]['plane_y_xz_m']
  for j in sorted(outside_index.candidates([p])):
   r=outside_owners[j]
   if overlap(bb,xb[j])and a.geo.point_in_convex_polygon(p,r['polygon_xz_m'],1e-10):return ('accepted_adjacent_owner',r['id']),r['plane_y_xz_m']
  for j in source_index.candidates([p]):
   r=index.rows[j]
   if overlap(bb,sb[j])and a.geo.point_in_convex_polygon(p,r['polygon_xz_m'],1e-10):return ('source',r['material'],r['triangle_index']),r['plane_y_xz_m']
  return None,None
 edgeowners={}
 for i,o in enumerate(logical):
  if i in probe_empty:continue
  p=o['polygon_xz_m']
  for u,v in zip(p,p[1:]+p[:1]):edgeowners.setdefault(key(u,v),[]).append(i)
 internal=set()
 for e,ids in edgeowners.items():
  if len(ids)!=2:continue
  i,j=ids;u,v=e;p,q=logical[i],logical[j]
  if max(abs(a.common.height(p['plane_y_xz_m'],x)-a.common.height(q['plane_y_xz_m'],x))for x in e)>1e-9:continue
  pi=p['polygon_xz_m'];pj=q['polygon_xz_m'];ci=[sum(x[k]for x in pi)/len(pi)for k in(0,1)];cj=[sum(x[k]for x in pj)/len(pj)for k in(0,1)]
  if a.geo._cross(u,v,ci)*a.geo._cross(u,v,cj)>=0:continue
  L=math.dist(u,v)
  if L<=1e-8:continue
  mid=[(u[k]+v[k])/2 for k in(0,1)];n=[(v[1]-u[1])/L*1e-5,-(v[0]-u[0])/L*1e-5]
  actual={owner_at([mid[k]+s*n[k]for k in(0,1)])[0]for s in(-1,1)}
  if actual=={i,j}:internal.add(e)
 print('Matched continuous interior edges',len(internal),'seconds',time.monotonic()-start,flush=True)
 seams=[];new=[];unknown=[];seen=set();skipped=0
 for i,o in enumerate(logical):
  if i in probe_empty:continue
  poly=o['polygon_xz_m'];sgn=1 if a.geo.signed_polygon_area(poly)>0 else-1
  for p,q in zip(poly,poly[1:]+poly[:1]):
   if key(p,q)in internal:skipped+=1;continue
   L=math.dist(p,q)
   if L<1e-8:continue
   n=[sgn*(q[1]-p[1])/L,sgn*(p[0]-q[0])/L];knots={0.,1.};bb=bounds([p,q])
   for j in oi.candidates([p,q]):
    if not overlap(bb,ob[j]):continue
    span=c.interval(p,q,logical[j]['polygon_xz_m'])
    if span:knots.update(span)
   for j in source_index.candidates([p,q]):
    if not overlap(bb,sb[j]):continue
    span=c.interval(p,q,index.rows[j]['polygon_xz_m'])
    if span:knots.update(span)
   knots=sorted(knots)
   for lo,hi in zip(knots,knots[1:]):
    if(hi-lo)*L<1e-7:continue
    mid=[p[k]+(lo+hi)/2*(q[k]-p[k])for k in(0,1)];own,ip=owner_at([mid[k]-n[k]*1e-5 for k in(0,1)]);other,op=owner_at([mid[k]+n[k]*1e-5 for k in(0,1)])
    if own!=i:continue
    e=[[p[k]+t*(q[k]-p[k])for k in(0,1)]for t in(lo,hi)];ek=tuple(sorted(tuple(round(v,7)for v in x)for x in e))
    if ek in seen:continue
    seen.add(ek)
    if op is None:unknown.append(dict(owner_id=o['id'],edge_xz_m=e));continue
    ys=[a.common.height(ip,x)for x in e];zs=[a.common.height(op,x)for x in e];delta=max(abs(y-z)for y,z in zip(ys,zs));seams.append(dict(owner_id=o['id'],other_owner=other,edge_xz_m=e,owned_y_m=ys,outside_y_m=zs,maximum_delta_m=delta,kind='continuous'if delta<1e-7 else'nonwalking_retaining'))
    if delta<1e-7:continue
    v=[[e[0][0],ys[0],e[0][1]],[e[1][0],ys[1],e[1][1]],[e[1][0],zs[1],e[1][1]],[e[0][0],zs[0],e[0][1]]]
    for tr in [[v[0],v[1],v[2]],[v[0],v[2],v[3]]]:
     if side_clearance.area3d(tr)>1e-10:new.append(tr)
  if i and i%2000==0:print('Boundary owners',i,'of',len(logical),'unknown',len(unknown),'seconds',time.monotonic()-start,flush=True)
 return dict(side_surface_edits=edits,retired_sides=removed,appended_retaining_triangles_xyz_m=new,boundary_seams=seams,unknown_exterior_segments=unknown,indexed_execution=dict(exact_continuous_edge_pairs=len(internal),omitted_continuous_halfedges=skipped,proved_empty_inward_probe_owners=tiny,proved_empty_inward_probe_area_m2=sum(r['area_m2']for r in tiny),authoritative_owners_removed=0,rendered_or_collision_triangles_removed=0,seconds=time.monotonic()-start))
