"""Export route hints snapped to the already-proven actual upper source field."""
from search_abbey import *
def main():
 d=load(O/'abbey_bent_route_proof.json');rows=[];index=geo._SpatialIndex(4)
 for part in d['support_checks']:
  for j,row in enumerate(part['source_pieces']):
   index.add(len(rows),row['polygon_xz_m']);rows.append(dict(row,ribbon_piece_id=part['id'],source_piece_index=j))
 points=[];witness=[]
 for i,(a,c)in enumerate(zip(d['polyline_xyz_m'],d['polyline_xyz_m'][1:])):
  n=max(1,math.ceil(math.hypot(c[0]-a[0],c[2]-a[2])))
  for t in np.linspace(0,1,n+1):
   if i and t==0:continue
   p=[a[k]+float(t)*(c[k]-a[k])for k in[0,2]];poly=b.rect(p[0]-.001,p[1]-.001,p[0]+.001,p[1]+.001);hits=[]
   for ri in index.candidates(poly):
    r=rows[ri]
    if geo.point_in_convex_polygon(p,r['polygon_xz_m'],1e-8):hits.append((terrain.common.height(r['plane_y_xz_m'],p),ri))
   assert hits,p
   y,ri=max(hits);r=rows[ri];points.append([p[0],y,p[1]]);witness.append({k:r[k]for k in('ribbon_piece_id','source_piece_index','material','triangle_index','source_triangle_sha256')})
 out=dict(scene=d['scene'],proof=ref(O/'abbey_bent_route_proof.json'),source_road_id=d['source_road_id'],road_cut=d['road_cut'],points_xyz_m=points,point_support_sources=witness,maximum_centerline_sample_spacing_m=1,source_hint_to_actual_floor_delta_at_road_cut_m=points[0][1]-d['road_cut']['point_xyz_m'][1],height_policy='Every hint sampled from the exact supported upper-envelope source pieces, not linear interpolation of corner heights. This is not a controller replay.')
 write('abbey_surface_snapped_profile.json',out);p=O/'abbey_route_for_parent.json';r=load(p);r['surface_snapped_profile']=ref(O/'abbey_surface_snapped_profile.json');r['source_hint_to_actual_floor_delta_at_road_cut_m']=out['source_hint_to_actual_floor_delta_at_road_cut_m'];write(p.name,r);print('profile',len(points),'points',out['source_hint_to_actual_floor_delta_at_road_cut_m'])
if __name__=='__main__':main()
