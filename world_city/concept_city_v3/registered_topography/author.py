"""Image-registered fictional terrain and finite water source contract.

No common compiler invocation. Pixel traces are observations; heights, flow roles,
road grades and occluded connections are authored, reviewable inferences.
"""
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
from world_city.runtime_city.checks.placement import convex_difference,polygon_area,convex_intersection
HERE=Path(__file__).resolve().parent;CITY=HERE.parent
CONTROL_PATH=CITY/'image_registration/controls.json';CONTROL_BYTES=CONTROL_PATH.read_bytes()
CONTROLS=json.loads(CONTROL_BYTES);CONTROLS_SHA256=hashlib.sha256(CONTROL_BYTES).hexdigest()
CAM=CONTROLS['camera_model'];S=CAM['scale_px_per_m'];YAW=math.radians(CAM['yaw_degrees']);EL=math.radians(CAM['elevation_degrees']);CX,CY=CAM['offset_pixel_xy']
ROAD_GRADE=.10;BASE_Y=1.
ROAD_CONTROL_PATH=CITY/'registered_source/road_controls.json'
ROAD_CONTROL_BYTES=ROAD_CONTROL_PATH.read_bytes() if ROAD_CONTROL_PATH.exists() else b'{}'
ROAD_CONTROL_DATA=json.loads(ROAD_CONTROL_BYTES)
ROAD_CONTROLS=ROAD_CONTROL_DATA.get('roads',CONTROLS['roads'])
ROAD_CONTROLS_SHA256=hashlib.sha256(ROAD_CONTROL_BYTES).hexdigest()
POLYS={p['id']:p for p in CONTROLS['polygons']};ESTATES={p['id']:p for p in CONTROLS['estates']}
WALL_LEVELS=[24,24,16,16,18,18,14,14,14,14,14,8,3,2.5,2.2,2.2,2.2,2.2,2.2,2.2,8,8,8,8,12,18,24]
ROAD_LEVELS={
 'UPPER_CONTOUR':[10,10,10,10,10,10,10,9,7,5],
 'MARKET_CONTOUR':[8,8,6,6,7,7,6,5,3.5],
 'LOWER_CONTOUR':[8,5,4.5,4,4,4,4,3,2.5],
 'SOUTH_MARKET_AXIS':[2.2,2.3,2.6,3,3.5,4,4,4],
 'MARKET_NORTH':[4,5.5,7,8,10,11.5,14,16,17],
 'CATHEDRAL_APPROACH':[10,11.5,13,14],
 'NOBLE_RISE':[10,12,13.5,16,16],
 'PORT_QUAY':[2.2]*5,'MAIN_BRIDGE':[2.2,2.4,2.4,2.2]}


def project(x,y,z):
 return [CX+S*(math.cos(YAW)*x-math.sin(YAW)*z),CY+S*(math.sin(EL)*math.sin(YAW)*x-math.cos(EL)*y+math.sin(EL)*math.cos(YAW)*z)]

def inverse(pixel,y):
 u=(pixel[0]-CX)/S;v=((pixel[1]-CY)/S+math.cos(EL)*y)/math.sin(EL)
 return [math.cos(YAW)*u+math.sin(YAW)*v,y,-math.sin(YAW)*u+math.cos(YAW)*v]

def _xz(p):return [p[0],p[2]]
def _poly(control):return [_xz(inverse(p,control['assumed_height_m'])) for p in control['trace_pixel_xy']]
def _bounds(p):return [min(q[0] for q in p),min(q[1] for q in p),max(q[0] for q in p),max(q[1] for q in p)]
def _overlap(a,b):return min(a[2],b[2])>=max(a[0],b[0]) and min(a[3],b[3])>=max(a[1],b[1])
def _inside(x,z,poly):
 inside=False
 for a,b in zip(poly,poly[1:]+poly[:1]):
  cross=(b[0]-a[0])*(z-a[1])-(b[1]-a[1])*(x-a[0])
  if abs(cross)<1e-8 and min(a[0],b[0])-1e-8<=x<=max(a[0],b[0])+1e-8 and min(a[1],b[1])-1e-8<=z<=max(a[1],b[1])+1e-8:return True
  if (a[1]>z)!=(b[1]>z) and x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]:inside=not inside
 return inside

def _project(x,z,a,b):
 dx,dz=b[0]-a[0],b[1]-a[1];den=dx*dx+dz*dz
 t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/den)) if den else 0
 return math.hypot(x-a[0]-t*dx,z-a[1]-t*dz),t

