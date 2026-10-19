"""Fresh source/cache, public ownership and accepted cemetery-route checks."""
from author_retirement import *
from verify_batch import refs
OUT=Path(__file__).resolve().parent

def main():
 assert not (OUT/'READY_SEAL.json').exists();pack=load(OUT/'resolved_native_candidate.json');patch=load(OUT/'surface_patch_candidate.json');part=load(OUT/'retirement_partition.json');ground=load(OUT/'ground_audit.json');p=pack['placements'][0];source=load(ROOT/p['source']['path']);oldsource=load(ROOT/pack['source_original']['path']);fresh=coordinate_planes.compile_master(source,{'pitch':.5},max_candidate_cells=200000,max_output_cells=50000);mesh=render_data.make_render_data(fresh);oldfresh=coordinate_planes.compile_master(oldsource,{'pitch':.5},max_candidate_cells=200000,max_output_cells=50000);oldmesh=render_data.make_render_data(oldfresh);cached=load(ROOT/p['cache']['path']);originalcached=load(ROOT/pack['cache_original']['path']);newtop=upper(faces(p)[0]);public=load(ROOT/part['public_source']['path']);pi=geo._SpatialIndex(8)
 for i,r in enumerate(public['records']):pi.add(i,r['polygon_xz_m'])
 overlap=[]
 for r in newtop:
  for i in pi.candidates(r['polygon_xz_m']):
   a=fg.area(fg.clip(r['polygon_xz_m'],public['records'][i]['polygon_xz_m']))
   if a>1e-7:overlap.append(dict(native_face_id=r['id'],public_owner_id=public['records'][i]['id'],area_m2=a))
 scene=terrain.load_scene();originalscene=terrain.load_scene();edits={(r['material'],r['triangle_index']):r for r in patch['surface_edits']};sourceindices=[]
 for key,r in edits.items():sourceindices.append(terrain.canonical_sha(scene['surfaces'][key[0]][key[1]*3:key[1]*3+3])==r['source_triangle_sha256'])
 for mat,vs in list(scene['surfaces'].items()):scene['surfaces'][mat]=[v for i in range(len(vs)//3)for t in edits.get((mat,i),dict(replacement_triangles_xyz_m=[vs[3*i:3*i+3]]))['replacement_triangles_xyz_m']for v in t]
 for mat,vs in patch['appended_surfaces'].items():scene['surfaces'].setdefault(mat,[]).extend(vs)
 routepath=OUT.parent/'retained_garden_access_r02/cemetery_entry_route.json';route=load(routepath);polys=route['ribbon_polygons_xz_m'];nv=[v for r in newtop if abs(r['plane_y_xz_m'][2]-14)<1e-8 for t in terrain.fan_upward(lift(r['polygon_xz_m'],r['plane_y_xz_m']))for v in t];nativeidx=terrain.TriangleIndex({'surfaces':{'new_actual_cemetery_floor':nv}},polys);terrainidx=terrain.TriangleIndex(scene,polys)
 class Support:
  def covering(self,p):
   claimed=[]
   for index in(nativeidx,terrainidx):
    for r in index.covering(p):
     for q in fg.subtract([r['intersection_polygon_xz_m']],claimed):
      if fg.area(q)>1e-8:yield dict(r,intersection_polygon_xz_m=q);claimed.append(q)
 checks=[terrain.audit_polygon(Support(),q,14)for q in polys];sides=SideIndex(scene,polys).audit([dict(id=route['id'],polygon_xz_m=q,floor_y_m=14)for q in polys]);body=[b.xform(q,p)for q in slab_rectangles(cached,.01,2.2)];hits=[dict(area_m2=geo.intersection_area(q,r))for q in polys for r in body if geo.intersection_area(q,r)>1e-7]
 # Wall-bearing geometry above the unchanged floor is exactly preserved.
 body_preserved=core.digest(slab_rectangles(cached,.01,2.2))==core.digest(slab_rectangles(originalcached,.01,2.2));prior=[];keys=set(edits)
 for f in [OUT.parent/'retained_garden_access_r02/cemetery_surface_patch.json',OUT.parent/'residual_extensions_r02/combined_all_precinct_surface_patch.json']:
  d=load(f);prior.append(dict(source=ref(f),conflicts=sorted(keys&{(e['material'],e['triangle_index'])for e in d['surface_edits']})))
 tests=dict(fresh_new_native_cache=core.digest(mesh)==core.digest(cached),actual_R7_cache_reproduced=core.digest(oldmesh)==core.digest(originalcached),only_one_obsolete_operation_removed=source['components'][0]['operations']==[o for o in oldsource['components'][0]['operations']if o['id']==o['id']and o['id']!=pack['retired_operation']],all_cemetery_wall_bearing_geometry_preserved=body_preserved,zero_new_native_public_top_overlap=not overlap,zero_restored_soil_public_overlap=not ground['public_overlap'],all_original_indices_match=all(sourceindices),unique_indices=len(keys)==len(patch['surface_edits']),private_perimeter_closed=not ground['side_closure']['unknown_exterior_segments'],retired_floor_area_conserved=abs(part['summary']['removed_floor_area_m2']-part['summary']['public_owned_retirement_area_m2']-part['summary']['off_public_same_datum_restoration_area_m2'])<1e-7,accepted_cemetery_route_supported=all(c['passes_existing_surface']for c in checks),accepted_cemetery_route_bank_clear=not sides['contacts'],accepted_cemetery_route_native_clear=not hits,prior_precinct_patch_indices_disjoint=all(not r['conflicts']for r in prior))
 report=dict(status='PASS_STATIC_JOINT_PUBLIC_AND_RUNTIME_PENDING'if all(tests.values())else'HELD_STATIC_FAILURE',tests=tests,public_native_contacts=overlap,accepted_route=ref(routepath),surface_checks=checks,bank_contacts=sides['contacts'],native_contacts=hits,prior_patch_checks=prior);write('tests.json',report);print(report['status'],tests,flush=True)
 if not all(tests.values()):return
 pack['status']='SOURCE_READY_JOINT_PUBLIC_ACTIVATION_RUNTIME_PENDING';pack['source_candidate']=ref(OUT/'resolved_native_candidate.json');write('resolved_placements.json',pack);patch['status']='SOURCE_READY_JOINT_PUBLIC_ACTIVATION_RUNTIME_PENDING';patch['native_pack']=ref(OUT/'resolved_placements.json');write('surface_patch.json',patch)
 handoff=dict(id='R8_CEMETERY_OBSOLETE_BRANCH_RETIREMENT_R03',native_pack=ref(OUT/'resolved_placements.json'),surface_patch=ref(OUT/'surface_patch.json'),retired_native_footprint_and_public_partition=ref(OUT/'retirement_partition.json'),tests=ref(OUT/'tests.json'),existing_native_placements_removed=pack['replacement_ledger']['existing_native_placements_removed'],off_public_finite_field_owners=ground['restoration_owners'],public_boundary_profile=[r for r in ground['side_closure']['boundary_seams']if r['kind']=='nonwalking_retaining'],public_source=part['public_source'],activation='Native retirement, exact off-public soil and canonical public traffic activation are atomic. No public top is emitted by this pack.',runtime_ready=False);write('integration_handoff.json',handoff)
 files=[p for p in OUT.rglob('*')if p.is_file()and p.suffix in('.py','.json')and '__pycache__'not in str(p)];deps={};bad=[]
 for f in files:
  if f.suffix=='.json':
   for r in refs(load(f)):
    deps[(r['path'],r['sha256'])]=r
    if not(ROOT/r['path']).exists()or sha(ROOT/r['path'])!=r['sha256']:bad.append(r)
 assert not bad,bad;write('dependency_closure.json',dict(status='PASS',references=list(deps.values()),missing_or_changed=bad));files.append(OUT/'dependency_closure.json');write('READY_SEAL.json',dict(status='SOURCE_READY_JOINT_PUBLIC_AND_RUNTIME_PENDING',integration_handoff=ref(OUT/'integration_handoff.json'),files=[ref(p)for p in files],summary=part['summary'],runtime_ready=False));print('SEALED',ref(OUT/'READY_SEAL.json'),'HANDOFF',ref(OUT/'integration_handoff.json'),flush=True)
if __name__=='__main__':main()
