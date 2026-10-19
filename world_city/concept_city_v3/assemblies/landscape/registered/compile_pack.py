"""Sequential bounded common compilation and source-bound native instance resolution."""
import copy,json,time
from pathlib import Path
from . import author as q,context as c
from world_city.concept_city_v3.assemblies.property.registered import author as a
from world_city.concept_city_v3.assemblies.property.registered.audit import candidate_budget
from world_city.concept_city_v3.assemblies.property.registered.r1.author import cross,sub
from voxel_character.common import coordinate_planes,render_data
HERE=c.HERE;CACHE=HERE/'cache'
def write(p,v):p.write_text(json.dumps(v,separators=(',',':'),allow_nan=False)+'\n')
def run():
 source_path=q.OUT/'source_pack.json';pack=json.loads(source_path.read_text());context=c.load();assert pack['sources']==context['sources'];CACHE.mkdir(exist_ok=True);records=pack['wrappers']+[dict(asset_key=k,**v) for k,v in pack['assets'].items() if v['kind']=='new_common'];assert len(records)==7
 manifest={};results=[]
 for key,rec in pack['assets'].items():
  if rec['kind']!='verified_native_cache':continue
  cached=copy.deepcopy(rec['cached']);cached['compiled_asset_ref']=cached.get('compiled_asset_ref',cached.get('render_path'));assert a.file_sha(cached['compiled_asset_ref'])==cached['render_sha256'];assert a.file_sha(cached['master_path'])==cached['master_file_sha256'];manifest[key]=cached
 write(HERE/'compile_checkpoint.json',dict(source_pack_sha256=a.file_sha(source_path),source_bindings=pack['sources'],authorization='Parent approved seven bounded common sources after source tests pass; no broad scene placement or GUI.',new_asset_count=7,reused_asset_count=len(manifest),candidate_cap=300000,output_cap=100000,sequential=True,source_assets={r['asset_key']:r['source_sha256'] for r in records}))
 for r in records:
  mp=c.ROOT/r['source_path'];assert a.file_sha(mp)==r['source_sha256'];master=json.loads(mp.read_text());budget=candidate_budget(master);assert budget==r['candidate_budget'] and budget['within_candidate_cap'];key=r['asset_key'];started=time.monotonic();print(json.dumps(dict(asset=key,status='starting',candidate_visits=budget['exact_candidate_visits_without_cell_sampling'])),flush=True)
  try:
   before=copy.deepcopy(master);compiled=coordinate_planes.compile_master(master,{'pitch':.5},max_candidate_cells=300000,max_output_cells=100000);assert compiled['valid'] and master==before;render=render_data.make_render_data(compiled);rp=CACHE/(key+'.render.json');write(rp,render)
   manifest[key]=dict(asset_key=key,master_path=str(mp),master_file_sha256=a.file_sha(mp),master_source_sha256=a.sha(master),compiled_asset_ref=str(rp),render_sha256=a.file_sha(rp),sampling_resource={'pitch':.5},pitch_m=.5,bounds=render['bounds'],cell_count=render['cell_count'],quad_count=render['quad_count'],common_master_hash=compiled['master_hash'],common_payload_hash=compiled['payload_hash'])
   result=dict(asset_key=key,status='compiled',candidate_cells=compiled['candidate_cells'],occupied_cells=render['cell_count'],quad_count=render['quad_count'],elapsed_s=round(time.monotonic()-started,3));results.append(result);print(json.dumps(result),flush=True)
  except Exception as exc:
   results.append(dict(asset_key=key,status='failed',error=str(exc)));write(HERE/'cache_build_report.json',dict(status='failed',results=results));raise
  write(HERE/'cache_build_report.json',dict(status='complete' if len(results)==7 else 'partial',results=results,sequential=True,candidate_cap=300000,output_cap=100000))
 write(CACHE/'manifest.json',dict(schema='riverstone.registered_landscape.cache.v1',source_pack_sha256=a.file_sha(source_path),assets=manifest,new_asset_count=7,reused_asset_count=3))
 placements=[];ownership=[]
 for p in pack['placements']:
  ins=copy.deepcopy(p);m=manifest[p['asset_key']];ins.update(compiled_asset_ref=m['compiled_asset_ref'],render_sha256=m['render_sha256'],source_space_polygon_sha256=a.sha(next(s['polygon_xz_m'] for s in context['plan']['spaces'] if s['id']==p['source_space_id'])));placements.append(ins)
 for w in pack['wrappers']:
  m=manifest[w['asset_key']];render=json.loads(Path(m['compiled_asset_ref']).read_text());origin=w['position_m'];tops=[]
  for group in render['groups']:
   for quad in group['quads']:
    n=cross(sub(quad[1],quad[0]),sub(quad[2],quad[0]))
    if n[1]>1e-7:tops.append(dict(polygon_xz_m=[[p[0]+origin[0],p[2]+origin[2]] for p in quad],y_m=quad[0][1]+origin[1],material=group['material']))
  mask=dict(id=w['id']+':surface_owner',owner_id=w['id'],source_site_ids=w['source_site_ids'],logical_owned_floor_regions_xz_m=w['owned_floor_regions_xz_m'],source_external_surface_profiles=w['external_surface_profiles'],compiled_upward_faces=tops,terrain_exclusion_regions_xz_m=[t['polygon_xz_m'] for t in tops],terrain_exclusion_union_required=True,policy='Exclude only the exact union of persisted upward-face XZ cells. Wall caps are occupied surfaces, not ground datums. Source continuous ramp profiles do not assert traversal of sampled steps.',sampled_render_sha256=m['render_sha256']);ownership.append(mask)
  placements.append(dict(id=w['id'],asset_key=w['asset_key'],role='finite_owned_floor_boundary_and_access',position_m=w['position_m'],yaw_rad=0,scale=[1,1,1],source_site_ids=w['source_site_ids'],compiled_asset_ref=m['compiled_asset_ref'],render_sha256=m['render_sha256'],surface_owner=w['id'],surface_ownership=mask))
 result=dict(schema='riverstone.registered_landscape.runtime_resolution.v1',status='compiled_pending_access_support_and_actual_view',sources=pack['sources'],source_pack_sha256=a.file_sha(source_path),cache_manifest_sha256=a.file_sha(CACHE/'manifest.json'),metrics=pack['metrics'],placements=placements,asset_manifest=manifest,ownership_masks=ownership,sites=pack['sites'],internal_routes=[r for s in pack['sites'] for r in s['internal_paths']],external_connections=[s['external_connection'] for s in pack['sites']],replacement_ledger=dict(source_building_ids=[],source_path_ids=[],source_space_ids=sorted({s['space'] for s in pack['sites']}),ground_replacement_policy='Only exact compiled wrapper upward-face XZ cells replace the corresponding terrain surface; source spaces stay as provenance.',existing_estate_or_forest_ids=[]),activation_requirements=['independent actual common geometry access and support checks','exact finite terrain ownership and public-side seam handoff','native landmark approach vertical acceptance','actual common geometry visual review'],runtime_ready=False,applied_to_scene=False)
 write(HERE/'resolved_placements.json',result);return result
if __name__=='__main__':run()
