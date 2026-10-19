from connect_routes import *
def main():
 scene=terrain.load_scene();d=load(HERE/'rejected_external_routes_r01.json');current=load(HERE/'external_routes.json');bad=[r for u in d['unresolved']+current['unresolved']for r in u['candidate_routes']];polys=[p for r in bad for p,c in zip(r['ribbon_polygons_xz_m'],r['terrain_checks'])if not c['passes_existing_surface']];ix=CompositeSupportIndex(scene,polys);regions=[]
 for p in polys:
  c=terrain.audit_polygon(ix,p)
  regions+=c['uncovered_polygons_xz_m']
  regions += [q['polygon_xz_m']for q in c['source_pieces']if q['actual_triangle_grade']>.12+1e-8]
 for r in bad:
  for contact in r['side_check']['contacts']:
   ps=[[v[0],v[2]]for v in contact['intersection_vertices_xyz_m']]
   for a,c in zip(ps,ps[1:]+ps[:1]):
    if math.dist(a,c)>1e-6:regions.append(geo.road_ribbon(a,c,2))
 expanded=[b.rect(min(v[0]for v in q)-1.5,min(v[1]for v in q)-1.5,max(v[0]for v in q)+1.5,max(v[1]for v in q)+1.5)for q in regions if geo.polygon_area(q)<1];hazard=b.buffer(b.mask(regions),1.5)|b.mask(expanded);np.savez_compressed(HERE/'route_hazards.npz',hazard=hazard);write('route_hazards.json',{'regions':regions,'source':'Exact rejected-route upward plane/gap and vertical-face evidence; expanded only for conservative path search. Does not edit terrain.','grid_area_m2':b.area(hazard)});print('hazard',len(regions),b.area(hazard))
if __name__=='__main__':main()
