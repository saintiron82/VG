"""Full-width private approach support and actual retained-native clearance."""
from build_ground_patch import *
OUT=Path(__file__).resolve().parent

def main():
 start=time.monotonic();pack=load(OUT/'resolved_native_candidate.json');ground=load(OUT/'native_ground_candidate_audit.json');patch=load(OUT/'native_ground_candidate_patch.json');routes=load(OUT/'runtime_routes.json');scene=terrain.load_scene();edits={(r['material'],r['triangle_index']):r for r in patch['surface_edits']}
 for mat,vs in list(scene['surfaces'].items()):scene['surfaces'][mat]=[v for i in range(len(vs)//3)for tri in edits.get((mat,i),dict(replacement_triangles_xyz_m=[vs[3*i:3*i+3]]))['replacement_triangles_xyz_m']for v in tri]
 for mat,vs in patch['appended_surfaces'].items():scene['surfaces'].setdefault(mat,[]).extend(vs)
 projection=load(BASE/'actual_native_projection.json');preserved=[p for p in projection['instances']if p['id']not in pack['replacement_ledger']['existing_native_placements_removed']];native=[]
 for p in preserved:native.append(dict(p,cache=projection['assets'][p['asset_key']]['cache']))
 native +=[p for p in pack['placements']if p['role']=='retained_base'];ni=geo._SpatialIndex(8);meshes={};footprints=[]
 for i,p in enumerate(native):
  if 'native_parts_xz_m'in p:polys=p['native_parts_xz_m']
  else:polys=[r['polygon_xz_m']for r in faces(p)[1]]
  for q in polys:ni.add(len(footprints),q);footprints.append((i,q))
 reports=[]
 for route in routes['routes']:
  eid=route['owner_id'];pts=route['polyline_xz_m'];end=np.array(pts[-2]);direction=end-np.array(pts[-3]);direction/=np.linalg.norm(direction);public=b.ribbon([(end+direction*route['public_transition_start_offset_m']).tolist(),(end+direction*1.5).tolist()],3.6)[0];polys=[q for poly in b.ribbon(pts,2)for q in terrain.common.subtract([poly],[public])];physical=load(ROOT/route['physical_top']['path'])['top_pieces'];base=[r for r in ground['retained_base_upward_faces']if r['native_id'].split(':')[1]==eid];nv=[v for r in physical+base for t in terrain.fan_upward(lift(r['polygon_xz_m'],r['plane_y_xz_m']))for v in t];nativeidx=terrain.TriangleIndex({'surfaces':{'actual_native_physical_walk':nv}},polys);groundidx=terrain.TriangleIndex(scene,polys)
  class Support:
   def covering(self,p):
    rows=list(nativeidx.covering(p));claimed=[r['intersection_polygon_xz_m']for r in rows];yield from rows
    for r in groundidx.covering(p):
     for q in terrain.common.subtract([r['intersection_polygon_xz_m']],claimed):
      if geo.polygon_area(q)>1e-8:yield dict(r,intersection_polygon_xz_m=q);claimed.append(q)
  checks=[terrain.audit_polygon(Support(),q,None)for q in polys];pieces=[r for c in checks for r in c['source_pieces']];side=SideIndex(scene,polys).audit([dict(id=eid+':'+str(i),polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'])for i,r in enumerate(pieces)]);contacts=[];slabs={}
  for piece in pieces:
   q=piece['polygon_xz_m'];ys=[terrain.common.height(piece['plane_y_xz_m'],v)for v in q];candidates=set(i for k in ni.candidates(q)if geo.intersection_area(q,footprints[k][1])>1e-8 for i in[footprints[k][0]])
   for i in candidates:
    p=native[i];key=p['cache']['path'];meshes.setdefault(key,load(ROOT/key));lo=min(ys)-p['position_m'][1]+.15;hi=max(ys)-p['position_m'][1]+2.2;sk=(key,round(lo,7),round(hi,7))
    if sk not in slabs:slabs[sk]=slab_rectangles(meshes[key],lo,hi)
    for local in slabs[sk]:
     pol=b.xform(local,p);ar=geo.intersection_area(q,pol)
     if ar>1e-7:contacts.append(dict(native_id=p['id'],area_m2=ar,polygon_xz_m=geo.convex_intersection(q,pol),route_floor_plane_y_xz_m=piece['plane_y_xz_m'],sampled_native_height_interval_m=[lo+p['position_m'][1],hi+p['position_m'][1]]))
  report=dict(owner_id=eid,private_polygons_xz_m=polys,public_R18_window_xz_m=public,full_width_m=2,surface_checks=checks,bank_contacts=side['contacts'],retained_native_contacts=contacts,passes=all(c['passes_existing_surface']for c in checks)and not side['contacts']and not contacts);reports.append(report);print(eid,report['passes'],'gap',sum(c['missing_area_m2']for c in checks),'banks',len(side['contacts']),'natives',len(contacts),flush=True)
 write('private_route_audit.json',dict(status='PASS_PRIVATE_STATIC_PUBLIC_AND_RUNTIME_PENDING'if all(r['passes']for r in reports)else'HELD_PRIVATE_ROUTE_FAILURE',owners=reports,seconds=time.monotonic()-start,runtime_ready=False))
if __name__=='__main__':main()
