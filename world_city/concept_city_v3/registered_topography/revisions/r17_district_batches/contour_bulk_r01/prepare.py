"""Prepare one hash-bound contour ownership batch; no terrain is activated here."""
import json,time,collections
from .screen import HERE,BULK,write
from .. import author as a,native_clearance,public_tails

def run():
 start=time.monotonic();bulk=json.loads(BULK.read_bytes());scene=a.load_scene();assets={};refs=[];layouts=[];parcels=[];packs=[];proposals=[]
 for d in bulk['districts']:
  hand=native_clearance.require_ref(d['terrain']);proposal=native_clearance.require_ref(d['ground_proposal']);layout=native_clearance.require_ref(proposal['layout']);pack=native_clearance.require_ref(d['pack']);local=native_clearance.require_ref(layout['native_local']);layouts.append(layout);parcels.extend(hand['parcels']);packs.append(pack);proposals.append(proposal)
  refs.extend([d['terrain'],d['ground_proposal'],d['pack'],proposal['layout'],layout['native_local'],hand['access'],hand['court_equipment']])
  for key,value in local['assets'].items():
   if key in assets and a.canonical_sha(value)!=a.canonical_sha(assets[key]):raise ValueError('Conflicting native asset '+key)
   assets[key]=value
 write('combined_native_local.json',dict(schema='riverstone.r17.contour_native_reference_union.v1',assets=assets,source_references=list({r['path']:r for r in refs}.values())))
 combined={k:[r for l in layouts for r in l[k]]for k in('placements','actual_doors','retirement_records','holdings','shared_private_routes')};combined['retired_source_ids']=sorted(set(x for l in layouts for x in l['retired_source_ids']));combined['native_local']=dict(path=str((HERE/'combined_native_local.json').relative_to(a.ROOT)),sha256=a.sha(HERE/'combined_native_local.json'));combined.update(schema='riverstone.r17.contour_combined_layout.v1',base_scene_sha256=a.SCENE_SHA256,source_references=list({r['path']:r for r in refs}.values()),activation=False)
 for key in('placements','actual_doors','holdings'):
  ids=[r['id']for r in combined[key]]
  if len(ids)!=len(set(ids)):raise ValueError('Duplicate '+key)
 write('combined_source_layout.json',combined);native=native_clearance.check(combined);write('native_source_preflight.json',native);print('native',native['summary'],flush=True)
 water=[r['polygon_xz_m']for r in scene['terrain_contract']['water_domain_polygons']];wi=a.geo._SpatialIndex(16)
 for i,p in enumerate(water):wi.add(i,p)
 plan=json.loads(a.PLAN_PATH.read_bytes());traffic=[];ti=a.geo._SpatialIndex(16)
 for r in plan['roads']:
  for p in[a.geo.road_ribbon(u,v,r['width_m'])for u,v in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])]+[public_tails.circle(q,r['width_m']/2)for q in r['polyline_xz_m'][1:-1]]:ti.add(len(traffic),p);traffic.append(dict(road_id=r['id'],polygon_xz_m=p))
 owners=[];wet=[];foot_traffic=[];support=[]
 for parcel in parcels:
  hid=parcel['id'];floor=parcel['floor_y_m']
  for j,p in enumerate(parcel['whole_holding_polygons_xz_m']):owners.append(dict(id=hid+':GROUND:'+str(j),holding_id=hid,kind='coherent_holding',polygon_xz_m=p,plane_y_xz_m=[0,0,floor],material='ground_earth'))
  for j,p in enumerate(parcel['footing_polygons_xz_m']):
   owners.append(dict(id=hid+':NATIVE:'+str(j),holding_id=hid,kind='native_footing',action='hole',polygon_xz_m=p))
   for i in ti.candidates(p):
    q=a.clip(p,traffic[i]['polygon_xz_m'])
    if q and(a0:=a.geo.polygon_area(q))>1e-7:foot_traffic.append(dict(holding_id=hid,footing_index=j,public_road_id=traffic[i]['road_id'],area_m2=a0,polygon_xz_m=q))
  for n in parcel['native_footing_owners']:
   for j,p in enumerate(n['polygons_xz_m']):
    gap=sum(a.geo.polygon_area(q)for q in a.common.subtract([p],parcel['whole_holding_polygons_xz_m']));support.append(dict(id=n['id']+':'+str(j),holding_id=hid,polygon_xz_m=p,floor_y_m=floor,native_bottom_y_m=n['native_bottom_y_m'],embedded_depth_m=floor-n['native_bottom_y_m'],outside_logical_earth_owner_m2=gap))
  for kind in('footing_polygons_xz_m','court_polygons_xz_m','walk_polygons_xz_m','whole_holding_polygons_xz_m'):
   for j,p in enumerate(parcel[kind]):
    for i in wi.candidates(p):
     q=a.clip(p,water[i])
     if q and(a0:=a.geo.polygon_area(q))>1e-7:wet.append(dict(holding_id=hid,kind=kind,polygon_index=j,water_index=i,area_m2=a0,polygon_xz_m=q))
 retirement=[];active={r['id']:r for r in scene['common_instances']};boxes={r['id']:r for r in scene['boxes']};seen={}
 for r in combined['retirement_records']:
  sid=r['source_id'];digest=a.canonical_sha(r)
  if sid in seen:
   if seen[sid]!=digest:raise ValueError('Conflicting retirement '+sid)
   continue
  seen[sid]=digest
  if sid not in active or sid+':owned_foundation'not in boxes:raise ValueError('Missing retired source '+sid)
  if a.canonical_sha(active[sid])!=a.canonical_sha(r['source_instance']):raise ValueError('Stale retired source '+sid)
  deps=[h['id']for h in combined['holdings']if sid in h['retired_source_ids']]
  retirement.append(dict(source_id=sid,affected_holding_ids=deps,source_instance=r['source_instance'],removed_foundation_proxy_id=sid+':owned_foundation',old_body_polygon_xz_m=r['old_terrain_body_hole_polygon_xz_m'],old_finished_floor_y_m=r['existing_finished_floor_y_m'],retired_path_ids=[p['id']for p in r['old_source_paths']],retired_actual_door_ids=[p['id']for p in r['actual_old_access_records']],source_record=r,policy='Retire only if every affected holding is activated. Restore exact old body residual outside accepted coherent ground and new native holes; preserve inherited residual top with explicit nonwalking side closure.'))
 report=dict(schema='riverstone.r17.contour_prepared_ownership.v1',base_scene_sha256=a.SCENE_SHA256,source_bulk=dict(path=str(BULK.relative_to(a.ROOT)),sha256=a.sha(BULK)),source_references=combined['source_references'],parcels=parcels,logical_owners=owners,native_earth_bearings=support,retirement_records=retirement,wet_conflicts=wet,footing_traffic_conflicts=foot_traffic,summary=dict(districts=len(layouts),holdings=len(parcels),native_ranges=len(combined['placements']),actual_doors=len(combined['actual_doors']),retired_ids=len(retirement),logical_owners=len(owners),native_bearings=len(support),native_bearing_owner_gaps=sum(r['outside_logical_earth_owner_m2']>1e-7 for r in support),native_bearing_negative_embed=sum(r['embedded_depth_m']< -1e-7 for r in support),wet_conflicts=len(wet),native_traffic_conflicts=len(foot_traffic),elapsed_s=time.monotonic()-start),status='PREPARED_PENDING_SHARED_PUBLIC_PROFILES_AND_EMITTED_SIDE_AUDIT',activation=False)
 write('prepared_ownership.json',report);print(report['summary'],flush=True)
if __name__=='__main__':run()
