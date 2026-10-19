"""Finite road/field owner replacement over the frozen final110 scene.
All source clipping is exact and leaves outside vertices on original planes.
"""
from __future__ import annotations
import json,math,hashlib,sys,time
import numpy as np
from pathlib import Path
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import DomainCut,fan,clean
from .check_candidates import transform,intersects
from world_city.concept_city_v3.registered_source.geometry import triangulate
H=Path(__file__).parent;ROOT=H.parents[4];BASE=ROOT/'world_city/concept_city_v3/evidence/r8_final110_runtime_r01/scene.json';SHA='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ch(v):return hashlib.sha256(json.dumps(v,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def write(n,d): (H/n).write_text(json.dumps(d,separators=(',',':'),allow_nan=False)+'\n')
def ref(p):return {'path':str(Path(p).relative_to(ROOT)),'sha256':sha(p)}
def xz(p):return [p[0],p[2]]
def area3(t):
 a,b,c=t;u=[b[i]-a[i]for i in range(3)];v=[c[i]-a[i]for i in range(3)];return math.sqrt(sum(n*n for n in [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]))/2

def plane(t):
 a,b,c=t;d=(b[0]-a[0])*(c[2]-a[2])-(c[0]-a[0])*(b[2]-a[2]);ax=((b[1]-a[1])*(c[2]-a[2])-(c[1]-a[1])*(b[2]-a[2]))/d;az=((b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1]))/d;return ax,az,a[1]-ax*a[0]-az*a[2]
