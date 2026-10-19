"""Exact cached navigation, continuous conservative leaf sweep and placement handoff."""
from __future__ import annotations
import itertools,json,math,time
from collections import defaultdict,deque
from voxel_character.common import core
from .author import HERE,ROOT,BASE,load,write,ref,state,corners,aabb,interval_sweep,plate_transform,barrier_transform,rigid
from world_city.concept_city_v3.registered_topography import author as terrain
EPS=1e-8

def box_hits(bb,occupied,pitch=.25):
 ranges=[range(math.floor(a/pitch+EPS),math.ceil(b/pitch-EPS)) for a,b in zip(bb['min'],bb['max'])]
 return [q for q in itertools.product(*ranges) if q in occupied]
def transformed_box(bb,tr):return aabb([core.apply(tr,q) for q in corners(bb)])
def face_proof(c,r):
 p=c['request']['pitch'] if 'request' in c else r['pitch'];occ={tuple(q[:3]) for q in c['cells']};expected=set()
 for q in occ:
  for axis in range(3):
   for sign in(-1,1):
    z=list(q);z[axis]+=sign
    if tuple(z) not in occ:expected.add((*q,axis,sign))
 total=len(expected);bad=0;rendered=0
 for group in r['groups']:
  for quad in group['quads']:
   grid=[[round(v/p) for v in q] for q in quad];a=[quad[1][i]-quad[0][i] for i in range(3)];b=[quad[2][i]-quad[1][i] for i in range(3)];n=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];ax=max(range(3),key=lambda i:abs(n[i]));sg=1 if n[ax]>0 else -1;other=[i for i in range(3) if i!=ax]
   for u in range(min(q[other[0]] for q in grid),max(q[other[0]] for q in grid)):
    for v in range(min(q[other[1]] for q in grid),max(q[other[1]] for q in grid)):
     q=[0,0,0];q[ax]=grid[0][ax]-(sg>0);q[other[0]]=u;q[other[1]]=v;f=(*q,ax,sg);rendered+=1
     if f not in expected:bad+=1
     else:expected.remove(f)
 return {'occupied_exterior_unit_faces':total,'expanded_render_unit_faces':rendered,'missing_faces':len(expected),'internal_or_duplicate_faces':bad}
def cell_bounds(q,p):return {'min':[v*p for v in q[:3]],'max':[(v+1)*p for v in q[:3]]}
def merged_row_boxes(c,p):
 """Exact disjoint occupied runs along X, preserving holes and full native cells."""
 rows=defaultdict(list)
 for x,y,z,*_ in c['cells']:rows[y,z].append(x)
 out=[]
 for (y,z),xs in rows.items():
  xs.sort();lo=prev=xs[0]
  for x in xs[1:]+[None]:
   if x is not None and x==prev+1:prev=x;continue
   out.append({'min':[lo*p,y*p,z*p],'max':[(prev+1)*p,(y+1)*p,(z+1)*p]})
   if x is not None:lo=prev=x
 return out

def rotation_interval_bounds(fn,box,start,end):
 lo,hi=math.radians(start),math.radians(end);values=[[],[],[]]
 for p in corners(box):
  f0=core.apply(fn(0),p);f90=core.apply(fn(90),p);f180=core.apply(fn(180),p)
  for axis in range(3):
   C=(f0[axis]+f180[axis])/2;A=(f0[axis]-f180[axis])/2;B=f90[axis]-C;angles=[lo,hi]
   for k in range(-2,3):
    t=math.atan2(B,A)+k*math.pi
    if lo<=t<=hi:angles.append(t)
   values[axis]+=[C+A*math.cos(t)+B*math.sin(t) for t in angles]
 return {'min':[min(q) for q in values],'max':[max(q) for q in values]}