def _strip(a,b,width):
 length=math.dist(a,b)
 if length<1e-9:return []
 nx,nz=-(b[1]-a[1])*width/2/length,(b[0]-a[0])*width/2/length
 return [[a[0]+nx,a[1]+nz],[a[0]-nx,a[1]-nz],[b[0]-nx,b[1]-nz],[b[0]+nx,b[1]+nz]]

def _clean(poly):
 out=[]
 for p in poly:
  if not out or math.dist(p,out[-1])>1e-8:out.append(p)
 if len(out)>1 and math.dist(out[0],out[-1])<1e-8:out.pop()
 return out

def _hull(points):
 pts=sorted(set(tuple(p) for p in points))
 def half(ps):
  out=[]
  for p in ps:
   while len(out)>1 and (out[-1][0]-out[-2][0])*(p[1]-out[-2][1])-(out[-1][1]-out[-2][1])*(p[0]-out[-2][0])<=0:out.pop()
   out.append(p)
  return out
 return [list(p) for p in half(pts)[:-1]+half(reversed(pts))[:-1]]


def river_water_y(x):return 1.2-.0035*(x+470)

# Each point is re-inverted at its authored water level, rather than keeping Y=0 XZ.
WTRACE={w['id']:w for w in CONTROLS['water']}
WLEVELS={'SPRING_VISIBLE':[24,23,21,19,17.2,16],
 'NORTHERN_CHANNEL_VISIBLE':[16,15.5,15,14.4,13.6,12.8],
 'CRAFT_CANAL_VISIBLE':[1.6,1.4,.6,-.2,-.6,-.8],
 'EAST_CHANNEL_VISIBLE':[1.3,1.2,1.1,.9,.6,.2,-.4,-.8,-1.7]}
WATERS=[]
for wid,levels in WLEVELS.items():
 trace=WTRACE[wid];xyz=[inverse(p,h) for p,h in zip(trace['trace_pixel_xy'],levels)]
 WATERS.append(dict(id=wid,polyline_xz_m=[_xz(p) for p in xyz],levels_m=levels,width_m=trace['design_width_m'],
     trace_pixel_xy=trace['trace_pixel_xy'],resolved_world_xyz_m=xyz,bed_depth_m=.6 if trace['design_width_m']==2 else .9))
WATER_BY_ID={w['id']:w for w in WATERS}
BASIN=_poly(POLYS['BASIN'])
AREA_PLATEAUS=[(_poly(POLYS[id]),POLYS[id]['assumed_height_m']) for id in ['MARKET','PORT','POOR']]
REGISTERED_PLAN_PATH=CITY/'registered_source/plan.json'
REGISTERED_PLAN=json.loads(REGISTERED_PLAN_PATH.read_bytes()) if REGISTERED_PLAN_PATH.exists() else {}
# Terminate spring inside the basin, and start its overflow inside: exact domains clip at the basin edge.
WATER_BY_ID['SPRING_VISIBLE']['polyline_xz_m'][-1]=_xz(inverse([685,114],16))
WATER_BY_ID['NORTHERN_CHANNEL_VISIBLE']['polyline_xz_m'][0]=_xz(inverse([780,121],16))
# Correspondence repairs are explicit and stored alongside the untouched observed trace.
for wid,index,pixel in [('SPRING_VISIBLE',-1,[685,114]),('NORTHERN_CHANNEL_VISIBLE',0,[780,121])]:
 w=WATER_BY_ID[wid];w['original_trace_pixel_xy']=[list(p) for p in w['trace_pixel_xy']]
 w['trace_pixel_xy']=[list(p) for p in w['trace_pixel_xy']];original=w['trace_pixel_xy'][index]
 w['trace_pixel_xy'][index]=pixel
 w['endpoint_repairs']=[dict(index=index,original_pixel_xy=original,resolved_pixel_xy=pixel,
     reason='extend through observed receiver bank only far enough for exact finite shoreline clipping')]
w=WATER_BY_ID['EAST_CHANNEL_VISIBLE'];pixel=w['trace_pixel_xy'][-1];y=w['levels_m'][-1]
for _ in range(8):q=inverse(pixel,y);y=river_water_y(q[0])
w['polyline_xz_m'][-1]=_xz(inverse(pixel,y));w['levels_m'][-1]=y
for w in WATERS:w['resolved_world_xyz_m']=[[p[0],h,p[1]] for p,h in zip(w['polyline_xz_m'],w['levels_m'])]
SHORE=[]
for pixel in WTRACE['RIVER_NORTH_SHORE']['trace_pixel_xy']:
 y=0.
 for _ in range(8):q=inverse(pixel,y);y=river_water_y(q[0])
 SHORE.append(_xz(inverse(pixel,y)))