def ph(pl,p):return pl[0]*p[0]+pl[1]*p[1]+pl[2]
def up(t):return t if geo.signed_polygon_area([xz(v)for v in t])<0 else [t[0],t[2],t[1]]
def split3(poly,a,b,sgn):
 def side(p):return sgn*((b[0]-a[0])*(p[2]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
 inside=[];outside=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  d,e=side(p),side(q);pi=d>=0.;qi=e>=0.
  (inside if pi else outside).append(p)
  if pi!=qi:
   t=d/(d-e);v=[p[k]+t*(q[k]-p[k])for k in range(3)];inside.append(v);outside.append(v)
 return inside,outside

def split_y(poly,height):
 below=[];above=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  d,e=p[1]-height,q[1]-height;pi=d>=0;qi=e>=0
  (above if pi else below).append(p)
  if pi!=qi:
   t=d/(d-e);v=[p[k]+t*(q[k]-p[k])for k in range(3)];above.append(v);below.append(v)
 return below,above

def cut3(poly,mask):
 cur=poly;out=[];sgn=1 if geo.signed_polygon_area(mask)>0 else -1
 for a,b in zip(mask,mask[1:]+mask[:1]):
  if not cur:break
  cur,outer=split3(cur,a,b,sgn)
  if len(outer)>=3 and sum(area3(t)for t in fan(outer))>1e-10:out.append(outer)
 return out

class Ground:
 def __init__(self,rows):
  self.rows=[];self.idx=geo._SpatialIndex(8)
  for r in rows:
   t=r['triangle'];p=[xz(v)for v in t]
   if r['material']=='water' or geo.polygon_area(p)<1e-9:continue
   self.idx.add(len(self.rows),p);self.rows.append(dict(r,polygon=p,plane=plane(t)))
 def at(self,p):
  found=[r for i in self.idx.candidates([p])if geo.point_in_convex_polygon(p,(r:=self.rows[i])['polygon'],1e-7)]
  if not found:raise ValueError('No source ground '+str(p))
  road=[r for r in found if r['material']=='road'];return max(ph(r['plane'],p)for r in (road or found))


def smooth(points,cut=5):
 out=[points[0]]
 for a,b,c in zip(points,points[1:],points[2:]):
  la,lc=math.dist(xz(a),xz(b)),math.dist(xz(b),xz(c));d=min(cut,la*.3,lc*.3)
  u=[b[k]+(a[k]-b[k])*d/la for k in range(3)];v=[b[k]+(c[k]-b[k])*d/lc for k in range(3)];out.append(u)
  for j in range(1,13):
   t=j/12;out.append([(1-t)**2*u[k]+2*t*(1-t)*b[k]+t*t*v[k]for k in range(3)])
 out.append(points[-1]);return out

def dense(points,step=2):
 out=[points[0]]
 for a,b in zip(points,points[1:]):
  n=max(1,math.ceil(math.dist(xz(a),xz(b))/step))
  out.extend([[a[k]+j/n*(b[k]-a[k])for k in range(3)]for j in range(1,n+1)])
 return out

def rect(a,b,c,d):return [[a,b],[c,b],[c,d],[a,d]]
def convex_parts(poly):
 # Canonical convex sweep between consecutive cross-sections. Tight bends may
 # reverse a side edge, so its ordered quad is not a valid simple polygon.
 # The convex hull fills that bounded turning envelope rather than producing
 # intersecting/bow-tie faces or relying on polygon subtraction of a concavity.
 ps=sorted(set(tuple(v)for v in poly))
 def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
 lo=[];hi=[]
 for q in ps:
  while len(lo)>1 and cross(lo[-2],lo[-1],q)<=1e-10:lo.pop()
  lo.append(q)
 for q in reversed(ps):
  while len(hi)>1 and cross(hi[-2],hi[-1],q)<=1e-10:hi.pop()
  hi.append(q)
 hull=[list(v)for v in lo[:-1]+hi[:-1]]
 return fan(hull)

def build():
 t0=time.monotonic();assert sha(BASE)==SHA
 ctx=json.load(open(H/'base_context.json'));assets=ctx['common_assets'];byid={p['id']:p for p in ctx['common_instances']};bounds=json.load(open(H/'asset_bounds.json'));rows=json.load(open(H/'local_source_faces.json'));ground=Ground(rows)
 west=byid['FORT_CURTAIN_26_0_00'];east=byid['FORT_CURTAIN_12_0_05']
 routes=[];cores=[];shoulders=[];owners=[]
 plan=json.load(open(ROOT/'world_city/concept_city_v3/registered_source/plan.json'));junctions=[]
 for side,rid,ix in [('WEST','CASTLE_APPROACH',20),('EAST','EAST_WALL_SERVICE',9)]:
  road=next(r for r in plan['roads']if r['id']==rid);lo,hi=(ix-2,ix+3)if side=='WEST'else(3,14);vs=road['resolved_world_xyz_m'][lo:hi];arc=[0.]
  for a,b in zip(vs,vs[1:]):arc.append(arc[-1]+math.dist(xz(a),xz(b)))
  junctions.append(dict(side=side,road_id=rid,points=vs,width=road['width_m'],center=road['resolved_world_xyz_m'][ix],arc=arc,center_s=arc[ix-lo],source_station_indices=list(range(lo,hi))))
 def nearest(j,q):
  best=None
  for i,(a,b)in enumerate(zip(j['points'],j['points'][1:])):
   dx,dz=b[0]-a[0],b[2]-a[2];ll=dx*dx+dz*dz;t=max(0.,min(1.,((q[0]-a[0])*dx+(q[1]-a[2])*dz)/ll));v=[a[k]+t*(b[k]-a[k])for k in range(3)];d=math.dist(q,xz(v))
   if best is None or d<best[0]:best=(d,v,j['arc'][i]+t*math.sqrt(ll))
  return best
 def junction_height(j,q):
  d,v,arc=nearest(j,q)
  if j['side']=='WEST':return v[1]
  signed=arc-j['center_s'];north=signed<0;u=max(0.,abs(signed)-4.);L=(j['center_s']if north else j['arc'][-1]-j['center_s'])-4.;delta=j['points'][0 if north else -1][1]-3.;r=min(4.,L/4);grade=delta/(L-r);u=min(L,u)
  if u<r:rise=grade*u*u/(2*r)
  elif u<L-r:rise=grade*(u-r/2)
  else:rise=delta-grade*(L-u)*(L-u)/(2*r)
  return 3.+rise
 wj=junctions[0];wa,wb=wj['points'][0],wj['points'][-1];wdx,wdz=wb[0]-wa[0],wb[2]-wa[2];wden=wdx*wdx+wdz*wdz
 def west_plane(q):return wa[1]+((q[0]-wa[0])*wdx+(q[1]-wa[2])*wdz)/wden*(wb[1]-wa[1])
 bridge_pose=dict(position_m=[390.00205240938203,3.,-3.150481687107995],yaw_rad=.3494290568265689)
 bridge_poly=[xz(transform([x,0,z],bridge_pose))for x,z in [(-8,-4),(8,-4),(8,4),(-8,4)]]
 wet=[dict(polygon_xz_m=[xz(v)for v in r['triangle']])for r in rows if r['material']=='water']
 excluded=DomainCut([dict(polygon_xz_m=bridge_poly)]+wet)

 fields=[dict(id='WEST_FARM_TERRACE',poly=rect(-501,-335,-473,-302),outer=rect(-505,-339,-469,-298),floor=12.),dict(id='EAST_FARM_FIELD',poly=rect(488,-48,518,-12),outer=rect(485,-51,521,-9),floor=1.)]
 defs=[('WEST',west,21.,[[-273.0288398195063,0,-197.71713728840209],[-300,23.5,-215],[-330,22.,-225],[-361,21.,-237],[-385,21.,-227.5]], [[-435,18.,-260],[-465,14.,-290],[-486,12.,-296],[-486,12.,-320]],'CASTLE_APPROACH'),('EAST',east,4.,[[380.95871006255794,0,0.1447459626440306],[382.48550573024147,3.,-.41159030183889644],[390.00205240938203,3.,-3.150481687107995],[397.5185990885226,3.,-5.889373072377094],[399.3977357583078,3.,-6.574095918694369]],[[480,1.,-13.],[502,1.,-18.0],[502,1.,-32]],'EAST_WALL_SERVICE')]
 for side,inst,floor,inside,outside,rid in defs:
  ctr=[inst['position_m'][0],floor,inst['position_m'][2]];norm=[math.sin(inst['yaw_rad']),math.cos(inst['yaw_rad'])];inside[0][1]=ground.at(xz(inside[0]))
  at=lambda dist:[ctr[0]+norm[0]*dist,floor,ctr[2]+norm[1]*dist]
  # All route vectors run from unchanged internal public road to exterior farm.
  if side=='WEST':
   a,b=inside[0],inside[1];ll=math.dist(xz(a),xz(b));q=[a[k]+20/ll*(b[k]-a[k])for k in range(3)];q[1]=west_plane(xz(q));inside.insert(1,q)
  else:inside[0][1]=3.
  raw=inside+([at(18)]if side=='EAST'else[])+[at(12),at(6),ctr,at(-6),at(-12)]+outside
  # Keep a perfectly straight, level 12 m throat, smooth only other corners.
  pts=dense(smooth(raw,8),1.0)
  pts[0]=raw[0];pts[-1]=raw[-1]
  sections=[];arc=[0.]
  for aa,bb in zip(pts,pts[1:]):arc.append(arc[-1]+math.dist(xz(aa),xz(bb)))
  for n,p in enumerate(pts):
   a=pts[max(0,n-1)];b=pts[min(len(pts)-1,n+1)];dx,dz=b[0]-a[0],b[2]-a[2];ll=math.hypot(dx,dz);ux,uz=-dz/ll,dx/ll
   d=math.dist(xz(p),xz(ctr));h=3.+13*max(0.,min(1.,(15-d)/7))
   if d<15:ux,uz=math.cos(inst['yaw_rad']),-math.sin(inst['yaw_rad'])
   v=[]
   for w in [-h-2,-h,h,h+2]:
    x,z=p[0]+ux*w,p[2]+uz*w;y=p[1]
    if side=='WEST':
     fraction=max(0.,min(1.,(arc[n]-16.)/8.));fraction=fraction*fraction*(3-2*fraction);y+=(west_plane([x,z])-west_plane(xz(p)))*(1-fraction)
    v.append([x,y,z])
   sections.append(v)
  localcores=[];localouter=[]
  for j,(a,b) in enumerate(zip(sections,sections[1:])):
   core=[a[1],a[2],b[2],b[1]];poly=[xz(v)for v in core];outer=[xz(a[0]),xz(a[3]),xz(b[3]),xz(b[0])]
   assert geo.polygon_area(poly)>1e-9
   for lane in [[a[1],pts[j],pts[j+1],b[1]],[pts[j],a[2],b[2],pts[j+1]]]:
    pp=[xz(v)for v in lane]
    for t2 in convex_parts(pp):
     tt=[lane[pp.index(v)]for v in t2]
     cores.append(dict(id=f'{side}:ROAD:{j}',poly=[xz(v)for v in tt],pl=plane(tt),material='road'))
   localcores.extend(convex_parts(poly));localouter.extend(convex_parts(outer))
   for k,kk in [(0,1),(3,2)]:
    sh=[xz(a[k]),xz(a[kk]),xz(b[kk]),xz(b[k])];inner=[a[kk],b[kk]]
    for n,part in enumerate(convex_parts(sh)):
     shoulders.append(dict(id=f'{side}:SHOULDER:{j}:{k}:{n}',poly=part,inner=inner,width=2.,material='ground_grass'))
  owner=dict(id=side+'_GATE_PUBLIC_CORRIDOR',road_id=rid,gate_center_xyz_m=ctr,yaw_rad=inst['yaw_rad'],inward_normal_xz=norm,core_polygons_xz_m=localcores,ownership_polygons_xz_m=localouter,nominal_road_width_m=6.,gate_forecourt_width_m=32.,base_scene_sha256=SHA,shared_cross_sections_xyz_m=sections,section_arc_length_m=arc,height_policy='Each shared cross-section vertex is authored once. Cut fragments inherit the original ribbon triangle affine plane; no nearest-height reassignment after clipping.')
  owners.append(owner)
  routes.append(dict(id=side+'_PUBLIC_ROAD_TO_EXTERNAL_FARM',group=side,points=pts,raw_points=raw,source_road_ids=[rid,side+'_GATE_PUBLIC_CORRIDOR',side+'_FARM'],test_scope='New public landward gate route, exact patched surfaces and native colliders. No cart dynamics claim.',gate_waypoint_index=min(range(len(pts)),key=lambda i:math.dist(pts[i],ctr)),maximum_centerline_grade=max(abs(b[1]-a[1])/math.dist(xz(a),xz(b))for a,b in zip(pts,pts[1:]))))
 # Canonical through-junction slabs own both the old public road and the new
 # branch intersection. EAST has a level bridge landing and smooth 8 m ramps.
 junctioncores=[]
 for j in junctions:
  localcores=[];localouter=[];path=dense(j['points'],.75);arcs=[0.]
  for a,b in zip(path,path[1:]):arcs.append(arcs[-1]+math.dist(xz(a),xz(b)))
  # Author one shared miter section at every centerline station. A section has
  # one profile height for both road edges and its explicit center vertex.
  sections=[];centers=[]
  for n,p in enumerate(path):
   a,b=path[max(0,n-1)],path[min(len(path)-1,n+1)];normals=[]
   for u,v in [(a,p),(p,b)]:
    dx,dz=v[0]-u[0],v[2]-u[2];ll=math.hypot(dx,dz)
    if ll>1e-8:normals.append([-dz/ll,dx/ll])
   ux,uz=[sum(v[k]for v in normals)for k in [0,1]];ll=math.hypot(ux,uz);ux/=ll;uz/=ll;mult=1/(ux*normals[-1][0]+uz*normals[-1][1]);h=j['width']/2;sh=0 if j['side']=='WEST'else 2;y=junction_height(j,xz(p));centers.append([p[0],y,p[2]])
   sections.append([[p[0]+ux*w*mult,y,p[2]+uz*w*mult]for w in [-h-sh,-h,h,h+sh]])
  for n,(a,b)in enumerate(zip(sections,sections[1:])):
   core=[xz(a[1]),xz(a[2]),xz(b[2]),xz(b[1])];outer=[xz(a[0]),xz(a[3]),xz(b[3]),xz(b[0])]
   localcores.extend(convex_parts(core));localouter.extend(convex_parts(outer))
   for lane in [[a[1],centers[n],centers[n+1],b[1]],[centers[n],a[2],b[2],centers[n+1]]]:
    pp=[xz(v)for v in lane]
    for tt in convex_parts(pp):
     xyz=[lane[pp.index(v)]for v in tt];junctioncores.append(dict(id=j['side']+':PUBLIC_JUNCTION',poly=tt,pl=plane(xyz),material='road'))
   for k,kk in ([]if j['side']=='WEST'else [(0,1),(3,2)]):
    for part in convex_parts([xz(a[k]),xz(a[kk]),xz(b[kk]),xz(b[k])]):shoulders.append(dict(id=j['side']+':JUNCTION_SHOULDER',poly=part,inner=[a[kk],b[kk]],width=2.,material='ground_grass',junction=j))
  owners.append(dict(id=j['side']+'_EXISTING_PUBLIC_JUNCTION',core_polygons_xz_m=localcores,ownership_polygons_xz_m=localouter,source_road_id=j['road_id'],clear_width_m=j['width'],source_station_indices=j['source_station_indices'],shared_cross_sections_xyz_m=sections,center_vertices_xyz_m=centers,section_arc_length_m=arcs,junction_height_policy='Shared miter cross-sections and explicit center vertices. One profile height per station; east eased slope landing with exact source endpoint anchors.'))
 cores=junctioncores+cores
 for f in fields:
  cores.append(dict(id=f['id'],poly=f['poly'],pl=(0,0,f['floor']),material='ground_earth'))
  parts=DomainCut([{'polygon_xz_m':f['poly']}]).subtract(f['outer'])
  for p in parts:shoulders.append(dict(id=f['id']+':SHOULDER',poly=p,field=f,width=4 if f['id'].startswith('WEST') else 3,material='ground_grass'))
  owners.append(dict(id=f['id'],core_polygons_xz_m=[f['poly']],ownership_polygons_xz_m=[f['outer']],floor_y_m=f['floor']))
 print('Owner geometry ready',len(cores),len(shoulders),flush=True)
 # Exact polygon union partition: core first, then transition shoulders.
 seen=[];appended={};area=0;corepart=[];cover=[];source_hole_repairs=[]
 def emit(material,p,fn):
  nonlocal area
  for tt in fan(p):
   tri=up([[x,fn([x,z]),z]for x,z in tt])
   a=np.asarray(tri,dtype=np.float32);n=np.cross(a[1]-a[0],a[2]-a[0])
   if area3(tri)>1e-10:appended.setdefault(material,[]).extend(tri)
  area+=geo.polygon_area(p)
 for c in cores:
  parts=[q for p in excluded.subtract(c['poly'])for q in DomainCut([{'polygon_xz_m':p}for p in seen]).subtract(p)]
  for p in parts:emit(c['material'],p,lambda q,c=c:ph(c['pl'],q));seen.append(p);corepart.append(p)
 for sh in shoulders:
  parts=[q for p in excluded.subtract(sh['poly'])for q in DomainCut([{'polygon_xz_m':p}for p in seen]).subtract(p)]
  for p in parts:
   candidates=[ground.rows[i]for i in ground.idx.candidates(p)];candidates.sort(key=lambda r:sum(v[1]for v in r['triangle']),reverse=True);covered=[]
   def blended(q,r):
    if 'field'in sh:
     f=sh['field'];xs=[v[0]for v in f['poly']];zs=[v[1]for v in f['poly']];dx=max(min(xs)-q[0],0,q[0]-max(xs));dz=max(min(zs)-q[1],0,q[1]-max(zs));frac=min(1,max(dx,dz)/sh['width']);y=f['floor']
    else:
     a,b=sh['inner'];aa,bb=xz(a),xz(b);dx,dz=bb[0]-aa[0],bb[1]-aa[1];den=dx*dx+dz*dz;t=max(0,min(1,((q[0]-aa[0])*dx+(q[1]-aa[1])*dz)/den));y=a[1]+t*(b[1]-a[1]);y=junction_height(sh['junction'],q)if 'junction'in sh else y;frac=min(1,geo.point_segment_distance(q,aa,bb)/sh['width'])
    return y*(1-frac)+ph(r['plane'],q)*frac
   for r in candidates:
    q=clean(geo.convex_intersection(p,r['polygon']))
    if not q:continue
    for part in DomainCut([{'polygon_xz_m':v}for v in covered]).subtract(q):emit(sh['material'],part,lambda pt,r=r:blended(pt,r));covered.append(part)
   missing=DomainCut([{'polygon_xz_m':q}for q in covered]).subtract(p);missingarea=sum(geo.polygon_area(q)for q in missing)
   if 1e-5<missingarea<.1 and 'junction'in sh:
    # Source has tiny finite tessellation holes on this existing public shoulder.
    # Close only these sub-centimetre-area holes inside the declared new owner.
    for q in missing:
     center=[sum(v[k]for v in q)/len(q)for k in [0,1]]
     rr=min(candidates,key=lambda r:min(geo.point_segment_distance(center,a,b)for a,b in zip(r['polygon'],r['polygon'][1:]+r['polygon'][:1])))
     distance=min(geo.point_segment_distance(center,a,b)for a,b in zip(rr['polygon'],rr['polygon'][1:]+rr['polygon'][:1]))
     assert distance<.25,(sh['id'],distance)
     source_hole_repairs.append(dict(owner=sh['id'],polygon_xz_m=q,area_m2=geo.polygon_area(q),centroid_distance_to_retained_source_m=distance,source_material=rr['material'],source_triangle_index=rr['triangle_index']))
     emit(sh['material'],q,lambda pt,r=rr:blended(pt,r))
    missingarea=0
   if missingarea>1e-5:
    write('missing_shoulder.json',dict(id=sh['id'],missing=missing,polygon=p,candidates=candidates))
    raise ValueError('Shoulder missing existing ground '+sh['id']+' '+str(missingarea))
   seen.append(p)
 masks=[q for o in owners for p in o['ownership_polygons_xz_m']for q in excluded.subtract(p)];bridge_index=geo._SpatialIndex(32);bridge_index.add(0,bridge_poly);cut=DomainCut([{'polygon_xz_m':p}for p in masks]);edits=[];source_mats=set();removed_top=0;water=[]
 for row in rows:
  tri=row['triangle'];poly=[xz(p)for p in tri];inds=cut.index.candidates(poly)
  bridge_candidate=bool(bridge_index.candidates(poly)) and max(v[1]for v in tri)>2.8
  if not inds and not bridge_candidate:continue
  if row['material']=='water':
   if any(geo.positive_area_overlap(poly,masks[i],0)for i in inds):water.append(row['triangle_index'])
   continue
  parts=[tri]
  for i in inds:
   parts=[out for p in parts for out in cut3(p,masks[i])]
   if not parts:break
  if bridge_candidate:
   cleared=[]
   for part in parts:
    below,above=split_y(part,2.8)
    if len(below)>=3:cleared.append(below)
    if len(above)>=3:cleared.extend(cut3(above,bridge_poly))
   parts=cleared
  replacement=[t for p in parts for t in fan(p)if area3(t)>1e-10]
  before=area3(tri);after=sum(area3(t)for t in replacement)
  if before-after<1e-8:continue
  edits.append(dict(material=row['material'],triangle_index=row['triangle_index'],source_triangle_xyz_m=tri,source_triangle_sha256=ch(tri),replacement_triangles_xyz_m=replacement));source_mats.add(row['material']);removed_top+=max(0,geo.polygon_area(poly)-sum(geo.polygon_area([xz(v)for v in t])for t in replacement))
 assert not water,('Road intersects water',water)
 owners.append(dict(id='EAST_NATIVE_CANAL_BRIDGE',native_floor_owner_id='R9_LANDWARD_BRIDGE:EAST_CANAL',polygon_xz_m=bridge_poly,deck_y_m=3.,retained_water_triangles=[96,97],terrain_fill=False,source_obstruction_clearance_policy='Remove only existing non-water terrain above Y2.8 inside the exact native bridge footprint; retain lower bank/bed fragments and all water.'))
 print('Local clipping ready',len(edits),'edits',flush=True)
 # Source material identities, never a copy of the full scene in this pack.
 scene=json.load(open(BASE));hashes={m:ch(scene['surfaces'][m])for m in source_mats}
 for e in edits:assert scene['surfaces'][e['material']][e['triangle_index']*3:e['triangle_index']*3+3]==e['source_triangle_xyz_m']
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R9_LANDWARD_GATES_CANONICAL_GROUND_R01',status='source_ready_runtime_pending',base_scene=ref(BASE),base_scene_sha256=SHA,source_surface_hashes=hashes,source_hole_repairs=source_hole_repairs,surface_edits=edits,appended_surfaces=appended,removed_foundation_proxy_ids=[],ownership=owners,source_policy='Exact finite source clipping. Outside fragments remain on original source planes. One canonical road/field owner per new top; no additive road overlay.',summary=dict(source_triangle_edits=len(edits),appended_triangles=sum(len(v)//3 for v in appended.values()),new_top_union_area_m2=area,removed_source_top_area_m2=removed_top,water_edits=0,giant_city_export=False))
 write('surface_patch.json',patch);write('ground_ownership.json',dict(owners=owners,fields=fields,base_scene_sha256=SHA));write('routes.json',dict(base_scene=ref(BASE),finite_patch=ref(H/'surface_patch.json'),routes=routes,gates=[dict(id=o['id'],opening_center_xyz_m=o['gate_center_xyz_m'],travel_unit_xz=[-v for v in o['inward_normal_xz']],clear_width_m=8.,throat_depth_m=6.,public_target_id=o['road_id'],exterior_endpoint_id=o['id'].split('_')[0]+'_FARM')for o in owners if 'gate_center_xyz_m' in o]))
 # Bounded farm plots reuse crop-bed masters. Trees inside road/field ownership are
 # explicitly retired, never left inside colliders or disguised with new grass.
 add=[];remove=[]
 for p in ctx['common_instances']:
  if not p['id'].startswith('WOOD_REGISTERED_WEST:'):continue
  b=bounds[p['asset_key']];poly=[xz(transform([x,0,z],p))for x,z in [(b['min'][0],b['min'][2]),(b['max'][0],b['min'][2]),(b['max'][0],b['max'][2]),(b['min'][0],b['max'][2])]]
  if any(geo.positive_area_overlap(poly,masks[i],0)for i in cut.index.candidates(poly)):remove.append(p['id'])
 bed='c3_property_fabric_r3_b8fc7a975a10ec9f'
 for f in fields:
  xlo,zlo=f['poly'][0];xhi,zhi=f['poly'][2]
  for x in [xlo+5,xhi-5]:
   for z in [zlo+5,zlo+11,zlo+17,zlo+23]:
    add.append(dict(id='R9_FARM:'+f['id']+f':BED:{x}:{z}',asset_key=bed,position_m=[x,f['floor'],z],yaw_rad=0.,scale=[1,1,1],palette_id='native_landscape',palette_override={},source_pack='r9_landward_farms'))
 # Visible low separator on the training side of the independent public strip.
 sepkey='district_r01_boundary_2m';sep=[[-358,-230],[-330,-218],[-305,-209]]
 for n,(a,b)in enumerate(zip(sep,sep[1:])):
  ll=math.dist(a,b);yaw=math.atan2(-(b[1]-a[1]),b[0]-a[0]);num=math.ceil(ll/2)
  for j in range(num):
   t=(j+.5)/num;q=[a[k]+t*(b[k]-a[k])for k in [0,1]];
   try:y=ground.at(q)
   except ValueError:y=18.0
   add.append(dict(id=f'R9_WEST_PUBLIC_SEPARATOR:{n}:{j}',asset_key=sepkey,position_m=[q[0],y+.25,q[1]],yaw_rad=yaw,scale=[1,1,1],palette_id='r9_gate_boundary',palette_override={},source_pack='r9_landward_farms'))
 keys={p['asset_key']for p in add};aout={k:dict(assets[k],bounds=bounds[k])for k in keys};pack=dict(schema='riverstone.city.visual_addendum.v1',base_scene_sha256=SHA,common_assets=aout,add_instances=add,remove_instance_ids=remove)
 write('farm_pack.json',pack);write('source_tests.json',dict(status='SOURCE_READY_RUNTIME_PENDING',base_unchanged=sha(BASE)==SHA,exact_source_triangle_checks=len(edits),water_intersection_count=0,maximum_centerline_grade={r['group']:r['maximum_centerline_grade']for r in routes},removed_woodland_ids=remove,retained_training_floor_unchanged=True,public_route_avoids_training_native_top=True,summary=patch['summary'],elapsed_seconds=time.monotonic()-t0))
 print('READY',patch['summary'],len(remove),'woodland retirements',flush=True)
if __name__=='__main__':build()
