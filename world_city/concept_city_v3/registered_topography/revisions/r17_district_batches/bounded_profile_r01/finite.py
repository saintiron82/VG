"""Distance-normalized fixed-owner containment for bounded finite profiles.

This local version leaves all previous helpers and sealed fields untouched.
The tolerance is measured in metres, independent of source polygon edge length.
"""
import math
from .. import author as a,regeneration
from ..contour_bulk_r01 import profile_mesh

def inside(point,poly,eps=1e-9):
 if len(poly)<3 or a.geo.polygon_area(poly)<=1e-12:return False
 sign=1 if a.geo.signed_polygon_area(poly)>0 else -1
 for u,v in zip(poly,poly[1:]+poly[:1]):
  length=math.dist(u,v)
  if length<=1e-12:continue
  if sign*a.geo._cross(u,v,point)/length < -eps:return False
 return True

def solve(domains,fixed_regions,target_y,pitch=.5,limit=.12,seam_points=()):
 omitted=[r for r in fixed_regions if a.geo.polygon_area(r['polygon_xz_m'])<=1e-12]
 fixed_regions=[r for r in fixed_regions if a.geo.polygon_area(r['polygon_xz_m'])>1e-12]
 parts,cells=profile_mesh.grid_parts(domains,fixed_regions,pitch);points,triangles,proof=profile_mesh.topology(parts,seam_points);fi=a.geo._SpatialIndex(4)
 for i,r in enumerate(fixed_regions):fi.add(i,r['polygon_xz_m'])
 fixed={};conflicts=[];targets=[]
 for i,p in enumerate(points):
  hits=[r for j in sorted(fi.candidates([p]))if inside(p,(r:=fixed_regions[j])['polygon_xz_m'])];ys=[a.common.height(r['plane_y_xz_m'],p)for r in hits]
  if ys and max(ys)-min(ys)>1e-7:conflicts.append(dict(point_xz_m=p,fixed_heights_m=ys,fixed_region_ids=[r['id']for r in hits]))
  if ys:fixed[i]=ys[0]
  targets.append(fixed[i]if i in fixed else target_y(p))
 if conflicts:return dict(status='INCOMPATIBLE_FIXED_REGIONS',conflicts=conflicts,topology_proof=proof,zero_area_fixed_regions=omitted,activation=False)
 result=regeneration.solve_field(points,triangles,fixed,targets,limit);result.update(topology_proof=proof,cell_partition_checks=cells,finite_domain_area_m2=sum(r['area_m2']for r in cells),fixed_regions=fixed_regions,zero_area_fixed_regions=omitted,activation=False)
 if result['status']=='PASSED_FINITE_TRIANGLE_GRADE':
  result['emitted_upward_triangles']=len(result['triangles']);result['downward_triangles']=sum(a.normal_y(t['vertices_xyz_m'])<=0 for t in result['triangles'])
  if result['downward_triangles']:raise ValueError('Emitter orientation regression')
 return result
