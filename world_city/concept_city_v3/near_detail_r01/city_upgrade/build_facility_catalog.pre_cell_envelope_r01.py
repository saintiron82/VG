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
  render=R/a['render_path'];assert sha(render)==a['render_sha256'];d=load(render)
  quads=sum(len(g['quads'])for g in d['groups']);assert quads==a['output_quad_count']==d['quad_count']
  coarse_bounds=load(R/source['render_path'])['bounds']
  bounds_contract=a.get('bounds_contract')
  if d['bounds']!=coarse_bounds:
   assert isinstance(bounds_contract,dict),'Different render bounds require an explicit original-source proof'
   assert bounds_contract['source_master_sha256']==source['master_sha256']
   assert bounds_contract['coarse_render_bounds']==coarse_bounds
   assert bounds_contract['composed_render_bounds']==d['bounds']
   assert bounds_contract['outside_analytic_aabb_vertices']==0 and bounds_contract['reason']
   analytic=bounds_contract['analytic_source_bounds']
   assert all(analytic['min'][n]-1e-6<=d['bounds']['min'][n]<=d['bounds']['max'][n]<=analytic['max'][n]+1e-6 for n in range(3))
  tests=a['tests']
  assert tests and (all(tests.values()) if isinstance(tests,dict) else all(t['pass']for t in tests))
  for region in a['window_regions']:
   assert all(region['max'][n]>region['min'][n]for n in range(3))
  n=quads*144
  assert n<=catalog['cache_budget_vertex_normal_bytes'], 'Needs spatial near-LOD partitions before runtime activation'
  entry={'render_path':a['render_path'],'sha256':a['render_sha256'],'source_master_sha256':source['master_sha256'],'geometry_estimated_bytes':n,'composed_manifest_path':str(path.relative_to(R)),'composed_manifest_sha256':sha(path),'window_regions':a['window_regions'],'surface_exclusion_regions':a['surface_exclusion_regions'],'retain_wall_surface_relief':True,'collision_repairs':[],'status':'bounded_composition_structural_pass_pending_actual_city_visual','semantic_variant_selector_path':str(selector_path.relative_to(R)),'semantic_variant_selector_sha256':sha(selector_path),'roof_variant_asset_key':a['roof_variant_asset_key'],'quality_scope':'source-equivalent detailed roof + finite recessed windows; retained coarse structure outside those regions'}
  if d['bounds']!=coarse_bounds:entry.update(visual_bounds=d['bounds'],bounds_contract=bounds_contract)
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
  catalog['assets'][key]=entry;reports.append({'asset':key,'quads':quads,'geometry_estimated_bytes':n,'window_regions':len(a['window_regions'])})
 output.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 (H/'evidence/facility_runtime_r01/catalog_binding_report.json').write_text(json.dumps({'assets':reports,'actual_visual_pass':False,'source_city_index_sha256':sha(index_path)},indent=2)+'\n')
 print(json.dumps(reports))
if __name__=='__main__':main(sys.argv[1:])