RIVER_POLYS=[[p,q,[q[0],q[1]+120],[p[0],p[1]+120]] for p,q in zip(SHORE,SHORE[1:])]


def _nearest_edge(point,poly):
 return min(zip(poly,poly[1:]+poly[:1]),key=lambda ab:_project(*point,*ab)[0])

def _line_value(point,edge):
 a,b=edge;return (b[0]-a[0])*(point[1]-a[1])-(b[1]-a[1])*(point[0]-a[0])

MOUTHS={}
for wid,end,receiver in [('SPRING_VISIBLE',-1,'basin'),('NORTHERN_CHANNEL_VISIBLE',0,'basin'),('EAST_CHANNEL_VISIBLE',-1,'river')]:
 w=WATER_BY_ID[wid];p=w['polyline_xz_m'][end]
 edge=_nearest_edge(p,BASIN) if receiver=='basin' else min(zip(SHORE,SHORE[1:]),key=lambda ab:_project(*p,*ab)[0])
 adjacent=1 if end==0 else len(w['levels_m'])-2;q=w['polyline_xz_m'][adjacent]
 target=16 if receiver=='basin' else river_water_y(q[0]);den=_line_value(q,edge)
 MOUTHS[wid]=dict(edge=edge,receiver=receiver,end=end,segment_index=0 if end==0 else len(w['levels_m'])-2,k=(w['levels_m'][adjacent]-target)/den)


def _segment_head(w,x,z,i):
 a,b=w['polyline_xz_m'][i:i+2];d,t=_project(x,z,a,b);h=w['levels_m'][i]+t*(w['levels_m'][i+1]-w['levels_m'][i])
 m=MOUTHS.get(w['id'])
 if m and i==m['segment_index']:
  h=(16 if m['receiver']=='basin' else river_water_y(x))+m['k']*_line_value([x,z],m['edge'])
 return h,d


def water_height_at(surface_id,x,z,segment_index=0):
 if surface_id=='MAIN_RIVER':return river_water_y(x)
 if surface_id=='NORTHERN_RESERVOIR':return 16.
 w=WATER_BY_ID[surface_id];nearest=None;weighted=[]
 mouth=MOUTHS.get(surface_id)
 if mouth and mouth['receiver']=='basin' and _inside(x,z,BASIN):return 16.
 if mouth and mouth['receiver']=='river' and any(_inside(x,z,p) for p in RIVER_POLYS):return river_water_y(x)
 network=[WATER_BY_ID['CRAFT_CANAL_VISIBLE'],WATER_BY_ID['EAST_CHANNEL_VISIBLE']] if surface_id in ['CRAFT_CANAL_VISIBLE','EAST_CHANNEL_VISIBLE'] else [w]
 for ww in network:
  radius=ww['width_m']*1.5
  for i in range(len(ww['levels_m'])-1):
   h,d=_segment_head(ww,x,z,i)
   if nearest is None or d<nearest[0]:nearest=(d,h)
   if d<radius:weighted.append((h,(1-(d/radius)**2)**2))
 result=sum(h*v for h,v in weighted)/sum(v for h,v in weighted) if weighted else nearest[1]
 if surface_id in ['CRAFT_CANAL_VISIBLE','EAST_CHANNEL_VISIBLE']:
  junction=WATER_BY_ID['CRAFT_CANAL_VISIBLE']['polyline_xz_m'][-1];distance=math.dist([x,z],junction)
  blend=max(0,min(1,(distance-12)/12));result=-.8+blend*(result+.8)
 return result


_DOMAINS=None

def finite_water_polygons():
 global _DOMAINS
 if _DOMAINS is not None:return _DOMAINS
 _DOMAINS=[]
 for i,p in enumerate(RIVER_POLYS):_DOMAINS.append(dict(surface_id='MAIN_RIVER',segment_index=i,polygon_xz_m=p,bed_depth_m=3))
 _DOMAINS.append(dict(surface_id='NORTHERN_RESERVOIR',polygon_xz_m=BASIN,bed_depth_m=2.4,water_y_m=16))
 for w in WATERS:
  strips=[_strip(p,q,w['width_m']) for p,q in zip(w['polyline_xz_m'],w['polyline_xz_m'][1:])]
  raw=[(i,p) for i,p in enumerate(strips)]+[(i,_hull(strips[i][2:]+strips[i+1][:2])) for i in range(len(strips)-1)]
  for i,poly in raw:
   pieces=[poly] if polygon_area(poly)>1e-8 else []
   for old in _DOMAINS:
    cut=old['polygon_xz_m']
    pieces=[_clean(part) for p in pieces for part in (convex_difference(p,cut) if _overlap(_bounds(p),_bounds(cut)) else [p]) if polygon_area(part)>1e-8]
   for p in pieces:_DOMAINS.append(dict(surface_id=w['id'],segment_index=i,polygon_xz_m=p,bed_depth_m=w['bed_depth_m']))
 for d in _DOMAINS:d['vertex_y_m']=[water_height_at(d['surface_id'],*p,d.get('segment_index',0)) for p in d['polygon_xz_m']]
 return _DOMAINS


