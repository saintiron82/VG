"""Bounded principal-axis stair and terrain-aligned productive ground sources."""
from inspect_baseline import *
from scipy import ndimage
from world_city.concept_city_v3.review_geometry import DomainCut
sys.path.insert(0,str(HERE.parent/'phase01'))
import author as p1
from world_city.runtime_city.parts.author import Source
from world_city.concept_city_v3.assemblies.landmarks.registered.build_audit import estimate_candidates

def world(p,origin,yaw):return[origin[0]+p[0]*math.cos(yaw)+p[1]*math.sin(yaw),origin[1]-p[0]*math.sin(yaw)+p[1]*math.cos(yaw)]
def circle(p,r,n=16):return[[p[0]+r/math.cos(math.pi/n)*math.cos(2*math.pi*i/n),p[1]+r/math.cos(math.pi/n)*math.sin(2*math.pi*i/n)]for i in range(n)]
def source_entry(s,path,pose,yaw,pitch,role):
 s['provenance'].update(author=ref(Path(__file__)),base_scene=ref(f.SCENE_PATH),sealed_module_reference=ref(CITY/'assemblies/waterworks/author.py'));write(path,s);return{'id':s['id'],'source':ref(path),'position_m':pose,'yaw_rad':yaw,'pitch_m':pitch,'role':role,'estimate':estimate_candidates(s,pitch)}
def staircase(c,ground_min):
 lower=c['lower_landing_y_m'];n=c['riser_count'];first=n//2;second=n-first;length=n*.3+3.6;rise=n*.15;base=math.floor((ground_min-.3-lower)/.15)*.15;a=Source('phase02_estate_stair',[-1.5,base,0],[1.5,rise+1.2,length]);sections=[(0,1.2,0,'lower_landing')]
 for i in range(first):sections.append((1.2+i*.3,1.5+i*.3,(i+1)*.15,'flight1_'+str(i)))
 mid=1.2+first*.3;sections.append((mid,mid+1.2,first*.15,'middle_landing'));begin=mid+1.2
 for i in range(second):sections.append((begin+i*.3,begin+(i+1)*.3,(first+i+1)*.15,'flight2_'+str(i)))
 sections.append((length-1.2,length,rise,'upper_landing'))
 for z,Z,y,id in sections:
  a.box(id,[-1.5,base,z],[1.5,y,Z],'stone',component='stair_bearing')
  for x in(-1.5,1.2):
   side=next(r for r in load(HERE/'collar_design.json')['native_stair_side_ground']if r['section']==id and r['x_interval_m'][0]==x);top=max(y+.9,math.ceil((side['max_ground_y_m']-lower)*20/3)*.15+.9);a.box(id+'_guard_'+str(x),[x,y,z],[x+.3,top,Z],'stone_light',component='stair_guard_retaining')
  a.clearance(id+'_headroom',[-1.2,y+.001,z+.001],[1.2,y+2.3,Z-.001],'2.4 m pedestrian stair clear width; source design only, separate stair controller needed.')
 s=a.finish();s['id']='registered_phase02_estate_two_flight_stair';s['extensions'].update(risers=n,rise_each_m=.15,going_m=.3,flights=[first,second],landings_m=[1.2,1.2,1.2],clear_width_m=2.4,total_width_m=3,total_length_m=length,sections=[{'z_interval_m':[z,Z],'top_local_y_m':y,'id':id}for z,Z,y,id in sections],lower_y_m=lower,middle_y_m=lower+first*.15,upper_y_m=12,source_bottom_world_y_m=lower+base,sampled_source_ground_min_m=ground_min,exact_side_retaining_design=load(HERE/'collar_design.json')['native_stair_side_ground'],exact_support_required=True,game_design_values_not_historic=True,controller_contract='Existing no-step replay does not certify stair use; dedicated player/NPC stair tests pending.');return s

def native_reservations(scene,windows):
 out=[];cache={}
 for inst in scene['common_instances']:
  a=scene['common_assets'][inst['asset_key']];cp=a.get('render_path')or a['cache']['path']
  if cp not in cache:cache[cp]=load(ROOT/cp)
  mesh=cache[cp];b=mesh['bounds'];pos=inst['position_m'];radius=max(math.hypot(x,z)for x in[b['min'][0],b['max'][0]]for z in[b['min'][2],b['max'][2]])
  if not any(pos[0]+radius>=w[0]-3 and pos[0]-radius<=w[2]+3 and pos[2]+radius>=w[1]-3 and pos[2]-radius<=w[3]+3 for w in windows):continue
  yaw=inst['yaw_rad']
  for group in mesh['groups']:
   for q in group['quads']:
    if not all(abs(v[1]-q[0][1])<1e-8 for v in q):continue
    u=[q[1][j]-q[0][j]for j in range(3)];v=[q[2][j]-q[0][j]for j in range(3)]
    if u[2]*v[0]-u[0]*v[2]>=0:continue
    p=[world([v[0],v[2]],[pos[0],pos[2]],yaw)for v in q];out.append({'id':inst['id'],'polygon_xz_m':p,'native_bottom_y_m':pos[1]+q[0][1]})
 return out

