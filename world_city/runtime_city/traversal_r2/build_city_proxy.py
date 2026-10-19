#!/usr/bin/env python3
"""Build finite exact-grade tile proxies, preserving every realized body void.

This is an optional collision adapter only, not a visual or voxel mesher.
"""
import argparse,json,math,sys
from pathlib import Path
import prepare as base
ROOT=base.ROOT;HERE=base.HERE
sys.path.insert(0,str(ROOT))
from world_city.runtime_city.topography import author as a

def bbox(poly):return [min(v[0] for v in poly),min(v[1] for v in poly),max(v[0] for v in poly),max(v[1] for v in poly)]
def overlap(b,c):return b[0]<c[2]-1e-8 and c[0]<b[2]-1e-8 and b[1]<c[3]-1e-8 and c[1]<b[3]-1e-8

def build(plan_path,infra_path,out):
 plan=base.read(plan_path);infra=base.read(infra_path);original={p['id']:p for p in infra['placements']}
 field=a.GradeField(plan['regions']);footprints=[(p['id'],a._convex(p['body_footprint_xz_m']),bbox(p['body_footprint_xz_m'])) for p in plan['building_footing_contracts']]
 assets={};placements=[];validation=[];all_triangles=0;total_area=0.;cut_area=0.;all_height_error=0.;all_void_error=0.
 for chunk in plan['chunks']:
  ident=chunk['id'];bounds=chunk['bounds_xz_m'];source=original[ident]
  # Every current graded tile is north of the river. Future river intersections
  # are rejected, not silently bridged by a broad tile proxy.
  if source['spec'].get('river_polygons_xz_m'):raise ValueError('River-intersecting tile needs explicitly reviewed polygon subtraction: '+ident)
  holes=[(id,poly) for id,poly,b in footprints if overlap(bounds,b)]
  triangles=[];surface_area=0.;source_area=0.;carved=0.;height_error=0.;void_error=0.
  for facet in field.facets(a._rect(bounds)):
   source_area+=abs(a._area(facet['polygon_xz_m']));pieces=[facet['polygon_xz_m']]
   for id,hole in holes:
    pieces=[piece for poly in pieces for piece in a._subtract_convex(poly,a._inside_planes(hole))]
   plane=facet['plane']
   for poly in pieces:
    surface_area+=abs(a._area(poly));verts=[[x,a._eval(plane,x,z),z] for x,z in poly]
    for i in range(1,len(verts)-1):
     triangle=[verts[0],verts[i],verts[i+1]]
     signed=((triangle[1][0]-triangle[0][0])*(triangle[2][2]-triangle[0][2])-(triangle[1][2]-triangle[0][2])*(triangle[2][0]-triangle[0][0]))/2
     if signed<=1e-10:continue
     center=[sum(v[j] for v in triangle)/3 for j in range(3)]
     height_error=max(height_error,abs(center[1]-field.height(center[0],center[2])))
     if height_error>1e-7:raise ValueError('Triangle left its source facet')
     # Exact convex polygon intersection proves no triangle covers a body void.
     tri_xz=[[v[0],v[2]] for v in triangle]
     for id,hole in holes:
      cross=a._intersect(tri_xz,a._inside_planes(hole))
      void_error=max(void_error,abs(a._area(cross)) if cross else 0.)
      if void_error>1e-7:raise ValueError('Proxy filled source body void '+id)
     triangles.append(triangle)
  actual_area=sum(abs((t[1][0]-t[0][0])*(t[2][2]-t[0][2])-(t[1][2]-t[0][2])*(t[2][0]-t[0][0]))/2 for t in triangles)
  if abs(actual_area-surface_area)>1e-6:raise ValueError('Triangulated surface area mismatch')
  carved=source_area-surface_area
  key='SOURCE_GRADE_'+ident.replace(':','_');path=out/'tiles'/(key+'.json')
  proxy={'schema':'riverstone.city.source_grade_collision_proxy.v1','bounds_xz_m':bounds,'triangles':triangles,
     'source_ground_id':ident,'source_plan_sha256':base.digest(plan_path),'excluded_body_ids':[id for id,_ in holes],
     'source_owned_area_m2':source_area,'public_surface_area_m2':surface_area,'body_void_area_m2':carved,
     'optional_collision_only':True,'visual_meshes_changed':False,'authored_steps_changed':False}
  if not triangles:validation.append({'source_ground_id':ident,'empty_after_source_voids':True});continue
  base.write(path,proxy);assets[key]={'render_path':str(path.relative_to(ROOT)),'render_sha256':base.digest(path),
     'collision_format':'source_grade_proxy_triangles','triangle_count':len(triangles),'bounds_xz_m':bounds}
  placements.append({'id':'PROXY:'+ident,'asset_key':key,'position_m':[0,0,0],'yaw_deg':0,
     'category':'source_grade_proxy','collision_layer':1,'world_bounds_xz_m':bounds,'source_ground_id':ident})
  validation.append({'source_ground_id':ident,'triangle_count':len(triangles),'source_owned_area_m2':source_area,
     'public_surface_area_m2':surface_area,'body_void_area_m2':carved,'body_void_intersection_area_m2':void_error,'source_H_triangle_center_max_error_m':height_error})
  all_triangles+=len(triangles);total_area+=surface_area;cut_area+=carved;all_height_error=max(all_height_error,height_error);all_void_error=max(all_void_error,void_error)
 manifest={'schema':'riverstone.city.finite_source_grade_proxy_layer.v1','sources':{'source_plan':{'path':str(plan_path.resolve()),'sha256':base.digest(plan_path)},
    'r1_infrastructure':{'path':str(infra_path.resolve()),'sha256':base.digest(infra_path)}},'assets':assets,'placements':placements,
    'source_building_body_void_count':len(footprints),'validation':validation,
    'summary':{'owned_source_tiles':len(plan['chunks']),'proxy_tiles':len(assets),'triangles':all_triangles,'public_surface_area_m2':total_area,
      'excluded_body_void_area_m2':cut_area,'river_intersecting_source_tile_count':0,'source_H_triangle_center_max_error_m':all_height_error,'body_void_intersection_area_m2':all_void_error},
    'policy':'Exact source H over611 finite source-owned tiles,326realized body footprints subtracted. R1river remains outside graded proxy. Actualstairs,foundations,retainingwalls,bridges and buildings remain actual.',
    'scope':'Optional candidate physics layer; unchanged common voxel visual meshes; not production controller/navmesh/NPC guarantee.'}
 base.write(out/'layer_manifest.json',manifest);return manifest
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,default=ROOT/'world_city/runtime_city/generated/r2_topography/source_plan.final.json')
 ap.add_argument('--infrastructure',type=Path,default=ROOT/'world_city/runtime_city/generated/r1/infrastructure.json')
 ap.add_argument('--out',type=Path,default=HERE/'proxy_city');args=ap.parse_args();r=build(args.plan,args.infrastructure,args.out);print(json.dumps(r['summary'],indent=2))
