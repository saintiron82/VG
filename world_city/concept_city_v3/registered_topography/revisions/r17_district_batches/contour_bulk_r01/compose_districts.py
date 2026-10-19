"""Finite coherent cluster ownership with atomic retired-body restoration.

Original public road triangles are reserved separately. Flat private owners may
replace obsolete ordinary pads and banks inside their explicit polygons.
"""
import json,math,collections
from .. import author as a,compose_fields as old,side_clearance,regeneration_interfaces as ri
from ..audit_retired_boundaries import interval

def owner_index(owners):
 idx=a.geo._SpatialIndex(16)
 for i,o in enumerate(owners):idx.add(i,o['polygon_xz_m'])
 return idx

class UnownedSourceHole(ValueError):
 def __init__(self,owner,missing,area):
  self.record=dict(owner=owner,missing=missing,area_m2=area)
  super().__init__('Unowned source hole '+owner['id']+' '+str(area))

def build(scene,owners,retirement_records,removed_boxes):
 windows=[o['polygon_xz_m']for o in owners];index=a.TriangleIndex(scene,windows);oi=owner_index(owners);edits=[];appended=collections.defaultdict(list);partitions=[];fieldproof=[]
 for r in index.rows:
  candidates=[owners[i]for i in sorted(oi.candidates(r['polygon_xz_m']))];assigned,remaining=old.classify_parts(r['polygon_xz_m'],candidates)
  if not assigned:continue
  replacement=[t for p in remaining for t in a.fan_upward(old.lift(p,r['plane_y_xz_m']))];owned=sum(a.geo.polygon_area(p)for _,p in assigned);before=a.geo.polygon_area(r['polygon_xz_m']);after=sum(a.normal_y(t)/2 for t in replacement)
  if abs(before-after-owned)>1e-7:raise ValueError('Source partition error')
  edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],replacement_triangles_xyz_m=replacement));partitions.append(dict(material=r['material'],triangle_index=r['triangle_index'],original_area_m2=before,retained_area_m2=after,reowned_area_m2=owned))
 holes=[r['old_terrain_body_hole_polygon_xz_m']for r in retirement_records];hi=a.geo._SpatialIndex(16)
 for i,p in enumerate(holes):hi.add(i,p)
 rendered=[]
 for i,o in enumerate(owners):
  if o['action']=='hole':continue
  p=o['polygon_xz_m'];prior=[owners[j]['polygon_xz_m']for j in sorted(oi.candidates(p))if j<i];parts=a.common.subtract([p],prior)
  if not parts:continue
  covers=[r['intersection_polygon_xz_m']for r in index.covering(p)]+[holes[j]for j in hi.candidates(p)];missing=a.common.subtract(parts,covers);gap=sum(a.geo.polygon_area(q)for q in missing)
  if gap>1e-7:
   raise UnownedSourceHole(o,missing,gap)
  tris=[t for q in parts for t in a.fan_upward(old.lift(q,o['plane_y_xz_m']))];appended[o['material']].extend(v for t in tris for v in t);rendered.extend(dict(id=o['id'],material=o['material'],polygon_xz_m=q,plane_y_xz_m=o['plane_y_xz_m'],kind=o['kind'])for q in parts);fieldproof.append(dict(id=o['id'],area_m2=sum(a.geo.polygon_area(q)for q in parts),triangles=len(tris),unknown_source_area_m2=gap))
 for values in appended.values():
  if any(a.normal_y(values[k:k+3])<=0 for k in range(0,len(values),3)):raise ValueError('Downward new top')
 boxes={r['id']for r in scene['boxes']}
 if not set(removed_boxes)<=boxes:raise ValueError('Missing retired foundation proxy')
 return dict(schema='riverstone.frozen_scene_patch.v1',id='R17_EFFECTIVE_DISTRICT_BATCH',status='CANDIDATE_PENDING_SIDE_AND_PUBLIC_GATES',base_scene_sha256=a.SCENE_SHA256,source_surface_hashes={m:a.canonical_sha(scene['surfaces'][m])for m in sorted({r['material']for r in edits})},surface_edits=edits,appended_surfaces=dict(appended),removed_foundation_proxy_ids=removed_boxes),dict(source_partitions=partitions,fields=fieldproof,rendered_owner_parts=rendered),index

def subtract_side(tri,poly):
 sign=1 if a.geo.signed_polygon_area(poly)>0 else-1;inside=tri;outside=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  fn=lambda v:sign*a.geo._cross(p,q,[v[0],v[2]])
  # Boundary walls belong to the explicit regenerated closure, so retire the
  # coincident original face as well instead of emitting duplicate solids.
  if all(abs(fn(v))<1e-9 for v in inside):continue
  cut=ri.clean3(side_clearance.halfspace(inside,lambda v:-fn(v)))
  if cut:outside.append(cut)
  inside=ri.clean3(side_clearance.halfspace(inside,fn))
  if not inside:break
 return outside,inside

