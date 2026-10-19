"""One immutable native/internal-access/bearing rebind for the R17 next18 batch."""
from . import geometry as g
from .design import HERE as SOURCE
from .activate_backlands_subset import ActualNative,SCENE
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles,transform
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from collections import defaultdict
import math,time
OUT=SOURCE/'coherent_datum_addendum_r01'
R17=a.HERE/'entry_continuation_r01';REQUEST=R17/'coherent_datum_rebind_request_r02.json';EXPECTED='7c4cd2fb5201cd138ee8019b233b220ee6513445f55f8b9ccdf2f819f698771d'
SKIP={'public_target_evidence','public_center_anchor','chosen_public_anchor','terrain_height_budget','native_face_evidence','source_position_local_xyz_m','actual_local_xyz_m','court_datum_evidence','public_root','source_terrain_evidence','source_terrain_height_budget','source_support_evidence'}
SCALAR={'floor_y_m','finished_floor_y_m','holding_floor_y_m','proposed_floor_y_m','native_bottom_y_m'}
COORD={'position_m','actual_door_xyz_m','gate_xyz_m','origin_xyz_m'}
ARRAYS={'polyline_xyz_m','vertices_xyz_m'}

def shift(obj,delta):
 if isinstance(obj,list):return [shift(v,delta)for v in obj]
 if not isinstance(obj,dict):return obj
 out={}
 for k,v in obj.items():
  if k in SKIP:out[k]=g.copy.deepcopy(v)
  elif k in SCALAR and isinstance(v,(int,float)):out[k]=v+delta
  elif k in COORD and isinstance(v,list)and len(v)==3:out[k]=[v[0],v[1]+delta,v[2]]
  elif k in ARRAYS:out[k]=[[p[0],p[1]+delta,p[2]]for p in v]
  else:out[k]=shift(v,delta)
 return out

def require(ref):
 p=g.ROOT/ref['path'];assert g.ref(p)['sha256']==ref['sha256'],str(p);return g.load(p)

