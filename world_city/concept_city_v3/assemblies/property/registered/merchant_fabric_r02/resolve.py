"""Exact rigid cached groups, actual native door leaves, and finite ground holes."""
import copy,json,math
from pathlib import Path
from .grammar import HERE,ROOT,ref,write,slab_rectangles,roof_rects,g
from ..merchant_block011.prepare_handoff import union,subtract,area
from voxel_character.common import core
from world_city.concept_city_v3.assemblies.ordinary.registered.r1.compile_rows import pose,inverse
from world_city.concept_city_v3.assemblies.ordinary.resolve_cached import ROOFS
from world_city.concept_city_v3.validation.check_landmark_access_candidate import transform

def run():
 source=json.loads((HERE/'effective_eligibility.json').read_text());budget=json.loads((HERE/'compile_budget.json').read_text());report=json.loads((HERE/'compile_report.json').read_text());assert budget['eligibility']==report['eligibility']==ref(HERE/'eligibility.json');assert report['budget']==ref(HERE/'compile_budget.json');assets=budget['reused_assets']|report['assets'];renders={}
 for key,a in assets.items():
  for kind in ('master','render'):assert ref(ROOT/a[kind+'_path'])['sha256']==a[kind+'_sha256']
  if a.get('compiled_path'):assert ref(ROOT/a['compiled_path'])['sha256']==a['compiled_sha256']
  renders[key]=json.loads((ROOT/a['render_path']).read_text())
 props={p['id']:p for p in source['properties']};members={q['id']:q for p in props.values() for q in p['placements']};placements=[];owner={}
 for inst in budget['placements']:
  
  if inst['property_id'] not in props:continue
  ms=[members[k] for k in inst['source_member_ids']];prop=props[inst['property_id']];a=assets[inst['asset_key']];palette=inst['palette_id'];p=copy.deepcopy(inst);p.update(source_block_id=prop['block_id'],source_plot_ids=prop['source_plot_ids'],pad_floor_y_m=prop['floor_y_m'],compiled_asset_ref=str(ROOT/a['render_path']),render_sha256=a['render_sha256'],palette_override=dict(zip(('slate','slate_light','slate_dark','slate_worn'),ROOFS[palette])),actual_body_footprint_polygons_xz_m=[v for q in ms for v in q['native_body_polygons_xz_m']],actual_outer_footprint_polygons_xz_m=[v for q in ms for v in q['native_roof_polygons_xz_m']],footprint_policy='Use exact native foundation regions or component polygons; group cache bounds are broadphase only.')
  placements.append(p)
  for k in inst['source_member_ids']:owner[k]=p
 doors=copy.deepcopy([d for p in props.values() for d in p['actual_doors']]);masks=[];slabs=[];proofs=[]
 for d in doors:
  p=owner[d['owner_id']];local=core.apply(inverse(pose(p)),d['actual_door_xyz_m']);matches=[]
  for gi,group in enumerate(renders[p['asset_key']]['groups']):
   if group['material'] not in ('door','door_dark'):continue
   for qi,quad in enumerate(group['quads']):
    lo=[min(v[k] for v in quad) for k in range(3)];hi=[max(v[k] for v in quad) for k in range(3)]
    for axis in (0,2):
     across=2-axis
     if abs(hi[axis]-lo[axis])<1e-8 and abs(lo[axis]-local[axis])<1e-6 and lo[across]-1e-6<=local[across]<=hi[across]+1e-6 and abs(lo[1]-local[1])<1e-6 and hi[1]>=local[1]+1-1e-6:matches.append(dict(group_index=gi,quad_index=qi,vertices_local_m=quad,normal_axis=axis,native_leaf_width_m=hi[across]-lo[across]))
  assert matches,(d['id'],local)
  d.update(actual_runtime_group_id=p['id'],actual_runtime_door_local_xyz_m=local,actual_union_threshold_evidence=matches,union_render_sha256=p['render_sha256'],cached_threshold_stub_xz_m=[[d['actual_door_xyz_m'][0],d['actual_door_xyz_m'][2]],d['threshold_lip_xz_m']],threshold_status='Measured closed native leaf at finished floor; external route begins at outer-envelope lip. No interior traversal claim.')
 for p in placements:
  floor=p['pad_floor_y_m']-p['position_m'][1];r=renders[p['asset_key']];found=[transform(q,p) for q in slab_rectangles(r,floor-.01,floor-.001)];assert found;expected=union([q for mid in p['source_member_ids'] for q in members[mid]['native_foundation_polygons_xz_m']]);missing=area(subtract(expected,found));extra=area(subtract(found,expected));assert max(missing,extra)<1e-5,(p['id'],missing,extra)
  roof=[transform(q,p) for q in roof_rects(r)];expected_roof=union([q for mid in p['source_member_ids'] for q in members[mid]['native_roof_polygons_xz_m']]);roof_missing=area(subtract(expected_roof,roof));roof_extra=area(subtract(roof,expected_roof));assert max(roof_missing,roof_extra)<1e-5,(p['id'],roof_missing,roof_extra)
  proofs.append(dict(group_id=p['id'],foundation_missing_m2=missing,foundation_extra_m2=extra,roof_missing_m2=roof_missing,roof_extra_m2=roof_extra))
  p['native_union_verified']=True;p['native_roof_polygons_xz_m']=roof;masks.append(dict(owner_id=p['id'],property_id=p['property_id'],floor_y_m=p['pad_floor_y_m'],kind='actual_native_foundation_at_threshold_floor',terrain_exclusion_regions_xz_m=found,foundation_embed_m=floor,render_sha256=p['render_sha256']))
  for j,q in enumerate(slab_rectangles(r,floor+.05,floor+1.85)):slabs.append(dict(id=p['id']+':WALKING_SLAB:'+str(j),property_id=p['property_id'],polygon_xz_m=transform(q,p),render_sha256=p['render_sha256']))
 pack=dict(schema='riverstone.registered_merchant_fabric_r02_pack.v1',status='compiled_native_candidate_pending_finite_terrain_support',source_plan_path=source['sources']['plan']['path'],source_plan_sha256=source['sources']['plan']['sha256'],sources=source['sources'],eligibility=ref(HERE/'effective_eligibility.json'),base_eligibility=ref(HERE/'eligibility.json'),compile_report=ref(HERE/'compile_report.json'),resolver=ref(Path(__file__)),assets=assets,placements=placements,component_placements=list(members.values()),actual_doors=doors,access_proposals=[r for p in props.values() for r in p['internal_routes']],external_gate_links=[dict(id=p['id']+':PUBLIC_LINK',property_id=p['id'],**p['external_gate_link']) for p in props.values()],courts=[p['court'] for p in props.values()],ownership_masks=masks,native_walking_slabs=slabs,native_union_mask_proofs=proofs,**source['replacement_ledger'],summary=dict(properties=len(props),runtime_groups=len(placements),native_modules=len(members),actual_doors=len(doors),new_shared_assets=len(report['assets']),reused_shared_assets=len(budget['reused_assets']),foundation_regions=sum(len(q['terrain_exclusion_regions_xz_m']) for q in masks),walking_slabs=len(slabs),retired_native_ids=len(source['replacement_ledger']['replaced_placement_ids'])),runtime_ready=False,applied_to_scene=False,integration_rules=['Retire exactly replaced_placement_ids and declared superseded private route IDs.','Render only runtime group placements; component_placements are provenance and measurements.','Apply the later exact platform/gate/retaining terrain ownership before placing raised groups.','Preserve all prior seven-merchant, B013/B015, public-lane, water and institutional masks.'],limits=['No finished native terrain support, capsule/controller, interior door or actual scene view approval.','Goods-store leaves are measured small doors. Carts reach their court only; no wide warehouse portal is claimed.'])
 write(HERE/'resolved_placements.json',pack);print(json.dumps(dict(pack=ref(HERE/'resolved_placements.json'),summary=pack['summary']),indent=2));return pack
if __name__=='__main__':run()
