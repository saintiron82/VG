"""Shared finite private-route topology and constrained upward surface emitter.

This is a bounded source mesh, never a voxel or city-wide terrain exporter.
All fixed regions are supplied explicitly by the caller. Retaining closures are
separate and must not be counted as walking surfaces.
"""
import math,collections
from .. import author as a,regeneration

def grid_parts(domains,fixed_regions,pitch=1.):
 di=a.geo._SpatialIndex(pitch*4);fi=a.geo._SpatialIndex(pitch*4);cells=set()
 for i,p in enumerate(domains):
  di.add(i,p);x0,z0,x1,z1=a.bounds(p)
  cells.update((x,z)for x in range(math.floor(x0/pitch),math.ceil(x1/pitch))for z in range(math.floor(z0/pitch),math.ceil(z1/pitch)))
 for i,r in enumerate(fixed_regions):fi.add(i,r['polygon_xz_m'])
 pieces=[];checks=[]
 for x,z in sorted(cells):
  cell=[[x*pitch,z*pitch],[(x+1)*pitch,z*pitch],[(x+1)*pitch,(z+1)*pitch],[x*pitch,(z+1)*pitch]];parts=[]
  for j in sorted(di.candidates(cell)):
   q=a.clip(cell,domains[j])
   if q:parts.extend(a.common.subtract([q],parts))
  before=sum(a.geo.polygon_area(p)for p in parts);remaining=parts;assigned=[]
  for j in sorted(fi.candidates(cell)):
   mask=fixed_regions[j]['polygon_xz_m'];new=[]
   for p in remaining:
    q=a.clip(p,mask)
    if q:assigned.append(q)
    new.extend(a.common.subtract([p],[mask]))
   remaining=new
  final=assigned+remaining;after=sum(a.geo.polygon_area(p)for p in final)
  if abs(before-after)>1e-7:raise ValueError('Finite cell partition mismatch')
  pieces.extend(final);checks.append(dict(cell=[x,z],area_m2=before,residual_area_m2=before-after))
 return pieces,checks

def topology(pieces,seam_points=()):
 # Distance-based neighbor buckets avoid round-key disagreement at coincident
 # vertices. The largest measured displacement remains part of the result.
 eps=1e-9;buckets=collections.defaultdict(list);points=[];maxmove=0.
 def vertex(p):
  nonlocal maxmove
  key=tuple(math.floor(v/eps)for v in p)
  candidates=[i for dx in(-1,0,1)for dz in(-1,0,1)for i in buckets[(key[0]+dx,key[1]+dz)]if math.dist(p,points[i])<=eps]
  if candidates:
   i=min(candidates);maxmove=max(maxmove,math.dist(p,points[i]));return i
  i=len(points);points.append(list(p));buckets[key].append(i);return i
 # Stable original points are retained; only near-coincident copies are joined.
 rings=[[vertex(p)for p in poly]for poly in pieces]
 for p in seam_points:vertex(p)
 pi=a.geo._SpatialIndex(2)
 for i,p in enumerate(points):pi.add(i,[p])
 triangles=[];part_areas=[]
 for source,ring in zip(pieces,rings):
  conformed=[]
  for iu,iv in zip(ring,ring[1:]+ring[:1]):
   u,v=points[iu],points[iv];length=math.dist(u,v)
   if length<=eps:continue
   found=[(0.,iu)]
   for j in pi.candidates([u,v]):
    p=points[j];s=sum((p[k]-u[k])*(v[k]-u[k])for k in(0,1))/(length*length)
    if 1e-11<s<1-1e-11 and abs(a.geo._cross(u,v,p))/length<=eps:found.append((s,j))
   for _,j in sorted(found):
    if not conformed or j!=conformed[-1]:conformed.append(j)
  if len(conformed)>1 and conformed[0]==conformed[-1]:conformed.pop()
  if len(conformed)<3:raise ValueError('Lost finite source polygon')
  center=[sum(points[i][k]for i in conformed)/len(conformed)for k in(0,1)];ci=vertex(center);start=len(triangles)
  for u,v in zip(conformed,conformed[1:]+conformed[:1]):
   ar=abs(a.geo._cross(points[ci],points[u],points[v]))/2
   if ar>1e-12:triangles.append([ci,u,v])
  area=sum(abs(a.geo._cross(*[points[i]for i in ids]))/2 for ids in triangles[start:]);expected=a.geo.polygon_area(source)
  if abs(area-expected)>1e-7:raise ValueError('Conformed topology changed source area')
  part_areas.append(dict(expected_area_m2=expected,triangulated_area_m2=area))
 used=sorted({i for tr in triangles for i in tr}); remap={i:j for j,i in enumerate(used)}
 points=[points[i]for i in used];triangles=[[remap[i]for i in tr]for tr in triangles]
 return points,triangles,dict(maximum_vertex_weld_distance_m=maxmove,source_parts=len(pieces),part_area_checks=part_areas)

def solve(domains,fixed_regions,target_y,pitch=1.,limit=.12,seam_points=()):
 parts,cells=grid_parts(domains,fixed_regions,pitch);points,triangles,proof=topology(parts,seam_points);fi=a.geo._SpatialIndex(4)
 for i,r in enumerate(fixed_regions):fi.add(i,r['polygon_xz_m'])
 fixed={};conflicts=[];targets=[]
 for i,p in enumerate(points):
  ys=[a.common.height(r['plane_y_xz_m'],p)for j in fi.candidates([p])if a.geo.point_in_convex_polygon(p,(r:=fixed_regions[j])['polygon_xz_m'],1e-9)]
  if ys and max(ys)-min(ys)>1e-7:conflicts.append(dict(point_xz_m=p,fixed_heights_m=ys))
  if ys:fixed[i]=ys[0]
  targets.append(fixed[i]if i in fixed else target_y(p))
 if conflicts:return dict(status='INCOMPATIBLE_FIXED_REGIONS',conflicts=conflicts,topology_proof=proof,activation=False)
 result=regeneration.solve_field(points,triangles,fixed,targets,limit);result.update(topology_proof=proof,cell_partition_checks=cells,finite_domain_area_m2=sum(r['area_m2']for r in cells),fixed_regions=fixed_regions,activation=False)
 if result['status']=='PASSED_FINITE_TRIANGLE_GRADE':
  result['emitted_upward_triangles']=len(result['triangles']);result['downward_triangles']=sum(a.normal_y(t['vertices_xyz_m'])<=0 for t in result['triangles'])
  if result['downward_triangles']:raise ValueError('Emitter orientation regression')
 return result
