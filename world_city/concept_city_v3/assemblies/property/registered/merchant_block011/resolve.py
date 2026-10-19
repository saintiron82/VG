"""Bind immutable shared common ranges to native doors and exact finite footprints."""
import copy,json,math
from pathlib import Path
from .grammar import HERE,ROOT,PLAN,ORDINARY,ref,write,g,estate
from voxel_character.common import core
from world_city.concept_city_v3.assemblies.ordinary.registered.r1.compile_rows import pose,inverse
from world_city.concept_city_v3.assemblies.ordinary.resolve_cached import ROOFS
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles,transform

def run():
 source=json.loads((HERE/'proposal.json').read_text());budget=json.loads((HERE/'compile_budget.json').read_text());report=json.loads((HERE/'compile_report.json').read_text())
 assert budget['proposal']==report['proposal']==ref(HERE/'proposal.json')
 assert report['budget']==ref(HERE/'compile_budget.json')
 assets=report['assets'];renders={}
 for k,a in assets.items():
  for kind in ('master','render','compiled'):assert ref(ROOT/a[kind+'_path'])['sha256']==a[kind+'_sha256']
  renders[k]=json.loads((ROOT/a['render_path']).read_text())
 members={p['id']:p for p in source['placements']};props={p['id']:p for p in source['properties']};placements=[];owner={}
 for inst in budget['placements']:
  m=[members[k] for k in inst['source_member_ids']];prop=next(p for p in source['properties'] if m[0]['id'].startswith(p['id']+':'));a=assets[inst['variant_key']]
  palette='wood_brown' if inst['group_id'].endswith(':rear') else ('clay_red' if list(props).index(prop['id'])%2 else 'slate_gray')
  p=dict(id=inst['group_id'],asset_key=inst['variant_key'],position_m=inst['position_m'],yaw_rad=inst['yaw_rad'],scale=[1,1,1],source_member_ids=inst['source_member_ids'],source_block_id=prop['block_id'],source_plot_ids=prop['source_plot_ids'],property_id=prop['id'],pad_floor_y_m=prop['floor_y_m'],compiled_asset_ref=str(ROOT/a['render_path']),render_sha256=a['render_sha256'],palette_id=palette,palette_override=dict(zip(('slate','slate_light','slate_dark','slate_worn'),ROOFS[palette])),actual_body_footprint_polygons_xz_m=[q['actual_body_footprint_xz_m'] for q in m],actual_outer_footprint_polygons_xz_m=[q['actual_outer_footprint_xz_m'] for q in m],native_union_verified=True,footprint_policy='Use exact finite component union or native foundation regions, never the group bounds.')
  placements.append(p)
  for k in inst['source_member_ids']:owner[k]=p
 doors=copy.deepcopy(source['actual_doors']);masks=[];slabs=[]
 for d in doors:
  p=owner[d['owner_id']];local=core.apply(inverse(pose(p)),d['actual_door_xyz_m']);matches=[]
  for gi,group in enumerate(renders[p['asset_key']]['groups']):
   if group['material'] not in ('door','door_dark'):continue
   for qi,quad in enumerate(group['quads']):
    lo=[min(v[k] for v in quad) for k in range(3)];hi=[max(v[k] for v in quad) for k in range(3)]
    for axis in (0,2):
     across=2-axis
     if abs(hi[axis]-lo[axis])<1e-8 and abs(lo[axis]-local[axis])<1e-6 and lo[across]-1e-6<=local[across]<=hi[across]+1e-6 and abs(lo[1]-local[1])<1e-6 and hi[1]>=local[1]+1-1e-6:
      matches.append(dict(group_index=gi,quad_index=qi,vertices_local_m=quad,normal_axis=axis,native_leaf_width_m=hi[across]-lo[across]))
  assert matches,(d['id'],local)
  d.update(actual_runtime_group_id=p['id'],actual_runtime_door_local_xyz_m=local,actual_union_threshold_evidence=matches,union_render_sha256=p['render_sha256'],cached_threshold_stub_xz_m=[[d['actual_door_xyz_m'][0],d['actual_door_xyz_m'][2]],d['threshold_lip_xz_m']],threshold_status='Exact closed native exterior leaf at declared finished floor. Route starts at outer-envelope lip; no walk-through-door or household claim.')
 for p in placements:
  floor=p['pad_floor_y_m']-p['position_m'][1];render=renders[p['asset_key']]
  foundation=[transform(poly,p) for poly in slab_rectangles(render,floor-.01,floor-.001)];assert foundation
  masks.append(dict(owner_id=p['id'],property_id=p['property_id'],floor_y_m=p['pad_floor_y_m'],kind='actual_native_foundation_at_threshold_floor',terrain_exclusion_regions_xz_m=foundation,foundation_embed_m=floor,render_sha256=p['render_sha256']))
  for j,poly in enumerate(slab_rectangles(render,floor+.05,floor+1.85)):slabs.append(dict(id=p['id']+':WALKING_SLAB:'+str(j),property_id=p['property_id'],polygon_xz_m=transform(poly,p),render_sha256=p['render_sha256']))
 pack=dict(schema='riverstone.registered_merchant_batch_pack.v1',status='compiled_native_candidate_pending_finite_floor_retaining_and_independent_review',source_plan_path=source['sources']['plan']['path'],source_plan_sha256=source['sources']['plan']['sha256'],proposal=ref(HERE/'proposal.json'),compile_report=ref(HERE/'compile_report.json'),resolver=ref(Path(__file__)),assets=assets,placements=placements,component_placements=source['placements'],actual_doors=doors,access_proposals=source['internal_routes'],external_gate_links=[dict(id=p['id']+':PUBLIC_LINK',property_id=p['id'],**p['external_gate_link']) for p in source['properties']],courts=source['courts'],ownership_masks=masks,native_walking_slabs=slabs,replaced_placement_ids=source['replacement_ledger']['replaced_placement_ids'],superseded_source_path_ids=source['replacement_ledger']['superseded_source_path_ids'],retired_source_residuals=source['replacement_ledger']['retired_source_residuals'],whole_block_metrics=source['whole_block_metrics'],summary=dict(properties=len(props),runtime_groups=len(placements),native_modules=len(members),actual_doors=len(doors),new_shared_assets=len(assets),new_shared_quads=report['total_quads'],foundation_regions=sum(len(m['terrain_exclusion_regions_xz_m']) for m in masks),walking_slabs=len(slabs),replaced_native_ids=len(source['replacement_ledger']['replaced_placement_ids'])),runtime_ready=False,applied_to_scene=False,integration_rules=['Remove exactly replaced_placement_ids before adding only the runtime group placements.','Component placements retain physical/provenance detail; do not render them again.','Bind finite floor and retaining ownership before enabling raised platforms; building origin is finished floor minus actual native door-local Y.','Keep current roads, water, institutional access and lower residual ground.'],limits=['No finished support, capsule, horse controller, interior traversal or visual approval claim.','Lower private yard service routes remain unresolved; the seven platform service courts have finite reserved native links.'])
 write(HERE/'resolved_placements.json',pack);print(json.dumps(dict(pack=ref(HERE/'resolved_placements.json'),summary=pack['summary']),indent=2));return pack
if __name__=='__main__':run()
