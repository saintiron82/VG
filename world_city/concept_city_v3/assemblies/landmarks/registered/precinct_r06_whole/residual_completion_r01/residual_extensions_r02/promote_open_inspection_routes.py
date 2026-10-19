"""Deliberately clear inspection/exercise verges with visible connected paths.
No repeated props are forced into narrow native-bounded residual strips.
"""
from pathlib import Path
import sys,json,collections,time,copy
OUT=Path(__file__).resolve().parent;RES=OUT.parent;BASE=RES.parent;sys.path.insert(0,str(BASE));sys.path.insert(0,str(RES))
from resolve_pack import *
from connect_routes import simplify
from retained_walks import RetainedWalkIndex
OUT=Path(__file__).resolve().parent;RES=OUT.parent

def main():
 t=time.monotonic();source=load(OUT/'functional_field_domains.json');pack=load(OUT/'resolved_field_placements.json');prior=load(RES/'resolved_residual_placements.json');ready=load(BASE/'resolved_connected_placements.json');anchors=prior['internal_routes']+prior['external_routes']+ready['external_routes'];holds=prior['holdings']+ready['holdings'];done={h['id']for h in pack['holdings']};scene=terrain.load_scene();surface=RetainedWalkIndex(scene,[b.rect(*b.BOUNDS)]);side=SideIndex(scene);obs=load(OUT/'exact_obstacles.json');oi=geo._SpatialIndex(16)
 for i,r in enumerate(obs):oi.add(i,r['polygon_xz_m'])
 tests=[];rejected=[]
 for field in source['fields']:
  if field['id']in done:continue
  f=copy.deepcopy(field);core=b.mask(f['screen_core_grid_parts_xz_m']);p=f['entry']['inside_point_xz_m'];start=(int(p[1]-b.BOUNDS[1]),int(p[0]-b.BOUNDS[0]));parent={start:None};todo=collections.deque([start]);distance={start:0}
  while todo:
   z,x=todo.popleft()
   for dz,dx in ((1,0),(-1,0),(0,1),(0,-1)):
    q=(z+dz,x+dx)
    if 0<=q[0]<b.NZ and 0<=q[1]<b.NX and core[q]and q not in parent:parent[q]=(z,x);distance[q]=distance[z,x]+1;todo.append(q)
  end=max(distance,key=distance.get);points=[];q=end
  while q is not None:points.append([b.BOUNDS[0]+q[1]+.5,b.BOUNDS[1]+q[0]+.5]);q=parent[q]
  points=simplify(points[::-1]);polys=b.ribbon(points,2)+[b.rect(q[0]-1,q[1]-1,q[0]+1,q[1]+1)for q in points];checks=[terrain.audit_polygon(surface,q,f['floor_y_m'])for q in polys];hits=[]
  for q in polys:
   for i in oi.candidates(q):
    ar=geo.intersection_area(q,obs[i]['polygon_xz_m'])
    if ar>1e-7:hits.append({'native_id':obs[i]['id'],'area_m2':ar})
  sc=side.audit([{'id':f['id']+':inspection','polygon_xz_m':q,'floor_y_m':f['floor_y_m']}for q in polys]);passed=all(c['passes_existing_surface']for c in checks)and not hits and not sc['contacts']
  if not passed:rejected.append({'id':f['id'],'reason':'Exact open inspection path fails','bad_checks':[c for c in checks if not c['passes_existing_surface']],'native_contacts':hits,'bank_contacts':sc['contacts']});continue
  anchor=next(r for r in anchors if r['id']==f['entry']['ready_route_id']);ah=next(h for h in holds if h['id']==anchor['holding_id']);facilities=ah['native_placement_ids'];assert facilities;f.update(area_m2=f['exact_area_m2'],native_placement_ids=[],facility_counts={},shared_existing_facility_ids=facilities,shared_facility_holding_id=ah['id'],function='clear_outer_bailey_inspection_and_exercise_verge'if f['owner_id']=='SITE_CASTLE'else'abbey_clear_processional_and_garden_inspection_verge',ground_material_policy='retain_original_source_ground_except_visible_inspection_path',status='FINITE_CLEAR_USE_WITH_VISIBLE_CONNECTED_INSPECTION_ROUTE_AND_SHARED_ACTUAL_FACILITIES');route={'id':f['id']+':inspection_walk','holding_id':f['id'],'width_m':2,'floor_y_m':f['floor_y_m'],'polyline_xz_m':points,'ribbon_polygons_xz_m':polys,'shared_facility_ids':facilities,'source_anchor_route_id':anchor['id'],'terrain_checks':[{k:v for k,v in c.items()if k not in('source_pieces','uncovered_polygons_xz_m')}for c in checks],'bank_contacts':[],'native_contacts':[],'pass':True};pack['holdings'].append(f);pack['internal_routes'].append(route);tests.append({'holding_id':f['id'],'clear_use_area_m2':f['area_m2'],'inspection_route_length_m':sum(math.dist(a,z)for a,z in zip(points,points[1:])),'shared_native_facilities':facilities,'pass':True});print('open_use',f['id'],round(f['area_m2']),tests[-1]['inspection_route_length_m'],flush=True)
 pack['external_routes']=[{'id':f['id']+':entry','holding_id':f['id'],'width_m':2,'floor_y_m':f['floor_y_m'],'polyline_xz_m':[f['entry']['inside_point_xz_m'],f['entry']['ready_route_point_xz_m']],'ribbon_polygons_xz_m':f['entry']['ribbon_polygons_xz_m'],'joins_verified_route_id':f['entry']['ready_route_id']}for f in pack['holdings']];pack['sources']['prior_residual_pack']=ref(RES/'resolved_residual_placements.json');pack['summary']={'functional_domains':len(pack['holdings']),'exact_domain_area_m2':sum(h['area_m2']for h in pack['holdings']),'native_placements':len(pack['placements']),'internal_routes':len(pack['internal_routes']),'external_routes':len(pack['external_routes']),'deliberately_open_verges':len(tests)};pack['status']='RESOLVED_EXTENSION_SOURCE_PENDING_PATCH_AND_FINAL_CROSSPACK';pack['activation']=False;(OUT/'resolved_extension_placements.json').write_text(json.dumps(pack,indent=2)+'\n');(OUT/'open_inspection_tests.json').write_text(json.dumps({'passed':tests,'rejected':rejected,'seconds':time.monotonic()-t},indent=2)+'\n');print(pack['summary'])
if __name__=='__main__':main()
