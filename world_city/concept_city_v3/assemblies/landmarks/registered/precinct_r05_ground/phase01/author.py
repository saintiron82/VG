"""Four level productive holdings, native low boundaries and open field gates."""
from prepare import *
import copy,time,resource
from recovered_range_factory import Source,estimate_candidates
from voxel_character.common import coordinate_planes,render_data,core
ACTIVE=['C_CHAPTER_GARDEN:1','C_SOUTH_ORCHARD:1','A_WEST_BOUNDARY:1','A_SOUTH_KITCHEN_PLOTS:1']
def contained_poly(parts,p):return abs(sum(geo.intersection_area(p,q)for q in parts)-geo.polygon_area(p))<1e-7

def choose_plants(h,m,x0,z0):
 parts=h['polygon_parts_xz_m'];route=h['ground_program']['service_ribbon_polygons_xz_m'];b=[min(p[0]for q in parts for p in q),min(p[1]for q in parts for p in q),max(p[0]for q in parts for p in q),max(p[1]for q in parts for p in q)];y=h['terrain_min_m'];rows=[]
 if 'orchard'in h['function']:
  candidates=[]
  for ox in(0,2,4,6):
   for oz in(0,2,4,6):
    pts=[]
    for z in np.arange(math.ceil(b[1]/8.5)*8.5+oz,b[3],8.5):
     for x in np.arange(math.ceil(b[0]/8.5)*8.5+ox,b[2],8.5):
      clear=rect(float(x)-4.25,float(z)-4.25,float(x)+4.25,float(z)+3.25)
      if contained(m,x0,z0,clear)and not any(geo.positive_area_overlap(clear,p,0)for p in route):pts.append((float(x),float(z)))
    candidates.append((len(pts),ox,oz,pts))
  _,ox,oz,pts=max(candidates,key=lambda r:(r[0],-r[1],-r[2]))
  for x,z in pts:rows.append({'id':h['id']+':orchard_tree:'+str(len(rows)),'kind':'tree','position_m':[x,y,z],'yaw_rad':0,'scale':[1,1,1],'footprint_xz_m':rect(x-4,z-4,x+4,z+3),'layout':'8.5m structured orchard rows; no random scattering','native_bottom_y_m':y-1})
 # Nursery margins use productive raised beds along the long narrow strips.
 if 'orchard'not in h['function']or h['id']=='A_WEST_BOUNDARY:1':
  occupied=[r['footprint_xz_m']for r in rows];options=[]
  for yaw,w,d,sx,sz in[(0,6,3,9,6),(math.pi/2,3,6,6,9)]:
   for ox,oz in[(0,0),(2,0),(0,2),(2,2)]:
    add=[]
    for z in np.arange(math.ceil(b[1]/sz)*sz+oz,b[3],sz):
     for x in np.arange(math.ceil(b[0]/sx)*sx+ox,b[2],sx):
      p=rect(float(x)-w/2,float(z)-d/2,float(x)+w/2,float(z)+d/2);clear=rect(float(x)-w/2-.75,float(z)-d/2-.75,float(x)+w/2+.75,float(z)+d/2+.75)
      if contained(m,x0,z0,clear)and not any(geo.positive_area_overlap(clear,q,0)for q in route+occupied):add.append((float(x),float(z),p))
    options.append((len(add),yaw,ox,oz,add))
  _,yaw,ox,oz,add=max(options,key=lambda r:r[0])
  for x,z,p in add:rows.append({'id':h['id']+':productive_bed:'+str(len(rows)),'kind':'bed','position_m':[x,y,z],'yaw_rad':yaw,'scale':[1,1,1],'footprint_xz_m':p,'layout':'Unscaled6×3m common beds in rows with2m-or-larger work aisles','native_bottom_y_m':y-.5})
 return rows

