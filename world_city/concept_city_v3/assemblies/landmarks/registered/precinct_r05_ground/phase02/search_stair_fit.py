"""Source-only alternatives for a real public stair, with finite ownership fits."""
from inspect_baseline import *
from world_city.concept_city_v3.review_geometry import DomainCut

def local_rect(origin,d,width,length):
 u=[-d[1],d[0]]
 return[[origin[j]+d[j]*t+u[j]*s for j in(0,1)]for s,t in[(-width/2,0),(width/2,0),(width/2,length),(-width/2,length)]]
def main():
 study=load(HERE/'baseline_study.json');h=study['holdings'][0];parts=h['polygon_parts_xz_m'];cutter=DomainCut([{'polygon_xz_m':p}for p in parts]);scene=f.load_scene();idx=f.SurfaceIndex(scene,[h['bounds_xz_m']],margin=16);road=next(r for r in load(CITY/'registered_source/plan.json')['roads']if r['id']=='NORTH_BACK_LANE');candidates=[];bounds=h['bounds_xz_m'];native=[];ni=geo._SpatialIndex(8)
 for inst in scene['common_instances']:
  a=scene['common_assets'][inst['asset_key']];cachepath=a.get('render_path')or a.get('cache',{}).get('path');mesh=load(ROOT/cachepath);b=a.get('bounds',mesh['bounds']);pos=inst['position_m'];radius=max(math.hypot(x,z)for x in[b['min'][0],b['max'][0]]for z in[b['min'][2],b['max'][2]])
  if pos[0]+radius<bounds[0]-20 or pos[0]-radius>bounds[2]+20 or pos[2]+radius<bounds[1]-20 or pos[2]-radius>bounds[3]+20:continue
  yaw=inst['yaw_rad'];cy,sy=math.cos(yaw),math.sin(yaw)
  for group in mesh['groups']:
   for q in group['quads']:
    if not all(abs(v[1]-q[0][1])<1e-8 for v in q):continue
    u=[q[1][j]-q[0][j]for j in range(3)];v=[q[2][j]-q[0][j]for j in range(3)]
    if u[2]*v[0]-u[0]*v[2]>=0:continue
    p=[[pos[0]+v[0]*cy+v[2]*sy,pos[2]-v[0]*sy+v[2]*cy]for v in q];ni.add(len(native),p);native.append({'id':inst['id'],'polygon_xz_m':p,'native_bottom_y_m':pos[1]+q[0][1]})
 for si,(a,b)in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
  L=math.dist(a,b);tangent=[(b[j]-a[j])/L for j in(0,1)]
  for k in range(max(1,math.ceil(L))):
   c=[a[j]+(b[j]-a[j])*(k+.5)/max(1,math.ceil(L))for j in(0,1)]
   if not(bounds[0]-15<c[0]<bounds[2]+15 and bounds[1]-15<c[1]<bounds[3]+15):continue
   for sign in(-1,1):
    d=[-tangent[1]*sign,tangent[0]*sign];edge=[c[j]+d[j]*road['width_m']/2 for j in(0,1)]
    er=idx.at(*edge)
    if not er:continue
    lower_road_y=max(idx.height(r,*edge)for r in er);n=round((12-lower_road_y)/.15)
    if not 6<=n<=40:continue
    lower_y=12-n*.15;length=n*.3+2.4+(1.2 if n>20 else 0);origin=[edge[j]+d[j]*1.2 for j in(0,1)];p=local_rect(origin,d,3,length);outside=cutter.subtract(p);outside_area=sum(geo.polygon_area(q)for q in outside);hits=[]
    for i in ni.candidates(p):
     ar=geo.intersection_area(p,native[i]['polygon_xz_m'])
     if ar>1e-7:hits.append({'id':native[i]['id'],'area_m2':ar})
    upper=[origin[j]+d[j]*length for j in(0,1)];rr=idx.at(*upper);uy=max([idx.height(r,*upper)for r in rr],default=-100)
    if abs(uy-12)>.01:continue
    if outside_area>12 or hits:continue
    covered=sum(geo.polygon_area(v['intersection_polygon_xz_m'])for v in idx.cover(p))
    if abs(covered-geo.polygon_area(p))>1e-6:continue
    prof=[]
    for j in range(math.ceil(length/.3)+1):
     t=min(length,j*.3);xz=[origin[k]+d[k]*t for k in(0,1)];r=idx.at(*xz);prof.append({'distance_m':t,'xz_m':xz,'ground_y_m':max([idx.height(v,*xz)for v in r],default=None)})
    candidates.append({'road_segment_index':si,'road_edge_xz_m':edge,'road_edge_ground_y_m':lower_road_y,'lower_landing_y_m':lower_y,'riser_count':n,'rise_m':n*.15,'riser_m':.15,'going_m':.3,'total_source_length_m':length,'lower_landing_outer_edge_xz_m':origin,'inward_direction_xz':d,'polygon_xz_m':p,'outside_holding_m2':outside_area,'outside_holding_polygons_xz_m':outside,'upper_landing_xz_m':upper,'upper_y_m':uy,'native_footprint_hits':hits,'center_ground_profile':prof})
 candidates.sort(key=lambda r:(r['outside_holding_m2']>1e-6,r['outside_holding_m2'],r['rise_m']))
 write(HERE/'stair_fit_candidates.json',{'base_scene':study['base_scene'],'holding_id':h['holding_id'],'native_support_reservations':native,'candidates':candidates,'status':'Source alternatives only; exact full-width cuts/retaining and public-profile continuity not yet accepted.'});print('CANDIDATES',len(candidates));print([{k:v for k,v in r.items()if k not in('center_ground_profile','outside_holding_polygons_xz_m')}for r in candidates[:6]])
if __name__=='__main__':main()
