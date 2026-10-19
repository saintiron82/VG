"""Four bounded common sources; three existing native building caches are reused."""
import copy,json,sys,time
from pathlib import Path
from . import author as t
from world_city.concept_city_v3.assemblies.property.registered import author as a
from world_city.concept_city_v3.assemblies.property.registered.audit import candidate_budget
from world_city.concept_city_v3.assemblies.property.registered.r1.author import cross,sub
from world_city.concept_city_v3.assemblies.ordinary.resolve_cached import ROOFS
from voxel_character.common import coordinate_planes,render_data
sys.path.insert(0,str(t.c.CITY/'validation'))
from check_landmark_access_candidate import slab_rectangles,transform
HERE=t.HERE;CACHE=HERE/'cache'
def write(p,v):p.write_text(json.dumps(v,separators=(',',':'),allow_nan=False)+'\n')
def run():
 p=json.loads((t.OUT/'source_pack.json').read_text());w=json.loads((t.OUT/'ground_wrapper.json').read_text());assert p['sources']==t.source_inputs()['sources'];CACHE.mkdir(exist_ok=True);assets={};renders={};results=[]
 for key,v in p['assets'].items():
  if v['kind']=='verified_native_cache':
   m=copy.deepcopy(v['cached']);assert a.file_sha(m['compiled_asset_ref'])==m['render_sha256'];assert a.file_sha(m['master_path'])==m['master_file_sha256'];assets[key]=m;renders[key]=json.loads(Path(m['compiled_asset_ref']).read_text())
 records=[w]+[dict(asset_key=k,**r) for k,r in p['assets'].items() if r['kind']=='new_common'];assert len(records)==4
 write(HERE/'compile_checkpoint.json',dict(source_pack_sha256=a.file_sha(t.OUT/'source_pack.json'),ground_wrapper_sha256=a.file_sha(t.OUT/'ground_wrapper.json'),new_assets=4,reused_assets=3,candidate_cap=300000,output_cap=100000,source_tests='Seven tests passed before compilation.',authorization='Parent approved this reversible SITE_TRAIN assembly and bounded cache work.'))
 existing=json.loads((CACHE/'manifest.json').read_text())['assets'] if (CACHE/'manifest.json').exists() else {}
 for r in records:
  mp=t.c.ROOT/r['source_path'];assert a.file_sha(mp)==r['source_sha256'];m=json.loads(mp.read_text());budget=candidate_budget(m);assert budget==r['candidate_budget'] and budget['within_candidate_cap'];key=r['asset_key'];start=time.monotonic();print(json.dumps(dict(asset=key,status='starting',candidates=budget['exact_candidate_visits_without_cell_sampling'])),flush=True)
  if key in existing and existing[key]['master_file_sha256']==a.file_sha(mp) and a.file_sha(existing[key]['compiled_asset_ref'])==existing[key]['render_sha256']:
   assets[key]=existing[key];renders[key]=json.loads(Path(existing[key]['compiled_asset_ref']).read_text());results.append(dict(asset=key,status='verified_native_cache_reuse',elapsed_s=0));print(json.dumps(results[-1]),flush=True);continue
  try:
   old=copy.deepcopy(m);compiled=coordinate_planes.compile_master(m,{'pitch':.5},max_candidate_cells=300000,max_output_cells=100000);assert compiled['valid'] and m==old;render=render_data.make_render_data(compiled);rp=CACHE/(key+'.render.json');write(rp,render);renders[key]=render;assets[key]=dict(asset_key=key,master_path=str(mp),master_file_sha256=a.file_sha(mp),master_source_sha256=a.sha(m),compiled_asset_ref=str(rp),render_sha256=a.file_sha(rp),sampling_resource={'pitch':.5},pitch_m=.5,bounds=render['bounds'],cell_count=render['cell_count'],quad_count=render['quad_count'],common_master_hash=compiled['master_hash'],common_payload_hash=compiled['payload_hash']);row=dict(asset=key,status='compiled',candidate_cells=compiled['candidate_cells'],occupied_cells=render['cell_count'],quad_count=render['quad_count'],elapsed_s=round(time.monotonic()-start,3));results.append(row);print(json.dumps(row),flush=True)
  except Exception as exc:
   results.append(dict(asset=key,status='failed',error=str(exc)));write(HERE/'cache_build_report.json',dict(status='failed',results=results));raise
  write(HERE/'cache_build_report.json',dict(status='complete' if len(results)==4 else 'partial',results=results))
 write(CACHE/'manifest.json',dict(schema='riverstone.registered_training.cache.v1',source_pack_sha256=a.file_sha(t.OUT/'source_pack.json'),assets=assets,new_assets=4,reused_assets=3))
 placements=copy.deepcopy(p['placements']);doors=[];ownership=[]
 for ins in placements:
  m=assets[ins['asset_key']];ins.update(compiled_asset_ref=m['compiled_asset_ref'],render_sha256=m['render_sha256'])
  if ins.get('entrances'):
   palette='wood_brown' if ins['role'] in ('barrack','stable') else 'clay_red';ins.update(palette_id=palette,palette_override=dict(zip(('slate','slate_light','slate_dark','slate_worn'),ROOFS[palette])),palette_provenance='existing approved semantic roof-slot mapping, native geometry/cache unchanged',runtime_material_remap_pending=False)
   render=renders[ins['asset_key']]
   for door in ins['entrances']:
    x,y,z=door['door_local_xyz_m'];matches=[]
    for gi,g in enumerate(render['groups']):
     if g['material'] not in ('door','door_dark'):continue
     for qi,quad in enumerate(g['quads']):
      lo=[min(p[i] for p in quad) for i in range(3)];hi=[max(p[i] for p in quad) for i in range(3)]
      if abs(hi[2]-lo[2])<1e-8 and abs(lo[2]-z)<1e-7 and lo[0]-1e-7<=x<=hi[0]+1e-7 and abs(lo[1]-y)<1e-7 and hi[1]>=y+1:matches.append(dict(group_index=gi,quad_index=qi,material=g['material'],vertices_local_m=quad))
    assert matches,door['id'];door.update(actual_cached_threshold_evidence=matches,render_sha256=m['render_sha256']);doors.append(door)
   dy=ins['entrances'][0]['door_local_xyz_m'][1];polys=[transform(poly,ins) for poly in slab_rectangles(render,dy-.01,dy-.001)];ownership.append(dict(owner_id=ins['id'],kind='actual_native_foundation_at_threshold_floor',floor_y_m=18,terrain_exclusion_regions_xz_m=polys,terrain_exclusion_union_required=True,render_sha256=m['render_sha256'],foundation_embed_m=dy,policy='Exact native closed-mesh foundation section just below floor18; never broad roof envelope.'))
 for ins in placements:
  if not ins.get('entrances'):
   checks=[dict(point_xz_m=q,terrain_y_m=t.terrain.land_height_at(*q),floor_delta_m=18-t.terrain.land_height_at(*q)) for q in ins['footprint_xz_m']]
   assert max(abs(v['floor_delta_m']) for v in checks)<1e-7;ins['ground_anchor']=dict(finished_floor_y_m=18,footing_embed_m=.5,support_points_xz_m=ins['footprint_xz_m'],support_samples=checks,preserve_xz_and_scale=True)
 m=assets[w['asset_key']];render=renders[w['asset_key']];origin=w['position_m'];tops=[]
 for group in render['groups']:
  for quad in group['quads']:
   if cross(sub(quad[1],quad[0]),sub(quad[2],quad[0]))[1]>1e-7:tops.append(dict(polygon_xz_m=[[p[0]+origin[0],p[2]+origin[2]] for p in quad],y_m=quad[0][1]+origin[1],material=group['material']))
 mask=dict(owner_id=w['id'],kind='finite_common_drill_floor_and_access',floor_y_m=18,compiled_upward_faces=tops,terrain_exclusion_regions_xz_m=[r['polygon_xz_m'] for r in tops],terrain_exclusion_union_required=True,logical_owned_floor_regions=w['owned_floor_regions'],source_external_surface=p['external_surface'],render_sha256=m['render_sha256'],policy='Exact compiled upward-face XZ union only. Continuous external triangles remain a separate proposed profile; sampled steps are not traversal-certified.');ownership.append(mask);placements.append(dict(id=w['id'],asset_key=w['asset_key'],role='finite_drill_courts_and_access',position_m=w['position_m'],yaw_rad=0,scale=[1,1,1],compiled_asset_ref=m['compiled_asset_ref'],render_sha256=m['render_sha256'],surface_owner=w['id'],surface_ownership=mask))
 road_index=a.geom._SpatialIndex(20);road_regions={}
 for road in t.source_inputs()['plan']['roads']:
  for j,(u,v) in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
   key=road['id']+':'+str(j);poly=a.geom.road_ribbon(u,v,road['width_m']);road_index.add(key,poly);road_regions[key]=dict(road_id=road['id'],road_segment_id=key,polygon_xz_m=poly)
 public_overrides=[]
 for i,face in enumerate(tops):
  for k in road_index.candidates(face['polygon_xz_m']):
   road=road_regions[k];intersection=a.geom.convex_intersection(face['polygon_xz_m'],road['polygon_xz_m'])
   if a.geom.polygon_area(intersection)<1e-7:continue
   assert road['road_id']=='CASTLE_APPROACH','Unexpected common-ground road intrusion'
   public_overrides.append(dict(owner_id=w['id'],road_id=road['road_id'],road_segment_id=k,compiled_face_index=i,polygon_xz_m=intersection,actual_compiled_top_y_m=face['y_m'],render_sha256=m['render_sha256'],status='explicit_finite_native_road_coownership_pending_adjacent_transition_review'))
 result=dict(schema='riverstone.registered_training.runtime_resolution.v1',status='compiled_pending_independent_support_access_and_actual_view',sources=dict(p['sources'],active_terrain_contract=dict(path=str((t.c.CITY/'registered_topography/revisions/r07_native_interfaces/contract.json').relative_to(t.c.ROOT)),sha256=a.file_sha(t.c.CITY/'registered_topography/revisions/r07_native_interfaces/contract.json'))),source_pack_sha256=a.file_sha(t.OUT/'source_pack.json'),ground_wrapper_sha256=a.file_sha(t.OUT/'ground_wrapper.json'),cache_manifest_sha256=a.file_sha(CACHE/'manifest.json'),placements=placements,asset_manifest=assets,ownership_masks=ownership,actual_public_surface_overrides=public_overrides,actual_doors=doors,internal_routes=p['internal_routes'],external_access_surfaces=[p['external_surface']],gate_proposals=[p['gate']],replacement_ledger=p['replacement_ledger'],source_space=p['source_space'],central_exercise_reservation=p['central_exercise_reservation'],native_support_samples=p['native_support_samples'],metrics=dict(placements=len(placements),native_buildings=4,props=7,new_assets=4,reused_assets=3,actual_doors=len(doors),internal_routes=len(p['internal_routes']),connected_open_drill_area_m2=a.geom.polygon_area(t.CORE),source_precinct_area_m2=p['source_space']['area_m2']),activation_requirements=['independent actual native corridor and finite interface checks','finite terrain exclusion and foundation support integration','public-side shared threshold profile','actual common geometry visual review'],runtime_ready=False,applied_to_scene=False)
 write(HERE/'resolved_placements.json',result);return result
if __name__=='__main__':run()
