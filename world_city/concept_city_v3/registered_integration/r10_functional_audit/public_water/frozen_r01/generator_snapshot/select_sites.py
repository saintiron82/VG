"""Finite read-only R8+R9 public pocket search. Writes this package only."""
from pathlib import Path
import json,math,hashlib,sys
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.side_clearance import SideIndex
from world_city.runtime_city.checks import placement as g
H=Path(__file__).resolve().parent;R=H.parents[4];B=R/'world_city/concept_city_v3';N=H.parent/'network'
S=B/'evidence/r8_final110_runtime_r01/scene.json';SHA='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
def load(p):return json.loads(p.read_bytes())
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def trans(q,p,yaw):
 c,s=math.cos(yaw),math.sin(yaw);return [[p[0]+c*x+s*z,p[2]-s*x+c*z]for x,z in q]
def rect(x0,z0,x1,z1):return [[x0,z0],[x1,z0],[x1,z1],[x0,z1]]
def ribbon(a,b,w):
 dx,dz=b[0]-a[0],b[1]-a[1];L=math.hypot(dx,dz);nx,nz=-dz/L*w/2,dx/L*w/2
 return [[a[0]+nx,a[1]+nz],[b[0]+nx,b[1]+nz],[b[0]-nx,b[1]-nz],[a[0]-nx,a[1]-nz]]
def at_arc(q,d):
 for a,b in zip(q,q[1:]):
  L=math.dist(a,b)
  if d<=L+1e-9:
   t=max(0,min(1,d/L));p=[a[i]+t*(b[i]-a[i])for i in range(3)];ll=math.dist([a[0],a[2]],[b[0],b[2]]);return p,[(b[0]-a[0])/ll,(b[2]-a[2])/ll]
  d-=L
 return q[-1],None

