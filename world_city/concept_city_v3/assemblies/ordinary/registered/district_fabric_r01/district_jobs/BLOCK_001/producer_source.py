"""Tight connected district holdings. Route backbones precede occupancy search."""
from .geometry import *
FLOORS=[12.0, 13.0]
from .prepare import PLAN,TERR
from scipy.signal import fftconvolve

def world_scene_floor(scene,floor,materials=None):
 ps=[]
 for mat,vs in scene['surfaces'].items():
  if mat in('water','bank')or(materials is not None and mat not in materials):continue
  for j in range(0,len(vs),3):
   t=vs[j:j+3]
   if max(v[1]for v in t)-floor>1e-7 or min(v[1]for v in t)-floor< -1e-7:continue
   p=[[v[0],v[2]]for v in t]
   if max(q[0]for q in p)<BOUNDS[0]or min(q[0]for q in p)>BOUNDS[2]or max(q[1]for q in p)<BOUNDS[1]or min(q[1]for q in p)>BOUNDS[3]:continue
   ps.append(p)
 return raster(ps)

def shortcut(line,clear):
 if len(line)<3:return line
 out=[line[0]];i=0
 while i<len(line)-1:
  for j in range(len(line)-1,i,-1):
   p=raster(ribbons([line[i],line[j]],3.5),True)
   if not np.any(p&~clear):break
  out.append(line[j]);i=j
 return out

def make_routes(scene,source,m,special):
 old=np.load(PLAN/'baseline_masks.npz');x=((XS-float(old['bounds'][0]))/float(old['pitch'])).astype(int);z=((ZS-float(old['bounds'][1]))/float(old['pitch'])).astype(int)
 hard=np.logical_or.reduce([old[k][np.ix_(z,x)]for k in['spaces','estates','water','wall','retained_native','retained_access']])|special|m['nonmatching_native']
 south_path=TERR/'south_access/source_handoff_r02.json';south=load(south_path)['route'];routes=[];floor_masks={};public_masks={};clear_masks={}
 for floor in FLOORS:
  oldholes=m['restorable_'+str(floor).replace('.','_')];actual=world_scene_floor(scene,floor);public=world_scene_floor(scene,floor,{'road','alley'})&old['road'][np.ix_(z,x)];band=(actual|oldholes)&~hard
  # Keep the exterior public road seam, but no unrelated outside-block shortcut.
  band &=m['domain']|ndimage.binary_dilation(public,iterations=5)
  clear=ndimage.distance_transform_edt(band)*GRID>=2.2;nearroad=ndimage.distance_transform_edt(~public)*GRID<1.5;goals=clear&nearroad
  if floor==1. and False: # Sealed optional connection; central continuation remains constrained.
   gate=[south['gate_anchor_xyz_m'][0],south['gate_anchor_xyz_m'][2]];start=nearest(clear,gate,8)
   if start is None:raise RuntimeError('No full-width southern continuation')
   continuation=[gate,point(start)];cp=ribbons(continuation,3.5);known=raster(south['ribbon_polygons_xz_m'],True)
   if np.any(raster(cp,True)&~(band|known)):raise RuntimeError('Southern continuation leaves proven band')
   goals[start]=True
   routes.append(dict(id=south['id'],floor_y_m=1.,width_m=3.5,polyline_xz_m=south['centerline_xz_m'],polygons_xz_m=south['ribbon_polygons_xz_m'],public_seam_knots_xyz_m=south['public_seam_knots_xyz_m'],source_handoff=ref(south_path),role='southern shared district access',connection_kind='exact unchanged EAST_WALL_SERVICE public seam',status='Source proof passed; atomic retirement required'))
   routes.append(dict(id='B1:R8:LANE:1_0:SOUTH_JOIN',floor_y_m=1.,width_m=3.5,polyline_xz_m=continuation,polygons_xz_m=cp,role='southern shared access continuation',connection_kind='same-level shared gate',status='Exact R17 review pending'))
  labels,n=ndimage.label(clear);connected=np.isin(labels,np.unique(labels[goals]));connected&=labels>0;clear&=connected
  floor_masks[floor]=band;public_masks[floor]=public;clear_masks[floor]=clear;network=goals.copy()
  for k in range(10):
   distance=ndimage.distance_transform_edt(~network)*GRID;space=ndimage.distance_transform_edt(band)*GRID;choice=clear&(space>=7)&m['domain'];score=np.where(choice,distance,-1);idx=np.unravel_index(np.argmax(score),SHAPE)
   if score[idx]<20:break
   line=astar(clear,idx,network)
   if not line:break
   line=shortcut(line,band);polys=ribbons(line,3.5);rm=raster(polys,True);network|=rm&clear;routes.append(dict(id=f'B1:R8:LANE:{str(floor).replace(".","_")}:{k+1:02}',floor_y_m=floor,width_m=3.5,polyline_xz_m=line,polygons_xz_m=polys,role='shared_craft_and_domestic_private_access',connection_kind='same-level existing public road approach'if k==0 else'same-level reserved private backbone',status='Reserved before parcels; exact R17 source-triangle and endpoint seam review pending'))
  print('routes',floor,len([r for r in routes if r['floor_y_m']==floor]),'flat accessible',area(clear),flush=True)
 write(HERE/'backland_routes.json',dict(schema='riverstone.district_fabric.route_backbones.v1',base_scene=ref(R7),source_plan=ref(HERE/'owner_route_source_snapshot.json'),routes=routes,policy='Full-width same-level bands; water, retained native and institutional owners remain blocked. Public endpoints require exact final terrain seam checks.'))
 return routes,floor_masks,public_masks,clear_masks

