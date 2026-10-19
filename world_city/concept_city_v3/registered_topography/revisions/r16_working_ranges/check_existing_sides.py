"""Check retained vertical bank faces, including zero-area XZ projections."""
import json,math
from . import author as a,frozen_r6 as f

def interval(start,end,poly):
 lo,hi=0.,1.;sign=1 if a.geo.signed_polygon_area(poly)>0 else -1
 for p,q in zip(poly,poly[1:]+poly[:1]):
  v0=sign*a.geo._cross(p,q,start);v1=sign*a.geo._cross(p,q,end);delta=v1-v0
  if abs(delta)<1e-12:
   if v0 < -1e-9:return None
  elif delta>0:lo=max(lo,-v0/delta)
  else:hi=min(hi,-v0/delta)
  if hi-lo<1e-10:return None
 return max(0,lo),min(1,hi)

def audit(scene,owners):
 ix=a.geo._SpatialIndex(8)
 for i,r in enumerate(owners):ix.add(i,r['polygon_xz_m'])
 hits=[];below=0;checked=0
 vs=scene['surfaces'].get('bank',[])
 for j in range(0,len(vs),3):
  t=vs[j:j+3];p=[[v[0],v[2]] for v in t];candidates=ix.candidates(p)
  if not candidates:continue
  checked+=1
  length,start,end=max((math.dist(u,v),u,v) for u in p for v in p)
  if length<1e-9:continue
  dx,dz=end[0]-start[0],end[1]-start[1]
  profile=[[(dx*(v[0]-start[0])+dz*(v[2]-start[1]))/length**2,v[1]] for v in t]
  if a.geo.polygon_area(profile)<1e-10:continue
  for i in candidates:
   owner=owners[i];ab=interval(start,end,owner['polygon_xz_m'])
   if not ab:continue
   lo,hi=ab;visible=a.geo.convex_intersection(profile,[[lo,2.50001],[hi,2.50001],[hi,5],[lo,5]])
   ar=a.geo.polygon_area(visible)*length
   if ar>1e-8:hits.append(dict(owner_id=owner['id'],bank_triangle_index=j//3,above_floor_vertical_area_m2=ar,vertices_xyz_m=t,intersection_parameter_interval=[lo,hi]))
   else:below+=1
 return dict(status='PASS' if not hits else 'FAIL',base_scene_sha256=f.SCENE_SHA256,nearby_bank_triangle_count=checked,buried_or_floor_contact_count=below,above_floor_intersections=hits,policy='All original bank triangles retained. Zero-area XZ projections tested as finite segment/Y profiles.')

if __name__=='__main__':
 report=audit(f.load_scene(),a.native_holes()+a.court_regions()+a.walk_reservations());p=a.HERE/'existing_side_audit.json'
 if p.exists():raise ValueError('Evidence already exists')
 p.write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(report['above_floor_intersections']),'above-floor contacts',a.sha(p))
