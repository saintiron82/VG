"""Bounded source, actual top winding, native support and local ownership proof."""
import json,math,time
from .prepare import HERE,REQUEST,write,load,ref
from .. import author as a
from .....registered_integration.r7 import surface_guard

def run():
 start=time.monotonic();hand=json.loads((HERE/'physical_owner_handoff_r02.json').read_bytes());patch=json.loads((HERE/'top_scene_patch_r01.json').read_bytes());request=json.loads(REQUEST.read_bytes());native_source=load(json.loads((HERE/'input_binding.json').read_bytes())['atomic_source_addendum']);native_audit=load(native_source['native_audit']);assert native_audit['passed']
 holes=hand['native_holes'];render=hand['rendered_plane_owners'];logical=hand['physical_earth_owners'];hi=a.geo._SpatialIndex(2);oi=a.geo._SpatialIndex(2)
 for i,r in enumerate(holes):hi.add(i,r['polygon_xz_m'])
 for i,r in enumerate(logical):oi.add(i,r['polygon_xz_m'])
 overlap=[]
 for r in render:
  for j in hi.candidates(r['polygon_xz_m']):
   q=a.clip(r['polygon_xz_m'],holes[j]['polygon_xz_m'])
   if q and a.geo.polygon_area(q)>1e-7:overlap.append(dict(render_id=r['id'],hole_id=holes[j]['id'],polygon_xz_m=q,area_m2=a.geo.polygon_area(q)))
 print('Top/native overlap',len(overlap),flush=True)
 support=[]
 for r in hand['native_earth_bearings']:
  p=r['polygon_xz_m'];covers=[];errors=[]
  for j in oi.candidates(p):
   o=logical[j];q=a.clip(p,o['polygon_xz_m'])
   if not q:continue
   err=max(abs(a.common.height(o['plane_y_xz_m'],v)-r['floor_y_m'])for v in q)
   if err<=1e-7:covers.append(q)
   elif a.geo.polygon_area(q)>1e-8:errors.append(dict(owner_id=o['id'],height_error_m=err,area_m2=a.geo.polygon_area(q)))
  support.append(dict(id=r['id'],missing_equal_datum_earth_m2=sum(a.geo.polygon_area(q)for q in a.common.subtract([p],covers)),embedded_depth_m=r['floor_y_m']-r['native_bottom_y_m'],height_conflicts=errors))
 step_support=[]
 for binding in hand['profile_native_extensions']:
  extension=load(binding)
  for r in extension['native_bottom_sections']:
   p=r['polygon_xz_m'];covers=[];minimum=1e30
   for j in oi.candidates(p):
    o=logical[j];q=a.clip(p,o['polygon_xz_m'])
    if not q:continue
    depth=min(a.common.height(o['plane_y_xz_m'],v)-r['y_m']for v in q);minimum=min(minimum,depth)
    if depth>=-1e-7:covers.append(q)
   step_support.append(dict(id=r['id'],missing_underlying_physical_field_m2=sum(a.geo.polygon_area(q)for q in a.common.subtract([p],covers)),minimum_native_depth_below_field_m=None if minimum==1e30 else minimum))
 grade=[];grade_fail=[]
 for hid,binding in request['profile_bindings'].items():
  data=json.loads((HERE/'profiles'/f"{hid.replace(':','_')}.json").read_bytes());limit=data['result']['grade_limit'];triangles=data['result']['triangles'];maxg=max(t['gradient']for t in triangles);grade.append(dict(holding_id=hid,limit=limit,maximum_actual_gradient=maxg,triangles=len(triangles),pedestrian_exception=limit>.12000001))
  if maxg>limit+1e-7:grade_fail.append(hid)
 sf=[r for r in support if r['missing_equal_datum_earth_m2']>1e-7 or r['embedded_depth_m']< -1e-7 or r['height_conflicts']]
 st=[r for r in step_support if r['missing_underlying_physical_field_m2']>1e-7]
 coverage=json.loads((HERE/'top_coverage_report_r01.json').read_bytes());guard=surface_guard.audit_patch(patch)
 passed=not overlap and not sf and not st and not grade_fail and not guard['downward'] and coverage['status']=='PASSED_TOP_SOURCE_COVERAGE'
 out=dict(status='PASS_BOUNDED_TOP_NATIVE_PROFILE'if passed else'HELD_BOUNDED_TOP_NATIVE_PROFILE',passed=passed,source_native_audit=native_source['native_audit'],source_handoff=ref(HERE/'physical_owner_handoff_r02.json'),native_top_overlaps=overlap,native_bearing_support=support,support_failures=sf,variable_step_bottom_support=step_support,step_support_failures=st,grade_records=grade,grade_failures=grade_fail,surface_guard=guard,top_coverage_status=coverage['status'],summary=dict(ordinary_bearings=len(support),variable_bottom_sections=len(step_support),native_top_conflicts=len(overlap),support_failures=len(sf),step_support_failures=len(st),elapsed_s=time.monotonic()-start),activation=False)
 write('physical_acceptance_r01.json',out);print(out['status'],out['summary'],flush=True)
if __name__=='__main__':run()