def gate_source(a,h,walls,origin,y):
 cells=[];step=.25 if h['id']=='A_WEST_BOUNDARY:1' else .5;post=step;leaflen=1.25 if step==.25 else 1.75
 for p in walls:
  xx=[v[0]for v in p];zz=[v[1]for v in p]
  for z in np.arange(min(zz)+step/2,max(zz),step):
   for x in np.arange(min(xx)+step/2,max(xx),step):cells.append([float(x),float(z)])
 anchors=[(h['opening_center_xz_m'],h['gate_direction_outward_xz'])]
 for aa,bb in reversed(list(zip(h['source_access']['polyline_xz_m'],h['source_access']['polyline_xz_m'][1:]))):
  L=math.dist(aa,bb);d=[(bb[j]-aa[j])/L for j in(0,1)]
  for t in np.arange(L,0,-.5):anchors.append(([aa[j]+float(t)*d[j]for j in(0,1)],d))
 chosen=None
 for q,d in anchors:
  if step==.25 and abs(d[0]*d[1])>1e-8:continue
  u=[-d[1],d[0]];centers=[]
  for p in cells:
   rel=[p[j]-q[j]for j in(0,1)];along=sum(rel[j]*d[j]for j in(0,1));across=sum(rel[j]*u[j]for j in(0,1))
   if abs(along)<2 and .95<abs(across)<4.25:centers.append((3*abs(along)+abs(across),p,along,across))
  selected=[]
  for sign in(-1,1):
   found=None
   for score,p,along,across in sorted(c for c in centers if c[3]*sign>0):
    leaf=[[p[j]-u[j]*post/2 for j in(0,1)],[p[j]-d[j]*leaflen-u[j]*post/2 for j in(0,1)],[p[j]-d[j]*leaflen+u[j]*post/2 for j in(0,1)],[p[j]+u[j]*post/2 for j in(0,1)]]
    if contained_poly(h['polygon_parts_xz_m'],leaf):found=(p,leaf,across);break
   if found is not None:selected.append(found)
  if len(selected)==2:chosen=(q,d,u,selected);break
 if chosen is None:raise ValueError('No contained two-jamb gateway '+h['id'])
 q,d,u,selected=chosen
 for sign,(p,leaf,across)in zip((-1,1),selected):
  a.box('gate_post_'+str(sign),[p[0]-origin[0]-post/2,-.75,p[1]-origin[1]-post/2],[p[0]-origin[0]+post/2,1.5,p[1]-origin[1]+post/2],'timber_dark',component='gate');a.plan('open_leaf_'+str(sign),[[x-origin[0],z-origin[1]]for x,z in leaf],.25,1.25,'timber',component='gate')
 center=[sum(s[0][j]for s in selected)/2 for j in(0,1)];actual_width=selected[1][2]-selected[0][2]-post
 return{'id':h['id']+':field_gate','center_xz_m':center,'source_opening_center_xz_m':h['opening_center_xz_m'],'gate_along_existing_source_path_xz_m':q,'outward_direction_xz':d,'jamb_centers_xz_m':[s[0]for s in selected],'open_leaf_polygons_xz_m':[s[1]for s in selected],'authored_jamb_clear_projection_m':actual_width,'required_pedestrian_clear_width_m':2,'floor_y_m':y,'leaf_state':'static_fully_open','animation_hook':'future rigid hinge around each jamb; no runtime interaction or closing clearance certified','route':h['source_access']}