def water_samples_at(x,z):
 return [{**d,'water_y_m':water_height_at(d['surface_id'],x,z,d.get('segment_index',0))} for d in finite_water_polygons() if _inside(x,z,d['polygon_xz_m'])]


ROAD_SEEDS=[(*_xz(inverse(pixel,h)),h) for r in CONTROLS['roads'] for pixel,h in zip(r['trace_pixel_xy'],ROAD_LEVELS[r['id']])]
ROAD_SEEDS += [(*_xz(inverse(p,y)),y) for p,y in [([311,249],24),([1378,354],14),([735,148],18)]]

def dry_height_at(x,z):
 """Shared continuous <=10% street datum, augmented by supported water banks."""
 h=max(BASE_Y,*(y-ROAD_GRADE*math.hypot(x-p,z-q) for p,q,y in ROAD_SEEDS))
 for poly,floor in AREA_PLATEAUS:
  distance=0 if _inside(x,z,poly) else min(_project(x,z,p,q)[0] for p,q in zip(poly,poly[1:]+poly[:1]))
  h=max(h,floor-ROAD_GRADE*distance)
 for w in WATERS:
  for i,(p,q) in enumerate(zip(w['polyline_xz_m'],w['polyline_xz_m'][1:])):
   d,t=_project(x,z,p,q);y=w['levels_m'][i]+t*(w['levels_m'][i+1]-w['levels_m'][i])
   h=max(h,y+.6-.06*max(0,d-w['width_m']/2))
 for offset in [0,120]:
  shore=[[p[0],p[1]+offset] for p in SHORE]
  for p,q in zip(shore,shore[1:]):
   distance,t=_project(x,z,p,q);head=river_water_y(p[0]+t*(q[0]-p[0]))
   h=max(h,head+.6-.06*distance)
 # Supported reservoir bank; finite source basin is not a floating water plane.
 distance=0 if _inside(x,z,BASIN) else min(_project(x,z,p,q)[0] for p,q in zip(BASIN,BASIN[1:]+BASIN[:1]))
 h=max(h,18-.08*distance)
 return h


def road_height_at(road_id,x,z):return dry_height_at(x,z)
def path_height_at(path_id,x,z):return dry_height_at(x,z)


def registered_point(pixel,height_api=dry_height_at):
 y=4.
 for _ in range(14):
  q=inverse(pixel,y);new=height_api(q[0],q[2])
  if abs(new-y)<1e-9:break
  y=new
 return inverse(pixel,y)


_ROADS=None

def registered_roads():
 global _ROADS
 if _ROADS is None:
  _ROADS=[]
  for r in ROAD_CONTROLS:
   pixels=r['trace_pixel_xy']
   if r['id']=='RESERVOIR_SERVICE':pixels=[p for p in pixels if p!=[735,128]]
   control_pixels=list(pixels);dense=[]
   for p,q in zip(pixels,pixels[1:]):
    count=max(1,math.ceil(math.dist(p,q)/8))
    dense.extend([[p[k]+(q[k]-p[k])*i/count for k in (0,1)] for i in range(count)])
   pixels=dense+[pixels[-1]]
   xyz=[registered_point(p) for p in pixels]
   _ROADS.append(dict(id=r['id'],kind='registered_trace_road',width_m=r.get('width_m',r.get('design_width_m')),
     polyline_xz_m=[_xz(p) for p in xyz],levels_m=[p[1] for p in xyz],resolved_world_xyz_m=xyz,
     trace_pixel_xy=pixels,control_pixel_xy=control_pixels,original_trace_pixel_xy=r.get('original_trace_pixel_xy',r['trace_pixel_xy']),
     endpoint_repair='end at dry bank [735,148]; original basin-centre [735,128] remains water anchor' if r['id']=='RESERVOIR_SERVICE' else None,registration_control_id=r.get('registration_control_id',r['id']),
     maximum_vertex_grade=max(abs(p[1]-q[1])/math.dist(_xz(p),_xz(q)) for p,q in zip(xyz,xyz[1:])),
     observed_vs_inferred=r.get('observed_vs_inferred','drawn curve; grade/width authored')+'; inverse repeated at resolved grade'))
 return _ROADS


