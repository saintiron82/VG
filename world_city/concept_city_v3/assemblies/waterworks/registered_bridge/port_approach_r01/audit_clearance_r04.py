"""Finite 1.2 m port walking band against actual native face volumes."""
from build import *
from world_city.concept_city_v3.registered_topography.revisions.r01_ownership.author import corridor

def clip3(poly, coeff):
 out=[]
 for u,v in zip(poly,poly[1:]+poly[:1]):
  fu=sum(c*x for c,x in zip(coeff[:3],u))+coeff[3];fv=sum(c*x for c,x in zip(coeff[:3],v))+coeff[3]
  if fu>=0:out.append(u)
  if (fu>=0)!=(fv>=0):
   f=fu/(fu-fv);out.append([u[k]+f*(v[k]-u[k])for k in range(3)])
 return out

def main():
 p=read(H.parent/'side_joins_r01/port_profile_candidate.json'); infill=read(H/'native_infill_plan.json');B=np.asarray(p['native_pose']['basis']);T=np.asarray(p['native_pose']['translation']);plan=read(CITY/'registered_source/plan.json');r=next(r for r in plan['roads']if r['id']=='PORT_BRIDGE_TIE');pts=[((np.array([x,0,z])-T)@B)[[0,2]].tolist()for x,z in r['polyline_xz_m'][1:]]
 bands=g.union(corridor(pts,1.2)); clipped=[]
 for row in p['owners']:
  for poly in bands:
   q=g.clip(poly,row['polygon_local_xz_m'])
   if q and g.area(q)>1e-10:clipped.append((q,row))
 conflicts=[];checked=0
 refs=infill['source_native_refs'];pack=read(H/'resolved_placements_r02.json');refs=refs+[dict(id=pack['placements'][0]['id'],pose=pack['placements'][0],asset=dict(render_path=pack['assets'][0]['cache']['path'],render_sha256=pack['assets'][0]['cache']['sha256']))]
 for refrow in refs:
  po=refrow['pose'];asset=refrow['asset'];cache=ROOT/asset['render_path'];assert sha(cache)==asset['render_sha256'];native=read(cache);yaw=po.get('yaw_rad',0);c,s=math.cos(yaw),math.sin(yaw);NB=np.array([[c,0,s],[0,1,0],[-s,0,c]]);NT=np.asarray(po['position_m'])
  for gi,group in enumerate(native['groups']):
   for qi,quad in enumerate(group['quads']):
    q=((np.asarray(quad)@NB.T+NT-T)@B).tolist();bd=a.bounds([[v[0],v[2]]for v in q])
    for poly,owner in clipped:
     if not a.intersects(bd,a.bounds(poly)):continue
     cr=q
     area=sum(u[0]*v[1]-v[0]*u[1]for u,v in zip(poly,poly[1:]+poly[:1]));sign=1 if area>0 else -1
     for u,v in zip(poly,poly[1:]+poly[:1]):
      dx,dz=v[0]-u[0],v[1]-u[1];cr=clip3(cr,[-sign*dz,0,sign*dx,sign*(dz*u[0]-dx*u[1])])
      if not cr:break
     if not cr:continue
     checked+=1;gx,gz,k=owner['plane_local_y_xz_m'];cr=clip3(cr,[-gx,1,-gz,-k-1e-7]);cr=clip3(cr,[gx,-1,gz,k+2.2])if cr else[]
     if len(cr)>=3:
      arr=np.asarray(cr);area3=sum(np.linalg.norm(np.cross(arr[j]-arr[0],arr[j+1]-arr[0]))/2 for j in range(1,len(arr)-1))
      if area3>1e-10:conflicts.append(dict(instance=refrow['id'],group=gi,quad=qi,owner=owner['id'],intersection_local_xyz_m=cr,area_m2=area3))
 replay=CITY/'traversal_r5/revisions/r06_r8_precinct/port_bridge_candidate_r04';rep=read(replay/'evidence/public_network_replay.json');checks=dict(native_swept_band_clear=not conflicts,six_cases_pass=len(rep['routes'])==6 and all(q['pass']for q in rep['routes']),zero_support_misses_airborne=all(q['ground_ray_miss_frames']==q['not_on_floor_frames']==0 for q in rep['routes']),controller_loader_unchanged=all((replay/n).read_bytes()==(ROOT/src).read_bytes()for n,src in [('Traversal.gd','world_city/concept_city_v3/traversal_r5/Traversal.gd'),('RenderData.gd','voxel_character/common/preview/RenderData.gd')]))
 out=dict(status='PASS'if all(checks.values())else'HOLD',checks=checks,profile=ref(H.parent/'side_joins_r01/port_profile_candidate.json'),native_pack=ref(H/'resolved_placements_r02.json'),source_native_refs=refs,band_width_m=1.2,head_clearance_m=2.2,capsule_radius_m=.3,tested_center_offsets_m=[0],band_polygons_local_xz_m=[q for q,r in clipped],checked_native_faces=checked,conflicts=conflicts,replay=ref(replay/'evidence/public_network_replay.json'),limits=['Full 6 m source footprint includes retained guard margins. The audited swept walking band is 1.2 m.','Final composed-scene activation and replay remain required. The focused replay does not certify carts, engineering loads or live bridge operation.'])
 write(H/'clearance_audit_r04.json',out);print(json.dumps(dict(status=out['status'],checks=checks,conflicts=len(conflicts))));assert all(checks.values())
if __name__=='__main__':main()
