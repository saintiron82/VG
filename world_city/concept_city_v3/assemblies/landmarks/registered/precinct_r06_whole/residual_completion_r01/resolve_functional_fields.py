"""Resolve varied field facilities and exact two metre internal service walks."""
from pathlib import Path
import sys,json,math,time,collections,copy,heapq
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from resolve_pack import *
from connect_routes import simplify
from retained_walks import RetainedWalkIndex
OUT=Path(__file__).resolve().parent

def roles(f):
 n=max(2,min(12,int(math.ceil(f['exact_area_m2']/180))));kind=f['function']
 if 'orchard'in kind:return (['tree','tree','compact_bed','park_bench']*((n+3)//4))[:n]
 if 'growing'in kind:return (['bed','bed','compact_bed','shelter_4x3','cargo_crate']*((n+4)//5))[:n]
 if 'training'in kind:return ['rack','target','trough','park_bench'][:max(2,min(4,n))]
 if 'bailey'in kind:return ['trough','rack','fuel_stack','cargo_crate','shelter_4x3'][:max(2,min(5,n))]
 if 'drying'in kind:return ['shelter_4x3','fuel_stack','cargo_crate','park_bench'][:max(2,min(4,n))]
 return (['compact_bed','park_bench']*((n+1)//2))[:n]

def main():
 started=time.monotonic();plan=load(OUT/'functional_field_domains.json');base=load(BASE/'resolved_placements.json');assets={a['role']:a for a in base['assets']};assets.update({a['role']:a for a in load(OUT/'compiled_assets.json')['assets']});native={}
 for role,a in assets.items():
  mesh=load(ROOT/a['cache']['path']);full,_=roof_rectangles(mesh,{g['material']for g in mesh['groups']});native[role]={'mesh':mesh,'full':full,'body':slab_rectangles(mesh,.01,2.2),'foot':horizontal(mesh,mesh['bounds']['min'][1],False),'bottom':mesh['bounds']['min'][1]}
 obs=load(OUT/'exact_obstacles.json');oi=geo._SpatialIndex(16)
 for i,o in enumerate(obs):oi.add(i,o['polygon_xz_m'])
 scene=terrain.load_scene();surface=RetainedWalkIndex(scene,[b.rect(*b.BOUNDS)]);sides=SideIndex(scene);fields=[];placements=[];bearings=[];allroutes=[];rejected=[];tests=[]
 for field in plan['fields']:
  f=copy.deepcopy(field);f['area_m2']=f['exact_area_m2'];coremask=b.mask(f['screen_core_grid_parts_xz_m']);entry=f['entry']['inside_point_xz_m'];ez,ex=int(entry[1]-b.BOUNDS[1]),int(entry[0]-b.BOUNDS[0]);ground=f['polygon_parts_xz_m'];fi=geo._SpatialIndex(8)
  for i,p in enumerate(ground):fi.add(i,p)
  def contained(q):return abs(sum(geo.intersection_area(q,ground[i])for i in fi.candidates(q))-geo.polygon_area(q))<1e-7
  local=[];occupied=[];bodymask=np.zeros(b.SHAPE,bool);servicepoints=[];entryclear=b.rect(entry[0]-2,entry[1]-2,entry[0]+2,entry[1]+2)
  zz,xx=np.nonzero(coremask);distedge=ndimage.distance_transform_edt(coremask);candidates=[[float(b.BOUNDS[0]+x+.5),float(b.BOUNDS[1]+z+.5)]for z,x in zip(zz,xx)if x%3==0 and z%3==0];candidates.sort(key=lambda p:(int(math.dist(p,entry)//8),p[1],p[0]))
  def try_add(role,x,z,yaw=0,boundary=False):
   nonlocal bodymask
   a,n=assets[role],native[role];p={'id':f['id']+':'+role+':'+str(len(local)),'holding_id':f['id'],'owner_id':f['owner_id'],'asset_key':a['id'],'source':a['source'],'cache':a['cache'],'position_m':[x,f['floor_y_m'],z],'yaw_rad':yaw,'scale':[1,1,1],'function':role,'actual_cached_bounds_local_m':n['mesh']['bounds']};full=[b.xform(q,p)for q in n['full']];body=[b.xform(q,p)for q in n['body']]
   if any(not contained(q)for q in full):return False
   if any(geo.intersection_area(q,r)>1e-7 for q in full for r in occupied):return False
   if any(geo.intersection_area(q,entryclear)>1e-7 for q in body):return False
   if any(geo.intersection_area(q,o)>1e-7 for q in body for o in f['entry']['ribbon_polygons_xz_m']):return False
   bm=bodymask|b.mask(body);walk=coremask&~b.buffer(bm,1.5);lab,nc=ndimage.label(walk);component=lab[ez,ex]
   if not component or any(lab[iz,ix]!=component for iz,ix in servicepoints):return False
   service=None
   if not boundary:
    bb=n['mesh']['bounds'];rrx=max(abs(bb['min'][0]),abs(bb['max'][0]))+1.5;rrz=max(abs(bb['min'][2]),abs(bb['max'][2]))+1.5
    for sx,sz in ((x+rrx,z),(x-rrx,z),(x,z+rrz),(x,z-rrz)):
     iz,ix=int(sz-b.BOUNDS[1]),int(sx-b.BOUNDS[0])
     if 0<=iz<b.NZ and 0<=ix<b.NX and lab[iz,ix]==component:service=(iz,ix);break
    if service is None:return False
   local.append(dict(p,native_projection_parts_xz_m=full,body_parts_xz_m=body));occupied.extend(full);bodymask=bm
   if service is not None:servicepoints.append(service);local[-1]['service_grid_iz_ix']=list(service)
   return True
  # Paired partial rails describe the open field entry; existing precinct
  # walls/terraces retain the outer boundary. These are not repeated enclosures.
  q=f['entry']['ready_route_point_xz_m'];dx,dz=entry[0]-q[0],entry[1]-q[1];length=math.hypot(dx,dz);tx,tz=(-dz/length,dx/length)if length else(1,0);yaw=math.atan2(tz,tx)
  for sign in(-1,1):
   for role,offset in [('field_edge_4m',4),('field_edge_2m',3)]:
    if try_add(role,entry[0]+sign*tx*offset,entry[1]+sign*tz*offset,yaw,True):break
  for role in roles(f):
   success=False
   for x,z in candidates:
    if math.dist([x,z],entry)<5:continue
    if try_add(role,x,z):success=True;break
   if not success and role in('tree','bed','shelter_4x3'):
    for x,z in candidates:
     if math.dist([x,z],entry)>=5 and try_add('compact_bed'if role!='shelter_4x3'else'fuel_stack',x,z):break
  if not any(not p['function'].startswith('field_edge')for p in local):rejected.append({'field_id':f['id'],'reason':'No meaningful native facility fits exact clear field domain'});continue
  walk=coremask&~b.buffer(bodymask,1.5);parent={ (ez,ex):None};todo=collections.deque([(ez,ex)])
  while todo:
   iz,ix=todo.popleft()
   for dz,dx in ((1,0),(-1,0),(0,1),(0,-1)):
    key=(iz+dz,ix+dx)
    if 0<=key[0]<b.NZ and 0<=key[1]<b.NX and walk[key]and key not in parent:parent[key]=(iz,ix);todo.append(key)
  routes=[];bad=[]
  for p in local:
   if 'service_grid_iz_ix'not in p:continue
   pos=tuple(p['service_grid_iz_ix']);points=[]
   while pos is not None:points.append([b.BOUNDS[0]+pos[1]+.5,b.BOUNDS[1]+pos[0]+.5]);pos=parent[pos]
   points=simplify(points);polys=b.ribbon(points,2)+[b.rect(q[0]-1,q[1]-1,q[0]+1,q[1]+1)for q in points];checks=[terrain.audit_polygon(surface,q,f['floor_y_m'])for q in polys];hits=[]
   for q in polys:
    for other in local:
     for qq in other['body_parts_xz_m']:
      ar=geo.intersection_area(q,qq)
      if ar>1e-7:hits.append({'native_id':other['id'],'area_m2':ar})
    for i in oi.candidates(q):
     ar=geo.intersection_area(q,obs[i]['polygon_xz_m'])
     if ar>1e-7:hits.append({'native_id':obs[i]['id'],'area_m2':ar})
   sc=sides.audit([{'id':p['id']+':walk','polygon_xz_m':q,'floor_y_m':f['floor_y_m']}for q in polys]);passed=all(c['passes_existing_surface']for c in checks)and not hits and not sc['contacts'];r={'id':p['id']+':service_walk','holding_id':f['id'],'native_facility_id':p['id'],'width_m':2,'floor_y_m':f['floor_y_m'],'polyline_xz_m':points,'ribbon_polygons_xz_m':polys,'terrain_checks':[{k:v for k,v in c.items()if k not in('source_pieces','uncovered_polygons_xz_m')}for c in checks],'native_contacts':hits,'bank_contacts':sc['contacts'],'pass':passed};routes.append(r)
   if not passed:bad.append(r)
  if bad:rejected.append({'field_id':f['id'],'reason':'Exact internal route support/native/bank check fails','route_failures':bad});print('blocked field',f['id'],len(bad),flush=True);continue
  support=[]
  for p in local:
   role=p['function'];n=native[role]
   for i,q in enumerate(n['foot']):
    world=b.xform(q,p);test=terrain.audit_polygon(surface,world,f['floor_y_m']);assert test['passes_existing_surface'],p['id'];support.append({'id':p['id']+':bearing:'+str(i),'placement_id':p['id'],'holding_id':f['id'],'polygon_xz_m':world,'bottom_y_m':f['floor_y_m']+n['bottom'],'finished_ground_y_m':f['floor_y_m'],'kind':'actual_native_underside'})
  for p in local:p.pop('native_projection_parts_xz_m');p.pop('body_parts_xz_m');p.pop('service_grid_iz_ix',None)
  f['native_placement_ids']=[p['id']for p in local];f['facility_counts']=dict(collections.Counter(p['function']for p in local));f['status']='FINITE_FACILITIES_AND_CONNECTED_INTERNAL_SERVICE_WALKS_PROVEN';fields.append(f);placements+=local;bearings+=support;allroutes+=routes;tests.append({'field_id':f['id'],'native_facilities':len(local),'native_bearings':len(support),'internal_service_routes':len(routes),'pass':True});print('resolved',f['id'],len(local),len(routes),round(f['area_m2']),flush=True)
 used={p['asset_key']for p in placements};out={'schema':'riverstone.precinct.r06.residual_functional_fields.v1','status':'RESOLVED_NATIVE_FIELD_BATCH_NOT_APPLIED','sources':{'domains':ref(OUT/'functional_field_domains.json'),'ready21':ref(BASE/'resolved_connected_placements.json'),'phase02':ref(CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase02/resolved_placements.json'),'training_entry':ref(OUT/'training_walk_tests.json'),'scene':ref(terrain.SCENE_PATH)},'assets':[a for a in assets.values()if a['id']in used],'holdings':fields,'placements':placements,'actual_bearing_footprints':bearings,'internal_routes':allroutes,'owned_floors':[],'replacement_ledger':{'existing_native_placements_removed':[]},'summary':{'functional_fields':len(fields),'exact_domain_area_m2':sum(f['area_m2']for f in fields),'native_placements':len(placements),'native_bearing_pieces':len(bearings),'internal_routes':len(allroutes),'rejected_fields':len(rejected),'seconds':time.monotonic()-started},'activation':False,'runtime_player_NPC_replay':'pending; especially retained native training treads'};(OUT/'resolved_field_placements.json').write_text(json.dumps(out,indent=2)+'\n');(OUT/'field_native_tests.json').write_text(json.dumps({'fields':tests,'rejected':rejected,'all_promoted_fields_pass':True},indent=2)+'\n');print(out['summary'])
if __name__=='__main__':main()