def main():
 scene=load(S);assert a.sha(S)==SHA
 mapping={r['id']:r for r in load(N/'observed_route_observation_mapping.json')};sites={r['addition_count']:r for r in load(N/'observed_facility_location_candidates.json')['selected']};roads={r['id']:r for r in load(B/'registered_source/plan.json')['roads']}
 bs=load(B/'registered_integration/r9/landward_gates/asset_bounds.json');ins={r['id']:r for r in scene['common_instances']}
 for ref in load(B/'registered_integration/r9/integration_r02/index.json')['packs']:
  p=load(R/ref['path']);bs.update({k:v['bounds']for k,v in p.get('common_assets',{}).items()})
  for k in p.get('remove_instance_ids',[]):ins.pop(k,None)
  for r in p.get('add_instances',[]):ins[r['id']]=r
  for r in p.get('replace_instances',[]):ins[r['id']]=dict(ins[r['id']],asset_key=r['asset_key'])
 solids=[];sidx=g._SpatialIndex(8)
 for p in ins.values():
  bb=bs[p['asset_key']];q=trans(rect(bb['min'][0],bb['min'][2],bb['max'][0],bb['max'][2]),p['position_m'],p.get('yaw_rad',0));r=dict(id=p['id'],polygon=q,min_y=p['position_m'][1]+bb['min'][1],max_y=p['position_m'][1]+bb['max'][1]);sidx.add(len(solids),q);solids.append(r)
 def hits(poly,y,h=4.2):return sorted({solids[i]['id']for i in sidx.candidates(poly)if solids[i]['max_y']>y+1e-5 and solids[i]['min_y']<y+h and g.polygon_area(g.convex_intersection(poly,solids[i]['polygon']))>1e-7})
 plan=load(B/'registered_source/plan.json'); plots=plan['plots']; plot_index=g._SpatialIndex(8)
 for i,row in enumerate(plots):
  if row.get('polygon_xz_m'):plot_index.add(i,row['polygon_xz_m'])
 def plot_hits(poly):
  from world_city.concept_city_v3.registered_source.geometry import triangulate
  return sorted({plots[i]['id']for i in plot_index.candidates(poly)if any(g.polygon_area(g.convex_intersection(poly,t))>1e-7 for t in triangulate(plots[i]['polygon_xz_m']))})
 selected=[];rejections=[]
 requested=[int(x)for x in (sys.argv[1] if len(sys.argv)>1 else "2,6").split(",")]
 for num in requested:
  site=sites[num];center=site['point_m'];window=rect(center[0]-35,center[2]-35,center[0]+35,center[2]+35);ix=a.TriangleIndex(scene,[window]);side=SideIndex(scene,[window]);path=mapping[site['road']]['observed_graph_points_xyz_m'];width=roads[site['road'][5:]]['width_m'];arc=0;best=(1e9,None)
  for aa,bb in zip(path,path[1:]):
   u=[bb[i]-aa[i]for i in range(3)];L=math.sqrt(sum(v*v for v in u));t=max(0,min(1,sum((center[i]-aa[i])*u[i]for i in range(3))/(L*L)));p=[aa[i]+t*u[i]for i in range(3)];dd=math.dist(center,p)
   if dd<best[0]:best=(dd,arc+t*L)
   arc+=L
  choices=[];trials=0
  for shift in [0,5,-5,10,-10,15,-15,20,-20,25,-25]:
   station,t=at_arc(path,best[1]+shift)
   if not t:continue
   for side_sign in [-1,1]:
    normal=[-t[1]*side_sign,t[0]*side_sign]
    for setback in [.5,1.5,3.5,5.5,7.5,9.5]:
     d=width/2+2+setback;p=[station[0]+normal[0]*d,station[1],station[2]+normal[1]*d]
     if math.dist(p,center)>30:continue
     # Front is inward to the public lane, so queue cannot be hidden behind tank.
     yaw=math.atan2(-normal[0],-normal[1]);body=trans(rect(-2,-2,2,2),p,yaw);trials+=1
     if hits(body,p[1]):continue
     if set(plot_hits(body))-({"P_REG_0668"}if num==2 else set()):continue
     pieces=list(ix.covering(body))
     if any(r['material']in ('road','alley')and g.polygon_area(r['intersection_polygon_xz_m'])>1e-7 for r in pieces):continue
     ground=a.audit_polygon(ix,body)
     if not ground['passes_existing_surface']:continue
     ys=[v for r in ground['source_pieces']for v in [r['min_y_m'],r['max_y_m']]]
     if not ys or max(ys)-min(ys)>1e-6 or abs(min(ys)-p[1])>.02:continue
     p[1]=min(ys);end=trans([[0,2]],p,yaw)[0];walk=ribbon([station[0],station[2]],end,2)
     if hits(walk,p[1],2.2):continue
     if set(plot_hits(walk))-({"P_REG_0668"}if num==2 else set()):continue
     access=a.audit_polygon(ix,walk)
     if not access['passes_existing_surface']:continue
     if max((abs(r[k]-p[1])for r in access['source_pieces']for k in ['min_y_m','max_y_m']),default=1)>.02:continue
     owners=[dict(id=f'{num}:{i}',polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'])for i,r in enumerate(ground['source_pieces']+access['source_pieces'])]
     sa=side.audit(owners)
     if sa['contacts']:continue
     out=dict(site=num,road=site['road'],station_xyz_m=station,original_station_xyz_m=center,along_route_shift_m=shift,position_m=p,yaw_rad=yaw,side=side_sign,setback_from_design_edge_m=setback,displacement_from_original_station_m=math.dist(p,center),design_road_width_m=width,footprint_xz_m=body,queue_polygon_xz_m=trans(rect(-1,.7,1,2),p,yaw),branch_width_m=2,branch_polygon_xz_m=walk,branch_points_xyz_m=[station,[end[0],p[1],end[1]]],branch_centerline_length_m=math.dist([station[0],station[2]],end),ground=ground,access=access,boundary_ownership=dict(footprint_existing_plot_ids=plot_hits(body),branch_existing_plot_ids=plot_hits(walk),policy='P_REG_0668 finite corner carve-out is authorized if otherwise clear; every other registered parcel is protected.'),native_clearance=dict(method='Conservative complete retained native oriented bounds, including R9 composed additions and replacements',body_hits=[],branch_hits=[]),side_clearance=sa)
     choices.append(out)
  choices.sort(key=lambda r:(r['displacement_from_original_station_m'],r['branch_centerline_length_m']))
  print(num,'trials',trials,'accepted',len(choices),[(v['position_m'],v['along_route_shift_m'],v['setback_from_design_edge_m'])for v in choices[:3]],flush=True)
  if choices:selected.append(choices[0])
  rejections.append(dict(site=num,candidate_tests=trials,passed_all_checks=len(choices),initial_preferred_rejected='Initial bound-only center was inside an actual road source face. No road material is reclassified as a facility footprint.',alternatives=[{k:v for k,v in r.items()if k not in ['ground','access']}for r in choices[:6]]))
 write(H/'selected_sites.json',dict(base_scene_sha256=SHA,status='PASS_FINITE_POCKETS'if len(selected)==len(requested) else'BLOCKED',requested_sites=requested,sites=selected,search=rejections,maximum_station_displacement_m=30))
 # local source rows only, sufficient for pack QA without loading whole scene repeatedly.
 ix=a.TriangleIndex(scene,[r['footprint_xz_m']for r in selected]+[r['branch_polygon_xz_m']for r in selected]);write(H/'local_ground_context.json',ix.rows)
if __name__=='__main__':main()
