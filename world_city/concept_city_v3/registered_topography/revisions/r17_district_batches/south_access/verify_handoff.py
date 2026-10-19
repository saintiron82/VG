"""Verify sealed local proposal without exporting or modifying a scene."""
import json,pathlib,math
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.side_clearance import SideIndex
H=pathlib.Path(__file__).resolve().parent;ROOT=H.parents[5]
h=json.loads((H/'source_handoff_r02.json').read_text());p=json.loads((H/'source_proof_r02.json').read_text());s=a.load_scene()
assert h['base_scene']['sha256']==a.SCENE_SHA256
assert h['proof']['sha256']==a.sha(H/'source_proof_r02.json')
for r in h['input_refs']:assert a.sha(ROOT/r['path'])==r['sha256']
for r in h['source_triangle_bindings']:
 t=s['surfaces'][r['material']][3*r['triangle_index']:3*r['triangle_index']+3];assert a.canonical_sha(t)==r['source_triangle_sha256']
r=h['route'];assert r['width_m']==3.5 and r['gate_anchor_xyz_m']==[195.5,1.,344.]
assert all(abs(a.common.plane(t)[0])+abs(a.common.plane(t)[1])<1e-10 and a.normal_y(t)>0 for t in h['body_restoration']['source_boundary_knot_preserving_top_triangles_xyz_m'])
assert p['unexplained_missing_area_after_explicit_body_restoration_m2']==0 and not p['protected_conflicts']
assert p['retired_body_boundary']['max_existing_seam_delta_m']==0
owners=[dict(id='route',polygon_xz_m=q,floor_y_m=1)for q in r['ribbon_polygons_xz_m']]+[dict(id='roadjoin',polygon_xz_m=r['unchanged_public_overlap_polygon_xz_m'],floor_y_m=1),dict(id='restoration',polygon_xz_m=h['body_restoration']['polygon_xz_m'],floor_y_m=1)]
latest=SideIndex(s,[o['polygon_xz_m']for o in owners]).audit(owners);assert latest['status']=='PASS'
manifest=dict(schema='riverstone.r17.south_access_seal.v1',authoritative_handoff='source_handoff_r02.json',supersedes_exploratory_handoff='source_handoff.json',files=[dict(path=str((H/n).relative_to(ROOT)),sha256=a.sha(H/n))for n in ['source_handoff_r02.json','source_proof_r02.json','package_handoff_r02.py','verify_handoff.py']],checked_implementation=[dict(path=str((H.parent/n).relative_to(ROOT)),sha256=a.sha(H.parent/n))for n in ['author.py','side_clearance.py','audit_retired_boundaries.py']],base_scene_sha256=a.sha(a.SCENE_PATH),source_triangle_bindings_verified=len(h['source_triangle_bindings']),current_side_checker_result=latest,tests=dict(source_hashes=True,positive_upward_actual_restoration_triangles=True,actual_restoration_triangle_grade_zero=True,complete_fixed_source_seams=True,no_unexplained_missing_top=True,protected_conflict_count=0),activation=False)
f=H/'manifest.json'
if f.exists():raise RuntimeError('Refuse overwrite manifest')
f.write_text(json.dumps(manifest,separators=(',',':'))+'\n');print(json.dumps(dict(manifest_sha256=a.sha(f),checked_implementation=manifest['checked_implementation'],side_faces=len(latest['contacts']),source_triangle_bindings=len(h['source_triangle_bindings']),minimum_water_distance_m=p['minimum_actual_water_distance_m'],minimum_canal_reservation_distance_m=p['minimum_canal_reservation_distance_m']),indent=2))
