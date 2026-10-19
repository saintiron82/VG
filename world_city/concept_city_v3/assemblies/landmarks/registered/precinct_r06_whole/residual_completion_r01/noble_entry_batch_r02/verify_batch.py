"""Independent exact native, contract, ownership and predecessor-row checks."""
from build_ground_patch import *
from world_city.concept_city_v3.registered_integration.r8 import compose_finite_patches as compose
from world_city.concept_city_v3.registered_integration.r6 import merge_patches as merger
import collections,copy,argparse
OUT=Path(__file__).resolve().parent;OLD=OUT.with_name('noble_entry_batch_r01')
def refs(obj):
 if isinstance(obj,dict):
  if isinstance(obj.get('path'),str)and isinstance(obj.get('sha256'),str):yield obj
  for v in obj.values():yield from refs(v)
 elif isinstance(obj,list):
  for v in obj:yield from refs(v)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--normalization',required=True);args=ap.parse_args();nd=Path(args.normalization).resolve();pack=load(OUT/'resolved_native_candidate.json');physical=load(OUT/'physical_profile_audit.json');bundle=load(OUT/'collision_contracts.json');ground=load(OUT/'native_ground_candidate_audit.json');norm=load(nd/'normalization_audit.json');binding=load(nd/'binding.json');scene=load(ROOT/binding['base_scene']['path']);patches=[load(ROOT/r['path'])for r in binding['patches']];started=time.monotonic();tests={};reg=[];pres=[];capchecks=[];reference=[];seen=set()
 docs=[pack,physical,bundle,ground,norm]+[load(ROOT/r['contract']['path'])for r in bundle['contracts']]
 for obj in docs:
  for r in refs(obj):
   k=r['path'],r['sha256']
   if k in seen:continue
   seen.add(k);p=ROOT/r['path'];reference.append(dict(**r,passed=not Path(r['path']).is_absolute()and p.is_file()and sha(p)==r['sha256']))
 for a in pack['assets']:
  source=load(ROOT/a['source']['path']);c=coordinate_planes.compile_master(source,{'pitch':a['pitch_m']},max_candidate_cells=6500000,max_output_cells=400000);cache=render_data.make_render_data(c);reg.append(dict(asset_id=a['id'],valid=c['valid'],cache_exact=core.digest(cache)==core.digest(load(ROOT/a['cache']['path']))));print('fresh',a['id'],reg[-1]['cache_exact'],flush=True)
 oldpack=load(OLD/'resolved_native_candidate.json');caps=load(CITY/'assemblies/property/registered/public_lane_repairs_r01/baseline/cap_columns.json')['records']
 for eid in ['E1','E2','E3','E4','E5','E6','E7']:
  base=next(p for p in pack['placements']if p['owner_id']==eid and p['role']=='retained_base');oldbase=next(p for p in oldpack['placements']if p['owner_id']==eid and p['role']=='retained_base');fine=next(p for p in pack['placements']if p['owner_id']==eid and p['role']=='fine_access');pres.append(dict(owner_id=eid,retained_base_exact=base==oldbase,pose_exact=fine['position_m']==base['position_m']and fine['yaw_rad']==base['yaw_rad']==0 and fine['scale']==[1,1,1]));cap=next((r for r in caps if r['property_id']==eid),None)
  if cap:
   foot=faces(fine)[1];contacts=[]
   for i,c in enumerate(cap['candidate_columns']):
    for r in foot:
     q=fg.clip(c['polygon_xz_m'],r['polygon_xz_m'])
     if fg.area(q)>1e-9:contacts.append(dict(column=i,native_face=r['id'],area_m2=fg.area(q)))
   capchecks.append(dict(owner_id=eid,columns=len(cap['candidate_columns']),contacts=contacts))
 collision=[]
 for item in bundle['contracts']:
  d=load(ROOT/item['contract']['path']);p=next(p for p in pack['placements']if p['id']==d['native_placement_id']);ts=d['add_triangles_world_xyz_m'];start=d['retained_native_triangle_count'];end=start+d['walking_triangle_count'];limit=d.get('explicit_private_grade_limit',.12);collision.append(dict(owner_id=item['owner_id'],pose_exact=d['replacement_transform']==dict(position_m=p['position_m'],yaw_rad=p['yaw_rad'],scale=p['scale']),only_own_fine_disabled=d['disable_native_mesh_collider_ids']==[p['id']],native_bound=d['native_source']==p['cache'],no_degenerate_faces=all(area3d(t)>1e-12 for t in ts),walking_winding=all(terrain.normal_y(t)<0 for t in ts[start:end]),finite_values=all(math.isfinite(v)for t in ts for q in t for v in q),visible_above_bound=d['maximum_visual_above_collision_m']<=.1500001,physical_above_bound=d['maximum_collision_above_visual_m']<=.0750001,declared_grade_bound=d['max_grade']<=limit+1e-7,world_mesh_exact=load(ROOT/d['replacement_world_mesh']['path'])['triangles']==ts))
 groups=collections.defaultdict(list)
 for p in patches:
  merger.validate_against_scene(scene,p)
  for r in p['surface_edits']:groups[(r['material'],r['triangle_index'])].append((p['id'],r))
 shared_errors=[];shared=0
 for key,rows in groups.items():
  if len(rows)<2:continue
  try:compose.compound_row(scene,key,rows,binding.get('finite_physical_side_retirement_union',False))
  except Exception as e:shared_errors.append(dict(key=key,error=str(e)))
  shared+=1
 rowproof=[]
 for change in norm['prior_appended_top_clips']+norm.get('prior_appended_side_clips',[]):
  old=load(ROOT/change['source_patch']['path']);new=load(ROOT/change['replacement_patch']['path']);bykey={(r['material'],r['triangle_index']):r for r in change['records']};expected=copy.deepcopy(old['appended_surfaces']);sourceok=True
  for mat,vs in old['appended_surfaces'].items():
   out=[]
   for i in range(len(vs)//3):
    tr=vs[3*i:3*i+3];r=bykey.get((mat,i))
    if r:
     sourceok &= merger.canonical_sha(tr)==r['old_triangle_sha256'];out +=[v for t in r['retained_triangles']for v in t]
    else:out+=tr
   expected[mat]=out
  rowproof.append(dict(patch_id=old['id'],unchanged_original_edits=old['surface_edits']==new['surface_edits'],every_unaffected_append_row_exact=expected==new['appended_surfaces'],all_clipped_old_row_hashes_match=sourceok))
 dependency_errors=[];byid={p['id']:p for p in patches}
 for p in patches:
  for pid in p.get('requires_patch_ids',[]):
   if pid not in byid:dependency_errors.append([p['id'],pid,'missing'])
  for pid,h in p.get('requires_patch_canonical_sha256',{}).items():
   if pid not in byid or merger.canonical_sha(byid[pid])!=h:dependency_errors.append([p['id'],pid,'hash'])
 tests.update(seven_owners_and_fourteen_assets=len(pack['owners'])==7 and len(pack['assets'])==14,seven_bound_collision_contracts=len(bundle['contracts'])==7 and all(all(v for k,v in r.items()if k!='owner_id')for r in collision),all_project_local_refs=all(r['passed']for r in reference),all_fourteen_fresh_caches=all(r['valid']and r['cache_exact']for r in reg),all_seven_retained_bases_exact=all(r['retained_base_exact']and r['pose_exact']for r in pres),all_101_approved_cap_columns_empty=sum(r['columns']for r in capchecks)==101 and not any(r['contacts']for r in capchecks),all_actual_fine_tops_public_disjoint=not any(r['public_projection_contacts']for r in physical['owners']),all_shared_original_rows_disjoint=not shared_errors,all_unaffected_predecessor_appended_rows_exact=all(all(v for k,v in r.items()if k!='patch_id')for r in rowproof),all_native_bearings_have_explicit_subgrade=not ground['unsupported'],baseline_scene_unchanged=sha(terrain.SCENE_PATH)==terrain.SCENE_SHA256,all_53_retained_internal_routes_accepted=load(ROOT/pack['sources']['actual_internal_route_acceptance']['path'])['passed'],all_exact_prerequisites_bound=not dependency_errors)
 report=dict(status='PASS_STATIC_SOURCE_RUNTIME_PENDING'if all(tests.values())else'HELD_STATIC_TEST_FAILURE',tests=tests,independent_regeneration=reg,non_access_preservation=pres,cap_column_tests=capchecks,collision_contract_tests=collision,project_local_references=reference,shared_source_rows_checked=shared,shared_source_errors=shared_errors,predecessor_append_row_tests=rowproof,runtime_ready=False,seconds=time.monotonic()-started);write('source_cache_contract_tests.json',report);print(report['status'],tests,flush=True)
if __name__=='__main__':main()