def registered_wall():
 p=POLYS['WALL'];pixels=[[178,116],[241,83],[403,67]]+p['trace_pixel_xy'][2:]
 levels=[24,24,24]+WALL_LEVELS[2:]
 xyz=[inverse(pixel,h) for pixel,h in zip(pixels,levels)]
 return dict(id='WALL',trace_pixel_xy=pixels,original_trace_pixel_xy=p['trace_pixel_xy'],levels_m=levels,world_xyz_m=xyz,
   polygon_xz_m=[_xz(p) for p in xyz],observed_vs_inferred='wall trace observed; adjacent-terrain ground Y inferred per vertex; castle wall replaces two provisional upper-left controls',
   image_space_repairs=[dict(reason='provisional city wall cut through castle; use visible castle curtain trace',replace_pixels=[[234,112],[411,81]],with_pixels=[[178,116],[241,83],[403,67]])])


_ROAD_SEG_INDEX=None

def _road_clearance(x,z):
 global _ROAD_SEG_INDEX
 if _ROAD_SEG_INDEX is None:
  _ROAD_SEG_INDEX={}
  roads=registered_roads();ids={r['id'] for r in roads}
  roads=roads+[r for r in REGISTERED_PLAN.get('roads',[]) if r['id'] not in ids]
  for r in roads:
   width=r['width_m']/2+2
   for p,q in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:]):
    bounds=[min(p[0],q[0])-width-1,min(p[1],q[1])-width-1,max(p[0],q[0])+width+1,max(p[1],q[1])+width+1]
    for ix in range(math.floor(bounds[0]/32),math.floor(bounds[2]/32)+1):
     for iz in range(math.floor(bounds[1]/32),math.floor(bounds[3]/32)+1):_ROAD_SEG_INDEX.setdefault((ix,iz),[]).append((p,q,width))
 return min((_project(x,z,p,q)[0]-width for p,q,width in _ROAD_SEG_INDEX.get((math.floor(x/32),math.floor(z/32)),[])),default=1000.)


def terrace_regions():
 # Later source ownership resolves image-occluded overlaps explicitly; priority is recorded, not hidden.
 ids=['CASTLE','CLERGY','MARKET','MONASTERY','TRAIN','PORT','POOR','COMMON','NOBLE']
 out=[dict(id=p['id'],polygon_xz_m=_poly(p),floor_y_m=p['assumed_height_m'],pad_floor_y_m=p['assumed_height_m'],
           trace_pixel_xy=p['trace_pixel_xy'],evidence='image area trace with authored level bench') for p in [POLYS[i] for i in ids]]
 for p in CONTROLS['estates']:
  refinement=ROAD_CONTROL_DATA.get('estate_edge_refinements',{}).get(p['id'])
  pixels=refinement['pixels'] if refinement else p['trace_pixel_xy']
  levels=refinement['ys'] if refinement else [p['assumed_height_m']]*len(pixels)
  xyz=[inverse(pixel,y) for pixel,y in zip(pixels,levels)]
  out.append(dict(id=p['id'],polygon_xz_m=[_xz(q) for q in xyz],floor_y_m=p['assumed_height_m'],pad_floor_y_m=p['assumed_height_m'],
     boundary_vertices_xyz_m=xyz,trace_pixel_xy=pixels,original_trace_pixel_xy=p['trace_pixel_xy'],
     evidence=refinement['reason'] if refinement else 'estate silhouette at authored bench datum',
     boundary_semantics='shared retaining-wall FOOT controls; bench top remains floor_y_m; do not flatten wall foot to upper bench'))
 return out


_WALL_SEGMENTS=None

def wall_ground_height_at(x,z):
    global _WALL_SEGMENTS
    if _WALL_SEGMENTS is None:
        points=registered_wall()['world_xyz_m'];_WALL_SEGMENTS=list(zip(points,points[1:]+points[:1]))
    best=None
    for p,q in _WALL_SEGMENTS:
        distance,t=_project(x,z,_xz(p),_xz(q));y=p[1]+t*(q[1]-p[1])
        if best is None or distance<best[0]:best=(distance,y)
    return best


