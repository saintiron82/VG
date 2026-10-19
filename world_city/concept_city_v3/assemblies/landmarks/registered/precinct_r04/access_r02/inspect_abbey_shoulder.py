"""Finite pedestrian ownership request; no terrain or native cache edits."""
from author_access import *
def pointseg(p,a,b):
 vx=b[0]-a[0];vz=b[1]-a[1];d=vx*vx+vz*vz;t=max(0,min(1,((p[0]-a[0])*vx+(p[1]-a[1])*vz)/d))if d else 0;return math.dist(p,[a[0]+t*vx,a[1]+t*vz])
def distance(a,b):
 if geo.intersection_area(a,b)>1e-9:return 0
 return min([pointseg(p,c,d)for p in a for c,d in zip(b,b[1:]+b[:1])]+[pointseg(p,c,d)for p in b for c,d in zip(a,a[1:]+a[:1])])
def main():
 pack=load(OUT/'exterior_access_proposal.json');route=next(r for r in pack['routes']if r['gate_id']=='ABBEY_EAST_ORCHARD:main_gate');ribbon=route['ribbon_polygons_xz_m'][2];bounds=[-154,178,-140,233];domains=terrain.surface_domains(bounds,conform=False);shoulders=[];lanes=[]
 for r in domains:
  if r['kind']=='road':lanes.append(r)
  p=clean(geo.convex_intersection(ribbon,r['polygon_xz_m']))
  if p and r['kind']=='road_shoulder':
   hs=[terrain.surface_height_at(r,*q)for q in p];shoulders.append({'source_owner_id':r['owner_id'],'polygon_xz_m':p,'source_kind':r['kind'],'source_vertex_y_m':hs,'finished_y_m':8,'area_m2':geo.polygon_area(p),'maximum_vertex_fill_m':max(8-h for h in hs)})
 conflicts=[]
 for r in lanes:
  for i,p in enumerate(route['ribbon_polygons_xz_m']+route['join_polygons_xz_m']):
   a=geo.intersection_area(p,r['polygon_xz_m'])
   if a>1e-8:conflicts.append({'road':r['owner_id'],'piece':i,'area_m2':a})
 clearance=min(distance(ribbon,r['polygon_xz_m'])for r in lanes if r.get('road_id')=='LOWER_CONTOUR' or 'LOWER_CONTOUR'in r['owner_id'])
 report={'schema':'riverstone.precinct.finite_pedestrian_shoulder_request.v1','source_proposal':ref(OUT/'exterior_access_proposal.json'),'source_native_pack':ref(BASE/'resolved_placements.json'),'source_terrain_module':ref(Path(terrain.__file__)),'route_id':route['id'],'requested_finished_y_m':8,'ribbon_piece_index':2,'ribbon_polygon_xz_m':ribbon,'exact_shoulder_intersections':shoulders,'total_projected_area_m2':sum(r['area_m2']for r in shoulders),'actual_traffic_intersections':conflicts,'minimum_ribbon_to_lower_contour_traffic_edge_m':clearance,'policy':['Keep frozen orchard gate and native boundary.','Only these finite unoccupied shoulder pieces may become the +8 pedestrian route owner.','Actual LOWER_CONTOUR traffic profile and width remain unchanged.','Provide support to existing terrain and explicit retained/guarded edge where a 12% blend cannot fit.','This request does not constitute terrain activation or controller acceptance.']}
 write(OUT/'abbey_shoulder_request.json',report);print('SHOULDER',len(shoulders),report['total_projected_area_m2'],'traffic',conflicts,'clearance',clearance)
if __name__=='__main__':main()
