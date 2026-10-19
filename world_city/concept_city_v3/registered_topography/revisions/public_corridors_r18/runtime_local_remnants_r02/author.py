import json,copy,collections,math
from pathlib import Path
from ..north_junction_transition_r01.author import ROOT,CITY,HERE as NORTH,a,g,ref,dump
from world_city.concept_city_v3.registered_integration.r6 import merge_patches as merger
HERE=Path(__file__).resolve().parent;DIAG=HERE.parent/'runtime_local_remainder_review_r01'

def main():
 bp=NORTH/'activation_binding.json';binding=json.loads(bp.read_bytes());patches=[json.loads((ROOT/r['path']).read_bytes())for r in binding['patches']];upper=json.loads((DIAG/'upper_contour_source_matches.json').read_bytes());removals=[]
 for r in upper['matches']:removals.append(dict(route='UPPER_CONTOUR',patch_index=r['patch_index'],source_edit_index=r['source_edit_index'],replacement_index=r['replacement_index'],triangle_xyz_m=r['triangle_xyz_m'],source_face_key=r['collision_source']['source_face_key'],collision_triangle_xyz_m=r['collision_source']['triangle_xyz_m']))
 for name in ['market_north','central_west_radial']:
  d=json.loads((DIAG/(name+'_local_faces.json')).read_bytes());assert len(d['source_matches'])==1;r=d['source_matches'][0];removals.append(dict(route=name.upper(),patch_index=r['patch_index'],source_edit_index=r['source_edit_index'],replacement_index=r['replacement_index'],triangle_xyz_m=r['triangle_xyz_m'],source_face_key=r['collision_source']['source_face_key'],collision_triangle_xyz_m=r['collision_source']['triangle_xyz_m']))
 lp=CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/lower_contour_diagnosis_r01/row_retirement_request.json';lower=json.loads(lp.read_bytes());r=patches[16]['surface_edits'][lower['source_edit_array_index']];assert r==lower['source_edit_before'];t=r['replacement_triangles_xyz_m'][0];removals.append(dict(route='LOWER_CONTOUR',patch_index=16,source_edit_index=lower['source_edit_array_index'],replacement_index=0,triangle_xyz_m=t,source_face_key=lower['current_runtime_source_face'],collision_triangle_xyz_m=[t[0],t[2],t[1]]))
 assert len(removals)==45
 final=copy.deepcopy(patches);groups=collections.defaultdict(list)
 for r in removals:groups[r['patch_index'],r['source_edit_index']].append(r)
 edits=[]
 for(pi,ei),rs in sorted(groups.items()):
  old=patches[pi]['surface_edits'][ei];new=copy.deepcopy(old);ids={r['replacement_index']for r in rs}
  for r in rs:assert old['replacement_triangles_xyz_m'][r['replacement_index']]==r['triangle_xyz_m']
  new['replacement_triangles_xyz_m']=[t for i,t in enumerate(old['replacement_triangles_xyz_m'])if i not in ids];final[pi]['surface_edits'][ei]=new;edits.append(dict(patch_index=pi,producer_id=patches[pi]['id'],source_edit_index=ei,before=old,after=new,retired_replacement_indices=sorted(ids)))
 for pi in[15,16]:final[pi]['diagnosed_obsolete_public_remnant_retirement']=dict(source=binding['patches'][pi],scope='Exact diagnosed source rows only. No area threshold filter.',source_edit_rows=[r['source_edit_index']for r in edits if r['patch_index']==pi],preserved_appended_surfaces=True)
 ids={r['id']:i for i,r in enumerate(final)};done=set();active=set()
 def rebind(i):
  if i in done:return
  assert i not in active;active.add(i)
  for pid in final[i].get('requires_patch_canonical_sha256',{}):rebind(ids[pid]);final[i]['requires_patch_canonical_sha256'][pid]=merger.canonical_sha(final[ids[pid]])
  active.remove(i);done.add(i)
 for i in range(len(final)):rebind(i)
 out=copy.deepcopy(binding);changed=[]
 for i,(old,new)in enumerate(zip(patches,final)):
  assert old['appended_surfaces']==new['appended_surfaces']
  if old!=new:
   out['patches'][i]=dump(HERE/f'producer_{i:02d}.json',new);changed.append(dict(patch_index=i,source=binding['patches'][i],replacement=out['patches'][i],geometry_changed=i in[15,16]))
 out['local_public_remnant_retirement']=dict(scope='45 exact diagnosed runtime triangles from38 producer source rows',runtime_pending=True);dump(HERE/'activation_binding.json',out)
 for r in removals:r['scene_triangle_sha256']=a.canonical_sha(r['triangle_xyz_m']);r['collision_triangle_sha256']=a.canonical_sha(r['collision_triangle_xyz_m'])
 runtime=dict(schema='riverstone.exact_runtime_face_retirement.v1',status='BOUNDED_DIAGNOSTIC_REPLAY_INPUT',runtime_scene=dict(path='world_city/concept_city_v3/evidence/r8_district_61_noble_r02_contracts_runtime/scene.json',sha256='014313db2409973ce3d3bc7a061fcbc43a21427eb6e84cb557e3295751027f34'),rows=removals,controller_or_route_changes=False,scope='Exact source-key plus triangle-byte matching only; retain every other collider face and native pose. North junction top transition is separate and not applied by this diagnostic filter.');dump(HERE/'runtime_retirement_map.json',runtime)
 coverage=json.loads((DIAG/'upper_contour_owner_coverage.json').read_bytes());other=json.loads((DIAG/'other_owner_coverage.json').read_bytes());tests=dict(status='PASS_BOUND_SOURCE_CORRECTION_RUNTIME_PENDING',source_edit_rows=len(edits),retired_actual_runtime_triangles=len(removals),all_appended_arrays_unchanged=True,all_unchanged_source_rows_verbatim=all(old['surface_edits'][j]==new['surface_edits'][j]for i,(old,new)in enumerate(zip(patches,final))for j in range(len(old['surface_edits']))if(i,j)not in groups),all_dependencies_exact=all(merger.canonical_sha(final[ids[pid]])==h for r in final for pid,h in r.get('requires_patch_canonical_sha256',{}).items()),upper_source_area_m2=coverage['total_source_projected_area_m2'],upper_rational_uncovered_area_m2=coverage['total_uncovered_area_m2'],upper_max_uncovered_fragment_width_bound_m=1.61e-11,other_owner_proof=ref(DIAG/'other_owner_coverage.json'),lower_owner_proof=ref(lp),public_plane_changes=0,new_floors_added=0);assert tests['all_dependencies_exact']and tests['all_unchanged_source_rows_verbatim'];dump(HERE/'source_tests.json',tests);dump(HERE/'source_retirement_ledger.json',dict(source=ref(bp),rows=edits))
 sources=[ref(bp),ref(lp),ref(DIAG/'upper_contour_source_matches.json'),ref(DIAG/'upper_contour_owner_coverage.json'),ref(DIAG/'other_owner_coverage.json'),ref(CITY/'traversal_r5/revisions/r06_r8_precinct/ordinary61_observer_r01/evidence/public_r18_six_contacts_r01/observer_handoff.json')];handoff=dict(schema='riverstone.combined_local_public_correction.v1',status=tests['status'],sources=sources,activation_binding=ref(HERE/'activation_binding.json'),producer_replacements=changed,source_retirement_ledger=ref(HERE/'source_retirement_ledger.json'),runtime_retirement_map=ref(HERE/'runtime_retirement_map.json'),source_tests=ref(HERE/'source_tests.json'),inherited_north_transition=ref(NORTH/'freeze_manifest.json'),required_replay=['UPPER_CONTOUR both directions','LOWER_CONTOUR both directions','MARKET_NORTH both directions','CENTRAL_WEST_RADIAL both directions','the separately bound north junction controls'],limits=['The exact rational residuals are disclosed as numerical edge-width remnants. No arbitrary positive-area threshold is used for runtime filtering.','Removing obsolete source fragments is a source ownership correction; floor-like slide contacts do not by themselves prove their causal role. Same-controller regression is required.','Nearby R18 thin fans remain unchanged. If a block persists, a separate plane-preserving local retriangulation is required.']);dump(HERE/'integration_handoff.json',handoff);dump(HERE/'freeze_manifest.json',dict(status=tests['status'],files=[ref(HERE/x)for x in['author.py','activation_binding.json','source_retirement_ledger.json','runtime_retirement_map.json','source_tests.json','integration_handoff.json']]+out['patches'],sources=sources));print(ref(HERE/'runtime_retirement_map.json'));print(ref(HERE/'integration_handoff.json'));print(ref(HERE/'freeze_manifest.json'));print(tests)
if __name__=='__main__':main()