def land_base_height_at(x,z):
    h=dry_height_at(x,z)
    for region in _REGIONS or terrace_regions():
        if region['id']=='NOBLE':continue
        poly=region['polygon_xz_m'];distance=0 if _inside(x,z,poly) else min(_project(x,z,p,q)[0] for p,q in zip(poly,poly[1:]+poly[:1]))
        h=max(h,region['floor_y_m']-.12*distance)
    return h


_REGIONS=None

def land_height_at(x,z):
 global _REGIONS
 if _REGIONS is None:_REGIONS=terrace_regions()
 road=dry_height_at(x,z)
 if _road_clearance(x,z)<=0:return road
 wall_distance,wall_y=wall_ground_height_at(x,z)
 if wall_distance<=2:return wall_y
 # Explicit small/foreground estate regions precede the larger noble quarter.
 priority=['CASTLE','E7','E6','E5','E4','E3','E2','E1','CLERGY','MARKET','MONASTERY','TRAIN','PORT','POOR','COMMON','NOBLE']
 by={r['id']:r for r in _REGIONS}
 for id in priority:
  p=by[id]
  if _inside(x,z,p['polygon_xz_m']):return p['floor_y_m']
 return land_base_height_at(x,z)


def height_at(x,z):
 if not math.isfinite(x) or not math.isfinite(z):raise ValueError('Finite XZ metres required')
 wet=water_samples_at(x,z)
 if wet:return min(w['water_y_m']-w['bed_depth_m'] for w in wet)
 return land_height_at(x,z)


def building_floor_at(x,z):
 """Finished floor, not cached asset origin; use originY=floor-door_localY."""
 return land_height_at(x,z)


def _line_interval(a,b,poly):
    lo,hi=0.,1.;area=sum(p[0]*q[1]-p[1]*q[0] for p,q in zip(poly,poly[1:]+poly[:1]));sign=1 if area>=0 else -1
    for p,q in zip(poly,poly[1:]+poly[:1]):
        f0=sign*((q[0]-p[0])*(a[1]-p[1])-(q[1]-p[1])*(a[0]-p[0]))
        f1=sign*((q[0]-p[0])*(b[1]-p[1])-(q[1]-p[1])*(b[0]-p[0]));delta=f1-f0
        if abs(delta)<1e-10:
            if f0< -1e-8:return None
            continue
        if delta>0:lo=max(lo,-f0/delta)
        else:hi=min(hi,-f0/delta)
        if hi<lo:return None
    return [max(0,lo),min(1,hi)] if hi>=0 and lo<=1 else None


def water_support_domains():
    """Finite bed surfaces and exposed bank faces, with internal joins removed."""
    domains=finite_water_polygons();beds=[];banks=[]
    for d in domains:
        poly=d['polygon_xz_m'];sid=d['surface_id'];depth=d['bed_depth_m']
        beds.append(dict(surface_id=sid,polygon_xz_m=poly,bed_depth_m=depth,
            vertex_y_m=[water_height_at(sid,*p)-depth for p in poly],lining_thickness_m=.3,
            continuous_height_api='water_height_at(surface_id,x,z) - bed_depth_m'))
        for a,b in zip(poly,poly[1:]+poly[:1]):
            if sid=='MAIN_RIVER' and abs(a[0]-b[0])<1e-8 and (abs(a[0]-SHORE[0][0])<1e-8 or abs(a[0]-SHORE[-1][0])<1e-8):continue # open finite inlet/outfall, not a river-closing bank
            intervals=[]
            for other in domains:
                if other is d or not _overlap(_bounds([a,b]),_bounds(other['polygon_xz_m'])):continue
                interval=_line_interval(a,b,other['polygon_xz_m'])
                if interval and interval[1]-interval[0]>1e-8:intervals.append(interval)
            pieces=[[0,1]]
            for lo,hi in sorted(intervals):
                parts=[]
                for p,q in pieces:
                    if hi<=p or lo>=q:parts.append([p,q]);continue
                    if lo>p:parts.append([p,min(lo,q)])
                    if hi<q:parts.append([max(hi,p),q])
                pieces=parts
            for lo,hi in pieces:
                count=max(1,math.ceil(math.dist(a,b)*(hi-lo)/4))
                for i in range(count):
                    ts=[lo+(hi-lo)*j/count for j in (i,i+1)]
                    ends=[[a[k]+(b[k]-a[k])*t for k in (0,1)] for t in ts]
                    low=[water_height_at(sid,*p)-depth for p in ends];top=[land_height_at(*p) for p in ends]
                    banks.append(dict(surface_id=sid,from_xz_m=ends[0],to_xz_m=ends[1],
                        bottom_y_m=low,top_y_m=top,thickness_m=.3,
                        vertices_xyz_m=[[ends[0][0],low[0],ends[0][1]],[ends[1][0],low[1],ends[1][1]],
                                        [ends[1][0],top[1],ends[1][1]],[ends[0][0],top[0],ends[0][1]]]))
    return dict(beds=beds,exterior_banks=banks,
        ownership='bed lining inside exact wet polygons; exterior banks only; no duplicate internal join faces',
        support='coarser buried soil under .3 m lining; no physics or common-cell completion claimed')


