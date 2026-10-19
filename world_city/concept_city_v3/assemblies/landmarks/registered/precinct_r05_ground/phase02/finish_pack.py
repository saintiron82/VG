"""Exact native gate intervals, productive props and finite route handoff."""
from compile_native import *

def occupancy_columns(mesh,pitch,ylo,yhi):
 events=collections.defaultdict(list)
 for g in mesh['groups']:
  for q in g['quads']:
   if not all(abs(v[1]-q[0][1])<1e-8 for v in q):continue
   sign=face_y_normal(q)
   if abs(sign)<1e-9:continue
   lo=[min(v[j]for v in q)for j in (0,2)];hi=[max(v[j]for v in q)for j in (0,2)]
   for x in range(round(lo[0]/pitch),round(hi[0]/pitch)):
    for z in range(round(lo[1]/pitch),round(hi[1]/pitch)):events[x,z].append((q[0][1],1 if sign<0 else -1))
 cols=[]
 for (x,z),ev in events.items():
  depth=0;previous=None
  for y,ds in sorted(ev):
   if depth>0 and previous is not None and min(y,yhi)-max(previous,ylo)>1e-8:cols.append((x,z));break
   depth+=ds;previous=y
 return cols

def main():
 plan=load(HERE/'design_plan.json');native=load(HERE/'native_geometry.json');scene=f.load_scene();idx=f.SurfaceIndex(scene,[box([v for p in h['polygon_parts_xz_m']for v in p])for h in plan['holdings']],margin=4);ni=geo._SpatialIndex(8)
 for i,r in enumerate(plan['native_reservations']):ni.add(i,r['polygon_xz_m'])
 tests=[];props={a['id']:a for a in load(HERE.parent/'phase01/active_ground_plan.json')['reused_prop_assets']};tree=next(a for a in props.values()if'05a884'in a['id']);bed=next(a for a in props.values()if'b8fc7'in a['id']);native['assets']+=list(props.values());prop_tests=[]
 for h in plan['holdings']:
  for p in h['plantings']:
   a=tree if p['kind']=='tree'else bed;assert ref(ROOT/a['source']['path'])==a['source']and ref(ROOT/a['cache']['path'])==a['cache'];mesh=load(ROOT/a['cache']['path']);pose=p['position_m'];yaw=p['yaw_rad'];native['placements'].append({**p,'holding_id':h['id'],'asset_key':a['id'],'source':a['source'],'cache':a['cache'],'actual_cached_bounds_local_m':mesh['bounds'],'function':'productive_orchard_tree'if p['kind']=='tree'else'medicinal_raised_bed'});rows=[]
   for g in mesh['groups']:
    for q in g['quads']:
     if not all(abs(v[1]-mesh['bounds']['min'][1])<1e-8 for v in q)or face_y_normal(q)>=0:continue
     poly=projected(q,pose,yaw);y=pose[1]+q[0][1];cl=idx.cover(poly);area=sum(geo.polygon_area(r['intersection_polygon_xz_m'])for r in cl);ys=[idx.height(r,*v)for r in cl for v in r['intersection_polygon_xz_m']];contacts=[{'id':plan['native_reservations'][i]['id'],'area_m2':geo.intersection_area(poly,plan['native_reservations'][i]['polygon_xz_m'])}for i in ni.candidates(poly)if geo.positive_area_overlap(poly,plan['native_reservations'][i]['polygon_xz_m'],0)];r={'id':p['id']+':bearing:'+str(len(rows)),'placement_id':p['id'],'holding_id':h['id'],'polygon_xz_m':poly,'bottom_y_m':y,'minimum_embed_m':min(ys)-y if ys else None,'native_area_m2':geo.polygon_area(poly),'source_support_covered_area_m2':area};rows.append(r);native['actual_bearing_footprints'].append(r);assert ys and min(ys)-y>=-1e-7 and abs(area-geo.polygon_area(poly))<1e-7,(p,r);assert not contacts,(p,contacts)
   prop_tests.append({'id':p['id'],'soil_support_pass':True,'existing_native_contact_count':0,'bearing_pieces':len(rows)})
  spec=next(s for s in plan['sources']if s['id'].endswith('estate_boundary'if h['id'].startswith('B03')else'abbey_boundary'));asset=next(a for a in native['assets']if a['id']==spec['id']);mesh=load(ROOT/asset['cache']['path']);pitch=spec['pitch_m'];pose=spec['position_m'];cols=occupancy_columns(mesh,pitch,.1,1.9);polys=[rect(pose[0]+x*pitch,pose[2]+z*pitch,pose[0]+(x+1)*pitch,pose[2]+(z+1)*pitch)for x,z in cols];routes=next(r for r in plan['internal_routes']if r['holding_id']==h['id'])['ribbon_polygons_xz_m'];ri=geo._SpatialIndex(8)
  for i,r in enumerate(routes):ri.add(i,r)
  hits=[{'body_polygon_xz_m':p,'route_index':i,'area_m2':geo.intersection_area(p,routes[i])}for p in polys for i in ri.candidates(p)if geo.positive_area_overlap(p,routes[i],0)];gate=h.get('gate');record={'holding_id':h['id'],'walking_height_boundary_route_hits':hits,'source_boundary_missing_spans':load(ROOT/spec['source']['path'])['extensions']['uncovered_boundary_spans']}
  if gate:
   d=gate['outward_direction_xz'];u=[-d[1],d[0]];intervals=[]
   for p in polys:
    q=[[sum((v[j]-gate['center_xz_m'][j])*u[j]for j in(0,1)),sum((v[j]-gate['center_xz_m'][j])*d[j]for j in(0,1))]for v in p];hit=geo.convex_intersection(q,rect(-5,-.25,5,.25))
    if geo.polygon_area(hit)>1e-9:intervals.append([min(v[0]for v in hit),max(v[0]for v in hit)])
   blocked=any(a<0<b for a,b in intervals);left=max([b for a,b in intervals if b<=0]+[-5]);right=min([a for a,b in intervals if a>=0]+[5]);record['gate_clear_width_m']=0 if blocked else right-left;record['native_gate_intervals_m']=intervals;assert record['gate_clear_width_m']>=2-1e-8,record
  assert not hits,record;tests.append(record)
 native.update(schema='riverstone.city.productive_ground.phase02.native_placements.v1',status='Compiled and source-resolved candidate; finite ground/collar and independent traversal acceptance pending.',holdings=plan['holdings'],internal_routes=plan['internal_routes'],public_handoff=plan['public_handoff'],owned_floors=[],summary={**plan['summary'],'resolved_placements':len(native['placements']),'new_assets':3,'reused_assets':2,'native_bearing_pieces':len(native['actual_bearing_footprints'])},compiled=True,resolved=True,placed_in_actual_scene=False,actual_viewed=False,player_NPC_stair_usability='Pending dedicated stair controller tests; no-step replay cannot certify stairs.',unresolved_original_access_gaps=11,unresolved_original_stepped_range_parcels=7)
 write(HERE/'resolved_placements.json',native);write(HERE/'gate_prop_tests.json',{'all_pass':True,'boundary_gates':tests,'props':prop_tests,'actual_native_support_geometry':ref(HERE/'resolved_placements.json'),'base_scene':plan['base_scene']});print(native['summary']);print(ref(HERE/'resolved_placements.json'))
if __name__=='__main__':main()
