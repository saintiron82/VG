"""Bind complete enclosure deferrals and exact native-bearing replacements."""
from . import geometry as g
from .activate_backlands_subset import MaskIndex
from .rebind_coherent_datums import shift
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from collections import Counter
import copy,time

OUT=g.HERE/'final_source_preparation_r02'
INPUTS=['hard_core_native_refit_r02','hard_core_native_refit_r03','hard_core_native_refit_r05','hard_core_native_refit_r08','paired_contour_entry_refit_r02','paired_contour_entry_refit_r05','b08_flat_core_refit_r01']
def area(ps):return sum(g.geo.polygon_area(p)for p in ps)
def run():
 start=time.monotonic();OUT.mkdir(exist_ok=True);inputs=[g.HERE/p/'source_candidates.json'for p in INPUTS];selected={r['holding_id']:(r,p)for p in inputs for r in g.load(p)['records']};mfpath=g.HERE/'effective_city_manifest_r01.json';mf=g.load(mfpath);bpp=g.HERE/'b07_terrace_refit_r02/BLOCK_007/resolved_placements.json';bp=g.load(bpp);original=mf['placements']+bp['placements'];result=[];stats=Counter()
 for hid,(r,path)in sorted(selected.items()):
  assert all(r['checks'][k]for k in ['all_doors_have_native_clear_flat_links','native_roofs_inside_holding','current_floor_within_core_interval'])
  n=g.load(g.ROOT/r['native_local']['path'])['assets'];ps=copy.deepcopy(r['replacement_native_placements']);original_ps=[p for p in original if p.get('holding_id')==hid];oldboundary=[p for p in original_ps if ':BOUNDARY:'in p['id']];extras=[p for p in original_ps if ':BOUNDARY:'not in p['id']and ':FABRIC:'not in p['id']];flat=r['flat_owner_polygons_xz_m'];checks=[];keep=[];defer=[];newobs=[q for p in ps for q in p['native_walking_obstacles_xz_m']];entry=r['profile_domain_polygons_xz_m'];mi=MaskIndex([dict(id='NEW_NATIVE',polygon_xz_m=p)for p in newobs]+[dict(id='PROFILE_ENTRY',polygon_xz_m=p)for p in entry]+[dict(id='DOOR_LINK',polygon_xz_m=p)for link in r['replacement_door_routes']for p in link['polygons_xz_m']])
  for p in oldboundary+extras:
   missing=area(a.common.subtract(p['native_foundation_polygons_xz_m'],flat));hits=mi.hit(p['native_walking_obstacles_xz_m']);checks.append(dict(id=p['id'],footing_outside_flat_union_m2=missing,clearance_contacts=hits,individually_supported_and_clear=missing<1e-7 and not hits))
  # A partly supported old perimeter is a held complete enclosure, never a
  # scattered selection of panels around a plot described as closed.
  bchecks=[q for q in checks if ':BOUNDARY:'in q['id']];complete=bool(bchecks)and all(q['individually_supported_and_clear']for q in bchecks)
  if complete:keep+=oldboundary
  else:defer+=[dict(id=p['id'],asset_key=p['asset_key'],reason='ENTIRE_UNACTIVATED_ENCLOSURE_HELD: revised flat/profile/margin partition or gate no longer supports the complete old perimeter.',original_placement=p)for p in oldboundary]
  for p in extras:
   test=next(q for q in checks if q['id']==p['id'])
   if test['individually_supported_and_clear']:keep.append(p)
   else:defer.append(dict(id=p['id'],asset_key=p['asset_key'],reason='UNACTIVATED_FIXTURE_OUTSIDE_FLAT_SUPPORT_OR_NEW_NATIVE_ENTRY_CLEARANCE',original_placement=p))
  floor=r['floor_y_m'];oldfloor=original_ps[0]['finished_floor_y_m'];keep=shift(keep,floor-oldfloor);ps+=keep;bearings=[];footowners=[];assets={}
  for p in ps:
   ass=n[p['asset_key']]['asset']if p['asset_key']in n else(mf['assets'].get(p['asset_key'])or bp['assets'][p['asset_key']]);assets[p['asset_key']]=ass;bb=ass.get('bounds')or g.load(g.ROOT/ass['render_path'])['bounds'];p['native_bottom_y_m']=p['position_m'][1]+bb['min'][1]
   footowners.append(dict(id=p['id'],asset_key=p['asset_key'],render_sha256=ass['render_sha256'],position_m=p['position_m'],yaw_rad=p['yaw_rad'],scale=[1,1,1],native_bottom_y_m=p['native_bottom_y_m'],polygons_xz_m=p['native_foundation_polygons_xz_m']))
   for i,q in enumerate(p['native_foundation_polygons_xz_m']):bearings.append(dict(id=p['id']+f':{i}',holding_id=hid,polygon_xz_m=q,floor_y_m=floor,native_bottom_y_m=p['native_bottom_y_m'],embedded_depth_m=floor-p['native_bottom_y_m'],outside_logical_earth_owner_m2=area(a.common.subtract([q],flat))))
  allfeet=[q for p in ps for q in p['native_foundation_polygons_xz_m']];ground=a.common.subtract(flat,allfeet);h=copy.deepcopy(r['replacement_holding']);h['boundary_status']='COMPLETE_SOURCE_PERIMETER_RETAINED'if complete else'COMPLETE_OLD_SOURCE_ENCLOSURE_HELD; REVISED_HOLDING_INTENTIONALLY_OPEN';h['active_boundary_placement_ids']=[p['id']for p in keep if ':BOUNDARY:'in p['id']];h['held_boundary_placement_ids']=[p['id']for p in oldboundary]if not complete else[]
  row=dict(holding_id=hid,selected_candidate=g.ref(path),candidate_index=r['candidate_index'],replacement_holding=h,replacement_native_placements=ps,replacement_actual_doors=r['replacement_actual_doors'],replacement_door_routes=r['replacement_door_routes'],replacement_native_earth_bearings=bearings,native_footing_owners=footowners,flat_visible_ground_polygons_xz_m=ground,assets=assets,original_source_placement_ids=[p['id']for p in original_ps],superseded_unactivated_source_native_ids=[p['id']for p in original_ps if ':FABRIC:'in p['id']],explicit_deferred_source_placements=defer,boundary_and_fixture_checks=checks,boundary_continuity_policy=h['boundary_status'],all_native_bearings_inside_flat_union=all(x['outside_logical_earth_owner_m2']<1e-7 for x in bearings),status='READY_NATIVE_OWNER_REPLACEMENTS_PENDING_FINAL_PROFILE_MANIFEST')
  assert row['all_native_bearings_inside_flat_union'];result.append(row);stats.update(dict(holdings=1,new_native_placements=len(ps),actual_doors=len(r['replacement_actual_doors']),held_complete_enclosures=bool(oldboundary)and not complete,retained_complete_enclosures=complete,deferred_source_boundary_panels=len(oldboundary)if not complete else 0,deferred_source_other_fixtures=sum(':BOUNDARY:'not in p['id']for p in defer)))
 report=dict(schema='riverstone.final_refit.native_owner_preparation.v1',source_candidates=[g.ref(p)for p in inputs],effective_manifest=g.ref(mfpath),B07_pack=g.ref(bpp),author=g.ref(__file__),records=result,summary=dict(stats,seconds=time.monotonic()-start),activation='NO_SCENE_ACTIVATION. Every selected profile and final datum must be bound by the final matched district request. Source boundary deferrals are atomic per enclosure; none retires an active scene instance.');g.write(OUT/'native_owner_replacements.json',report);print(report['summary'],flush=True);print(g.ref(OUT/'native_owner_replacements.json'),flush=True)
if __name__=='__main__':run()
