"""Finite old-side retirement and new retaining closure for a source field."""
import math,collections
from . import author as a,side_clearance
from .audit_retired_boundaries import interval

def clean3(poly):
 out=[]
 for p in poly:
  if not out or math.dist(p,out[-1])>1e-10:out.append(p)
 if len(out)>1 and math.dist(out[0],out[-1])<1e-10:out.pop()
 return out if side_clearance.area3d(out)>1e-10 else[]
def subtract_plan(triangle,polygon):
 sign=1 if a.geo.signed_polygon_area(polygon)>0 else-1;inside=triangle;outside=[]
 for p,q in zip(polygon,polygon[1:]+polygon[:1]):
  fn=lambda v:sign*a.geo._cross(p,q,[v[0],v[2]])
  cut=clean3(side_clearance.halfspace(inside,lambda v:-fn(v)))
  # A face wholly on this boundary belongs to the unchanged exterior.
  if cut and all(abs(fn(v))<1e-10 for v in inside):return[triangle],[]
  if cut:outside.append(cut)
  inside=clean3(side_clearance.halfspace(inside,fn))
  if not inside:break
 return outside,inside

def build(scene,index,profile):
 poly=profile['polygon_xz_m'];fields=profile['triangles'];sides=side_clearance.SideIndex(scene,[poly]);edits=[];retired=[]
 for r in sides.rows:
  outside,inside=subtract_plan(r['vertices_xyz_m'],poly)
  if not inside:continue
  area=side_clearance.area3d(inside)
  if area<=1e-9:continue
  replacement=[[p[0],p[j],p[j+1]]for p in outside for j in range(1,len(p)-1)];before=side_clearance.area3d(r['vertices_xyz_m']);after=sum(side_clearance.area3d(t)for t in replacement)
  if abs(before-after-area)>1e-7:raise ValueError('Finite side partition mismatch')
  edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],replacement_triangles_xyz_m=replacement));retired.append(dict(material=r['material'],triangle_index=r['triangle_index'],removed_area_m2=area,removed_polygon_xyz_m=inside))
 edgeowners=collections.defaultdict(list)
 for field in fields:
  tri=field['vertices_xyz_m']
  for p,q in zip(tri,tri[1:]+tri[:1]):edgeowners[tuple(sorted((tuple(p),tuple(q))))].append(field)
 new_sides=[];seams=[];uncovered=[];sign=1 if a.geo.signed_polygon_area(poly)>0 else-1
 for key,owners in edgeowners.items():
  if len(owners)!=1:continue
  p,q=[list(v)for v in key];xz=[[v[0],v[2]]for v in(p,q)];L=math.dist(*xz);mid=[sum(v[k]for v in xz)/2 for k in(0,1)];delta=[(xz[1][1]-xz[0][1])/L*1e-5,-(xz[1][0]-xz[0][0])/L*1e-5];probe=[mid[k]+delta[k]for k in(0,1)]
  if a.geo.point_in_convex_polygon(probe,poly,1e-10):p,q=q,p;xz=xz[::-1];delta=[-v for v in delta]
  # p->q now has the field on its left, exterior on its right.
  spans=[]
  for j in index.index.candidates(xz):
   row=index.rows[j];span=interval(*xz,row['polygon_xz_m'])
   if not span:continue
   t=sum(span)/2;probe=[xz[0][k]+t*(xz[1][k]-xz[0][k])+delta[k]for k in(0,1)]
   if not a.geo.point_in_convex_polygon(probe,row['polygon_xz_m'],1e-10):continue
   spans.append(span)
   top=[[p[k]+t*(q[k]-p[k])for k in range(3)]for t in span];bottom=[[v[0],a.common.height(row['plane_y_xz_m'],[v[0],v[2]]),v[2]]for v in top];quad=[top[0],top[1],bottom[1],bottom[0]];ar=side_clearance.area3d(quad)
   seams.append(dict(edge_xyz_m=top,old_edge_xyz_m=bottom,source_material=row['material'],source_triangle_index=row['triangle_index'],maximum_delta_m=max(abs(v[1]-w[1])for v,w in zip(top,bottom)),closure_kind='finite_nonwalking_retaining'if ar>1e-9 else'exact_walkable_shared_seam'))
   if ar>1e-9:new_sides.extend([[quad[0],quad[1],quad[2]],[quad[0],quad[2],quad[3]]])
  covered=0.;end=0.
  for lo,hi in sorted(spans):
   if hi>end:covered+=hi-max(lo,end);end=hi
  if (1-covered)*L>1e-6:uncovered.append(dict(edge_xyz_m=[p,q],uncovered_length_m=(1-covered)*L))
 changes=[]
 for field in fields:
  for row in index.covering(field['polygon_xz_m']):
   vals=[a.common.height(field['plane_y_xz_m'],p)-a.common.height(row['plane_y_xz_m'],p)for p in row['intersection_polygon_xz_m']];changes.append(dict(source_material=row['material'],source_triangle_index=row['triangle_index'],polygon_xz_m=row['intersection_polygon_xz_m'],minimum_delta_m=min(vals),maximum_delta_m=max(vals)))
 return dict(schema='riverstone.r17.field_support_interfaces.v1',id=profile['id'],base_scene_sha256=a.SCENE_SHA256,side_surface_edits=edits,retired_side_pieces=retired,appended_retaining_triangles_xyz_m=[t for t in new_sides if side_clearance.area3d(t)>1e-10],boundary_seams=seams,uncovered_boundary_segments=uncovered,source_height_changes=changes,maximum_fill_m=max((r['maximum_delta_m']for r in changes),default=0.),maximum_cut_m=max((-r['minimum_delta_m']for r in changes),default=0.),status='SOURCE_CLOSURE_COMPLETE'if not uncovered else'HELD_MISSING_EXTERIOR_SUPPORT',activation=False)
