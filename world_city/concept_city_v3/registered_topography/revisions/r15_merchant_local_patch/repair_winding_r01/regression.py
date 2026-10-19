"""Bounded actual-render/native-mask regression; no geometry generation."""
import hashlib,json,math
from collections import Counter
from . import author as r

a=r.a;geo=a.geo
PACK_PATH=a.HERE/'subset_07/merchant_pack.json'
PACK_SHA='d3716b00c4537b5d742dcb4165e07a7f9a8253deca0ef2199f691a0741f28440'
def clean(p):return a.polygon(p)
def area(ps):return sum(geo.polygon_area(p) for p in ps)
def difference(ps,qs):return a.subtract(ps,qs)
def bbox(p):
 x,z=zip(*p);return min(x),min(z),max(x),max(z)
def touches(b,c):return b[0]<=c[2]+1e-8 and b[2]>=c[0]-1e-8 and b[1]<=c[3]+1e-8 and b[3]>=c[1]-1e-8
def clips(p,ps):return [q for poly in ps if (q:=clean(geo.convex_intersection(poly,p)))]
def court_parts(poly):
 """Validation-only ear partition for the source's concave L-shaped courts."""
 points=[list(p) for p in poly]
 if geo.signed_polygon_area(points)<0:points.reverse()
 out=[]
 while len(points)>3:
  for i in range(len(points)):
   tri=[points[i-1],points[i],points[(i+1)%len(points)]]
   if geo.signed_polygon_area(tri)<=1e-10:continue
   if any(geo.point_in_convex_polygon(p,tri,0) for j,p in enumerate(points) if j not in {(i-1)%len(points),i,(i+1)%len(points)}):continue
   out.append(tri);points.pop(i);break
  else:raise ValueError('Unpartitioned source court')
 out.append(points);assert abs(area(out)-geo.polygon_area(poly))<1e-7
 return out

def world(p,placement):
 x,y,z=p;c=math.cos(placement['yaw_rad']);s=math.sin(placement['yaw_rad']);v=placement['position_m']
 return [v[0]+c*x+s*z,v[1]+y,v[2]-s*x+c*z]

