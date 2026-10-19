"""Independent checks and runtime-request preparation for the bounded candidate."""
from build_candidate import *

def main():
 ctx=read(H/'context.json')['sites']['abbey'];patch=read(H/'surface_patch.json');
 changed={(e['material'],e['triangle_index']):e for e in patch['surface_edits']};actual=[]
 for r in ctx['surface_rows']:
  e=changed.get((r['material'],r['triangle_index']))
  actual.extend([dict(r,triangle=t)for t in e['replacement_triangles_xyz_m']] if e else [r])
 oldground=Ground(ctx['surface_rows']);ground=Ground(actual);appended=patch['appended_surfaces'];pack=read(H/'pack.json');assets=pack['common_assets'];adds=pack['add_instances'];float_skips=[]
 gate=[-259.,-7.823607];road=[-247.49131238451622,-7.333062439626094];arrival=[road,[-253.,-7.568],gate];ward=[gate,[-291.,-7.823607],[-298.,-8.],[-311.5,-8.],[-311.5,-13.5],[-324.,-13.5],[-324.,-17.25]]

 plan=read(C/'registered_source/plan.json');source_road=next(r for r in plan['roads']if r['id']=='WEST_MONASTERY_EDGE');through=[xz(v)for v in source_road['resolved_world_xyz_m'][9:12]]
 route_defs=[dict(id='R10_ABBEY_EXISTING_PUBLIC_ROAD_THROUGH',access='unrestricted_public',pts=through,width=2.5),dict(id='R10_ABBEY_PUBLIC_ROAD_TO_ADMISSION',access='unrestricted_public',pts=arrival,width=2.5),dict(id='R10_ABBEY_ADMITTED_PATIENT_TO_WARD_DOOR',access='admitted_patient_staff',pts=ward,width=1.5)]
 tests=[];routes=[];newground=Ground([dict(material=m,triangle_index=i//3,triangle=vs[i:i+3])for m,vs in appended.items()for i in range(0,len(vs),3)])
 def support(p):
  if any(geo.point_in_convex_polygon(p,r['polygon_xz_m'],0)for r in ctx['floors']):return 8.
  try:return newground.at(p)
  except ValueError:return ground.at(p)
 for rr in route_defs:
  polys=ribbons(rr['pts'],rr['width']);hits=[]
  for q in polys:
   for b in ctx['bodies']:
    ar=geo.intersection_area(q,b['polygon_xz_m'])
    if ar>1e-8:hits.append(dict(id=b['id'],area_m2=ar))
   for i in adds:
    a=assets[i['asset_key']];mesh=read(ROOT/a.get('render_path') or a['cache']['path'])
    for b in slab_rectangles(mesh,8-i['position_m'][1]+.01,10.2-i['position_m'][1]):
     ar=geo.intersection_area(q,transform(b,i))
     if ar>1e-8:hits.append(dict(id=i['id'],area_m2=ar))
  points=[]
  for a,b in zip(rr['pts'],rr['pts'][1:]):
   n=max(1,math.ceil(math.dist(a,b)/.25))
   for j in range(n):
    p=[a[k]+j/n*(b[k]-a[k])for k in [0,1]];points.append([p[0],support(p),p[1]])
  p=rr['pts'][-1];points.append([p[0],support(p),p[1]])
  allsupport=DomainCut(ctx['floors']+[dict(polygon_xz_m=r['polygon'])for r in newground.rows]+[dict(polygon_xz_m=r['polygon'])for r in ground.rows]);missing=sum(geo.polygon_area(p)for q in polys for p in allsupport.subtract(q))
  result=dict(id=rr['id'],width_m=rr['width'],native_contacts=hits,missing_support_area_m2=missing,length_3d_m=sum(math.dist(a,b)for a,b in zip(points,points[1:])),length_horizontal_m=sum(math.dist(a,b)for a,b in zip(rr['pts'],rr['pts'][1:])),max_sampled_step_025m_m=max(abs(b[1]-a[1])for a,b in zip(points,points[1:])),max_sampled_grade=max(abs(b[1]-a[1])/math.dist(xz(a),xz(b))for a,b in zip(points,points[1:])),coverage_numeric_area_tolerance_m2=2e-6,passes=not hits and missing<2e-6)
  before=[]
  for p in points:
   q=xz(p)
   try:y=oldground.at(q)
   except ValueError:y=8. if any(geo.point_in_convex_polygon(q,r['polygon_xz_m'],0)for r in ctx['floors']) else None
   before.append(y)
  result['before_max_sampled_step_025m_m']=max(abs(b-a)for a,b in zip(before,before[1:])if a is not None and b is not None)
  tests.append(result);routes.append(dict(id=rr['id'],group='ABBEY_ADMISSION',points=points,design_clear_width_m=rr['width'],width_m=rr['width'],public_access=rr['access'],source_road_ids=['WEST_MONASTERY_EDGE'] if rr['access']=='unrestricted_public' else ['ABBEY_NORTH_WORK:main_gate','ABBEY_NORTH_WORK:infirmary:actual_entry'],cart_test=False,test_scope='Pedestrian only; no handcart, bed, stretcher, staffing or medical-service-capacity claim.'))
 assert all(t['passes']for t in tests),tests
 idx=read(C/'registered_integration/r9/integration_r02_camera/index.json');idx['packs'].append(ref(H/'pack.json'));write('index.json',idx)
 write('routes.json',dict(schema='riverstone.r10.institution_runtime_request.v1',base_scene=ref(BASE),base_scene_sha256=SHA,finite_patch=ref(H/'surface_patch.json'),visual_index=ref(H/'index.json'),collision_margin_m=8,routes=routes,public_graph_policy='Only unrestricted_public arrival may join ordinary public graph. Admitted inner court must remain excluded.',cameras=[dict(id='R10_ABBEY_ADMISSION_OVERVIEW',position=[-230,47,30],target=[-286,8,-8]),dict(id='R10_ABBEY_PUBLIC_GATE_EYE',position=[-245,10,-7.3],target=[-267,9,-7.8]),dict(id='R10_ABBEY_WARD_APPROACH',position=[-311,11,-13.5],target=[-324,9.5,-16])]))
 write('source_tests.json',dict(status='SOURCE_PASS_RUNTIME_AND_VIEW_PENDING',base_unchanged=sha(BASE)==SHA,tests=tests,summary=patch['summary'],native_sources=[dict(id=r['instance']['id'],master=r['asset'].get('source'),cache=r['asset'].get('cache'))for r in ctx['instances']],float32_degenerate_skips=float_skips,unchanged_private_boundary=True,actual_doorway=dict(id='ABBEY_NORTH_WORK:infirmary:actual_entry',center_xyz_m=[-324,8,-16],source_opening_width_m=2.5,source_opening_height_m=3.5),runtime_capsule_tested=False,gui_viewed=False))
 print(json.dumps(dict(summary=patch['summary'],tests=tests),indent=2))

if __name__=='__main__':main()
