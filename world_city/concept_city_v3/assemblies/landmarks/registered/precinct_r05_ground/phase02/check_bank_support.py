from inspect_baseline import *
from world_city.concept_city_v3.review_geometry import DomainCut
plan=load(HERE/'design_plan.json');p=plan['selected_stair_fit']['candidate']['polygon_xz_m'];scene=f.load_scene();idx=f.SurfaceIndex(scene,[box(p)],margin=0);cover=idx.cover(p);cut=DomainCut([{'polygon_xz_m':r['intersection_polygon_xz_m']}for r in cover]);missing=cut.subtract(p);rows=[]
for i in range(0,len(scene['surfaces']['bank']),3):
 tri=scene['surfaces']['bank'][i:i+3]
 if f.normal_y(tri)<=1e-10:continue
 poly=[[v[0],v[2]]for v in tri]
 for q in missing:
  hit=geo.convex_intersection(q,poly);area=geo.polygon_area(hit)
  if area>1e-8:rows.append({'triangle_index':i//3,'polygon_xz_m':hit,'area_m2':area,'source_triangle':tri})
write(HERE/'bank_support_diagnosis.json',{'missing_polygons_xz_m':missing,'missing_area_m2':sum(geo.polygon_area(p)for p in missing),'upward_bank_faces':rows,'bank_area_m2':sum(r['area_m2']for r in rows)});print(sum(geo.polygon_area(p)for p in missing),sum(r['area_m2']for r in rows),len(rows))