def run():
 assert a.sha(PACK_PATH)==PACK_SHA
 pack=json.loads(PACK_PATH.read_bytes());scene=r.load_scene();fixed=r.apply_orientation(scene)
 # Exact replay of the parent's newly written derived scene, when present.
 derived=a.CITY/'evidence/visual_registered_common_r6_winding_r01/scene.json'
 replay_equal=None
 if derived.exists():replay_equal=fixed==json.loads(derived.read_bytes());assert replay_equal
 wanted=set(pack['subset_binding']['accepted_property_ids'])
 platforms=[p for p in a.PLATFORMS if p['property_id'] in wanted]
 pboxes=[bbox(p['polygon_xz_m']) for p in platforms]
 nearby=[]
 for mat,vs in fixed['surfaces'].items():
  for i in range(0,len(vs),3):
   tri=vs[i:i+3]
   if r.normal_y(tri)<=1e-10:continue
   poly=[[v[0],v[2]] for v in tri];bb=bbox(poly)
   if any(touches(bb,b) for b in pboxes):nearby.append((poly,bb,tri,mat,i//3))
 native={pid:{'bottoms':[],'floors':[]} for pid in wanted};native_hashes={}
 for placement in pack['placements']:
  path=a.ROOT/placement['compiled_asset_ref']
  if not path.exists():path=a.ROOT/str(path).split('riverstone-expansion-recovered/',1)[-1]
  assert a.sha(path)==placement['render_sha256'];native_hashes[str(path.relative_to(a.ROOT))]=a.sha(path)
  render=json.loads(path.read_bytes());floor=placement['finished_floor_y_m'];bottom=placement['position_m'][1]
  for group in render['groups']:
   for q in group['quads']:
    w=[world(v,placement) for v in q];ny=r.normal_y(w[:3]);poly=[[v[0],v[2]] for v in w]
    if ny < -1e-10 and max(abs(v[1]-bottom) for v in w)<1e-8:native[placement['property_id']]['bottoms'].append(poly)
    if ny > 1e-10 and max(abs(v[1]-floor) for v in w)<1e-8:native[placement['property_id']]['floors'].append(poly)
 reports=[]
 for p in platforms:
  pid=p['property_id'];poly=p['polygon_xz_m'];bb=bbox(poly);floor=p['floor_y_m'];n=native[pid]
  candidates=[t for t in nearby if touches(bb,t[1]) and max(abs(v[1]-floor) for v in t[2])<1e-7]
  tops=clips(poly,[t[0] for t in candidates]);bottoms=clips(poly,n['bottoms']);floors=clips(poly,n['floors'])
  declared=[q for m in pack['ownership_masks'] if m['property_id']==pid for q in m['terrain_exclusion_regions_xz_m']]
  gap=area(difference([poly],tops+bottoms))
  native_missing=area(difference(declared,n['bottoms']));native_excess=area(difference(n['bottoms'],declared))
  overlap=sum(geo.polygon_area(geo.convex_intersection(t,h)) for t in tops for h in bottoms if touches(bbox(t),bbox(h)))
  court=next(c for c in pack['courts'] if c['id'].startswith(pid+':'))
  pieces=court_parts(court['polygon_xz_m'])
  court_gap=area(difference(pieces,tops+bottoms))
  no_visible_floor=area(difference(pieces,tops+floors))
  item=dict(property_id=pid,floor_y_m=floor,platform_area_m2=geo.polygon_area(poly),actual_upward_terrain_piece_count=len(tops),actual_native_bottom_quad_count=len(n['bottoms']),actual_native_floor_quad_count=len(n['floors']),platform_uncovered_m2=gap,court_uncovered_including_native_solid_m2=court_gap,court_without_horizontal_floor_m2=no_visible_floor,terrain_native_bottom_overlap_m2=overlap,declared_native_mask_missing_m2=native_missing,declared_native_mask_excess_m2=native_excess)
  # Native wall sections can occupy court edges, so their supported solid is
  # recorded separately from horizontal floor. No invented floor fills it.
  assert max(gap,court_gap,native_missing,native_excess,overlap)<1e-6,item
  reports.append(item);print(pid,'PASS',flush=True)
 failures=json.loads((a.CITY/'traversal_r5/revisions/r03_r6_merchant/evidence/failure_ray_geometry.json').read_bytes())
 rays=[]
 for case in failures['cases']:
  for hit in case['candidate_triangles_in_ray_interval']:
   mat,i=hit['scene_material_and_triangle'];old=scene['surfaces'][mat][i*3:i*3+3];new=fixed['surfaces'][mat][i*3:i*3+3]
   point=case['final_repeated_miss_center_xyz_m'];assert geo.point_in_convex_polygon([point[0],point[2]],[[v[0],v[2]] for v in new],1e-8)
   assert [old[0],old[2],old[1]]==hit['triangle_world_xyz_m'] and r.normal_y(old)<0 and r.normal_y(new)>0
   rays.append(dict(route_id=case['route_id'],material=mat,triangle_index=i,normal_y_before=r.normal_y(old),normal_y_after=r.normal_y(new),same_xyz_set=sorted(old)==sorted(new)))
 assert len(rays)==10
 for poly in ([[0,1,0],[1,1,0],[1,1,1],[0,1,1]],[[0,1,1],[1,1,1],[1,1,0],[0,1,0]]):
  ts=list(r.fan_upward(poly));assert len(ts)==2 and all(r.normal_y(t)>0 for t in ts)
 result=dict(status='PASS_RENDERED_ORIENTATION_AND_SEVEN_PLATFORM_NATIVE_COVERAGE',base_scene_sha256=r.SCENE_SHA256,patch_sha256=a.sha(r.HERE/'scene_patch.json'),merchant_pack_sha256=PACK_SHA,derived_scene_equal=replay_equal,native_render_hashes=native_hashes,properties=reports,failed_ray_regressions=rays,producer_cw_ccw_pass=True,limits=['Exact finite planar coverage and front-facing regression, not a capsule or cart pass.','Court portions occupied by actual native solids remain distinct from exposed horizontal walking floors.'])
 path=r.HERE/'coverage_report.json'
 if path.exists():raise ValueError('Refusing to overwrite coverage evidence')
 path.write_text(json.dumps(result,indent=2)+'\n');print('coverage_report',a.sha(path),flush=True)
if __name__=='__main__':run()
