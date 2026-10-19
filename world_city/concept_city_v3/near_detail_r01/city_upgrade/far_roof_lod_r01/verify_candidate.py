"""Verify the frozen candidate without relying on mutable runtime catalog entries."""
from pathlib import Path
import gzip,hashlib,json,sys
H=Path(__file__).resolve().parent;R=H.parents[4];sys.path.insert(0,str(R))
from voxel_character.common import core
import source_surface_adapter as adapter

def load(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz' else p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bound_ref(value):
 p=R/value['path'];assert sha(p)==value['sha256'],str(p);return p
p=load(H/'candidate.provenance.json')
for k in ['render','roof_only_render','canonical_source_solids','base_far_render','base_far_contract','source_master','source_revision','revised_master','source_shadow_proxy']:bound_ref(p[k])
for helper in p['existing_helpers']:bound_ref(helper)
render=load(bound_ref(p['render']));base=load(bound_ref(p['base_far_render']));records=load(bound_ref(p['canonical_source_solids']))['solids']
assert render['materials']==base['materials'] and render['pitch']==base['pitch'] and render['grid_origin']==base['grid_origin']
for g in p['unchanged_nonroof_groups']:
 a=next(q for q in render['groups']if q['material']==g['material']);b=next(q for q in base['groups']if q['material']==g['material'])
 assert a==b and core.digest(a)==g['before']['sha256']==g['after']['sha256']
solids=[adapter.solid(r)for r in records];regions,_=adapter.regions(solids);groups,faces=adapter.quads(regions)
assert groups==load(bound_ref(p['roof_only_render']))['groups']
for g in groups:assert g==next(q for q in render['groups']if q['material']==g['material'])
audit=adapter.audit_boundary(faces,solids)
assert audit['interior_surface_area_m2']<1e-6 and audit['coincident_surface_overlap_m2']<1e-6
assert all(audit[k]==0 for k in ['normal_probe_errors','open_or_nonmanifold_edge_segments','edge_winding_errors'])
assert sha(H/'validation/RenderData.gd')==sha(R/'world_city/concept_city_v3/playable_detail_r01/RenderData.gd')
godot=load(H/'validation/godot_validation.json');assert godot['all_pass']and godot['render_sha256']==p['render']['sha256']
print(json.dumps({'all_pass':True,'frozen_input_hashes_verified':True,'exact_nonroof_groups_verified':4,'source_union_roof_groups_replayed':len(groups),'shared_RenderData_copy_identical':True,'shared_Godot_result_bound_to_current_candidate':True,'output_quad_count':render['quad_count'],'render_sha256':p['render']['sha256'],'actual_city_review_pending':True}))
