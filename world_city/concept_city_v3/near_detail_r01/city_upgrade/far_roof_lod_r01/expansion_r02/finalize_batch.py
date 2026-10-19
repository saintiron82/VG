"""Seal a bounded candidate-only handoff after replay, Godot and shared-gate checks."""
from pathlib import Path
import hashlib,json,difflib
E=Path(__file__).resolve().parent;R=next(p for p in E.parents if(p/'voxel_character/common/core.py').is_file());E1=E.parent/'expansion_r01'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(R)),'sha256':sha(p)}
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
scope=load(E/'batch_scope.json');index=load(E/'candidate_index.json');manifest=load(E/'integration_manifest.json');replay=load(E/'expansion_validation.json');godot=load(E/'validation/godot_validation.json');gate=load(E/'validation/gate_validation.json')
assert index['complete'] and manifest['all_pass'] and replay['all_pass'] and godot['all_pass'] and gate['all_pass']
selected={r['asset_key']for r in scope['selected']};built={e['asset_key']for e in manifest['entries']};assert selected==built and len(selected)==29
for p,h in scope['frozen_method'].items():assert sha(R/p)==h
for x in ['catalog_at_selection','city_index_at_selection']:assert sha(R/scope[x]['path'])==scope[x]['sha256']
for row in index['rows']:
 assert row['status']=='CANDIDATE_GEOMETRY_PASS_PENDING_GODOT'
 row['status']='CANDIDATE_VERIFIED_PENDING_ACTUAL_CITY_REVIEW'
 row['godot_pass']=next(x['all_pass']for x in godot['reports']if x['render_sha256']==row['render']['sha256'])
 row['shared_runtime_gate_positive_pass']=next(x['all_pass']for x in gate['cases']if x['asset_key']==row['asset_key'])
