"""Seven bounded replacement wrappers; unchanged native modules reuse r0 caches."""
import copy,json,time
from pathlib import Path
from . import author as q
from .. import author as a
from ..audit import candidate_budget
from voxel_character.common import coordinate_planes,render_data
HERE=q.HERE;OUT=q.OUT;CACHE=HERE/'cache'
def write(p,x):p.write_text(json.dumps(x,separators=(',',':'),allow_nan=False)+'\n')
def run():
 overlay=json.loads((OUT/'access_overlay.json').read_text());assert overlay['status']=='source_complete_pending_independent_audit';assert overlay['registered_source_sha256']==a.file_sha(a.CITY/'registered_source/plan.json')
 old=json.loads((a.HERE/'resolved_placements.json').read_text());recipes=[json.loads((OUT/(i+'.recipe.json')).read_text()) for i in a.IDS];assert all(a.validate_recipe(r)['valid'] for r in recipes)
 CACHE.mkdir(exist_ok=True);manifest={};progress=[]
 for r in recipes:
  for key in r['cache_specs']:
   m=old['asset_manifest'][key];assert a.file_sha(m['compiled_asset_ref'])==m['render_sha256'];assert a.file_sha(m['master_path'])==m['master_file_sha256'];manifest[key]=m
 write(HERE/'compile_checkpoint.json',dict(source_overlay_sha256=a.file_sha(OUT/'access_overlay.json'),r0_pack_sha256=a.file_sha(a.HERE/'resolved_placements.json'),source_master_sha256={r['property_id']:r['master_sha256'] for r in overlay['records']},authorization='Parent authorized r1 overlay and rebuilt wrappers where gate changes require it; source buildings and public roads unchanged.',new_asset_count=7,reused_asset_count=len(manifest),candidate_cap=300000,output_cap=100000,sequential=True))
 for row in overlay['records']:
  started=time.monotonic();mp=OUT/row['master_file'];assert a.file_sha(mp)==row['master_sha256'];master=json.loads(mp.read_text());before=copy.deepcopy(master);budget=candidate_budget(master);assert budget['within_candidate_cap'];key=master['id'];print(json.dumps(dict(property_id=row['property_id'],asset=key,status='starting',candidate_visits=budget['exact_candidate_visits_without_cell_sampling'])),flush=True)
  try:
   compiled=coordinate_planes.compile_master(master,{'pitch':.5},max_candidate_cells=300000,max_output_cells=100000);assert compiled['valid'] and master==before;render=render_data.make_render_data(compiled);rp=CACHE/(key+'.render.json');write(rp,render)
   manifest[key]=dict(asset_key=key,master_path=str(mp),master_file_sha256=a.file_sha(mp),master_source_sha256=a.sha(master),compiled_asset_ref=str(rp),render_sha256=a.file_sha(rp),sampling_resource={'pitch':.5},pitch_m=.5,bounds=render['bounds'],cell_count=render['cell_count'],quad_count=render['quad_count'],common_master_hash=compiled['master_hash'],common_payload_hash=compiled['payload_hash'])
   stat=dict(property_id=row['property_id'],status='compiled',candidate_cells=compiled['candidate_cells'],occupied_cells=render['cell_count'],quad_count=render['quad_count'],elapsed_s=round(time.monotonic()-started,3));progress.append(stat);print(json.dumps(stat),flush=True)
  except Exception as exc:
   progress.append(dict(property_id=row['property_id'],status='failed',error=str(exc)));write(HERE/'cache_build_report.json',dict(status='failed',results=progress));raise
  write(HERE/'cache_build_report.json',dict(status='partial' if len(progress)<7 else 'complete',results=progress,sequential=True,candidate_cap=300000,output_cap=100000))
 write(CACHE/'manifest.json',dict(schema='riverstone.registered_property.r1_cache.v1',source_overlay_sha256=a.file_sha(OUT/'access_overlay.json'),assets=manifest,new_asset_count=7,reused_asset_count=len(manifest)-7))
 placements=[];masks=[];doors=[];routes=[];ledgers=[]
 for r,row in zip(recipes,overlay['records']):
  for p in r['placements']:
   m=manifest[p['asset_key']];ins=copy.deepcopy(p);ins.update(property_id=r['id'],source_plot_sha256=r['source_plot_sha256'],source_polygon_sha256=r['source_polygon_sha256'],compiled_asset_ref=m['compiled_asset_ref'],render_sha256=m['render_sha256']);placements.append(ins);doors.extend(p.get('entrances',[]))
  key=row['master_id'];m=manifest[key];origin=r['origin_xz_m'];floor=r['plot']['pad_floor_y_m'];render=json.loads(Path(m['compiled_asset_ref']).read_text());tops=[];gate_hits=[];g=r['gates'][0];passage=a.geom.road_ribbon(g['inside_point_xz_m'],g['outside_point_xz_m'],4.)
  for group in render['groups']:
   for quad in group['quads']:
    normal=q.cross(q.sub(quad[1],quad[0]),q.sub(quad[2],quad[0]))
    if normal[1]<=1e-7:continue
    poly=[[p[0]+origin[0],p[2]+origin[1]] for p in quad];tops.append(dict(polygon_xz_m=poly,y_m=quad[0][1]+floor,material=group['material']))
    if quad[0][1]>1 and a.overlap(poly,passage):gate_hits.append(poly)
  assert not gate_hits,'Persisted common gate clear band obstructed'
  mask=dict(property_id=r['id'],**r['surface_ownership'],external_access_domains_xz_m=r['external_surface']['polygon_regions_xz_m'],compiled_upward_faces=tops,terrain_exclusion_regions_xz_m=[r['plot']['polygon_xz_m']]+r['external_surface']['polygon_regions_xz_m']+[t['polygon_xz_m'] for t in tops],terrain_exclusion_union_required=True,sampled_render_sha256=m['render_sha256'],sampling_pitch_m=.5,source_gate_width_m=5,verified_sampled_gate_clear_band_m=4,compiled_gate_intrusions=[])
  masks.append(mask);placements.append(dict(id=r['id']+':registered_r1:infrastructure',property_id=r['id'],role='owned_irregular_floor_boundary_and_access',asset_key=key,position_m=[origin[0],floor,origin[1]],yaw_rad=0,scale=[1,1,1],source_plot_sha256=r['source_plot_sha256'],source_polygon_sha256=r['source_polygon_sha256'],local_bounds=m['bounds'],footprint_regions_xz_m=[r['plot']['polygon_xz_m']]+r['external_surface']['polygon_regions_xz_m'],compiled_asset_ref=m['compiled_asset_ref'],render_sha256=m['render_sha256'],surface_ownership=mask,shared_boundary_ownership=r['shared_edge_ownership']))
  ledgers.append(dict(property_id=r['id'],**r['replacement_proposal'],supersede_r0_infrastructure_id=row['supersede_r0_infrastructure_id'],supersede_r0_route_ids=row['supersede_r0_route_ids'],property_pose_updates=r['garden_pose_revision_ledger']));routes.extend(r['entrance_routes'])
 result=dict(schema='riverstone.registered_property.runtime_resolution.v2',revision='r1_access',status='compiled_pending_independent_access_support_and_actual_view',registered_source_sha256=overlay['registered_source_sha256'],source_overlay_sha256=a.file_sha(OUT/'access_overlay.json'),r0_pack_sha256=a.file_sha(a.HERE/'resolved_placements.json'),cache_manifest_sha256=a.file_sha(CACHE/'manifest.json'),placements=placements,asset_manifest=manifest,ownership_masks=masks,actual_doors=doors,internal_routes=routes,external_access_surfaces=[r['external_surface'] for r in recipes],gate_proposals=[dict(property_id=r['id'],gates=r['gates'],source_polygon_sha256=r['source_polygon_sha256']) for r in recipes],replacement_ledger=ledgers,activation_requirements=['independent full door-to-road traversal and ownership acceptance','registered terrain support overlay and retaining closure','actual compiled common-geometry visual review'],runtime_ready=False,applied_to_scene=False)
 write(HERE/'resolved_placements.json',result);return result
if __name__=='__main__':run()