def retaining_contract():
    """Cheap finite riser proxies; exact common ownership is a later stage."""
    out=[]
    for region in terrace_regions():
        if region['id']=='NOBLE':continue # aggregate district is not a second retaining slab
        walls=[];poly=region['polygon_xz_m'];floor=region['floor_y_m']
        for p,q in zip(poly,poly[1:]+poly[:1]):
            count=max(1,math.ceil(math.dist(p,q)/2))
            for i in range(count):
                ends=[[p[k]+(q[k]-p[k])*t/count for k in (0,1)] for t in (i,i+1)]
                mid=[(ends[0][k]+ends[1][k])/2 for k in (0,1)]
                if _road_clearance(*mid)<1:continue
                lower=[land_base_height_at(*v) for v in ends]
                if max(abs(h-floor) for h in lower)<.15:continue
                walls.append(dict(from_xz_m=ends[0],to_xz_m=ends[1],pad_y_m=floor,
                    source_ground_y_m=lower,top_y_m=max(floor,*lower),bottom_y_m=min(floor,*lower),
                    thickness_m=.4,tier_count_for_4m_max=max(1,math.ceil(max(abs(h-floor) for h in lower)/4)),
                    status='sampled riser proxy outside protected street; adjacent exact area owner still requires final clipping'))
        out.append(dict(**region,retaining_segments=walls,
            road_opening_rule='entire road width and 2 m shoulders excluded; no road is quantized into stairs'))
    return out


def _graph():
 nodes=[];edges=[]
 def node(id,xz,h,network):nodes.append(dict(id=id,xz_m=xz,head_y_m=h,network=network))
 def edge(a,b,mode='gravity',**kw):edges.append(dict(source=a,target=b,mode=mode,**kw))
 node('RAW_SPRING',WATER_BY_ID['SPRING_VISIBLE']['polyline_xz_m'][0],24,'raw_source')
 center=[sum(p[k] for p in BASIN)/len(BASIN) for k in (0,1)]
 node('RESERVOIR',center,16,'raw_storage');edge('RAW_SPRING','RESERVOIR')
 node('COVERED_CISTERN',center,15.5,'protected_supply');edge('RESERVOIR','COVERED_CISTERN')
 for id,h in [('cathedral',14.5),('market',4.6),('monastery',8.5)]:
  point=next(a['inferred_target_world_xyz_m'] for a in CONTROLS['anchors'] if a['id']==id)
  node(id.upper()+'_DRAW',_xz(point),h,'protected_supply');edge('COVERED_CISTERN',id.upper()+'_DRAW')
 node('CASTLE_CISTERN',_xz(CONTROLS['anchors'][0]['inferred_target_world_xyz_m']),22.8,'local_rain')
 node('CASTLE_DRAW',_xz(CONTROLS['anchors'][0]['inferred_target_world_xyz_m']),24.6,'local_lifted_draw');edge('CASTLE_CISTERN','CASTLE_DRAW','manual_lift',energy_source='manual bucket or pump, source proposal')
 north=WATER_BY_ID['NORTHERN_CHANNEL_VISIBLE'];node('OVERFLOW_HEAD',north['polyline_xz_m'][-1],12.8,'industrial_nonpotable');edge('RESERVOIR','OVERFLOW_HEAD',role='one-way overflow, no dirty return')
 for wid in ['CRAFT_CANAL_VISIBLE','EAST_CHANNEL_VISIBLE']:
  w=WATER_BY_ID[wid]
  for i,(p,h) in enumerate(zip(w['polyline_xz_m'],w['levels_m'])):
   if wid=='EAST_CHANNEL_VISIBLE' and i==len(w['levels_m'])-1:h=river_water_y(p[0])
   node(wid+':'+str(i),p,h,'industrial_nonpotable')
   if i:edge(wid+':'+str(i-1),wid+':'+str(i),role='controlled descent; flow capacity unverified')
  edge('OVERFLOW_HEAD',wid+':0',role='authored covered descending service feeder; not observed in image')
 node('CANAL_JOIN',WATER_BY_ID['CRAFT_CANAL_VISIBLE']['polyline_xz_m'][-1],-.8,'industrial_nonpotable')
 edge('CRAFT_CANAL_VISIBLE:5','CANAL_JOIN',mode='level_join',head_tolerance_m=.02)
 edge('EAST_CHANNEL_VISIBLE:7','CANAL_JOIN',mode='level_join',head_tolerance_m=.02)
 out=WATER_BY_ID['EAST_CHANNEL_VISIBLE']['polyline_xz_m'][-1];node('RIVER_OUTFALL',out,river_water_y(out[0])-.01,'receiving_river');edge('CANAL_JOIN','RIVER_OUTFALL')
 return dict(nodes=nodes,edges=edges,quality='unverified; raw storage/settling is not potable treatment',
    interpretation='visible north channel is assigned one-way overflow/service use; separate covered drinking conduit, local high-quarter cisterns',
    missing_proof=['spring yield','flow capacity','flood/backwater','soil and structural support','historical site provenance'])


