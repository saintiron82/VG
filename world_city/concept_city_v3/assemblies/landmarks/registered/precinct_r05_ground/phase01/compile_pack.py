"""Four bounded native low-boundary unions and exact support/access masks."""
from author import *
def horizontal_faces(mesh,y,sign):
 out=[]
 for g in mesh['groups']:
  for q in g['quads']:
   if not all(abs(v[1]-y)<1e-7 for v in q):continue
   u=[q[1][j]-q[0][j]for j in range(3)];v=[q[2][j]-q[0][j]for j in range(3)]
   if (u[2]*v[0]-u[0]*v[2])*sign>0:out.append([[v[0],v[2]]for v in q])
 return out

def compile_all():
 start=time.monotonic();pre=load(HERE/'common_preflight.json');plan=load(HERE/'active_ground_plan.json');assets=[];placements=[];bearings=[];tests=[];routes=[]
 for r in pre['sources']:
  t=time.monotonic();s=load(ROOT/r['source']['path']);c=coordinate_planes.compile_master(s,{'pitch':.25},max_candidate_cells=500000,max_output_cells=160000);assert c['valid'];mesh=render_data.make_render_data(c);cp=HERE/'cache'/f"{s['id']}.pitch_0.25.render.json";write(cp,mesh);asset={'id':s['id'],'source':r['source'],'cache':ref(cp),'master_hash':core.digest(s),'pitch_m':.25,'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells']),'quad_count':mesh['quad_count'],'bounds':mesh['bounds'],'seconds':time.monotonic()-t};assets.append(asset);pose=r['position_m'];pid=r['holding_id']+':native_boundary';placements.append({'id':pid,'holding_id':r['holding_id'],'asset_key':s['id'],'source':asset['source'],'cache':asset['cache'],'position_m':pose,'yaw_rad':0,'scale':[1,1,1],'actual_cached_bounds_local_m':mesh['bounds'],'function':'continuous low stone boundary and static open field gate'})
  nativefoot=[]
  for i,p in enumerate(horizontal_faces(mesh,-.75,-1)):
   worldp=[[x+pose[0],z+pose[2]]for x,z in p];nativefoot.append(worldp);bearings.append({'id':pid+':bearing:'+str(i),'placement_id':pid,'holding_id':r['holding_id'],'polygon_xz_m':worldp,'bottom_y_m':pose[1]-.75,'finished_ground_y_m':pose[1],'native_top_y_m':pose[1]+1.25,'kind':'native_boundary_footing'})
  h=next(h for h in plan['holdings']if h['id']==r['holding_id']);route=h['source_access'];ribbons=route['ribbon_polygons_xz_m']+[circle(p,1,16)for p in route['polyline_xz_m']];ix=geo._SpatialIndex(8)
  for i,p in enumerate(ribbons):ix.add(i,p)
  cols={(q[0],q[2])for q in c['cells']if 0<=q[1]*.25<1.9};hits=[]
  for x,z in cols:
   p=rect(pose[0]+x*.25,pose[2]+z*.25,pose[0]+(x+1)*.25,pose[2]+(z+1)*.25)
   for i in ix.candidates(p):
    area=geo.intersection_area(p,ribbons[i])
    if area>1e-7:hits.append({'cell_xz':[x,z],'area_m2':area,'polygon_xz_m':geo.convex_intersection(p,ribbons[i])})
  # Gate clearance is checked from the actual native occupied cells.
  cells={tuple(q[:3])for q in c['cells']};gate=r['gate'];d=gate['outward_direction_xz'];u=[-d[1],d[0]];clear=[]
  for k in range(-100,101):
   tt=k*.025;blocked=False
   for along in(-.25,0,.25):
    for y in(.1,.7,1.2):
     pp=[gate['center_xz_m'][j]+u[j]*tt+d[j]*along for j in(0,1)];idxc=(math.floor((pp[0]-pose[0])/.25),math.floor(y/.25),math.floor((pp[1]-pose[2])/.25));blocked|=idxc in cells
   clear.append(not blocked)
  lo=hi=100
  while lo>0 and clear[lo-1]:lo-=1
  while hi<200 and clear[hi+1]:hi+=1
  width=(hi-lo)*.025 if clear[100] else 0
  intervals=[];slabclip=rect(-5,-.25,5,.25)
  for x,z in cols:
   corners=rect(pose[0]+x*.25,pose[2]+z*.25,pose[0]+(x+1)*.25,pose[2]+(z+1)*.25)
   localpoly=[[sum((p[j]-gate['center_xz_m'][j])*u[j]for j in(0,1)),sum((p[j]-gate['center_xz_m'][j])*d[j]for j in(0,1))]for p in corners]
   clip=geo.convex_intersection(localpoly,slabclip)
   if geo.polygon_area(clip)>1e-9:intervals.append((min(p[0]for p in clip),max(p[0]for p in clip)))
  middle_blocked=any(lo<0<hi for lo,hi in intervals);left=max([hi for lo,hi in intervals if hi<=0]+[-5]);right=min([lo for lo,hi in intervals if lo>=0]+[5]);exact_width=0 if middle_blocked else right-left
  slab={(q[0],q[2])for q in c['cells']if q[1]==1};xmin=min(x for x,z in slab);zmin=min(z for x,z in slab);im=np.zeros((max(z for x,z in slab)-zmin+1,max(x for x,z in slab)-xmin+1),bool)
  for x,z in slab:im[z-zmin,x-xmin]=True
  n4=ndimage.label(im)[1];n8=ndimage.label(im,np.ones((3,3)))[1]
  # Existing source route elevations are checked at both full-width edges and joins.
  pts=[]
  for a,b in zip(route['polyline_xz_m'],route['polyline_xz_m'][1:]):
   L=math.dist(a,b);u=[-(b[1]-a[1])/L,(b[0]-a[0])/L]
   for i in range(max(1,math.ceil(L/.5))+1):
    t=i/max(1,math.ceil(L/.5))
    for side in(-1,0,1):pts.append([a[j]+(b[j]-a[j])*t+u[j]*side for j in(0,1)])
  ys=[terrain.land_height_at(*p)for p in pts];test={'holding_id':r['holding_id'],'route_native_boundary_overlap_count':len(hits),'route_native_boundary_overlap_area_sum_m2':sum(p['area_m2']for p in hits),'gate_slab_sample_clear_width_m':width,'native_gate_clear_width_exact_slab_m':exact_width,'gate_exact_method':'Convex intersection of every walking-height native column with0.5m-deep gate slab; exact center free interval.','required_clear_width_m':2,'horizontal_slice_face_connected_components':int(n4),'horizontal_slice_edge_connected_components':int(n8),'edge_only_joins_present':n4!=n8,'route_full_width_sample_count':len(pts),'route_height_range_m':[min(ys),max(ys)],'route_profile_level_at_host':all(abs(y-pose[1])<1e-6 for y in ys),'route_conflicts':hits[:20],'external_existing_body_collision':'pending independent review'};tests.append(test);assert not hits,(r['holding_id'],test);assert exact_width>=2-1e-8,(r['holding_id'],width,exact_width);assert n4==n8,(r['holding_id'],n4,n8)
  routes.append({'id':r['holding_id']+':field_access','holding_id':r['holding_id'],'polyline_xz_m':route['polyline_xz_m'],'ribbon_polygons_xz_m':ribbons,'width_m':2,'gate':gate,'sampled_ground_range_m':[min(ys),max(ys)],'finished_ground_y_m':pose[1],'source_target':route['target_point_xz_m'],'native_boundary_clear':True,'external_existing_body_collision':'pending independent review','full_width_profile_accepted':False});print('BOUNDARY',r['holding_id'],c['candidate_cells'],len(c['cells']),width,n4,n8,flush=True)
 # Reuse verified productive parts without scaling or new compilation.
 props={a['id']:a for a in plan['reused_prop_assets']};tree=next(a for a in props.values()if'05a884'in a['id']);bed=next(a for a in props.values()if'b8fc7'in a['id']);assets+=list(props.values())
 for h in plan['holdings']:
  for p in h['plantings']:
   a=tree if p['kind']=='tree'else bed;assert ref(ROOT/a['source']['path'])==a['source']and ref(ROOT/a['cache']['path'])==a['cache'];mesh=load(ROOT/a['cache']['path']);placements.append({**p,'holding_id':h['id'],'asset_key':a['id'],'source':a['source'],'cache':a['cache'],'actual_cached_bounds_local_m':mesh['bounds'],'function':'productive_orchard_tree'if p['kind']=='tree'else'kitchen_or_nursery_raised_bed'})
   for i,q in enumerate(horizontal_faces(mesh,mesh['bounds']['min'][1],-1)):
    poly=[world(v,[p['position_m'][0],p['position_m'][2]],math.degrees(p['yaw_rad']))for v in q];bearings.append({'id':p['id']+':bearing:'+str(i),'placement_id':p['id'],'holding_id':h['id'],'polygon_xz_m':poly,'bottom_y_m':p['position_m'][1]+mesh['bounds']['min'][1],'finished_ground_y_m':p['position_m'][1],'kind':'native_productive_prop_footing'})
 write(HERE/'native_tests.json',{'rows':tests,'all_native_gate_and_boundary_route_checks_pass':True,'total_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'compiler_runs':4,'independent_access_accepted':False,'actual_viewed':False});pack={'schema':'riverstone.city.productive_ground.native_placements.v1','status':'four level holdings compiled/resolved; finite ground patch and external handoff pending','sources':plan['sources'],'active_ground_plan':ref(HERE/'active_ground_plan.json'),'native_tests':ref(HERE/'native_tests.json'),'assets':assets,'placements':placements,'actual_bearing_footprints':bearings,'owned_floors':[],'internal_routes':routes,'holdings':[{k:v for k,v in h.items()if k not in('boundary_spans','plantings')}for h in plan['holdings']],'replacement_ledger':{'source_buildings_removed':[],'existing_native_placements_removed':[],'terrain_policy':'Finite material ownership and exact native footing holes only; inherit frozen surface heights.'},'summary':{**plan['summary'],'new_common_boundary_assets':4,'reused_common_prop_assets':2,'resolved_placements':len(placements),'bearing_pieces':len(bearings),'meaningful_area_m2':11430.5},'pending_step_inputs':plan['pending_step_inputs'],'activation_requirements':['Compose finite terrain surface edits on frozen R5 original indices.','Resolve existing-target opening/access support from native meshes.','Independent cross-pack checks and actual city art view.'],'compiled':True,'resolved':True,'placed_in_actual_scene':False,'actual_viewed':False};write(HERE/'resolved_placements.json',pack);print(ref(HERE/'resolved_placements.json'));print(pack['summary'])
if __name__=='__main__':compile_all()