def prepare_sources():
 pre=load(HERE/'preflight.json');active=[];pending=[];sources=[]
 clergy=load(HERE.parent/'local_frame_r01/corner_repair_r01/changed_masks.json');preserved=[r['polygon_xz_m']for r in clergy['add_actual_bearing_footprints']];preserved_ix=geo._SpatialIndex(8)
 for i,p in enumerate(preserved):preserved_ix.add(i,p)
 for h in pre['holdings']:
  if h['id']not in ACTIVE:pending.append(h);continue
  assert h['terrain_min_m']==h['terrain_max_m'];h=copy.deepcopy(h);parts=h['polygon_parts_xz_m'];m,x0,z0=grid_for(parts);step=.25 if h['id']=='A_WEST_BOUNDARY:1' else .5;wm=np.repeat(np.repeat(m,2,axis=0),2,axis=1)if step==.25 else m;wall=wm&~ndimage.binary_erosion(wm,structure=np.ones((3,3),bool));polyline=h['source_access']['polyline_xz_m'];cutwidth=2 if step==.25 else 3;cut=[geo.road_ribbon(a,b,cutwidth)for a,b in zip(polyline,polyline[1:])if math.dist(a,b)>1e-7]+[circle(p,cutwidth/2,16)for p in polyline]
  for iz,ix in np.argwhere(wall):
   p=rect(x0+ix*step,z0+iz*step,x0+(ix+1)*step,z0+(iz+1)*step)
   if any(geo.positive_area_overlap(p,q,0)for q in cut):wall[iz,ix]=False
  # Join diagonal boundary returns through an existing interior cell only.
  bridges=0
  for iteration in range(8):
   labels,n=ndimage.label(wall);added=[]
   for iz,ix in np.argwhere(wall):
    for dz,dx in[(1,1),(1,-1)]:
     zz,xx=iz+dz,ix+dx
     if not(0<=zz<wall.shape[0]and 0<=xx<wall.shape[1])or not wall[zz,xx]or labels[zz,xx]==labels[iz,ix]:continue
     for cz,cx in[(zz,ix),(iz,xx)]:
      if not wm[cz,cx]or wall[cz,cx]:continue
      pp=rect(x0+cx*step,z0+cz*step,x0+(cx+1)*step,z0+(cz+1)*step)
      if not any(geo.positive_area_overlap(pp,q,0)for q in cut):added.append((cz,cx));break
   if not added:break
   for z,x in added:wall[z,x]=True
   bridges+=len(set(added))
  h['source_inside_corner_bridge_cells']=bridges
  shared=[];shared_mask=np.zeros(wall.shape,bool)
  for iz,ix in np.argwhere(wall):
   p=rect(x0+ix*step,z0+iz*step,x0+(ix+1)*step,z0+(iz+1)*step)
   if any(geo.intersection_area(p,preserved[i])>1e-8 for i in preserved_ix.candidates(p)):shared.append(p);shared_mask[iz,ix]=True
  omission=ndimage.binary_dilation(shared_mask,structure=np.ones((3,3),bool),iterations=3)&wall
  shared_band=[rect(x0+ix*step,z0+iz*step,x0+(ix+1)*step,z0+(iz+1)*step)for iz,ix in np.argwhere(omission)];wall[omission]=False
  h['boundary_direct_contact_cells_xz_m']=shared
  h['boundary_cells_omitted_for_corrected_clergy_owner_xz_m']=shared_band
  h['shared_edge_policy']='Preserve the corrected existing clergy edge; omit new low-wall cells meeting its actual native floor.'
  labels,n=ndimage.label(wall);removed=[]
  for label,count in collections.Counter(labels[labels>0]).items():
   if count*step*step<=.2500001:
    for iz,ix in np.argwhere(labels==label):removed.append(rect(x0+ix*step,z0+iz*step,x0+(ix+1)*step,z0+(iz+1)*step));wall[iz,ix]=False
  h['removed_optional_boundary_corner_tips_xz_m']=removed
  walls=[[[x/2,z/2]for x,z in q]for q in cellrects(wall,x0*2,z0*2)]if step==.25 else cellrects(wall,x0,z0);ps=[p for q in parts for p in q];origin=[math.floor((min(p[0]for p in ps)+max(p[0]for p in ps))/2),math.floor((min(p[1]for p in ps)+max(p[1]for p in ps))/2)];y=h['terrain_min_m'];a=Source('productive_boundary_'+h['id'].replace(':','_').lower(),[-150,-.75,-150],[150,1.5,150])
  for i,p in enumerate(walls):
   # Each short source operation stays on the native0.25m sampling lattice.
   xx=[v[0]for v in p];zz=[v[1]for v in p];axis=0 if max(xx)-min(xx)>=max(zz)-min(zz)else 1;lo=min(xx)if axis==0 else min(zz);hi=max(xx)if axis==0 else max(zz)
   for j,start in enumerate(np.arange(lo,hi,8)):
    end=min(start+8,hi);q=rect(start,min(zz),end,max(zz))if axis==0 else rect(min(xx),start,max(xx),end);xs=[v[0]-origin[0]for v in q];zs=[v[1]-origin[1]for v in q];a.box(f'boundary_{i}_{j}',[float(min(xs)),-.75,float(min(zs))],[float(max(xs)),1.25,float(max(zs))],'stone',component='boundary')
  gate=gate_source(a,h,walls,origin,y);s=a.finish();s['id']='registered_productive_boundary_'+h['id'].replace(':','_').lower();s['provenance'].update(author=ref(Path(__file__)),reviewed_remaining_land=ref(PLAN/'remaining_land_plan.json'),preflight=ref(HERE/'preflight.json'));s['extensions'].update(holding_id=h['id'],world_origin_xyz_m=[origin[0],y,origin[1]],source_ground_regions_xz_m=parts,gate=gate,boundary_band='Inside-cell0.5m low stone band; diagonal staircase returns include the necessary inside corner cell for face connectivity.',wall_visible_height_m=1.25,wall_embed_m=.75,inside_edge_band_m=step,all_dimensions_unscaled=True,actual_viewed=False)
  sp=HERE/'masters'/f"{s['id']}.json";write(sp,s);e=estimate_candidates(s,.25);assert e['candidate_cells_exact_aabb_visits']<500000;sources.append({'holding_id':h['id'],'source':ref(sp),'estimate':e,'position_m':[origin[0],y,origin[1]],'yaw_rad':0,'pitch_m':.25,'gate':gate});h['plantings']=choose_plants(h,m,x0,z0);h['native_boundary_regions_xz_m']=walls;h['gate']=gate;h['boundary_band_connectivity']='8-neighbour erosion interior band, then native4-neighbour slab check after compilation';h['status']='active_phase01_native_candidate';active.append(h)
 write(HERE/'phase02_step_inputs.json',{'status':'pending retaining terraces, landings/stairs and alternative access design','source_preflight':ref(HERE/'preflight.json'),'holdings':pending,'unresolved_original_access_gaps':11,'unresolved_original_stepped_range_parcels':7,'compiled':False,'activation_allowed':False});write(HERE/'active_ground_plan.json',{'sources':pre['sources'],'holdings':active,'reused_prop_assets':pre['reused_prop_assets'],'summary':{'holding_count':4,'meaningful_program_area_m2':sum(h['area_m2']for h in active),'plantings':sum(len(h['plantings'])for h in active),'trees':sum(p['kind']=='tree'for h in active for p in h['plantings']),'beds':sum(p['kind']=='bed'for h in active for p in h['plantings'])},'pending_step_inputs':ref(HERE/'phase02_step_inputs.json'),'terrain_activated':False,'actual_viewed':False});write(HERE/'common_preflight.json',{'sources':sources,'candidate_cap_each':500000,'output_cap_each':160000,'sequential':True,'whole_city_compile':False});print([(r['holding_id'],r['estimate']['candidate_cells_exact_aabb_visits'])for r in sources]);print(load(HERE/'active_ground_plan.json')['summary'],flush=True)
if __name__=='__main__':prepare_sources()
