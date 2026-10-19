"""Source-bound generic runtime handoff; does not install or alter any binding."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"expansion_r01"))
from input_contract_r02 import *
import gzip

def render(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def bounds(vs):return {'min':[min(v[i]for v in vs)for i in range(3)],'max':[max(v[i]for v in vs)for i in range(3)]}
def outside(vs,b):return sum(not all(b['min'][i]-1e-7<=v[i]<=b['max'][i]+1e-7 for i in range(3))for v in vs)

def prepare(output, keys, index_path, catalog_path):
 H=Path(output)
 lock=load(H/'input.lock.json')
 if lock.get('schema')!='riverstone.source_roof_authoring_lock.v1'or not set(keys)<=set(lock['asset_keys'])or(H/'complete.json').exists():raise ValueError('manifest output must be an incomplete managed revision')
 idx_path=Path(index_path);idx=load(idx_path)['common_assets'];near=load(catalog_path)['assets'];gv=load(H/'validation/godot_validation.json');entries=[]
 for key in sorted(keys):
  pp=H/key/'candidate.provenance.json'
  p=load(pp);k=p['asset_key'];source=idx[k];inp=load(R/p['input_contract']['path']);m=load(R/source['master_path']);data=render(R/p['render']['path'])
  analytic=inp['source_paint_bounds_audit']['conservative_all_paint_bounds']
  roof_groups=[g for g in data['groups']if g['material']in inp['materials']];retained=[g for g in data['groups']if g['material']not in inp['materials']]
  rv=[v for g in roof_groups for q in g['quads']for v in q];nv=[v for g in retained for q in g['quads']for v in q];retained_bounds=bounds(nv);roof_bounds=p['exact_source_roof_bounds'];allowed={'min':[min(retained_bounds['min'][i],roof_bounds['min'][i])for i in range(3)],'max':[max(retained_bounds['max'][i],roof_bounds['max'][i])for i in range(3)]}
  godot=next(r for r in gv['reports']if r['render_sha256']==p['render']['sha256']);assert godot['all_pass']
  tests={**p['tests'],'godot_read_build_and_winding':True,'new_roof_within_exact_source_roof_aabb':outside(rv,roof_bounds)==0,'all_candidate_vertices_in_proven_union_envelope':outside(rv+nv,allowed)==0}
  entry={'asset_key':k,'all_pass':all(tests.values()),'original_source_master_path':source['master_path'],'original_source_master_sha256':source['master_sha256'],'original_source_render_path':source['render_path'],'original_source_render_sha256':source['render_sha256'],'render_path':p['render']['path'],'render_sha256':p['render']['sha256'],'output_quad_count':data['quad_count'],'pitch':data['pitch'],'grid_origin':data['grid_origin'],'materials_sha256_canonical':core.digest(data['materials']),'candidate_bounds':data['bounds'],'analytic_source_bounds':analytic,'analytic_source_bounds_scope':'Conservative transformed common.core.shape_bounds envelope of original paint operands, before cuts. Outward-rounded bounds authorize no geometry, occupancy or filled volume; only negative separation proofs. Exact roof union algorithm unchanged.','exact_source_roof_bounds':roof_bounds,'original_coarse_bounds':p['original_coarse_bounds'],'retained_nonroof_bounds':retained_bounds,'allowed_visual_union_bounds':allowed,'bounds_policy':'Only the new roof may differ from indexed cache. It must fit the exact original continuous roof domain. Retained nonroof groups are byte-canonical identical, including their existing coarse cell-bound excess. Candidate envelope is their union, tolerance 1e-7 m.','outside_source_analytic_vertices':outside(rv+nv,analytic),'outside_source_analytic_new_roof_vertices':outside(rv,analytic),'outside_allowed_union_vertices':outside(rv+nv,allowed),'retained_nonroof_group_hashes':p['unchanged_nonroof_groups'],'removed_roof_groups':p['removed_roof_groups'],'new_roof_groups_sha256_canonical':core.digest(roof_groups),'source_roof_input_contract':p['input_contract'],'source_roof_operation_bindings_sha256_canonical':core.digest(inp['source_operations']),'source_roof_boundary_audit':p['geometry_audit'],'original_vs_canonical_roof_domain_difference':p['raw_vs_canonical_boundary_difference'],'roof_cut_exclusion_proofs':inp['cut_exclusion_proofs'],'strict_conservative_roof_cut_exclusion_proofs':inp['strict_cut_exclusion_proofs'],'source_paint_bounds_audit':inp['source_paint_bounds_audit'],'conservative_source_bounds_helper':inp['conservative_bounds_helper'],'candidate_provenance':ref(pp),'godot_validation':ref(H/'validation/godot_validation.json'),'near_render_identity_observed':{'path':near[k]['render_path'],'sha256':near[k]['sha256']},'near_shadow_proxy_equivalence_claimed':False,'source_revision_required':False,'collision_reference_changed':False,'source_master_changed':False,'near_render_changed':False,'actual_city_visual_reviewed':False,'tests':tests}
  assert entry['all_pass'];entries.append(entry)
 manifest={'schema':'riverstone.source_roof_far_lod_integration_manifest.v1','source_city_index':ref(idx_path),'all_pass':all(e['all_pass']for e in entries),'entries':entries,'runtime_activation':False,'actual_city_review_required':True,'source_bounds_helper':ref(Path(__file__).resolve().parent/'source_bounds.py'),'author':ref(Path(__file__))}
 write(H/'integration_manifest.json',manifest)
 return manifest
