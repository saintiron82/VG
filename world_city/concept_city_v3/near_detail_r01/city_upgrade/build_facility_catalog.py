"""Bind completed finite-region composition to the existing near LOD cache.
Source building poses, city index and collisions remain byte-preserved inputs.
This is a mesh composition/transport registration, not another voxel compiler.
"""
from pathlib import Path
import hashlib,json,gzip,sys
from build_near_catalog import source_parts
H=Path(__file__).resolve().parent; R=H.parents[3]; C=H.parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def preserve_generated_bindings(previous,entry):
 # Derived native/shadow/far transports remain valid only for the same immutable
 # source and complete finite-composition manifest, not just the same mesh count.
 if all(previous.get(k)==entry.get(k) and entry.get(k) for k in ('sha256','source_master_sha256','composed_manifest_sha256')):
  for k,v in previous.items():
   if k not in entry and k.startswith(('native_scene_','shadow_proxy_','surface_feature_mask_','far_visual_','far_union_')):entry[k]=v
 return entry
def main(paths):
 index_path=C/'playable_r01/generated/tile_r01/index.json';index=load(index_path)
 output=C/'playable_detail_r01/near_catalog.json';catalog=load(output)
 assert catalog['source_city_index_sha256']==sha(index_path)
 reports=[]
 selector_path=H/'facility_roofs/variant_selection.v3.json';selector=load(selector_path)
 assert selector['index']['sha256']==sha(index_path)
 for raw in paths:
  path=Path(raw).resolve();a=load(path);key=a['asset_key'];source=index['common_assets'][key]
  assert a['schema']=='riverstone.facility.composed_render.v1' and a['all_pass'] is True
  assert a['collision_reference_changed'] is False
  selected={x['selected_variant_asset_key']for x in selector['placements']if x['native_asset_key']==key}
  assert len(selected)==1 and a['roof_variant_asset_key'] in selected, 'Per-instance variant routing required; do not substitute roof type' 
  assert a['source_master_sha256']==source['master_sha256'] and a['source_render_sha256']==source['render_sha256']
  assert sha(R/source['master_path'])==source['master_sha256'] and sha(R/source['render_path'])==source['render_sha256']
  for item in a['source_inputs']:assert sha(R/item['path'])==item['sha256'],item
  if a.get('source_revision'):
   from window_revision_contract import validate as validate_revision
   revision=a['source_revision']
   assert revision['original_master_sha256']==source['master_sha256'] and revision['original_master_path']==source['master_path']
   assert sha(R/a['source_revision_path'])==a['source_revision_sha256']
   assert load(R/a['source_revision_path'])['source_revision']==revision
   assert sha(R/revision['revised_master_path'])==revision['revised_master_sha256']
   validate_revision(revision,load(R/source['master_path']),load(R/revision['revised_master_path']))
  render=R/a['render_path'];assert sha(render)==a['render_sha256'];d=load(render)
  quads=sum(len(g['quads'])for g in d['groups']);assert quads==a['output_quad_count']==d['quad_count']
  coarse_bounds=load(R/source['render_path'])['bounds']
  bounds_contract=a.get('bounds_contract')
  if d['bounds']!=coarse_bounds:
   assert isinstance(bounds_contract,dict),'Different render bounds require an explicit original-source proof'
   assert bounds_contract['source_master_sha256']==source['master_sha256']
   assert bounds_contract['coarse_render_bounds']==coarse_bounds
   assert bounds_contract['composed_render_bounds']==d['bounds']
   from bounds_contract import validate
   proof=None
   if bounds_contract.get('voxel_cell_envelope'):
    proof_path=R/bounds_contract['cell_envelope_proof_path']
    assert sha(proof_path)==bounds_contract['cell_envelope_proof_sha256']
    proof=load(proof_path)
    assert proof['asset_key']==key and proof['render_sha256']==a['render_sha256'] and proof['render_path']==a['render_path']
    assert sha(R/proof['canonical_master_path'])==proof['canonical_master_sha256']
   validate(bounds_contract,d['bounds'],coarse_bounds,source['master_sha256'],proof)
  tests=a['tests']
  assert tests and (all(tests.values()) if isinstance(tests,dict) else all(t['pass']for t in tests))
  for region in a['window_regions']:
   assert all(region['max'][n]>region['min'][n]for n in range(3))
  n=quads*144
  assert n<=catalog['cache_budget_vertex_normal_bytes'], 'Needs spatial near-LOD partitions before runtime activation'
  entry={'render_path':a['render_path'],'sha256':a['render_sha256'],'source_master_sha256':source['master_sha256'],'geometry_estimated_bytes':n,'composed_manifest_path':str(path.relative_to(R)),'composed_manifest_sha256':sha(path),'window_regions':a['window_regions'],'surface_exclusion_regions':a['surface_exclusion_regions'],'retain_wall_surface_relief':True,'collision_repairs':[],'status':'bounded_composition_structural_pass_pending_actual_city_visual','semantic_variant_selector_path':str(selector_path.relative_to(R)),'semantic_variant_selector_sha256':sha(selector_path),'roof_variant_asset_key':a['roof_variant_asset_key'],'quality_scope':'source-equivalent detailed roof + finite recessed windows; retained coarse structure outside those regions'}
  if a.get('material_revision'):
   for field in ['material_revision','material_revision_path','material_revision_sha256','palette_source_revision','palette_source_revision_path','palette_source_revision_sha256','material_role_aliases','material_alias_color_space']:entry[field]=a[field]
   assert sha(R/a['material_revision_path'])==a['material_revision_sha256'] and sha(R/a['palette_source_revision_path'])==a['palette_source_revision_sha256']
   assert a['material_alias_color_space']=='linear_rgb_from_srgb_base_after_placement_override'
  if d['bounds']!=coarse_bounds:entry.update(visual_bounds=d['bounds'],bounds_contract=bounds_contract)
  if a.get('source_revision'):entry.update(source_revision=a['source_revision'],source_revision_path=a['source_revision_path'],source_revision_sha256=a['source_revision_sha256'])
  if a.get('surface_source_render_path'):
   assert a.get('source_revision'), 'Revised wall support requires explicit source revision'
   assert sha(R/a['surface_source_render_path'])==a['surface_source_render_sha256']
   support=load(R/a['surface_source_render_path'])
   assert support['schema']==a['surface_source_render_schema']=='riverstone.facility.revision_overlay_support.v1'
   assert support['asset_key']==key and support['source_render_sha256']==source['render_sha256']
   assert support['source_render_path']==source['render_path'] and support['collision_reference_changed'] is False
   assert support['revised_master_sha256']==a['source_revision']['revised_master_sha256']
   entry.update({k:a[k]for k in ('surface_source_render_path','surface_source_render_sha256','surface_source_render_schema')})
  # A shadow-only source underlay is allowed only for this declared, cut-free
  # complete port roof. Other forms keep their actual fine geometry as caster.
  if key=='registered_port_long_loading_shed':
   master=load(R/source['master_path']);planes=[]
   for instance,op,tr in source_parts(master):
    shape=op.get('shape',{})
    if instance.get('component')=='roof' and op['action']=='paint' and shape.get('kind')=='extrusion' and len(shape['polygon'])==4:
     planes.append({'polygon':shape['polygon'],'z_min':shape['z_min'],'z_max':shape['z_max'],'transform':{'basis':tr['basis'],'translation':tr['translation']}})
   assert len(planes)==6
   proxy=H/'shadow_proxies'/f'{key}.json'
   payload={'schema':'riverstone.source_roof_shadow_proxy.v1','asset':key,'source_master_sha256':source['master_sha256'],'extrusions':planes,'visible_geometry':False,'scope':'Six original continuous source roof slope strips, shadows only. Actual roof cuts/entry disjointness verified by roof handoff.'}
   proxy.write_text(json.dumps(payload,indent=2)+'\n');entry.update(shadow_proxy_path=str(proxy.relative_to(R)),shadow_proxy_sha256=sha(proxy))
  catalog['assets'][key]=preserve_generated_bindings(catalog['assets'].get(key,{}),entry);reports.append({'asset':key,'quads':quads,'geometry_estimated_bytes':n,'window_regions':len(a['window_regions'])})
 output.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 (H/'evidence/facility_runtime_r01/catalog_binding_report.json').write_text(json.dumps({'assets':reports,'actual_visual_pass':False,'source_city_index_sha256':sha(index_path)},indent=2)+'\n')
 print(json.dumps(reports))
if __name__=='__main__':main(sys.argv[1:])