def main():
 study=load(HERE/'baseline_study.json');pre=load(HERE.parent/'phase01/phase02_step_inputs.json');choice=next(r for r in load(HERE/'selected_fit_review.json')['rows']if r['riser_count']==26 and r['collar_length_m']==1.8);c=choice['candidate'];assert choice['outside_area_m2']==0 and not choice['native_hits'] and abs(choice['support_uncovered_m2'])<1e-6;scene=f.load_scene();windows=[h['bounds_xz_m']for h in study['holdings']];idx=f.SurfaceIndex(scene,windows,margin=4);native=native_reservations(scene,windows);ni=geo._SpatialIndex(8)
 for i,r in enumerate(native):ni.add(i,r['polygon_xz_m'])
 stair=staircase(c,choice['ground_range_m'][0]);yaw=math.atan2(c['inward_direction_xz'][0],c['inward_direction_xz'][1]);sources=[source_entry(stair,HERE/'masters'/f"{stair['id']}.json",[c['lower_landing_outer_edge_xz_m'][0],c['lower_landing_y_m'],c['lower_landing_outer_edge_xz_m'][1]],yaw,.15,'real_neighborhood_stair')];holdings=[];source_routes=[]
 for h0 in pre['holdings']:
  h=dict(h0);m,x0,z0=p1.grid_for(h['polygon_parts_xz_m']);host=12 if h['id'].startswith('B03')else 8;h['terrain_min_m']=host
  if h['id'].startswith('B03'):
   path=c['internal_service_route_xz_m']+[c['upper_landing_xz_m']];path=[p for i,p in enumerate(path)if i==0 or math.dist(p,path[i-1])>1e-7];h['source_access']={'polyline_xz_m':path,'ribbon_polygons_xz_m':[geo.road_ribbon(a,b,2)for a,b in zip(path,path[1:])],'target_point_xz_m':c['upper_landing_xz_m'],'target_kind':'actual_stair_upper_landing','superseded_original_route':h0['source_access']};h['opening_center_xz_m']=c['upper_landing_xz_m'];h['gate_direction_outward_xz']=[-v for v in c['inward_direction_xz']]
  path=h['source_access']['polyline_xz_m'];routes=h['source_access']['ribbon_polygons_xz_m']+[circle(p,1.2)for p in path];h['ground_program']['service_ribbon_polygons_xz_m']=routes;source_routes.append({'holding_id':h['id'],'polylines_xz_m':[path],'width_m':2,'ribbon_polygons_xz_m':routes,'status':'exact native/terrain route replay pending'})
  boundary=m&~ndimage.binary_erosion(m,structure=np.ones((3,3),bool));contact=np.zeros(m.shape,bool)
  for iz,ix in np.argwhere(boundary):
   p=rect(x0+ix*.5,z0+iz*.5,x0+(ix+1)*.5,z0+(iz+1)*.5)
   if any(geo.intersection_area(p,native[i]['polygon_xz_m'])>1e-8 for i in ni.candidates(p)):contact[iz,ix]=True
   if any(geo.positive_area_overlap(p,q,0)for q in routes+[c['polygon_xz_m']]if h['id'].startswith('B03')):boundary[iz,ix]=False
   if not h['id'].startswith('B03')and any(geo.positive_area_overlap(p,q,0)for q in routes):boundary[iz,ix]=False
  omitted=ndimage.binary_dilation(contact,structure=np.ones((3,3),bool),iterations=3)&boundary;boundary[omitted]=False
  # Whole near-owner spans are omitted, not individual fragments.
  labels,n=ndimage.label(boundary);small=[]
  for lab,count in collections.Counter(labels[labels>0]).items():
   if count<=2:
    for z,x in np.argwhere(labels==lab):small.append(rect(x0+x*.5,z0+z*.5,x0+(x+1)*.5,z0+(z+1)*.5));boundary[labels==lab]=False
  walls=p1.cellrects(boundary,x0,z0);origin=[math.floor((windows[len(holdings)][0]+windows[len(holdings)][2])/2),math.floor((windows[len(holdings)][1]+windows[len(holdings)][3])/2)];a=Source('phase02_boundary_'+str(len(holdings)),[-150,-10,-150],[150,20,150]);bearing_design=[];uncovered_boundary=[]
  for i,p in enumerate(walls):
   b=box(p);axis=0 if b[2]-b[0]>=b[3]-b[1]else 1;start,end=(b[0],b[2])if axis==0 else(b[1],b[3])
   for k,t in enumerate(np.arange(start,end,4)):
    q=rect(float(t),b[1],min(float(t)+4,end),b[3])if axis==0 else rect(b[0],float(t),b[2],min(float(t)+4,end));cover=idx.cover(q);area=sum(geo.polygon_area(r['intersection_polygon_xz_m'])for r in cover)
    if abs(area-geo.polygon_area(q))>1e-6:
     uncovered_boundary.append({'polygon_xz_m':q,'uncovered_native_or_terrain_area_m2':geo.polygon_area(q)-area,'status':'Omitted unsupported boundary span; ownership unresolved.'});continue
    yy=[idx.height(r,*v)for r in cover for v in r['intersection_polygon_xz_m']];low=math.floor((min(yy)-.35)*4)/4;top=math.ceil(max(yy)*4)/4+1;qb=box(q);a.box(f'wall_{i}_{k}',[qb[0]-origin[0],low-host,qb[1]-origin[1]],[qb[2]-origin[0],top-host,qb[3]-origin[1]],'stone',component='boundary');bearing_design.append({'polygon_xz_m':q,'bottom_y_m':low,'top_y_m':top,'source_ground_min_m':min(yy),'source_ground_max_m':max(yy),'minimum_embed_m':min(yy)-low})
  gate=None
  if not h['id'].startswith('B03'):gate=p1.gate_source(a,h,[r['polygon_xz_m']for r in bearing_design],origin,host)
  s=a.finish();s['id']='registered_phase02_'+('estate'if host==12 else'abbey')+'_boundary';s['extensions'].update(terrain_aligned_native_support=bearing_design,shared_existing_native_edge_omissions_xz_m=p1.cellrects(omitted,x0,z0),removed_small_source_tips_xz_m=small,uncovered_boundary_spans=uncovered_boundary,gate=gate,host_datum_m=host);sources.append(source_entry(s,HERE/'masters'/f"{s['id']}.json",[origin[0],host,origin[1]],0,.25,'terrain_aligned_boundary_retaining'))
  flat=m.copy()
  for iz,ix in np.argwhere(flat):
   x,z=x0+(ix+.5)*.5,z0+(iz+.5)*.5;rr=idx.at(x,z)
   if not rr or abs(max(idx.height(r,x,z)for r in rr)-host)>1e-6:flat[iz,ix]=False
  plants=p1.choose_plants(h,flat,x0,z0);h['plantings']=plants;h['functional_ground_policy']='Use the existing exact ground planes for productive plots and service walks. Sloped edges remain green working banks; native owners stay reserved.';h['native_boundary_source_regions']=bearing_design;h['gate']=gate;h['host_datum_m']=host;holdings.append(h)
 write(HERE/'design_plan.json',{'schema':'riverstone.productive_ground.phase02.plan.v1','status':'bounded source design; no native compile, terrain activation or traversal acceptance','base_scene':ref(f.SCENE_PATH),'source_holdings':ref(HERE.parent/'phase01/phase02_step_inputs.json'),'baseline_study':ref(HERE/'baseline_study.json'),'selected_stair_fit':choice,'native_reservations':native,'sources':sources,'holdings':holdings,'internal_routes':source_routes,'public_handoff':{'road':'NORTH_BACK_LANE','length_m':c['collar_length_m'],'clear_width_m':2.4,'edge_samples':choice['road_edge_samples'],'maximum_longitudinal_sample_grade':choice['maximum_collar_grade'],'policy':'Match exact frozen road edge; modify only finite private-side collar, preserve public traffic triangles.'},'summary':{'source_holdings_m2':5379.25,'sampled_level_ground_m2':4824.5,'sampled_sloped_ground_m2':327.25,'sampled_existing_native_holes_m2':227.5,'new_sources':len(sources),'plantings':sum(len(h['plantings'])for h in holdings),'candidate_visits_total':sum(r['estimate']['candidate_cells_exact_aabb_visits']for r in sources)},'R16_reserved':study['R16_reserved'],'native_compile_allowed_after_budget_review':True,'player_NPC_stair_usability':'untested; separate explicit stair controller contract needed','unresolved_original_access_gaps':11,'unresolved_original_stepped_range_parcels':7});print([(r['role'],r['estimate']['candidate_cells_exact_aabb_visits'])for r in sources]);print(load(HERE/'design_plan.json')['summary'])
if __name__=='__main__':main()
