from author import *
def main():
 c=load(O/'collision_contract.json');audit=load(O/'geometry_audit.json');auth=load(O/'authored_collision_mesh.json');mesh=load(ROOT/c['native_source']['path']);p=audit['native_placement'];retained=c['add_triangles_world_xyz_m'][:c['retained_native_triangle_count']];proxy=c['add_triangles_world_xyz_m'][c['retained_native_triangle_count']:];tests=[]
 def check(name,value,details=None):assert value,(name,details);tests.append(dict(name=name,passed=True,details=details))
 check('Native source and visual master hashes exact',sha(ROOT/c['native_source']['path'])==c['native_source']['sha256']and sha(ROOT/c['source_profile']['path'])==c['source_profile']['sha256'])
 retainedkeys={canonical(t)for t in retained};negative=[]
 for row in audit['negative_walls_and_exterior_faces']:
  q0=mesh['groups'][row['group_index']]['quads'][row['quad_index']];q=[[v[k]+p['position_m'][k]for k in range(3)]for v in q0];negative.append(all(canonical(t)in retainedkeys for t in tris(q)))
 check('Every exterior/negative face retained verbatim',all(negative),dict(count=len(negative)))
 removed_top=sum(r['removed_area3_m2']for r in audit['removed_native_face_ledger']if r['kind']=='upward_walking');area=sum(geo.polygon_area([[v[0],v[2]]for v in t])for t in proxy);check('Walking domain equals only retired actual top union',abs(area-removed_top)<1e-7,dict(proxy_area_m2=area,removed_top_area_m2=removed_top,error_m2=area-removed_top))
 check('Finite native partition exact',abs(audit['partition_error_m2'])<1e-7,audit['partition_error_m2']);check('Envelope stays below visible and within0.15m',audit['maximum_collision_above_visual_m']<1e-7 and audit['maximum_visual_above_collision_m']<=.1500001);check('Pedestrian grade at most12percent',audit['max_grade']<=.1200001,audit['max_grade'])
 # No discarded nonzero runtime faces; surviving triangles preserve exact order.
 prec=load(O/'exact_precision_ledger.json');expected=[auth['triangles'][i]for i in prec['retained_source_indices']];check('Runtime normalization exact indexed source subsequence',expected==c['add_triangles_world_xyz_m']);_,_,_,zero=zero_mask([v for t in expected for v in t]);check('No exact float32 degenerate triangles',not any(zero));check('Godot walking normals point upward',all(h.normal(t)[1]<0 for t in proxy))
 terminal=[v for t in proxy for v in t if abs(v[0]+255.625)<1e-7];check('Actual native outer cap stays exactY18.125',bool(terminal)and max(abs(v[1]-18.125)for v in terminal)<1e-7,dict(vertex_count=len(terminal),max_error_m=max(abs(v[1]-18.125)for v in terminal)))
 cat=load(CITY/'traversal_r5/revisions/r06_r8_precinct/public_network_final_catalog_r01/route_catalog_481_r01.json');route=next(r for r in cat['routes']if r['id']=='TRAIN_RETAINED_ENTRY_R01');tube=b.ribbon([[q[0],q[2]]for q in route['points_xyz_m'][3:]],.6);windows=[audit['corridor_polygon_xz_m']];missing=0;outside=[]
 for q in tube:
  cut=geo.convex_intersection(q,windows[0]);uncovered=terrain.common.subtract([cut],[r['polygon_xz_m']for r in audit['profile_errors']]);outside+=uncovered
  for r in audit['actual_top_source_faces']:
   for v in uncovered:missing+=geo.intersection_area(v,r['polygon_xz_m'])
 check('Full unchanged capsule tube has actual proxy support insidecorridor',missing<1e-7,missing)
 scene=load(ROOT/audit['source_scene']['path']);index=terrain.TriangleIndex(scene,outside);outside_checks=[terrain.audit_polygon(index,q,None,grade_limit=1)for q in outside if geo.polygon_area(q)>1e-9];check('Beyond-native strip remains supported by unchanged actual terrain',all(r['passes_existing_surface']for r in outside_checks),dict(area_m2=sum(r['area_m2']for r in outside_checks),missing_area_m2=sum(r['missing_area_m2']for r in outside_checks)))
 report=write('source_tests.json',dict(status='PASS_RUNTIME_PENDING',tests=tests,route_catalog=ref(CITY/'traversal_r5/revisions/r06_r8_precinct/public_network_final_catalog_r01/route_catalog_481_r01.json'),route_id=route['id'],case_directions=['TRAIN_RETAINED_ENTRY_R01','TRAIN_RETAINED_ENTRY_R01_REVERSE'],source_visible_geometry_unchanged=True,controller_source=ref(CITY/'traversal_r5/Traversal.gd'),negative_native_faces_preserved=len(negative),outside_native_unchanged_terrain_checks=outside_checks))
 hand=load(O/'integration_handoff.json');hand['source_tests']=report;hand['approved_continuous_collision_pattern']=ref(HELP);hh=write('integration_handoff.json',hand);write('freeze_manifest.json',dict(handoff=hh,files=[ref(x)for x in sorted(O.iterdir())if x.is_file()and x.name!='freeze_manifest.json'],runtime_ready=False));print(json.dumps(hh));print('tests',len(tests),'area',area,'negative',len(negative))
if __name__=='__main__':main()