index.update(all_pass=True,integration_manifest=ref(E/'integration_manifest.json'),independent_replay=ref(E/'expansion_validation.json'),godot_validation=ref(E/'validation/godot_validation.json'),shared_runtime_gate_positive_validation=ref(E/'validation/gate_validation.json'),actual_city_visual_reviewed=False,runtime_activation=False,unsupported_count=0)
write(E/'candidate_index.json',index)
write(E/'unsupported.json',{'scope':ref(E/'batch_scope.json'),'selected_count':29,'unsupported_count':0,'unsupported':[],'not_selected':scope['excluded'],'policy':'Only source-proven supported input solids were built. No guessed shapes, implicit cut filling or runtime activation.','explicit_rejection_boundaries':['ROOF_INTERSECTING_OR_SELECTOR_RELEVANT_CUT','UNSUPPORTED_ROOF_SHAPE_OR_THICKNESS','WHOLE_MATERIAL_GROUP_OWNERSHIP_UNPROVEN','UNSUPPORTED_TRANSFORM_OR_INVALID_SOURCE','PITCH_DEPENDENT_MINIMUM_SHAPE_UNSUPPORTED','DYNAMIC_ROOF_PART_UNSUPPORTED','BOUNDED_SOLID_BUDGET_EXCEEDED','UNSUPPORTED_GEOMETRY including open or nonmanifold union boundary','SOURCE_REVISED_NEAR_REQUIRES_SEPARATE_CONTRACT']})
(E/'recipe.diff').write_text(''.join(difflib.unified_diff((E1/'build_generic_candidate.py').read_text().splitlines(True),(E/'build_candidate.py').read_text().splitlines(True),fromfile='frozen expansion_r01/build_generic_candidate.py',tofile='expansion_r02/build_candidate.py')))
proofs=[load(E/k/'candidate.provenance.json')for k in sorted(selected)]
summary={'schema':'riverstone.source_roof_far_lod_batch_validation.v1','all_pass':True,'scope':ref(E/'batch_scope.json'),'candidate_index':ref(E/'candidate_index.json'),'integration_manifest':ref(E/'integration_manifest.json'),'unsupported':ref(E/'unsupported.json'),'registered_count_at_selection':32,'selected_count':29,'existing_far_excluded_count':3,'geometry_pass_count':29,'independent_replay_pass_count':replay['candidate_count'],'godot_pass_count':len(godot['reports']),'shared_runtime_gate_positive_pass_count':len(gate['cases']),'roof_quads':sum(p['roof_quad_count']for p in proofs),'retained_nonroof_quads':sum(sum(g['quad_count']for g in p['unchanged_nonroof_groups'])for p in proofs),'total_quads':sum(p['output_quad_count']for p in proofs),'godot_float32_triangles':sum(x['triangles']for x in godot['reports']),'open_or_nonmanifold_roof_edge_segments':sum(p['geometry_audit']['open_or_nonmanifold_edge_segments']for p in proofs),'normal_probe_errors':sum(p['geometry_audit']['normal_probe_errors']for p in proofs),'edge_winding_errors':sum(p['geometry_audit']['edge_winding_errors']for p in proofs),'raw_vs_canonical_boundary_difference_m2_max':max(max(p['raw_vs_canonical_boundary_difference'].values())for p in proofs),'max_asset_build_seconds':max(p['seconds']for p in proofs),'max_asset_build_rss_kib':max(p['max_rss_kib']for p in proofs),'generated_output_limit_bytes':scope['output_cap_bytes'],'catalog_and_city_index_unchanged_from_selection':True,'frozen_source_geometry_method_unchanged':True,'runtime_activation':False,'actual_city_visual_reviewed':False,'source_master_changed':False,'near_render_changed':False,'collision_reference_changed':False,'original_assets_duplicated':False,'supported_scope':'Only the frozen selected current-near set; no inference that every city asset is eligible.','source_bounds_scope':'Original pre-cut paint-operand envelope, not occupancy. Candidate envelope is retained original nonroof plus source roof union.','gate_source_snapshots':[{**ref(E/'validation/validation'/n),'production_path':str((R/'world_city/concept_city_v3/playable_detail_r01/validation'/n).relative_to(R))}for n in ['SourceRoofFarVisualContract.gd','SourceBoundsContract.gd']]}
for x in summary['gate_source_snapshots']:assert sha(R/x['production_path'])==x['sha256']
write(E/'batch_validation.json',summary)
(E/'README.md').write_text('''# Pending-near source roof LOD batch r02

29 of 29 selected candidates pass. The scope is the frozen 32-entry near catalog minus the three already integrated cathedral, cloister and attached-row candidates. No other city assets were added to the batch.

## Handoff

- `integration_manifest.json`: 29 source/proof/geometry-bound entries using the already reviewed source-roof far manifest schema. This is the binder input; no runtime contracts or catalog bindings were written.
- `candidate_index.json`: per-asset candidate/provenance references and verification status.
- `batch_validation.json`: aggregate checks and exact handoff hashes.
- Each asset directory contains only its source-input contract, candidate render, provenance and bounded build log. Original source masters and original coarse/fine assets were not duplicated.
- `unsupported.json`: explicit unsupported result (zero in this batch), excluded existing contracts, and fail-closed boundaries.

## Verified

Original nonroof indexed groups and palette are exact; only source-owned roof materials were replaced. Raw and canonical source roof union boundaries agree. All roof boundaries are closed and manifold, with no interior/duplicate faces or winding errors. Shared RenderData read/build and float32 triangle winding passed for all 29. Independent replay rehashed all source/render/adapter references and recomputed the unions. The current shared runtime geometry gate accepts all 29 under in-memory candidate bindings.

The method reuses the frozen generic source-surface adapter. `recipe.diff` shows output-directory/import changes plus schema/key/source assertions only. No geometry algorithm changes were made. Outputs remain analytical source-equivalent distant visuals, not new fine voxel occupancy.

## Bounds and cuts

Analytical whole-source bounds are the envelope of original paint operands before cuts, not occupied-volume bounds. Retained nonroof voxel excess is preserved; only new roof vertices must fit the exact source roof AABB. Every complete candidate must fit their proven union envelope.

Read-only source audit found 5,568 box and 282 extrusion paint instances, valid axis-aligned rigid transforms, no pending source revisions, and 143 raw / 137 canonical roof solids. Component cuts occur outside roof-owning components. The loading shed's four assembly cuts have 28 strict roof/cut AABB exclusion proofs. Minimum-size nonroof eave rails in 28 assets do not change their overall analytical AABB.

Relevant roof cuts, unsupported curved/triangular/nonconvex shapes, dynamic roof parts, unsupported transforms, ambiguous material ownership, solid-budget excess and nonmanifold unions remain explicit failures. No guessed substitute shapes were generated.

## Remaining review

Actual-pose LOD and visual acceptance remain with the parent integration workflow. This directory does not alter runtime, catalog, placements, source geometry, near geometry, collision data or palette. The shared runtime gate check is a positive compatibility check; the earlier expansion_r01 revision_r03 evidence contains the adversarial gate/binder suite.
''')
size=sum(p.stat().st_size for p in E.rglob('*')if p.is_file());assert size<scope['output_cap_bytes'];print(json.dumps({'all_pass':True,'candidates':29,'integration_manifest':ref(E/'integration_manifest.json'),'batch_validation':ref(E/'batch_validation.json'),'generated_bytes':size,'roof_quads':summary['roof_quads'],'nonroof_quads':summary['retained_nonroof_quads'],'total_quads':summary['total_quads'],'max_asset_build_seconds':summary['max_asset_build_seconds'],'max_asset_build_rss_kib':summary['max_asset_build_rss_kib']},indent=2))
