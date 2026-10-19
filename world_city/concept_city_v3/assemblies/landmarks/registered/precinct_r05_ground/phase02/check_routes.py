from author_plan import *
def main():
 plan=load(HERE/'design_plan.json');pack=load(HERE/'resolved_placements.json');scene=f.load_scene();idx=f.SurfaceIndex(scene,[box([v for p in h['polygon_parts_xz_m']for v in p])for h in plan['holdings']],margin=4);out=[]
 for h in plan['holdings']:
  r=next(r for r in plan['internal_routes']if r['holding_id']==h['id']);pieces=[];seen=DomainCut([])
  for poly in r['ribbon_polygons_xz_m']:
   for p in seen.subtract(poly):pieces.append(p)
   seen=DomainCut([{'polygon_xz_m':p}for p in pieces])
  hY=h['host_datum_m'];fail=[];missing=[];covered=0
  own=[q for q in pack['native_upward_faces']if abs(q['top_y_m']-hY)<1e-8];owncut=DomainCut(own)
  for p in pieces:
   clips=idx.cover(p);cc=DomainCut([{'polygon_xz_m':q['intersection_polygon_xz_m']}for q in clips]);covered+=sum(geo.polygon_area(q['intersection_polygon_xz_m'])for q in clips)
   for q in clips:
    ys=[idx.height(q,*v)for v in q['intersection_polygon_xz_m']]
    if max(abs(y-hY)for y in ys)>1e-7:fail.append({'polygon_xz_m':q['intersection_polygon_xz_m'],'height_range_m':[min(ys),max(ys)],'material':q['material'],'triangle_index':q['triangle_index']})
   missing.extend(v for q in cc.subtract(p)for v in owncut.subtract(q))
  out.append({'holding_id':h['id'],'finite_route_area_m2':sum(geo.polygon_area(p)for p in pieces),'source_terrain_covered_m2':covered,'source_profile_deviations':fail,'unresolved_surface_gaps':missing,'unresolved_surface_gap_m2':sum(geo.polygon_area(p)for p in missing),'finite_ribbon_polygons_xz_m':pieces,'accepted_level_geometry':not fail and sum(geo.polygon_area(p)for p in missing)<1e-7,'player_NPC_accepted':False})
 write(HERE/'route_geometry_tests.json',{'base_scene':plan['base_scene'],'resolved_pack':ref(HERE/'resolved_placements.json'),'rows':out,'all_level_ground_routes_pass':all(r['accepted_level_geometry']for r in out),'stair_usability':'Dedicated controller test pending; authored dimensions and native treads alone do not certify player/NPC access.'});print([{k:v for k,v in r.items()if k not in('finite_ribbon_polygons_xz_m','source_profile_deviations','unresolved_surface_gaps')}for r in out]);print('fail counts',[(len(r['source_profile_deviations']),len(r['unresolved_surface_gaps']))for r in out])
if __name__=='__main__':main()
