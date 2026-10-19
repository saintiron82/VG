"""Independent native source/cache and finite collision/ground closure checks."""
from pathlib import Path
import sys,json,math,time,collections
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE));sys.path.insert(0,str(OUT))
from resolve_pack import *
from build_ground_patch import faces,upper
OUT=Path(__file__).resolve().parent

def refs(obj):
 if isinstance(obj,dict):
  if 'path'in obj and'sha256'in obj and isinstance(obj['path'],str):yield obj
  for v in obj.values():yield from refs(v)
 elif isinstance(obj,list):
  for v in obj:yield from refs(v)
def main():
 started=time.monotonic();pack=load(OUT/'resolved_native_candidate.json');proof=load(OUT/'native_ground_candidate_audit.json');patch=load(OUT/'native_ground_candidate_patch.json');geometry=load(OUT/'geometry_audit.json');bundle=load(OUT/'collision_contracts.json');caps=load(CITY/'assemblies/property/registered/public_lane_repairs_r01/baseline/cap_columns.json');scene=terrain.load_scene();reference_tests=[];seen=set();documents=[pack,proof,patch,geometry,bundle]
 for item in bundle['contracts']:documents.append(load(ROOT/item['contract']['path']))
 for document in documents:
  for r in refs(document):
   key=(r['path'],r['sha256'])
   if key in seen:continue
   seen.add(key);p=ROOT/r['path'];reference_tests.append(dict(**r,relative_project_path=not Path(r['path']).is_absolute(),exists=p.exists(),hash_matches=p.exists()and sha(p)==r['sha256']))
 regeneration=[];preservation=[];cap_tests=[]
 for a in pack['assets']:
  src=load(ROOT/a['source']['path']);c=coordinate_planes.compile_master(src,{'pitch':a['pitch_m']},max_candidate_cells=5000000,max_output_cells=400000);m=render_data.make_render_data(c);regeneration.append(dict(asset_id=a['id'],valid=c['valid'],cache_exact=core.digest(m)==core.digest(load(ROOT/a['cache']['path'])),candidate_cells=c['candidate_cells'],output_cells=len(c['cells'])));print('fresh',a['property_id'],a['role'],regeneration[-1]['cache_exact'],flush=True)
 for o in pack['owners']:
  eid=o['owner_id'];base=next(p for p in pack['placements']if p['owner_id']==eid and p['role']=='retained_base');fine=next(p for p in pack['placements']if p['owner_id']==eid and p['role']=='fine_access');oldops=load(ROOT/o['actual_R7_source']['path'])['components'][0]['operations'];newops=load(ROOT/base['source']['path'])['components'][0]['operations'];preservation.append(dict(owner_id=eid,non_access_source_operations_equal=[r for r in oldops if not r['id'].startswith('r1_access_skin_')]==newops,source_pose_unchanged=base['position_m']==fine['position_m']and base['yaw_rad']==fine['yaw_rad']==0,old_instance_id=o['replaces_native_instance_id']))
  c=next((r for r in caps['records']if r['property_id']==eid),None)
  if c:
   foot=[r['polygon_xz_m']for r in faces(fine)[1]];hits=[dict(column=j,area_m2=geo.intersection_area(col['polygon_xz_m'],q))for j,col in enumerate(c['candidate_columns'])for q in foot if geo.intersection_area(col['polygon_xz_m'],q)>1e-7];cap_tests.append(dict(owner_id=eid,source_column_count=len(c['candidate_columns']),remaining_fine_native_contacts=hits,pass_=not hits))
 collision=[]
 for c in bundle['contracts']:
  d=load(ROOT/c['contract']['path']);vs=d['add_triangles_world_xyz_m'];p=next(p for p in pack['placements']if p['id']==d['native_placement_id']);audit=next(a for a in geometry['owners']if a['owner_id']==c['owner_id']);collision.append(dict(owner_id=c['owner_id'],native_pose_exact=d['replacement_transform']==dict(position_m=p['position_m'],yaw_rad=p['yaw_rad'],scale=p['scale']),only_own_fine_disabled=d['disable_native_mesh_collider_ids']==[p['id']],no_zero_area_triangles=all(float(np.linalg.norm(np.cross(np.subtract(t[1],t[0]),np.subtract(t[2],t[0]))))>1e-11 for t in vs),finite_triangles=all(math.isfinite(v)for t in vs for q in t for v in q),source_face_area_partition=abs(audit['area_partition_error_m2'])<1e-6,visual_above_collision_bound=d['maximum_visual_above_collision_m']<=.1500001,collision_above_visual_bound=d['maximum_collision_above_visual_m']<=.0750001,walking_triangles_correct_godot_winding=all(terrain.normal_y(t)<-1e-12 for t in vs[d['retained_native_triangle_count']:]),public_source_fixed_exact=audit['maximum_fixed_error_m']<1e-8,full_gradient_bound=d['max_grade']<=.1200001,public_cap_trim_bound=all(r['maximum_above_physical_floor_m']<=.1500001 for r in d['public_walking_end_cap_collision_lips']),world_mesh_exact=load(ROOT/d['replacement_world_mesh']['path'])['triangles']==vs))
 original_index=[]
 for e in patch['surface_edits']:
  v=scene['surfaces'][e['material']][3*e['triangle_index']:3*e['triangle_index']+3];original_index.append(dict(material=e['material'],triangle_index=e['triangle_index'],hash_matches=terrain.canonical_sha(v)==e['source_triangle_sha256']))
 cap_polys=[col['polygon_xz_m']for r in caps['records']for col in r['candidate_columns']]+[o['source_external_profile']['public_lane_endpoint']['same_datum_landing_polygon_xz_m']for o in pack['owners']if o['owner_id']in('E4','E5','E6','E7')];unknown=[];public_unknown=[];native_closed=[];native_proofs=load(OUT/'native_edge_diagnosis.json')
 for e in proof['side_closure']['unknown_exterior_segments']:
  a,c=e['edge_xz_m'];m=[(a[i]+c[i])/2 for i in(0,1)];near=any(geo.point_in_convex_polygon(m,q,1e-6)for q in cap_polys)
  matched=next((r for r in native_proofs if r['owner_id']==e['owner_id']and r['edge_xz_m']==e['edge_xz_m']),None)
  closed=matched and any(r['minimum_y_m']<=matched['native_bottom_y_m']+1e-8 and r['maximum_y_m']>=matched['native_bottom_y_m']+.125-1e-8 for r in matched['actual_retained_native_side_faces'])
  (public_unknown if near else native_closed if closed else unknown).append(e)
 tests=dict(seven_owners_fourteen_assets=len(pack['owners'])==7 and len(pack['assets'])==14,all_local_hash_refs=all(r['relative_project_path']and r['exists']and r['hash_matches']for r in reference_tests),all_fresh_native_caches=all(r['valid']and r['cache_exact']for r in regeneration),all_original_non_access_operations_preserved=all(r['non_access_source_operations_equal']and r['source_pose_unchanged']for r in preservation),all_101_cap_columns_retired=sum(r['source_column_count']for r in cap_tests)==101 and all(r['pass_']for r in cap_tests),all_seven_collision_geometry_contracts=all(all(v for k,v in r.items()if k!='owner_id')for r in collision),all_finite_original_indices_match=all(r['hash_matches']for r in original_index),unique_source_indices=len({(e['material'],e['triangle_index'])for e in patch['surface_edits']})==len(patch['surface_edits']),finite_bearings_supported=not proof['unsupported'],private_native_perimeter_closed=not unknown,actual_retained_internal_routes_accepted=load(ROOT/pack['sources']['actual_internal_route_acceptance']['path'])['passed'])
 report=dict(status='PASS_STATIC_PUBLIC_R18_AND_RUNTIME_PENDING'if all(tests.values())else'HELD_STATIC_FAILURE',tests=tests,reference_tests=reference_tests,independent_regeneration=regeneration,non_access_preservation=preservation,public_cap_column_tests=cap_tests,collision_contract_tests=collision,source_index_tests=original_index,unknown_private_edges=unknown,pending_public_cap_edges=public_unknown,exact_retained_native_side_closures=native_closed,unsupported_bearings=proof['unsupported'],runtime_ready=False,seconds=time.monotonic()-started);(OUT/'source_cache_contract_tests.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],tests,'private unknown',len(unknown),'public pending',len(public_unknown),'unsupported',len(proof['unsupported']),flush=True)
if __name__=='__main__':main()
