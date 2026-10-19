"""Route-first finite native holding placement; no scene mutation."""
from .geometry import *
from .prepare import PLAN,TERR
GRAMMAR={'CRAFT_U_30_28':'district_r01_craft_U','DOMESTIC_L_24_25':'district_r01_domestic_L','COMPACT_L_17_22':'district_r01_compact_L'}

def inside(p,holding):return abs(geo.intersection_area(p,holding)-geo.polygon_area(p))<1e-6

def run():
 source=load(PLAN/'block_015_route_parcels.json');native=load(HERE/'native_local.json')['assets'];m=np.load(HERE/'planning_masks.npz');retire=load(HERE/'input.json')['restorable_candidates'];special=raster(source['special_reserved_polygon_parts_xz_m'],True);protected=m['protected']|special|m['nonmatching_native'];accepted=[];reject=[];placements=[];doors=[];retired=set();used=np.zeros(SHAPE,bool)
 safe_ids={r['source_id']for r in load(TERR/'retired_body_boundary_audit.json')['rows']if r['status']=='COMPLETE_LEVEL_BODY_BOUNDARY'}
 # The full route system is reserved by the planner before any native placement.
 for h in source['holdings']:
  hid=h['id'];origin=h['origin_xz_m'];yaw=h['yaw_rad'];holding=h['holding_polygon_xz_m'];hm=raster([holding]);key=GRAMMAR.get(h['grammar_id'],'district_r01_compact_L');choice=None;attempts=[]
  keys=list(dict.fromkeys([key,'district_r01_compact_L']))
  for key in keys:
   n=native[key]
   for dx,dz in sorted(((x,z)for x in range(-7,8)for z in range(-7,8)),key=lambda q:(q[0]**2+q[1]**2,q)):
    center=xform([dx,dz],origin,yaw);foot=transform(n['foundation_local_polygons_xz_m'],center,yaw);roof=transform(n['roof_local_polygons_xz_m'],center,yaw);walking=transform(n['walking_local_polygons_xz_m'],center,yaw);court=transform([n['court_local_polygon_xz_m']],center,yaw);check=foot+court
    if not all(inside(p,holding)for p in roof+court):continue
    rm=raster(roof,True);cm=raster(check,True)
    if np.any(rm&(protected|used)):continue
    for floor in(2.5,1.):
     band=m['floor_'+str(floor).replace('.','_')];bad=area(cm&~band);attempts.append(dict(key=key,offset=[dx,dz],floor=floor,off_band_m2=bad))
     if bad<=1e-8:choice=(key,n,center,foot,roof,walking,court,floor);break
    if choice:break
   if choice:break
  if not choice:reject.append(dict(holding_id=hid,reason='No whole native footing plus usable court fits exact flat-band/restorable-hole planning domain within holding',best=sorted(attempts,key=lambda x:x['off_band_m2'])[:3]));continue
  key,n,center,foot,roof,walking,court,floor=choice;pid=hid+':ATTACHED_FABRIC';palette=n['asset']['native_metadata']['palette'];p=dict(id=pid,holding_id=hid,block_id='BLOCK_015',asset_key=key,position_m=[center[0],floor-.5,center[1]],yaw_rad=yaw,scale=[1,1,1],finished_floor_y_m=floor,palette_id=palette,source_pack='district_fabric_r01',native_foundation_polygons_xz_m=foot,native_walking_obstacles_xz_m=walking,native_roof_polygons_xz_m=roof,actual_door_ids=[],roof_area_m2=n['roof_area_m2'],foundation_area_m2=n['foundation_area_m2'],source_holding_id=hid,role=h['role'],activation_status='source_candidate_exact_terrain_and_full_route_review_pending')
  for d0 in n['doors']:
   d=copy.deepcopy(d0);q=d['actual_local_xyz_m'];wxz=xform([q[0],q[2]],center,yaw);out=xform(d['outward_local_xz'],[0,0],yaw);d.update(id=pid+':'+d['id'],parcel_id=pid,holding_id=hid,actual_door_xyz_m=[wxz[0],floor-.5+q[1],wxz[1]],outward_xz=out,threshold_lip_xz_m=xform(d['threshold_lip_local_xz_m'],center,yaw),render_sha256=n['asset']['render_sha256']);doors.append(d);p['actual_door_ids'].append(d['id'])
  owners=[]
  for old in retire:
   if old['matching_level_band_y_m']!=floor or old['source_id']not in safe_ids:continue
   if geo.intersection_area(old['actual_native_outer_footprint_xz_m'],holding)>1e-7:owners.append(old['source_id']);retired.add(old['source_id'])
  accepted.append(dict(source_holding=h,id=hid,parcel_id=pid,floor_y_m=floor,holding_polygon_xz_m=holding,core_court_polygons_xz_m=court,gate_position_xz_m=h['gate_position_xz_m'],external_route=h['street_connection_polyline_xz_m'],external_width_m=h['gate_width_m'],retired_source_ids=owners,native_roof_area_m2=n['roof_area_m2'],holding_area_m2=geo.polygon_area(holding)));placements.append(p);used|=raster(roof,True)
 d=dict(schema='riverstone.district_fabric.selected_layout.v1',source_plan=ref(PLAN/'block_015_route_parcels.json'),native_local=ref(HERE/'native_local.json'),planning_masks=ref(HERE/'planning_masks.npz'),holdings=accepted,placements=placements,actual_doors=doors,rejected_holding_candidates=reject,retired_source_ids=sorted(retired),retirement_records=[r for r in retire if r['source_id']in retired],summary=dict(holdings=len(accepted),source_candidates=len(source['holdings']),native_roof_m2=sum(p['roof_area_m2']for p in placements),holding_area_m2=sum(h['holding_area_m2']for h in accepted),actual_exterior_doors=len(doors),retired_ordinary_instances=len(retired),unaccepted_candidates=len(reject)),scope='Whole-district route-first candidate; isolated failed slots remain explicit, not reported complete.');write(HERE/'selected_layout.json',d);print(json.dumps(d['summary'],indent=2));print(json.dumps(reject,indent=2)[:4000]);return d
if __name__=='__main__':run()
