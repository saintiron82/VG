"""Read actual canonical sources to classify remaining upgrade work; never grant art pass."""
from pathlib import Path
import json,hashlib,collections,datetime
H=Path(__file__).resolve().parents[2];R=H.parents[3];O=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def requirement(category):
 if category in ('trees_understory',):return ('organic_volume','Existing trunk/branch/crown solids are real 3D. Near crowns need multiview curvature/branch structure review; pitch 0.5–1m foliage remains a coarse proxy, not approved near quality.','After building roofs/windows: bounded shared tree/crown family; do not instantiate all1563 near models.')
 if category=='garden_crop_beds':return ('planted_bed','Two-box bed source does not encode crops/herbs. Owned garden soil/crop rows and distinct planting volumes are missing near forms.','Reusable bed/plant clump modules restricted to original owned bed; retain paths.')
 if category=='precinct_garden_ground':return ('ground_ownership','Authored polygon grounds/path openings are exact ownership inputs. Raising their voxel resolution alone adds no plant detail.','Keep ground/collision; add bounded common planting/paving within existing semantic use.')
 if category=='market_canopies':return ('cloth_and_timber','Source has actual roof extrusion and dimensional posts; broad cloth lacks sag thickness/seams and frame joint detail.','Reusable canopy curve/sag profile plus timber rules; source stall clearance and market gaps fixed.')
 if category in ('port_market_logistics_props','fuel_cargo_props','domestic_wash_props','workyard_props'):
  return ('cargo_and_tools','Barrels already use lathe/annulus volumes; crates/benches/racks use dimensional solids. Thin staves/hoops/plank separation and bindings need selected close review.','Shared barrel/crate/rack families at near range, original envelope/collision; no full-house voxelization.')
 if category=='drawbridge_state_components':return ('mechanism','Moving leaves/barriers/chain/counterweight are separate tested state geometry. Detail changes must preserve transforms/swept volumes and occupancy interlocks.','Reused timber/iron/stone surface rules, with envelope/sweep regression; do not decorate across hinge or gates.')
 if category in ('native_paving_access','main_bridge_static_approaches','small_bridges'):
  return ('access_surface','Many existing 0.05–0.15m stair/landing sources encode real supports and repaired public routes. Preserve them; public BIN road treatment alone does not cover these native surfaces.','Use actual native top-face ownership for stone/plank detail. No height drift, hole filling or invented flat floor.')
 if category in ('waterworks','canal_mill'):
  return ('water_facility','Fountain/draw points already have lathe/tube/annulus construction at0.05–0.1m; other basin/walk sources are coarse dimensional geometry. Fine pitch is not surface-art acceptance.','Reuse existing source details, masonry/planking on dry surfaces; water/source/opening semantics remain intact.')
 if category in ('cemetery_park_props','property_boundaries_guards','training_props'):
  return ('boundary_and_furniture','Boundary/guard collisions and deliberate gaps remain authoritative. Stone timber joins, bench/grave shapes need bounded near review.','Shared geometric material rules within envelope; preserve entries, gates and court clearance.')
 if category in ('bearing_supports',):return ('structural_support','Load-bearing supports exist and cannot become decorative hollow replacements.','Surface-only ashlar/wood rules, exact support geometry retained.')
 return ('building_and_fortification','Source-linked house or facility roof/window/masonry pipeline applies. Source completion and candidate binding are different from visual acceptance.','Compile reusable archetypes/variants once, finite near LOD/shared cache, source placement and public access unchanged.')
def main():
 inv=load(H/'coverage/asset_master_inventory.json');progress=load(H/'coverage/current_quality_progress.json');types=load(H/'coverage/type_coverage.json')['types'];assets={}
 for a in inv['assets']:
  p=R/a['master_path'];assert sha(p)==a['master_sha256'];m=load(p);ops=[o for c in m.get('components',[])for o in c.get('operations',[])]
  e=progress['assets'][a['asset_key']]
  assets[a['asset_key']]={'source_path':a['master_path'],'source_sha256':a['master_sha256'],'baseline_pitch_m':a['pitch_m'],'source_shape_kinds':dict(collections.Counter(o.get('shape',{}).get('kind','unknown')for o in ops)),'source_materials':sorted({o.get('material','cut')for o in ops}),'source_operation_count':len(ops),'existing_pipeline':{'whole_house_source':e['whole_house_source_ready'],'facility_roof_source':e['facility_roof_source_ready'],'wall_semantics':e['wall_relief_semantic_candidate']},'current_actual_art_acceptance':False}
 rows=[]
 for t in types:
  if not t['asset_keys']:continue
  kind,findings,next_step=requirement(t['category'])
  rows.append({'category':t['category'],'label_ko':t['label_ko'],'asset_keys':t['asset_keys'],'native_placements_not_buildings':t['placement_count'],'family':kind,'source_findings':findings,'bounded_next_batch':next_step,'acceptance':['Source provenance and occupied shape kept or explicitly versioned','Before/after actual city close view plus representative oblique','Near/far transition and bounded resource residency','Affected support, entrance or moving-envelope regression'],'art_status':'PENDING_ACTUAL_REVIEW','unconditional_regenerate':False})
 d={'schema':'riverstone.city.remaining_quality_scope.v1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'index_sha256':inv['baseline_index_sha256'],'scope':'Read source geometry and existing mappings; not a fresh visual review. No generated model or source mutated.','categories':rows,'assets':assets,'retained_zero_placement_assets':[a['asset_key']for a in inv['assets']if a['placement_count']==0],'used_asset_count':sum(a['placement_count']>0 for a in inv['assets']),'uncategorized_active_assets':[a['asset_key']for a in inv['assets']if a['placement_count']>0 and not a['category_counts']],'whole_city_quality_complete':False,'tests':{'all_inventory_source_hashes_match':len(assets)==len(inv['assets']),'all43_categories_accounted':len(rows)==43,'no_category_auto_accepted':all(t['art_status']=='PENDING_ACTUAL_REVIEW'for t in rows)}}
 assert all(d['tests'].values());(O/'ledger.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'assets':len(assets),'categories':len(rows),'uncategorized':d['uncategorized_active_assets'],'tests':d['tests']}))
if __name__=='__main__':main()
