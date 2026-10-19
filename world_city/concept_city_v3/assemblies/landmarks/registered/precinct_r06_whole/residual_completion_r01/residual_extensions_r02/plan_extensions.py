"""Finite connected open grounds, retaining real native boundaries and facilities."""
from pathlib import Path
import sys,json,math,time
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE));sys.path.insert(0,str(OUT.parent))
from resolve_pack import *
from native_walks import CompositeSupportIndex
from retained_walks import RetainedWalkIndex
from world_city.concept_city_v3.assemblies.landmarks.registered.coverage_r5_draft_01.project_native import roof_rectangles
OUT=Path(__file__).resolve().parent

def make_obstacles():
 source=load(BASE/'actual_native_projection.json');walk=load(BASE/'native_walk_support.json');special={r['id']:r for r in walk['instances']};rows=[]
 for p in source['instances']:
  ps=special[p['id']]['walking_body_parts_xz_m']if p['id']in special else p['native_parts_xz_m'];rows.extend({'id':p['id'],'polygon_xz_m':q,'kind':'existing_native'}for q in ps)
 for p in load(BASE/'resolved_placements.json')['placements']:
  mesh=load(ROOT/p['cache']['path']);rows.extend({'id':p['id'],'polygon_xz_m':b.xform(q,p),'kind':'ready_or_reserved_native'}for q in slab_rectangles(mesh,.01,2.2))
 phase=CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase02/resolved_placements.json';cache={}
 for p in load(phase)['placements']:
  rp=p['cache']['path']
  if rp not in cache:
   m=load(ROOT/rp);cache[rp]=roof_rectangles(m,{g['material']for g in m['groups']})[0]
  rows.extend({'id':p['id'],'polygon_xz_m':b.xform(q,p),'kind':'phase02_native'}for q in cache[rp])
 for p in load(BASE/'preserved_reservations.json')['reservations']:
  if p['kind']in('phase01','phase02','existing_designed_garden','existing_productive_frame'):rows.extend({'id':p['id'],'polygon_xz_m':q,'kind':'preserved_domain'}for q in p['polygon_parts_xz_m'])
 for p in load(CITY/'assemblies/waterworks/registered_services_r01/locations.json')['drawhouses']:rows.append({'id':p['id'],'polygon_xz_m':p['footprint_xz_m'],'kind':'water_fixture'})
 for p in load(OUT.parent/'resolved_residual_placements.json')['placements']:
  mesh=load(ROOT/p['cache']['path']);rows.extend({'id':p['id'],'polygon_xz_m':b.xform(q,p),'kind':'prior_residual_native'}for q in slab_rectangles(mesh,.01,2.2))
 return rows

def function(field):
 owner=field['owner_id'];x,z=field['centroid_xz_m']
 if owner=='SITE_TRAIN':return 'training_exercise_and_tack_verge'
 if owner=='SITE_CASTLE':return 'outer_bailey_exercise_and_service_court'
 if owner=='SITE_CLOISTER':return 'cloister_quiet_garden'
 if owner=='SITE_CLERGY':return 'canons_orchard_service_garden'if x>300 else'clergy_kitchen_growing_and_alms_court'
 if owner=='SITE_MONASTERY':
  if x<-290 and z>70:return 'abbey_orchard_and_nursery'
  if z>170:return 'abbey_kitchen_growing_ground'
  if x>-210:return 'abbey_east_work_and_drying_court'
  return 'abbey_processional_and_herb_court'
 return 'retained_owner_service_ground'

