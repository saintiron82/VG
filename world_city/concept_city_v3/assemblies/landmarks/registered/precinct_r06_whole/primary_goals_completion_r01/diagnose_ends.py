from find_branches import *
scene=load(SC);out=[]
for group in ['castle','cathedral','monastery']:
 r=load(O/(group+'_branch_search_r02.json'));q=r['selected_exterior_standing_xz_m'];fy=r['entrance']['threshold_world_xyz_m'][1];circle=b.rect(q[0]-.3,q[1]-.3,q[0]+.3,q[1]+.3);hits=[]
 for pr in r['actual_native_sources']:
  p=next(p for p in scene['common_instances']if p['id']==pr['id']);m=load(ROOT/pr['cache']['path'])
  for k,poly in enumerate(slab_rectangles(m,fy-p['position_m'][1]+.01,fy-p['position_m'][1]+1.8)):
   poly=b.xform(poly,p);ar=geo.intersection_area(circle,poly)
   if ar>1e-8:hits.append(dict(native_id=p['id'],asset_key=p['asset_key'],body_piece=k,polygon_xz_m=poly,overlap_area_m2=ar,cache=pr['cache']))
 ix=terrain.TriangleIndex(scene,[circle]);check=terrain.audit_polygon(ix,circle,fy);out.append(dict(group=group,target=q,body_contacts=hits,actual_scene_terrain_support=check));print(group,'hits',[(h['native_id'],h['overlap_area_m2'])for h in hits],'terrain missing',check['missing_area_m2'],flush=True)
write('opening_endpoint_diagnosis.json',dict(scene=ref(SC),rows=out))
