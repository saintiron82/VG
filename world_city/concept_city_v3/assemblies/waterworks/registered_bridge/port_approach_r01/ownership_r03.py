"""Exact native footprint and current scene top retirement requests; no scene changes."""
from build import *
from normalized import normalized,NORMALIZATION
from world_city.concept_city_v3.assemblies.waterworks.registered_bridge.side_joins_r01.port_profile import half
def main():
 p=read(H.parent/'side_joins_r01/port_profile_candidate.json');pack=read(H/'resolved_placements_r02.json');plan=read(H/'native_infill_plan.json');B=np.asarray(p['native_pose']['basis']);T=np.asarray(p['native_pose']['translation']);world=lambda q:(np.asarray(q)@B.T+T).tolist();fine=read(ROOT/pack['assets'][1]['cache']['path']);coarse=read(ROOT/pack['assets'][0]['cache']['path']);foot=[];fine_rows=[];protrusions=[]
 for gi,group in enumerate(fine['groups']):
  for qi,q in enumerate(group['quads']):
   n=np.cross(np.asarray(q[1])-q[0],np.asarray(q[2])-q[0])
   if n[1]<=0:continue
   poly=[[v[0],v[2]]for v in q];foot.append(poly);fine_rows.append(dict(group=gi,quad=qi,polygon_local_xz_m=poly,top_y_m=q[0][1]))
 support_faces=[]
 for gi,gg in enumerate(coarse['groups']):
  for qi,q in enumerate(gg['quads']):
   n=np.cross(np.asarray(q[1])-q[0],np.asarray(q[2])-q[0])
   if n[1]>0:support_faces.append(dict(group=gi,quad=qi,y_m=q[0][1],polygon_xz_m=[[v[0],v[2]]for v in map(world,q)]))
 support_index=a.geo._SpatialIndex(4)
 for i,r in enumerate(support_faces):support_index.add(i,r['polygon_xz_m'])
 support_masks=[]
 foot=g.union(foot);worldfoot=[[[v[0],v[2]]for x,z in poly for v in[world([x,0,z])]]for poly in foot];ix=a.geo._SpatialIndex(4)
 for i,poly in enumerate(worldfoot):ix.add(i,poly)
 for gi,gg in enumerate(coarse['groups']):
  for qi,q in enumerate(gg['quads']):
   ar=np.asarray(q);n=np.cross(ar[1]-ar[0],ar[2]-ar[0])
   if n[1]<=0:continue
   poly=[[v[0],v[2]]for v in q]
   for r in p['owners']:
    if not a.intersects(a.bounds(poly),a.bounds(r['polygon_local_xz_m'])):continue
    z=g.clip(poly,r['polygon_local_xz_m'])
    if z and g.area(z)>1e-9:
     delta=max(q[0][1]-a.common.height(r['plane_local_y_xz_m'],v)for v in z)
     if delta>1e-8:protrusions.append(dict(group=gi,quad=qi,owner=r['id'],protrusion_m=delta))
 prepared=read(CITY/'traversal_r5/revisions/r06_r8_precinct/public_network_r18_runtime_r01/prepared_runtime.json');ass=prepared['assets']['SCENE:PUBLIC_NETWORK:ROAD:PORT_BRIDGE_TIE'];loc=read(ROOT/ass['render_path']);requests=[];above=[]
 for key,ct in zip(loc['source_face_indices'],loc['triangles']):
  if key[0]in ['water','bank']:continue
  t=[ct[0],ct[2],ct[1]]
  if a.normal_y(t)<=1e-10 or max(v[1]for v in t)<.5:continue
  poly=[[v[0],v[2]]for v in t];finecuts=[q for i in ix.candidates(poly)if(q:=g.clip(poly,worldfoot[i]))];plane=a.common.plane(t);coarsecuts=[]
  for i in support_index.candidates(poly):
   sf=support_faces[i];cl=g.clip(poly,sf['polygon_xz_m']);cl=half(cl,[-plane[0],-plane[1],sf['y_m']-plane[2]])
   if cl and g.area(cl)>1e-12:coarsecuts.append(cl);support_masks.append(dict(source_key=key,coarse_group=sf['group'],coarse_quad=sf['quad'],coarse_top_y_m=sf['y_m'],polygon_xz_m=cl,source_plane_y_xz_m=plane))
  cuts=g.union(finecuts+coarsecuts);cutarea=sum(g.area(q)for q in cuts)
  if cutarea<=1e-9:continue
  plane=a.common.plane(t);rest=g.subtract([poly],cuts);triangles=[]
  for qi,q in enumerate(rest):
   q=normalized(q,str(key)+':'+str(qi))
   for j in range(1,len(q)-1):
    tt=[[v[0],a.common.height(plane,v),v[1]]for v in[q[0],q[j],q[j+1]]]
    if a.normal_y(tt)<0:tt=[tt[0],tt[2],tt[1]]
    if a.normal_y(tt)>0:triangles.append(tt)
  error=abs(g.area(poly)-sum(g.area(q)for q in rest)-cutarea);assert error<1e-7
  requests.append(dict(runtime_source_key=key,source_triangle_xyz_m=t,source_triangle_sha256=a.canonical_sha(t),replacement_triangles_xyz_m=triangles,removed_area_m2=cutarea,partition_error_m2=error))
 report=dict(schema='riverstone.port_compiled_native_ownership.v1',scene=prepared['sources']['scene'],prepared_asset=ass,native_pack=ref(H/'resolved_placements_r02.json'),profile=ref(H.parent/'side_joins_r01/port_profile_candidate.json'),actual_fine_top_polygons_local_xz_m=foot,actual_fine_top_polygons_xz_m=worldfoot,actual_fine_top_records=fine_rows,actual_fine_top_area_m2=sum(g.area(q)for q in foot),coarse_above_walking_profile=protrusions,current_top_retirement_requests=requests,removed_current_top_area_m2=sum(r['removed_area_m2']for r in requests),new_walk_profile_triangle_count=sum(len(r['triangles_world_xyz_m'])for r in p['owners']),native_cache_changes=0,water_surface_changes=0,limits=['Retirement requests are keyed to exact current runtime source triangles, not guessed R7 indices. Parent composition must resolve exact source/append ownership and retain all unaffected parts.','Only dry top masks under actual compiled fine cap. Water, submerged beds, existing native cache geometry and state barriers remain unchanged.','The retained two quarter-metre guard caps touch the nominal ribbon edge; tested lane centers ±2.3 m and capsule radius0.3 m are separately audited.'])
 report['predecessor_requests']=ref(H/'ownership_requests_r02.json');report['actual_coarse_top_ownership_masks']=support_masks;report['coarse_mask_rule']='Retire old dry top only where an actual compiled coarse support top covers it at or above its unchanged source plane.';report['normalization_policy']='Only redundant free partition knots within 1 nm of their finite neighboring segment are removed; every retained vertex and original source plane is unchanged.';report['normalization_rows']=NORMALIZATION;report['normalization_maximum_distance_m']=max((v['distance_to_retained_edge_m']for r in NORMALIZATION for v in r['removed']),default=0);report['normalization_total_absolute_area_delta_m2']=sum(abs(r['area_delta_m2'])for r in NORMALIZATION);tris=[t for r in requests for t in r['replacement_triangles_xyz_m']];q=np.array(tris,dtype=np.float32);cross=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);report['float32_nonzero_downward_faces']=int(((cross[:,1]<=0)&np.any(cross!=0,axis=1)).sum());report['float32_exact_zero_faces']=int(np.all(cross==0,axis=1).sum());report['retained_faces']=len(tris);report['float32_nonzero_downward_records']=[dict(i=i,triangle=t,normal=q)for i,(t,q)in enumerate(zip(tris,cross.tolist()))if q[1]<=0 and any(q)];write(H/'ownership_requests_r03.json',report);assert report['float32_nonzero_downward_faces']==0,report['float32_nonzero_downward_faces'];print(json.dumps(dict(footprint_area=report['actual_fine_top_area_m2'],pieces=len(foot),retirements=len(requests),retired_area=report['removed_current_top_area_m2'],support_protrusions=len(protrusions))))
 assert not protrusions,protrusions
if __name__=='__main__':main()