def interfaces(scene,index,logical,outside_owners=()):
 """Retire finite sides, then close only actual outer or cross-level edges."""
 outside_index=owner_index(outside_owners)
 oi=owner_index(logical);sides=side_clearance.SideIndex(scene,[o['polygon_xz_m']for o in logical]);edits=[];removed=[]
 for r in sides.rows:
  remaining=[r['vertices_xyz_m']];cuts=[];candidates=sorted(oi.candidates(r['projection_xz_m']))
  for j in candidates:
   nextparts=[]
   for p in remaining:
    outside,inside=subtract_side(p,logical[j]['polygon_xz_m']);nextparts.extend(outside)
    if inside:cuts.append(inside)
   remaining=nextparts
  ar=sum(side_clearance.area3d(p)for p in cuts)
  if ar<1e-9:continue
  replacement=[[p[0],p[k],p[k+1]]for p in remaining for k in range(1,len(p)-1)];before=side_clearance.area3d(r['vertices_xyz_m']);after=sum(side_clearance.area3d(p)for p in replacement)
  if abs(before-after-ar)>1e-6:raise ValueError('Side partition mismatch')
  edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],replacement_triangles_xyz_m=replacement));removed.append(dict(material=r['material'],triangle_index=r['triangle_index'],removed_area_m2=ar))
 def owner_at(p):
  for j in sorted(oi.candidates([p])):
   o=logical[j]
   if a.geo.point_in_convex_polygon(p,o['polygon_xz_m'],1e-10):return j,o['plane_y_xz_m']
  for j in sorted(outside_index.candidates([p])):
   r=outside_owners[j]
   if a.geo.point_in_convex_polygon(p,r['polygon_xz_m'],1e-10):return ('accepted_adjacent_owner',r['id']),r['plane_y_xz_m']
  for j in index.index.candidates([p]):
   r=index.rows[j]
   if a.geo.point_in_convex_polygon(p,r['polygon_xz_m'],1e-10):return ('source',r['material'],r['triangle_index']),r['plane_y_xz_m']
  return None,None
 seams=[];new=[];unknown=[];seen=set()
 for i,o in enumerate(logical):
  poly=o['polygon_xz_m'];sgn=1 if a.geo.signed_polygon_area(poly)>0 else-1
  for p,q in zip(poly,poly[1:]+poly[:1]):
   L=math.dist(p,q)
   if L<1e-8:continue
   n=[sgn*(q[1]-p[1])/L,sgn*(p[0]-q[0])/L];knots={0.,1.}
   for j in oi.candidates([p,q]):
    span=interval(p,q,logical[j]['polygon_xz_m'])
    if span:knots.update(span)
   for j in index.index.candidates([p,q]):
    span=interval(p,q,index.rows[j]['polygon_xz_m'])
    if span:knots.update(span)
   knots=sorted(knots)
   for lo,hi in zip(knots,knots[1:]):
    if (hi-lo)*L<1e-7:continue
    mid=[p[k]+(lo+hi)/2*(q[k]-p[k])for k in(0,1)];inside=[mid[k]-n[k]*1e-5 for k in(0,1)];outside=[mid[k]+n[k]*1e-5 for k in(0,1)];own,ip=owner_at(inside);other,op=owner_at(outside)
    if own!=i:continue
    e=[[p[k]+t*(q[k]-p[k])for k in(0,1)]for t in(lo,hi)]
    key=tuple(sorted(tuple(round(v,7)for v in x)for x in e))
    if key in seen:continue
    seen.add(key)
    if op is None:unknown.append(dict(owner_id=o['id'],edge_xz_m=e));continue
    ys=[a.common.height(ip,x)for x in e];zs=[a.common.height(op,x)for x in e];delta=max(abs(y-z)for y,z in zip(ys,zs));seams.append(dict(owner_id=o['id'],other_owner=other,edge_xz_m=e,owned_y_m=ys,outside_y_m=zs,maximum_delta_m=delta,kind='continuous'if delta<1e-7 else'nonwalking_retaining'))
    if delta<1e-7:continue
    v=[[e[0][0],ys[0],e[0][1]],[e[1][0],ys[1],e[1][1]],[e[1][0],zs[1],e[1][1]],[e[0][0],zs[0],e[0][1]]]
    for tr in [[v[0],v[1],v[2]],[v[0],v[2],v[3]]]:
     if side_clearance.area3d(tr)>1e-10:new.append(tr)
 return dict(side_surface_edits=edits,retired_sides=removed,appended_retaining_triangles_xyz_m=new,boundary_seams=seams,unknown_exterior_segments=unknown)