def main():
 started=time.monotonic();source=load(OUT.parent/'whole_owner_use_plan.json');screens=np.load(OUT.parent/'field_screen.npz')['labels'];ready=load(BASE/'resolved_connected_placements.json');training=load(OUT.parent/'training_walk_tests.json');training_route=load(OUT.parent/'training_entry_audit.json');prior=load(OUT.parent/'resolved_residual_placements.json');used=b.mask([q for h in prior['holdings']for q in h['polygon_parts_xz_m']]);screens=screens.copy();screens[used]=0;ready['holdings']+=prior['holdings'];ready['external_routes']+=prior['external_routes'];ready['external_routes'] += [r for r in prior['internal_routes']if 'polyline_xz_m'in r]
 if training['status']=='PASS':
  unit=next(u for u in load(BASE/'resolved_placements.json')['holdings']if u['owner_id']=='SITE_TRAIN');ready['holdings'].append(unit);ready['external_routes'].append({'id':'RETAINED_TRAINING_ENTRY_R01','holding_id':unit['id'],'polyline_xz_m':training_route['proposed_spur_polyline_xz_m']})
 scene=terrain.load_scene();index=RetainedWalkIndex(scene,[b.rect(*b.BOUNDS)]);sides=SideIndex(scene);obs=make_obstacles();oi=geo._SpatialIndex(16)
 for i,o in enumerate(obs):oi.add(i,o['polygon_xz_m'])
 accepted=[];rejected=[]
 for f in source['fields']:
  if f['owner_id']not in('SITE_CASTLE','SITE_CLERGY','SITE_MONASTERY','SITE_TRAIN','SITE_CLOISTER'):continue
  owner=f['owner_id'];mask=screens==int(f['id'].split('_')[-1]);core=ndimage.distance_transform_edt(mask)>=1.5;ll,n=ndimage.label(core)
  for component in range(1,n+1):
   center=ll==component
   if center.sum()<64:continue
   field=b.buffer(center,1)&mask;zs,xs=np.nonzero(center);xy=np.stack([xs+b.BOUNDS[0]+.5,zs+b.BOUNDS[1]+.5],axis=1);best=np.full(len(xy),np.inf);targets=np.zeros_like(xy,dtype=float);routeids=np.empty(len(xy),object)
   for route in ready['external_routes']:
    h=next(u for u in ready['holdings']if u['id']==route['holding_id'])
    if h['owner_id']!=owner and not(owner in('SITE_CLOISTER','SITE_CEMETERY')and h['owner_id']=='SITE_CLERGY'):continue
    for aa,bb in zip(route['polyline_xz_m'],route['polyline_xz_m'][1:]):
     a,c=np.array(aa),np.array(bb);v=c-a;tt=np.clip(((xy-a)*v).sum(axis=1)/max(float(v@v),1e-10),0,1);q=a+tt[:,None]*v;dist=np.linalg.norm(xy-q,axis=1);better=dist<best;best[better]=dist[better];targets[better]=q[better];routeids[better]=route['id']
   entry=None;tried=[]
   for ci in np.argsort(best)[:160]:
    if best[ci]>80:break
    p,q=xy[ci].tolist(),targets[ci].tolist()
    if any(math.dist(p,r)<2 for r in tried):continue
    tried.append(p);polys=b.ribbon([p,q],2)+[b.rect(p[0]-1,p[1]-1,p[0]+1,p[1]+1),b.rect(q[0]-1,q[1]-1,q[0]+1,q[1]+1)];checks=[terrain.audit_polygon(index,r,f['floor_y_m'])for r in polys]
    if not all(c['passes_existing_surface']for c in checks):continue
    hits=[{'owner':obs[i]['id'],'kind':obs[i]['kind'],'area_m2':geo.intersection_area(r,obs[i]['polygon_xz_m'])}for r in polys for i in oi.candidates(r)if geo.intersection_area(r,obs[i]['polygon_xz_m'])>1e-7]
    if hits:continue
    sc=sides.audit([{'id':f['id']+':entry','polygon_xz_m':r,'floor_y_m':f['floor_y_m']}for r in polys])
    if sc['contacts']:continue
    entry={'inside_point_xz_m':p,'ready_route_point_xz_m':q,'ready_route_id':routeids[ci],'width_m':2,'ribbon_polygons_xz_m':polys,'terrain_checks':checks,'side_clearance_status':sc['status'],'exact_native_contacts':[],'distance_m':float(best[ci])};break
   if not entry:rejected.append({'field_id':f['id'],'component':component,'reason':'No finite level two metre entry joins a proven ready21 route clear of actual native, phase02 and protected domains.'});continue
   parts=b.parts(field);pieces=[];badgrade=[]
   for p in parts:
    for r in index.covering(p):
     plane=r['plane_y_xz_m'];q=r['intersection_polygon_xz_m'];ys=[terrain.common.height(plane,v)for v in q]
     if max(abs(y-f['floor_y_m'])for y in ys)>1e-7 or math.hypot(*plane[:2])>1e-7:badgrade.append(q);continue
     pieces.append({'material':r['material'],'triangle_index':r['triangle_index'],'source_triangle_sha256':r['source_triangle_sha256'],'polygon_xz_m':q,'plane_y_xz_m':plane})
   # Whole-domain bank and exact geometry audit remains finite over source pieces.
   sc=sides.audit([{'id':f['id']+':ground','polygon_xz_m':p['polygon_xz_m'],'floor_y_m':f['floor_y_m'],'headroom_m':9}for p in pieces]);hits=[{'owner':obs[i]['id'],'area_m2':geo.intersection_area(p['polygon_xz_m'],obs[i]['polygon_xz_m'])}for p in pieces for i in oi.candidates(p['polygon_xz_m'])if geo.intersection_area(p['polygon_xz_m'],obs[i]['polygon_xz_m'])>1e-7]
   if sc['contacts']or hits:rejected.append({'field_id':f['id'],'component':component,'reason':'Exact domain native or bank contact','native_contacts':hits,'bank_contacts':sc['contacts']});continue
   row=dict(f);row['id']='EXT02:'+f['id']+f':{component}';row.update(function=function(f),source_pieces=pieces,polygon_parts_xz_m=[p['polygon_xz_m']for p in pieces],exact_area_m2=sum(geo.polygon_area(p['polygon_xz_m'])for p in pieces),entry=entry,screen_core_grid_parts_xz_m=b.parts(center),retained_side_contacts=[],exact_native_contacts=[],status='FINITE_CONNECTED_DOMAIN_FACILITIES_PENDING');accepted.append(row);print('field',row['id'],round(row['exact_area_m2']),row['function'],flush=True)
 out={'sources':{'use_plan':ref(OUT.parent/'whole_owner_use_plan.json'),'prior_residual_fields':ref(OUT.parent/'resolved_residual_placements.json'),'ready21':ref(BASE/'resolved_connected_placements.json'),'phase02':ref(CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase02/resolved_placements.json'),'training_entry':ref(OUT.parent/'training_walk_tests.json')},'fields':accepted,'rejected':rejected,'summary':{'finite_connected_fields':len(accepted),'exact_area_m2':sum(r['exact_area_m2']for r in accepted),'rejected_components':len(rejected),'seconds':time.monotonic()-started},'completion_claim':'Domains and connected entries proven; no completed-use claim before facilities and internal walks resolve.'};(OUT/'functional_field_domains.json').write_text(json.dumps(out,indent=2)+'\n');(OUT/'exact_obstacles.json').write_text(json.dumps(obs,separators=(',',':'))+'\n');print(out['summary'])
if __name__=='__main__':main()