def verify():
 started=time.monotonic();candidate=load(HERE/'candidate.json');report=load(HERE/'compile_report.json');assert report['all_valid'];overlay=load(BASE/'continuous_deck_overlay.json');frame=overlay['bridge_to_world'];compiled={};renders={};assets={};faces={}
 for item in report['reports']:
  c=load(ROOT/item['compiled']['path']);r=load(ROOT/item['render']['path']);assert core.digest(c['cells'])==c['payload_hash']==r['payload_hash'];key=item['asset_key'];compiled[key]=c;renders[key]=r;faces[key]=face_proof(c,r)
  assets[key]={'key':key,'master_path':item['master']['path'],'master_sha256':item['master']['sha256'],'compiled_path':item['compiled']['path'],'compiled_sha256':item['compiled']['sha256'],'render_path':item['render']['path'],'render_sha256':item['render']['sha256'],'pitch_m':item['pitch_m'],'bounds':r['bounds'],'quad_count':r['quad_count'],'cell_count':r['cell_count']}
 assert all(not p['missing_faces'] and not p['internal_or_duplicate_faces'] for p in faces.values())
 occ={tuple(q[:3]) for q in compiled['stone_approaches']['cells']};leaf=compiled['timber_lift_leaf_7x14'];leafboxes=merged_row_boxes(leaf,.25);sweep_conflicts=[];sweep_samples=0
 # Exact trigonometric bounds enclose the entire occupied run over each interval.
 # If an enclosure touches fixed occupancy, refine to0.05 degree before reporting.
 for side in(-1,1):
  for angle in range(90):
   for box in leafboxes:
    bb=interval_sweep(side,angle,angle+1,box)['bounds_bridge_local_m'];hits=box_hits(bb,occ)
    if hits:
     for k in range(20):
      fine=interval_sweep(side,angle+k/20,angle+(k+1)/20,box)['bounds_bridge_local_m'];hh=box_hits(fine,occ)
      if hh:sweep_conflicts.append({'side':side,'interval':[angle+k/20,angle+(k+1)/20],'native_run':box,'fixed_cells':hh[:8]});break
    sweep_samples+=1
  print('leaf sweep',side,len(sweep_conflicts),flush=True)
 # Simultaneous leaves must remain separated at the centre for the entire cycle.
 left_max=max(interval_sweep(-1,0,90,b)['bounds_bridge_local_m']['max'][0] for b in leafboxes);right_min=min(interval_sweep(1,0,90,b)['bounds_bridge_local_m']['min'][0] for b in leafboxes)
 counterweights=[];plate_conflicts=[];barrier_conflicts=[];motion=[state(a,0,overlay,1.) for a in range(91)];barriers=[state(0,a,overlay,0.) for a in range(91)];plates=[state(0,0,overlay,j/60) for j in range(61)]
 for side in(-1,1):
  for j in range(60):
   p0,p1=plate_transform(side,j/60),plate_transform(side,(j+1)/60)
   for bb in merged_row_boxes(compiled['sliding_hinge_cover'],.25):
    swept=aabb([core.apply(t,q) for t in(p0,p1) for q in corners(bb)])
    hits=box_hits(swept,occ)
    if hits:plate_conflicts.append({'id':f'HINGE_PLATE_{side}','interval':[j,j+1],'fixed_cells':hits[:8]});break
  for lateral in(-1,1):
   ident=f'BARRIER_{side}_{lateral}';zero=next(q for q in barriers[0]['movable_placements'] if q['id']==ident)['transform_bridge_local'];floor=zero['translation'][1]-.5
   fn=lambda angle:barrier_transform(side,lateral,angle,floor)
   for j in range(90):
    for bb in merged_row_boxes(compiled['timber_road_barrier_half'],.25):
     swept=rotation_interval_bounds(fn,bb,j,j+1);hits=box_hits(swept,occ)
     if hits:barrier_conflicts.append({'id':ident,'interval':[j,j+1],'fixed_cells':hits[:8]});break
 for side in(-1,1):
  for lateral in(-1,1):
   ident=f'WEIGHT_{side}_{lateral}';poses=[next(p for p in s['movable_placements'] if p['id']==ident)['transform_bridge_local'] for s in motion];bb=aabb([core.apply(t,q) for t in poses for q in corners(renders['guided_stone_counterweight']['bounds'])]);counterweights.append({'id':ident,'swept_bounds_bridge_local_m':bb,'fixed_cell_intersections':len(box_hits(bb,occ))})
 # Entire vessel route, including all continuous and cached rig extrema.
 navigation=[]
 open_state=state(90,0,overlay,1.)
 for vessel in candidate['navigation_vessels']:
  b=vessel['union_source_cache_bounds_local_m'];x=vessel['route_origin_bridge_x_m'];zs=vessel['travel_bridge_z_m'];heads=[];wet=[]
  for z in range(int(zs[0])-12,int(zs[1])+13):
   world=core.apply(frame,[x,0,z]);heads.append(terrain.river_water_y(world[0]))
   for xx in (x+b['min'][0],x+b['max'][0]):
    w=core.apply(frame,[xx,0,z]);wet.append(bool(terrain.water_samples_at(w[0],w[2])))
  swept={'min':[x+b['min'][0],min(heads)+b['min'][1],zs[0]+b['min'][2]],'max':[x+b['max'][0],max(heads)+b['max'][1],zs[1]+b['max'][2]]}
  fixed_hits=box_hits(swept,occ);moving=[];minimum_side=1e9
  for q in open_state['movable_placements']:
   bb=transformed_box(renders[q['asset_key']]['bounds'],q['transform_bridge_local']);overlap=all(min(bb['max'][i],swept['max'][i])>max(bb['min'][i],swept['min'][i])+EPS for i in range(3))
   if overlap:moving.append(q['id'])
   if q['id'].startswith('LEAF_'):minimum_side=min(minimum_side,max(bb['min'][0]-swept['max'][0],swept['min'][0]-bb['max'][0]))
  chain_conflicts=[]
  for chain in open_state['chains']:
   bb=aabb(chain['polyline_bridge_xyz_m']);bb={'min':[v-.3 for v in bb['min']],'max':[v+.3 for v in bb['max']]}
   if all(min(bb['max'][i],swept['max'][i])>max(bb['min'][i],swept['min'][i])+EPS for i in range(3)):chain_conflicts.append(chain['id'])
  navigation.append({'asset_key':vessel['asset_key'],'full_source_cache_swept_envelope_bridge_m':swept,'fixed_cell_intersections':len(fixed_hits),'open_movable_intersections':moving,'open_chain_envelope_intersections':chain_conflicts,'minimum_actual_leaf_side_margin_m':minimum_side,'all_route_edge_water_samples_wet':all(wet),'minimum_bed_clearance_m':3+b['min'][1]-.2,'bed_note':'Conservative normal-stage draft allowance; 0.2m reserved for static head change across the level vessel, no hydrodynamic validation.'})
 # Explicit source and sampled closed-floor interface checks at the two hinges and meeting line.
 closed=state(0,90,overlay,0.);closed_occ=set(occ)
 for q in closed['movable_placements']:
  if not (q['id'].startswith('LEAF_') or q['id'].startswith('HINGE_PLATE_')):continue
  for cell in compiled[q['asset_key']]['cells']:
   center=core.apply(q['transform_bridge_local'],[(v+.5)*.25 for v in cell[:3]]);closed_occ.add(tuple(math.floor(v/.25) for v in center))
 floor_samples=[]
 for ix in range(-42,43):
  for iz in range(-24,25):
   if (ix,15,iz) not in closed_occ:floor_samples.append([ix,15,iz])
 checks={'native_sources_valid':report['all_valid'],'render_face_bijections':faces,'continuous_leaf_sweep':{'interval_enclosures_tested':sweep_samples,'coarse_interval_degrees':1,'conflict_refinement_degrees':.05,'conflicts':sweep_conflicts,'left_max_x_m':left_max,'right_min_x_m':right_min,'leaf_to_leaf_positive_overlap':left_max>right_min+EPS},'counterweight_sweeps':counterweights,'hinge_plate_sample_conflicts':plate_conflicts,'barrier_sample_conflicts':barrier_conflicts,'navigation':navigation,'closed_road_missing_top_cells':floor_samples,'limitations':['Leaf and barrier checks enclose full rotations analytically; cover checks enclose every point of each piecewise-linear translation. Counterweight full travel boxes are checked.','No collision solver, structural load, vessel roll/yaw/drift or flood validation.'],'seconds':time.monotonic()-started}
 checks['valid']=not(sweep_conflicts or left_max>right_min+EPS or plate_conflicts or barrier_conflicts or floor_samples or any(q['fixed_cell_intersections'] for q in counterweights) or any(q['fixed_cell_intersections'] or q['open_movable_intersections'] or q['open_chain_envelope_intersections'] or not q['all_route_edge_water_samples_wet'] for q in navigation))
 write(HERE/'geometry_audit.json',checks)
 print(json.dumps({'valid':checks['valid'],'leaf_sweep_conflicts':len(sweep_conflicts),'plate_conflicts':len(plate_conflicts),'barrier_conflicts':len(barrier_conflicts),'missing_floor_cells':len(floor_samples),'navigation':navigation,'seconds':checks['seconds']},indent=2),flush=True)
 if not checks['valid']:return
 for collection in(motion,barriers,plates):
  for sample in collection:sample.update(road_enabled=False,navigation_enabled=False,context='transition_only; named locked states grant route authority')
 stages=[{'id':'ROAD_OPEN','duration_s':4,'pose_state':'ROAD_OPEN'},{'id':'CLOSE_BARRIERS','duration_s':3,'sample_array':'barrier_samples','start_angle':90,'end_angle':0},{'id':'ROAD_SECURED','duration_s':1,'pose_state':'ROAD_SECURED'},{'id':'RETRACT_HINGE_COVERS','duration_s':5,'sample_array':'hinge_cover_samples','start_angle':0,'end_angle':60},{'id':'LIFT','duration_s':12,'sample_array':'motion_samples','start_angle':0,'end_angle':90},{'id':'NAVIGATION_OPEN','duration_s':8,'pose_state':'NAVIGATION_OPEN'},{'id':'LOWER','duration_s':12,'sample_array':'motion_samples','start_angle':90,'end_angle':0},{'id':'SEAT_HINGE_COVERS','duration_s':5,'sample_array':'hinge_cover_samples','start_angle':60,'end_angle':0},{'id':'ROAD_SECURED','duration_s':1,'pose_state':'ROAD_SECURED'},{'id':'OPEN_BARRIERS','duration_s':3,'sample_array':'barrier_samples','start_angle':0,'end_angle':90}]
 for stage in stages:stage.update(road_enabled=stage['id']=='ROAD_OPEN',navigation_enabled=stage['id']=='NAVIGATION_OPEN')
 runtime={**candidate,'status':'compiled_native_candidate_with_source_state_checks_pending_scene_physics','motion_samples':motion,'barrier_samples':barriers,'hinge_cover_samples':plates,'cycle_stages':stages,'sample_contract':{'leaf_and_barrier_spacing_degrees':1,'hinge_cover_intervals':60,'interpolation':'Slerp rotation, linear translation and chain endpoints between neighboring exact samples; easing applies to sample index only.','leaf_max_render_only_chord_error_bound_m':.0005,'continuous_collision_authority':'geometry_audit continuous leaf/barrier/cover enclosures; interpolation is only a viewer approximation.','manual_clearance_and_lock_confirmation_required':True,'demo_cycle_is_not_an_autonomous_navigation_controller':True}}
 write(HERE/'state_contract.json',runtime)
 vessel=candidate['navigation_vessels'][-1];r=load(ROOT/vessel['cache']['path']);vkey=vessel['asset_key'];assets[vkey]={'key':vkey,'master_path':vessel['source']['path'],'master_sha256':vessel['source']['sha256'],'render_path':vessel['cache']['path'],'render_sha256':vessel['cache']['sha256'],'bounds':r['bounds'],'pitch_m':r['pitch'],'quad_count':r['quad_count'],'cell_count':r['cell_count'],'reuse_only':True}
 p=core.apply(frame,[vessel['route_origin_bridge_x_m'],0,0]);vpose=copy_transform=core.compose(frame,rigid(translation=[vessel['route_origin_bridge_x_m'],terrain.river_water_y(p[0]),0]))
 fixed={'id':'BRIDGE_MAIN_RIVER:DRAWBRIDGE_FIXED','asset_key':'stone_approaches','transform':frame,'position_m':frame['translation'],'scale_xyz':[1,1,1],'collision_policy':'Exact concave exterior mesh; retain eight real arches and central open slot.'}
 pack={'schema':'riverstone.registered_drawbridge_placement_pack.v1','status':'bounded_candidate_ready_for_visual_review_pending_independent_geometry_and_physics','candidate':ref(HERE/'candidate.json'),'state_contract':ref(HERE/'state_contract.json'),'geometry_audit':ref(HERE/'geometry_audit.json'),'compile_report':ref(HERE/'compile_report.json'),'source_plan_path':load(BASE/'resolved_placements.json')['source_plan_path'],'source_plan_sha256':load(BASE/'resolved_placements.json')['source_plan_sha256'],'assets':assets,'placements':[fixed],'states':runtime['states'],'motion_samples':motion,'barrier_samples':barriers,'hinge_cover_samples':plates,'cycle_stages':stages,'bridge_to_world':frame,'inspection_vessel':{'asset_key':vkey,'transform_world':vpose,'visible_only_in_navigation_open':True,'full_rig_geometry_reused':True},'surface_ownership':runtime['surface_ownership'],'replacement_overlay':{'suppress_placement_ids':['BRIDGE_MAIN_RIVER:COMMON_UNION'],'keep_original_fixed_pack_as_reversible_alternative':True,'movable_ids_owned_by_mechanism_only':[q['id'] for q in runtime['states']['ROAD_OPEN']['movable_placements']]},'integration_rules':['Render only one fixed placement plus mechanism movable nodes. Never duplicate leaves as static children.','Suppress central terrain/road faces in every state; the lifted slot remains water and bed.','Runtime animation is kinematic only; disable both routes during any transition or fault.','ROAD_OPEN enables traffic only after both leaves and covers seat; NAVIGATION_OPEN enables vessels only after both leaves lock at90 degrees.'],'summary':{'new_native_assets':len(report['reports']),'native_quads':sum(q['quad_count'] for q in report['reports']),'compile_seconds':report['total_seconds'],'peak_rss_mib':report['peak_rss_mib'],'leaves':2,'hinge_covers':2,'barriers':4,'counterweights':4,'source_and_cache_rig_width_m':11,'source_rig_air_height_m':17.5,'worst_navigation_design_margin_each_m':.75,'actual_minimum_leaf_margin_each_m':min(q['minimum_actual_leaf_side_margin_m'] for q in navigation),'closed_road_floor_gaps':len(floor_samples)}}
 write(HERE/'resolved_placements.json',pack);print('pack',ref(HERE/'resolved_placements.json'),flush=True)
if __name__=='__main__':verify()
