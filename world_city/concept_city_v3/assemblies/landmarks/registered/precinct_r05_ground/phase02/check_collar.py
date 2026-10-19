from author_plan import *
def main():
 plan=load(HERE/'design_plan.json');c=plan['selected_stair_fit']['candidate'];d=c['inward_direction_xz'];u=[-d[1],d[0]];edge=c['road_edge_xz_m'];L=c['collar_length_m'];lower=c['lower_landing_y_m'];scene=f.load_scene();idx=f.SurfaceIndex(scene,[box(c['polygon_xz_m'])],margin=5)
 def p(s,t):return[edge[j]+u[j]*s+d[j]*t for j in (0,1)]
 poly=[p(-1.2,0),p(1.2,0),p(1.2,L),p(-1.2,L)];cover=idx.cover(poly);breaks={-1.2,1.2};lineage=[]
 for r in cover:
  for v in r['intersection_polygon_xz_m']:
   t=sum((v[j]-edge[j])*d[j]for j in (0,1));s=sum((v[j]-edge[j])*u[j]for j in (0,1))
   if abs(t)<1e-7:breaks.add(round(s,12))
 bs=sorted(breaks);tris=[];rows=[]
 for a,b in zip(bs,bs[1:]):
  if b-a<1e-8:continue
  e0,e1=p(a,0),p(b,0);rr=idx.at(*p((a+b)/2,0));assert rr
  r=max(rr,key=lambda r:idx.height(r,*p((a+b)/2,0)));y0=idx.height(r,*e0);y1=idx.height(r,*e1);v=[[e0[0],y0,e0[1]],[e1[0],y1,e1[1]],[p(b,L)[0],lower,p(b,L)[1]],[p(a,L)[0],lower,p(a,L)[1]]]
  ts=f.fan_upward(v)
  for tri in ts:
   pl=f.a.plane(tri);grade=math.hypot(pl[0],pl[1]);rows.append({'triangle_xyz_m':tri,'grade':grade,'source_road_triangle':{'material':r['material'],'triangle_index':r['triangle_index']}});tris.append(tri)
 sections=load(ROOT/plan['sources'][0]['source']['path'])['extensions']['sections'];side=[]
 origin=c['lower_landing_outer_edge_xz_m'];yaw=plan['sources'][0]['yaw_rad']
 for section in sections:
  for x,X in[(-1.5,-1.2),(1.2,1.5)]:
   q=[world(v,origin,yaw)for v in rect(x,*[section['z_interval_m'][0]],X,section['z_interval_m'][1])];cl=idx.cover(q);ys=[idx.height(r,*v)for r in cl for v in r['intersection_polygon_xz_m']];side.append({'section':section['id'],'x_interval_m':[x,X],'max_ground_y_m':max(ys),'tread_y_m':lower+section['top_local_y_m'],'source_guard_top_y_m':lower+section['top_local_y_m']+.9})
 out={'base_scene':plan['base_scene'],'polygon_xz_m':poly,'triangles':rows,'maximum_grade':max(r['grade']for r in rows),'all_gradients_below_12percent':max(r['grade']for r in rows)<=.12,'native_stair_side_ground':side,'terrain_cover_m2':sum(geo.polygon_area(r['intersection_polygon_xz_m'])for r in cover),'area_m2':geo.polygon_area(poly),'status':'Exact private collar planes; no patch emitted.'};write(HERE/'collar_design.json',out);print({k:v for k,v in out.items()if k not in('triangles','native_stair_side_ground')});print('side guard below ground',max(r['max_ground_y_m']-r['source_guard_top_y_m']for r in side))
if __name__=='__main__':main()
