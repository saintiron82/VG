"""Resolve physical roof variants by explicit placement and source semantics, never RGB."""
import collections,json
from pathlib import Path
import author_facility_roofs as a
import finish_roofs as f
import expand_facilities as e
import extend_roof_shapes as x
INDEX=a.ROOT/'world_city/concept_city_v3/playable_r01/generated/tile_r01/index.json'
PROPERTY=a.ROOT/'world_city/concept_city_v3/assemblies/property/registered/r1/resolved_placements.json'
SEMANTIC={'wood_brown':'wood_shingle','b13_wood_brown':'wood_shingle','clay_red':'roof_tile','b13_clay_red':'roof_tile','slate_gray':'roof_tile','weathered_slate_gray':'roof_tile','b13_weathered_slate_gray':'roof_tile'}
SLATE={'slate','slate_dark','slate_light','slate_worn'}

def native_semantics(d,source):
 refs=[{'component':p['component'],'operations':p['source_operations'],'material':p['material']} for p in d['planes']]+[{'component':r['component'],'operations':[r['operation']['id']],'material':r['operation']['material']} for r in d['retained_ridge_boxes']]+[{'component':r['component'],'operations':[r['operation']],'material':r['material']} for r in d['pending']]
 assemblies=source.get('extensions',{}).get('source_assemblies',[]);component_rules=[]
 if assemblies:
  for cid in sorted({r['component'] for r in refs}):
   matches=[(j,q) for j,q in enumerate(assemblies) if cid.startswith(q['key']+'__')];matches.sort(key=lambda v:-len(v[1]['key']))
   if not matches or matches[0][1].get('roof_family') not in SEMANTIC:return None,{'reason':'source_assembly_roof_family_missing','component':cid}
   j,q=matches[0];component_rules.append({'component':cid,'roof_family':q['roof_family'],'covering':SEMANTIC[q['roof_family']],'source_json_pointer':'/extensions/source_assemblies/%d/roof_family'%j})
  coverings={r['covering'] for r in component_rules}
  if len(coverings)!=1:return None,{'reason':'mixed_component_coverings_need_mixed_geometry','component_rules':component_rules}
  return next(iter(coverings)),{'basis':'explicit_source_assembly_roof_families','component_rules':component_rules}
 policy=source.get('metadata',{}).get('palette_policy','')
 if 'external' in policy.lower():return None,{'reason':'generic_slate_slots_require_missing_external_semantics','source_palette_policy':policy}
 if refs and all(r['material'] in SLATE for r in refs):
  return 'roof_tile',{'basis':'native_semantic_slate_ids_and_source_roof_operation_provenance','roof_operations':refs,'source_external_palette_policy':policy or None}
 return None,{'reason':'material_ids_without_unambiguous_covering_provenance','roof_operations':refs}

def main():
 idx=a.read(INDEX);bundle=f.layers.load_master(f.OUT/'shape_support_descriptors.v2.json.gz')['assets'];property_pack=a.read(PROPERTY);property_rows={r['id']:(j,r) for j,r in enumerate(property_pack['placements'])};sources={k:a.read(a.ROOT/d['source_master_path']) for k,d in bundle.items()};native={k:native_semantics(d,sources[k]) for k,d in bundle.items()};available={}
 for cp in (e.OUT/'layered_compile_catalog.json',x.OUT/'layered_compile_catalog.json'):
  if cp.exists():
   for r in a.read(cp)['assets']:available[(r['native_asset_key'],r['covering'])]={'variant_asset_key':r['asset_key'],'catalog':a.rel(cp),'emitted_master_path':r['emitted_master_path'],'emitted_master_sha256':r['emitted_master_sha256'],'source_only_not_runtime_ready':True}
 rows=[];tiles={};assets={};seen=set()
 for tid,t in idx['tiles'].items():
  tp=a.ROOT/t['instances_path'];tile=a.read(tp)
  for j,ins in enumerate(tile['common_instances']):
   key=ins['asset_key']
   if key not in bundle:continue
   identity=(ins['id'],key)
   if identity in seen:raise ValueError('duplicate_native_placement_identity')
   seen.add(identity);d=bundle[key];pal=ins.get('palette_id');family=pal if pal in SEMANTIC else None;covering=SEMANTIC.get(pal);evidence={'basis':'explicit_city_palette_id','source_json_pointer':'/common_instances/%d/palette_id'%j} if covering else None
   if not covering and ins['id'] in property_rows:
    pi,pr=property_rows[ins['id']];manifest=property_pack['asset_manifest'].get(key,{})
    if pr['asset_key']==key and manifest.get('master_file_sha256')==d['source_master_sha256'] and pr.get('roof_material_family') in SEMANTIC:
     family=pr['roof_material_family'];covering=SEMANTIC[family];evidence={'basis':'exact_placement_id_asset_and_source_master_hash_match','roof_material_family':family,'source':a.ref(PROPERTY),'source_json_pointer':'/placements/%d/roof_material_family'%pi,'source_master_hash_match':True,'current_native_palette_kept_unchanged':True}
   if not covering:covering,evidence=native[key]
   variant=available.get((key,covering));status='RESOLVED_SOURCE_VARIANT' if variant else 'PENDING_VARIANT_SOURCE' if covering else 'UNKNOWN_COVERING_NO_FALLBACK';tiles[tid]={'path':t['instances_path'],'sha256':t['instances_sha256']}
   row={'placement_id':ins['id'],'native_asset_key':key,'tile_id':tid,'tile_instance_index':j,'city_palette_id':pal,'source_pack':ins.get('source_pack'),'palette_override_preserved':ins.get('palette_override',{}),'source_master_sha256':d['source_master_sha256'],'roof_covering':covering,'semantic_family':family,'status':status,'selected_variant_asset_key':variant['variant_asset_key'] if variant else None,'evidence':evidence,'fallback_allowed':False,'replacement_allowed':False};rows.append(row)
   assets.setdefault(key,{'source_master':{'path':d['source_master_path'],'sha256':d['source_master_sha256']},'placements':[],'available_variants':{c:v for (k,c),v in available.items() if k==key}})['placements'].append(ins['id'])
 counts=collections.Counter(r['status'] for r in rows);coverings=collections.Counter(r['roof_covering'] or 'unknown' for r in rows);pending=[{'placement_id':r['placement_id'],'native_asset_key':r['native_asset_key'],'status':r['status'],'roof_covering':r['roof_covering'],'reason':r['evidence']} for r in rows if r['status']!='RESOLVED_SOURCE_VARIANT'];out={'schema':'riverstone.facility_roof.placement_variant_selection.v1','index':a.ref(INDEX),'author':a.ref(Path(__file__)),'selection_contract':{'lookup_key':['placement_id','native_asset_key','city_palette_id'],'native_source_sha256_must_match':True,'explicit_placement_rows_take_precedence':True,'do_not_infer_from_rgb':True,'missing_or_unknown':'retain original coarse roof; do not activate another variant or count completed','selected_variant_key_is_not_native_asset_key':True,'full_compilation_required_before_runtime':True,'source_palette_and_override_kept_unchanged':True},'semantic_palette_rules':SEMANTIC,'tiles':tiles,'assets':assets,'placements':rows,'pending':pending,'counts':{'native_assets':len(assets),'placements':len(rows),'by_status':dict(counts),'by_covering':dict(coverings),'rgb_classification_calls':0},'runtime_activation':False,'replacement_allowed':False};a.write(a.HERE/'variant_selection.json',out);print(json.dumps(out['counts']));print(json.dumps(pending,indent=2)[:6000])

if __name__=='__main__':main()