TYPES=[
 ('district_r01_craft_U',rect(-16,-15,16,16)),
 ('district_r01_domestic_L',rect(-13,-13.5,13,14.5)),
 ('working_r01_bank_joinery',rect(-15.75,-5.75,15.75,11)),
 ('working_r01_bank_craft_lodging',rect(-15.75,-5.75,15.75,11)),
 ('working_r01_bank_loft_store',rect(-15.75,-5.75,15.75,11)),
 ('working_r01_market_lodging',rect(-12.75,-5.25,12.75,10)),
 ('district_r01_compact_L',rect(-9.25,-10,9.25,13.5))]

def kernel(poly,yaw):
 center=point((NZ//2,NX//2));a=raster(transform([poly],center,yaw),True);z,x=cell(center);zz,xx=np.where(a);dz=max(z-int(zz.min()),int(zz.max())-z);dx=max(x-int(xx.min()),int(xx.max())-x);return a[z-dz:z+dz+1,x-dx:x+dx+1].astype(float)
def valid_positions(allowed,poly,yaw):
 k=kernel(poly,yaw);return fftconvolve(allowed.astype(float),k[::-1,::-1],mode='same')>=k.sum()-.01

def run():
 snapshot=HERE/'owner_route_source_snapshot.json'
 if not snapshot.exists():write(snapshot,load(PLAN/'block_015_route_parcels.json'))
 source=load(snapshot);scene=load(R7);native=load(HERE/'native_local.json')['assets'];m=np.load(HERE/'planning_masks.npz');special=raster(source['special_reserved_polygon_parts_xz_m'],True)
 # Planner's available source land excludes 2m public shoulders and4m banks.
 base=np.load(PLAN/'baseline_masks.npz');bx=((XS-float(base['bounds'][0]))/float(base['pitch'])).astype(int);bz=((ZS-float(base['bounds'][1]))/float(base['pitch'])).astype(int)
 water=base['water'][np.ix_(bz,bx)];road=base['road'][np.ix_(bz,bx)]
 eligible=m['domain']&~m['protected']&~special&~m['nonmatching_native']&(ndimage.distance_transform_edt(~water)*GRID>4)&(ndimage.distance_transform_edt(~road)*GRID>2)
 routes,bands,public,clear=make_routes(scene,source,m,special)
 lanes=raster([p for r in routes for p in r['polygons_xz_m']],True);used=np.zeros(SHAPE,bool);holdings=[];placements=[];doors=[];safe_ids={r['source_id']for r in load(TERR/'all_blocks_r01/body_boundary_audit.json')['rows']if r['status']=='COMPLETE_LEVEL_BODY_BOUNDARY'};retire=load(HERE/'input.json')['restorable_candidates'];retired=set();network={f:raster([p for r in routes if r['floor_y_m']==f for p in r['polygons_xz_m']])|public[f]for f in bands};yaw_values=[math.radians(a)for a in list(range(0,360,15))+[-48,42,132,222,-26,64,154,244]]
 # Precompute feasible whole tight holdings on native floor. Greedy competition
 # favours connected frontage and useful roof area, never scattered small props.
 candidates=[]
 for floor in bands:
  allowed=eligible&bands[floor]&~lanes
  distance=ndimage.distance_transform_edt(~network[floor])*GRID
  for ti,(key,hpoly)in enumerate(TYPES):
   for yaw in yaw_values:
    valid=valid_positions(allowed,hpoly,yaw);zz,xx=np.where(valid)
    if not len(xx):continue
    # Every candidate gate must face an existing pre-reserved lane/road within
    # eight metres; the front connector is reserved before accepting its roof.
    gate=xform([0,max(q[1]for q in hpoly)],[0,0],yaw)
    gx=np.rint(xx+gate[0]/GRID).astype(int);gz=np.rint(zz+gate[1]/GRID).astype(int);ok=(gx>=0)&(gx<NX)&(gz>=0)&(gz<NZ);ii=np.where(ok)[0];ii=ii[distance[gz[ii],gx[ii]]<=8]
    # Half-metre exact candidates, subsampled to2m for bounded search.
    ii=ii[(zz[ii]%4==0)&(xx[ii]%4==0)]
    for j in ii:candidates.append((native[key]['roof_area_m2']/(geo.polygon_area(hpoly))+.10*(6-ti)/6-.015*distance[gz[j],gx[j]],floor,ti,yaw,int(zz[j]),int(xx[j]),gate))
  print('candidate count',floor,len(candidates),flush=True)
 candidates.sort(reverse=True,key=lambda q:q[0]);obstacle=np.zeros(SHAPE,bool)
 for _,floor,ti,yaw,z,x,gate_delta in candidates:
  key,hpoly=TYPES[ti];center=point((z,x));hp=transform([hpoly],center,yaw)[0];hm=raster([hp],True)
  if np.any(hm&used):continue
  
  if key=='working_r01_bank_joinery':
   bank_count=sum(p['asset_key'].startswith('working_r01_bank_')for p in placements);key=['working_r01_bank_joinery','working_r01_bank_loft_store','working_r01_bank_craft_lodging'][bank_count%3]
  n=native[key];gate=[center[0]+gate_delta[0],center[1]+gate_delta[1]];start=nearest(clear[floor]&~used,gate,3)
  # Route the gate to the already reserved network without crossing another
  # holding. The fixed backbone was established before this occupancy pass.
  free=clear[floor]&~used;goals=network[floor]&free;line=astar(free,start,goals)
  if not line:continue
  line=[gate]+line;line=shortcut(line,bands[floor]&~used);rp=ribbons(line,3.5);rm=raster(rp,True)
  foot=transform(n['foundation_local_polygons_xz_m'],center,yaw);roof=transform(n['roof_local_polygons_xz_m'],center,yaw);walk=transform(n['walking_local_polygons_xz_m'],center,yaw)
  if np.any(rm&raster(roof,True))or np.any(rm&used):continue
  count=len(holdings)+1;hid=f'BLOCK_001:R8_D{count:03}';pid=hid+':ATTACHED_FABRIC';court=n['court_local_polygon_xz_m']or rect(-hpoly[2][0]+2,6,hpoly[2][0]-2,max(q[1]for q in hpoly)-1);cp=transform([court],center,yaw);palette=n['asset']['native_metadata']['palette'];p=dict(id=pid,holding_id=hid,block_id='BLOCK_001',asset_key=key,position_m=[center[0],floor-.5,center[1]],yaw_rad=yaw,scale=[1,1,1],finished_floor_y_m=floor,palette_id=palette,source_pack='district_fabric_r01',native_foundation_polygons_xz_m=foot,native_walking_obstacles_xz_m=walk,native_roof_polygons_xz_m=roof,actual_door_ids=[],roof_area_m2=n['roof_area_m2'],foundation_area_m2=n['foundation_area_m2'],role=n['asset']['native_metadata']['role'],activation_status='Bulk native candidate; exact terrain, routes and actual view pending')
  for d0 in n['doors']:
   d=copy.deepcopy(d0);q=d['actual_local_xyz_m'];wxz=xform([q[0],q[2]],center,yaw);d.update(id=pid+':'+d['id'],parcel_id=pid,holding_id=hid,actual_door_xyz_m=[wxz[0],floor-.5+q[1],wxz[1]],outward_xz=xform(d['outward_local_xz'],[0,0],yaw),threshold_lip_xz_m=xform(d['threshold_lip_local_xz_m'],center,yaw),render_sha256=n['asset']['render_sha256']);doors.append(d);p['actual_door_ids'].append(d['id'])
  ids=[]
  for old in retire:
   if old['source_id']not in safe_ids:continue
   if geo.intersection_area(old['actual_native_outer_footprint_xz_m'],hp)>1e-7:ids.append(old['source_id']);retired.add(old['source_id'])
  holdings.append(dict(id=hid,parcel_id=pid,floor_y_m=floor,holding_polygon_xz_m=hp,core_court_polygons_xz_m=cp,gate_position_xz_m=gate,external_route=line,external_route_polygons_xz_m=rp,external_width_m=3.5,retired_source_ids=ids,native_roof_area_m2=n['roof_area_m2'],holding_area_m2=geo.polygon_area(hp),design='Tight native parcel frontage with actual open court and pre-reserved shared access.'))
  placements.append(p);used|=hm|rm;obstacle|=raster(roof,True)
  if count%5==0:print('placed',count,round(sum(q['roof_area_m2']for q in placements)),flush=True)
 # Any ordinary body obstructing an accepted backbone is explicitly retired,
 # only if it passed the source boundary proof. Others were hard obstacles.
 route_mask=raster([p for r in routes for p in r['polygons_xz_m']],True)
 for old in retire:
  if old['source_id']in safe_ids and np.any(route_mask&raster([old['actual_native_outer_footprint_xz_m']])):retired.add(old['source_id'])
 projection=load(PLAN/'native_projection.json');before=[i for i in projection['instances']if i['source_pack']=='ordinary'and any(r['source_id']==i['id']for r in retire)];oldroof=sum(i['roof_area_m2']for i in before);removed=sum(i['roof_area_m2']for i in before if i['id']in retired);newroof=sum(p['roof_area_m2']for p in placements)
 result=dict(schema='riverstone.district_fabric.selected_layout.v1',source_plan=ref(HERE/'owner_route_source_snapshot.json'),native_local=ref(HERE/'native_local.json'),planning_masks=ref(HERE/'planning_masks.npz'),shared_private_routes=routes,holdings=holdings,placements=placements,actual_doors=doors,retired_source_ids=sorted(retired),retirement_records=[r for r in retire if r['source_id']in retired],retired_foundation_proxy_ids=[k+':owned_foundation'for k in sorted(retired)],summary=dict(holdings=len(holdings),native_roof_m2=newroof,holding_area_m2=sum(h['holding_area_m2']for h in holdings),actual_exterior_doors=len(doors),retired_ordinary_instances=len(retired),before_ordinary_roof_m2=oldroof,retired_ordinary_roof_m2=removed,after_ordinary_roof_m2=oldroof-removed+newroof,net_ordinary_roof_gain_m2=newroof-removed,shared_private_routes=len(routes)),scope='Whole B1 tight district parcel candidate; finite land-use allocation and actual route/terrain audit follow.');write(HERE/'selected_layout.json',result);print(json.dumps(result['summary'],indent=2));return result
if __name__=='__main__':run()