def build_contract():
 plan_path=CITY/'registered_source/plan.json';plan_hash=hashlib.sha256(plan_path.read_bytes()).hexdigest() if plan_path.exists() else None
 surfaces=[dict(id='MAIN_RIVER',polyline_xz_m=[[p[0],p[1]+60] for p in SHORE],width_m=120,levels_m=[river_water_y(p[0]) for p in SHORE]),
           dict(id='NORTHERN_RESERVOIR',polygon_xz_m=BASIN,water_y_m=16,bed_depth_m=2.4)]+[dict(w,
      resolved_world_xyz_m=[[p[0],water_height_at(w['id'],*p),p[1]] for p in w['polyline_xz_m']],
      mouth_repair='finite source channel extends into receiving water only for exact clip; bank head matches receiver' if w['id'] in MOUTHS else None) for w in WATERS]
 return dict(schema='riverstone.registered_terrain.v1',status='cheap_registered_source_proxy_not_voxel_or_physics_approval',
  controls_sha256=CONTROLS_SHA256,road_controls_sha256=ROAD_CONTROLS_SHA256,source_plan_sha256=plan_hash,source_image_sha256=CONTROLS['source_image_sha256'],
  camera_model=CAM,matched_engine_camera=CONTROLS['matched_engine_camera'],review_bounds_xz_m=[-530,-530,530,650],
  registered_wall=registered_wall(),terrace_regions=terrace_regions(),neighborhood_terraces=retaining_contract(),roads=registered_roads(),road_profiles={r['id']:r for r in registered_roads()},
  water_surfaces=surfaces,water_domain_polygons=finite_water_polygons(),water_graph=_graph(),water_support=water_support_domains(),
  grade_contract=dict(road_grade_limit=.12,seed_cone_grade=.10,shared_continuous_decks=True,
    terrace_road_rule='whole precinct/estate benches exclude full road width plus 2 m shoulders; retaining edges are barriers outside those corridors',
    finished_floor='pad_floor_y_m is actual entrance floor; cached origin_y=pad_floor_y_m-door_local_y, never floor+0.5 by accident'),
  support_contract=dict(feeder_bed_depth_m=.6,canal_bed_depth_m=.9,river_bed_depth_m=3,reservoir_bed_y_m=13.6,
    banks='finite clipped edge from land_height_at to water_height_at minus bed depth; no unsupported water-only ribbon',
    common_backend='existing coordinate_planes/core/render_data later; macro ground and sparse small surface caps only'),
  ambiguity_ledger=[
    'Painting contains occlusion and perspective inconsistency; exact inverse of a single orthographic camera is a design registration, not survey recovery.',
    'Per-wall-vertex ground datums inferred from adjacent terraces; Y=0 wall was not retained.',
    'Estate overlap ownership needs shared image-space boundary correction from registered_source; raw traces retained here.',
    'Reservoir overflow is chosen as the industrial source for visible southeast canals; covered connectors are authored and unobserved.',
    'Main river south shore is inferred 120 m in world Z from traced north shore; river flow is authored west to east.',
    'Water heads and finished floors are inferred, not measured from pixels; no hydraulic, staircase or capsule approval.'],
  frozen_versions_modified=False)


def main():
 c=build_contract();(HERE/'contract.json').write_text(json.dumps(c,indent=2,sort_keys=True)+'\n')
 print(json.dumps(dict(controls_sha256=CONTROLS_SHA256,roads=len(c['roads']),terraces=len(c['terrace_regions']),water_domains=len(c['water_domain_polygons']),source_plan_sha256=c['source_plan_sha256']),indent=2))
if __name__=='__main__':main()