def run():
 started=time.monotonic();assert g.ref(REQUEST)['sha256']==EXPECTED;request=g.load(REQUEST);layout=require(request['source_layout']);prepared=require(request['source_prepared_parcels']);mf=g.load(SOURCE/'effective_city_manifest_r01.json');ids=set(request['matched_next_batch_holding_ids']);changes={r['holding_id']:r for r in request['datum_changes']};assert len(ids)==18 and len(changes)==16;OUT.mkdir(exist_ok=True)
 sourcepacks={};refs={};byholding={h['id']:h for h in layout['holdings']};sourceps={p['id']:p for p in mf['placements']};records=[];allps=[];alldoors=[];allroutes=[];allbearings=[];retire=set();retrows={r['source_id']:r for r in prepared['retirement_records']};assets={};metadata_checks=[]
 for d in mf['districts']:
  if any(h.startswith(d['block_id']+':')for h in ids):
   pack=require(d['pack']);root=(g.ROOT/d['pack']['path']).parent;sourcepacks[d['block_id']]=dict(pack=pack,root=root,access=g.load(root/'access_handoff.json'),terrain=g.load(root/'terrain_handoff.json'),equipment=g.load(root/'court_equipment.json'));refs[d['block_id']]=dict(pack=d['pack'],terrain=g.ref(root/'terrain_handoff.json'),access=g.ref(root/'access_handoff.json'),equipment=g.ref(root/'court_equipment.json'))
 for hid in sorted(ids):
  old=byholding[hid];ch=changes.get(hid,dict(holding_id=hid,original_floor_y_m=old['floor_y_m'],candidate_floor_y_m=old['floor_y_m'],delta_y_m=0.,reason='Already-passing shared-retirement neighbor; exact bytes retained.'));delta=ch['delta_y_m'];new=ch['candidate_floor_y_m'];assert abs(old['floor_y_m']-ch['original_floor_y_m'])<1e-10
  bid=hid.split(':')[0];src=sourcepacks[bid];original=[p for p in mf['placements']if p.get('holding_id')==hid];ps=shift(original,delta);doors=shift([d for d in layout['actual_doors']if d['holding_id']==hid],delta);routes=shift([r for r in src['access']['routes']if r['holding_id']==hid],delta);parcel=shift(next(p for p in prepared['parcels']if p['id']==hid),delta);ground=shift(next(x for x in src['equipment']['holding_grounds']if x['holding_id']==hid),delta);holding=shift(old,delta);chain=shift(next(x for x in src['terrain']['court_route_chains']if x['holding_id']==hid),delta);bearings=shift([r for r in prepared['native_earth_bearings']if r['holding_id']==hid],delta)
  if hid in changes:holding['court_datum_evidence']=dict(previous_source_evidence=old.get('court_datum_evidence'),floor_y_m=new,rigid_y_delta_m=delta,request=g.ref(REQUEST),reason='Shared finite full-width entry solve against the actual fixed public field; native/internal-floor datum moves atomically, with no change to local caches or XZ.');
  check=dict(all_native_origins_shifted=all(abs(p['position_m'][1]-sourceps[p['id']]['position_m'][1]-delta)<1e-10 for p in ps),xz_yaw_scale_unchanged=all(p['position_m'][::2]==sourceps[p['id']]['position_m'][::2]and p['yaw_rad']==sourceps[p['id']]['yaw_rad']and p['scale']==[1,1,1]for p in ps),source_native_bottoms_shifted=all(abs(p['native_bottom_y_m']-sourceps[p['id']]['native_bottom_y_m']-delta)<1e-10 for p in ps),native_masks_unchanged=all(all(p[k]==sourceps[p['id']][k]for k in('native_foundation_polygons_xz_m','native_walking_obstacles_xz_m'))for p in ps),all_actual_doors_at_new_native_threshold=all(abs(d['actual_door_xyz_m'][1]-new)<1e-9 for d in doors),all_internal_routes_at_new_floor=all(abs(r['floor_y_m']-new)<1e-9 and all(abs(v[1]-new)<1e-9 for v in r['polyline_xyz_m'])for r in routes),prepared_bearing_and_native_bottoms_consistent=all(abs(r['floor_y_m']-new)<1e-9 and abs(r['floor_y_m']-r['native_bottom_y_m']-r['embedded_depth_m'])<1e-9 for r in bearings),new_floor_inside_required_core_interval=hid not in changes or ch['required_core_interval_m'][0]-1e-7<=new<=ch['required_core_interval_m'][1]+1e-7,source_public_evidence_unchanged=holding.get('public_target_evidence')==old.get('public_target_evidence'))
  if not all(check.values()):raise ValueError((hid,check))
  record=dict(holding_id=hid,old_floor_y_m=old['floor_y_m'],new_floor_y_m=new,rigid_y_delta_m=delta,required_core_allowed_floor_interval_m=ch.get('required_core_interval_m'),source_bindings=refs[bid],replacement_native_placements=ps,replacement_actual_doors=doors,replacement_door_routes=routes,replacement_terrain_parcel=parcel,replacement_holding_ground=ground,replacement_holding=holding,replacement_court_route_chain=chain,replacement_native_earth_bearings=bearings,unchanged_public_source_evidence=old.get('public_target_evidence'),checks=check,passed=True,status='RIGID_REBIND'if hid in changes else'UNCHANGED_REQUIRED_NEIGHBOR')
  records.append(record);allps+=ps;alldoors+=doors;allroutes+=routes;allbearings+=bearings;retire.update(parcel['retired_source_ids'])
  for p in ps:assets[p['asset_key']]=src['pack']['assets'][p['asset_key']]
 # Verify exact cache bottoms, height and threshold transformations after rebind.
 local={};cache={}
 for key,asset in assets.items():
  path=g.ROOT/asset['render_path'];assert g.ref(path)['sha256']==asset['render_sha256'];cache[key]=g.load(path);bb=asset.get('bounds',cache[key]['bounds']);local[key]=slab_rectangles(cache[key],bb['min'][1]+.001,bb['max'][1]-.001)
 for p in allps:
  lo=cache[p['asset_key']]['bounds']['min'][1]+p['position_m'][1];metadata_checks.append(dict(id=p['id'],exact_cache_bottom_y_m=lo,rebound_bottom_y_m=p['native_bottom_y_m'],passes=abs(lo-p['native_bottom_y_m'])<1e-9))
 assert all(r['passes']for r in metadata_checks)
 # Actual retained scene plus the separate private23 source batch are checked.
 # Original selected old bodies and their exact foundation proxies are removed
 # only hypothetically here; the final R17 owner batch performs the retirement.
 scene=g.load(SCENE);ready=g.load(a.HERE/'contour_bulk_r01/ready_subset_contract_r01.json');first23=require(ready['native_pack']);excluded=retire|set(first23.get('replaced_placement_ids',first23.get('retired_source_ids',[])));print('first23keys',list(first23),'exclude',len(excluded),flush=True)
 sc=dict(scene);sc['common_instances']=[p for p in scene['common_instances']if p['id']not in excluded];sc['boxes']=[p for p in scene['boxes']if p['id']not in{i+':owned_foundation'for i in excluded}];sc['common_assets']=dict(scene['common_assets'])
 for key,v in first23['assets'].items():
  if key in sc['common_assets']:assert sc['common_assets'][key]['render_sha256']==v['render_sha256']
  sc['common_assets'][key]=v
 sc['common_instances']+=first23['placements'];ni=ActualNative(sc);candidates=[]
 for p in allps:
  full=[transform(q,p)for q in local[p['asset_key']]];bb=cache[p['asset_key']]['bounds'];hits=ni.hit(full,p['position_m'][1]+bb['min'][1]+1e-5,p['position_m'][1]+bb['max'][1]-1e-5)
  if hits:candidates.append(dict(id=p['id'],holding_id=p['holding_id'],contacts=hits))
 # This is a conservative whole-height collision screen. Any reported candidate
 # must receive an exact per-height native-volume check before physical release.
 g.write(OUT/'native_rebind_audit.json',dict(request=g.ref(REQUEST),base_actual_scene=g.ref(SCENE),private23=ready['native_pack'],checks=dict(all_per_holding_rigid_checks=all(r['passed']for r in records),all_exact_cache_bottoms_match=all(r['passes']for r in metadata_checks),all_cache_bytes_unchanged=True,no_retained_native_vertical_projection_candidates=not candidates),native_bottom_records=metadata_checks,retained_native_collision_candidates=candidates,hypothetically_retired_ids=sorted(excluded),status='PASSED_SOURCE_REBIND_COLLISION_SCREEN'if not candidates else'EXACT_VERTICAL_CONTACT_REVIEW_REQUIRED',limits=['Expected native support is the R17 coherent court/earth plane, not the superseded raw private pad elevation. Actual composed bearing and outer sides remain R17 gates.','Internal same-holding relationships remain rigid and preserve their existing local native and route clearance. Cross-holding source XY masks remain unchanged.']))
 out=dict(schema='riverstone.district_fabric.atomic_court_datum_batch.v1',base_scene=g.ref(g.R7),base_actual_native_scene=g.ref(SCENE),request=g.ref(REQUEST),source_layout=request['source_layout'],source_prepared_parcels=request['source_prepared_parcels'],effective_city_manifest=g.ref(SOURCE/'effective_city_manifest_r01.json'),records=records,datum_changes=request['datum_changes'],rebound_holding_ids=request['proposed_rebound_holding_ids'],unchanged_required_neighbor_ids=request['unchanged_newly_unlocked_holding_ids'],matched_next_batch_holding_ids=sorted(ids),assets=assets,placements=allps,actual_doors=alldoors,door_routes=allroutes,native_earth_bearings=allbearings,retired_source_ids=sorted(retire),retired_foundation_proxy_ids=[i+':owned_foundation'for i in sorted(retire)],retirement_records=[retrows[i]for i in sorted(retire)],native_audit=g.ref(OUT/'native_rebind_audit.json'),summary=dict(matched_holdings=len(ids),requested_rigid_records=len(changes),nonzero_native_datum_changes=sum(abs(x['delta_y_m'])>1e-12 for x in changes.values()),unchanged_neighbor_holdings=2,native_placements=len(allps),actual_doors=len(alldoors),internal_routes=len(allroutes),native_bearing_regions=len(allbearings),selected_old_native_retirements=len(retire),new_compilations=0,vertical_collision_candidates=len(candidates),seconds=time.monotonic()-started),status='ATOMIC_SOURCE_REBIND_READY_FOR_R17_COMPOSITION'if not candidates else'ATOMIC_REBIND_HELD_FOR_EXACT_NATIVE_CONTACT_REVIEW',integration_policy=['Apply every replacement record by exact holding/native/door/route ID as one batch. Do not change original source packs or cache bytes.','Only the per-holding world Y values change. Existing XZ masks, scales, cache geometry, palettes, semantic role and original public evidence stay fixed.','R17 owns the matched finite external/shared route profiles and support/outer-side composition. B010 C006 alone uses its explicitly approved local 15% profile; no other grade limit changes.','Keep the separate private23 and all other held source records unchanged.'],implementation_tier='exterior_only',new_compilations=0);g.write(OUT/'atomic_datum_addendum.json',out);print(out['summary'],flush=True);print(g.ref(OUT/'atomic_datum_addendum.json'),flush=True)
if __name__=='__main__':run()
