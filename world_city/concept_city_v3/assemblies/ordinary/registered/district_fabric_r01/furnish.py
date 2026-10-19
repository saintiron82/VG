"""Real private boundaries and purposeful court equipment, reused native cache."""
from .geometry import *
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import author as terrain_common

def run():
 layout=load(HERE/'selected_layout.json');access=load(HERE/'access_handoff.json');scene=load(R7);assets={};native={};assetkeys=['domestic_wash_barrel','drying_frame','workbench','b13_workyard_wood_stack','productive_bed']
 for key in assetkeys:
  assets[key]=scene['common_assets'][key]
 assets['district_r01_boundary_2m']=load(HERE/'compile_report.json')['assets']['district_r01_boundary_2m']
 for key,a in assets.items():
  r=load(ROOT/a['render_path']);lo=a['bounds']['min'][1];native[key]=dict(foot=slab_rectangles(r,lo+.001,lo+min(.124,a.get('pitch_m',.125)-.001)),walk=slab_rectangles(r,.01,3))
 route_polys=[p for r in access['routes']for p in r['polygons_xz_m']]+[p for h in layout['holdings']for p in h['external_route_polygons_xz_m']]+[p for r in layout['shared_private_routes']for p in r['polygons_xz_m']]
 route_mask=raster(route_polys,True);roof_polys=[p for b in layout['placements']for p in b['native_roof_polygons_xz_m']];roof_mask=raster(roof_polys,True);reserved=np.zeros(SHAPE,bool);fixtures=[];grounds=[];skipped=[];built={p['holding_id']:p for p in layout['placements']}
 def place(id,key,h,center,yaw,role):
  a=assets[key];foot=transform(native[key]['foot'],center,yaw);walk=transform(native[key]['walk'],center,yaw)
  p=dict(id=id,asset_key=key,holding_id=h['id'],position_m=[center[0],h['floor_y_m'],center[1]],yaw_rad=yaw,scale=[1,1,1],finished_floor_y_m=h['floor_y_m'],native_bottom_y_m=h['floor_y_m']+a['bounds']['min'][1],native_foundation_polygons_xz_m=foot,native_walking_obstacles_xz_m=walk,palette_id='native_court_timber_and_stone',palette_override={},source_pack='district_fabric_courts_r01',role=role,implementation_tier='exterior_only');fixtures.append(p);return p
 for h in layout['holdings']:
  b=built[h['id']];yaw=b['yaw_rad'];center=[b['position_m'][0],b['position_m'][2]];domestic=('domestic' in b['asset_key']or'market_lodging'in b['asset_key']or'compact'in b['asset_key']);court=h['core_court_polygons_xz_m'][0];local=[xform([p[0]-center[0],p[1]-center[1]],[0,0],-yaw)for p in court];x0,z0=min(p[0]for p in local),min(p[1]for p in local);x1,z1=max(p[0]for p in local),max(p[1]for p in local)
  needs=[('domestic_wash_barrel','shared_hand_filled_wash_and_water_storage'),('drying_frame','shared_linen_drying')]if domestic else[('workbench','craft_repair_workbench'),('b13_workyard_wood_stack','dry_timber_and_fuel_store')]
  placed=[]
  for j,(key,role)in enumerate(needs):
   a=assets[key];candidates=[(x,z)for x in np.arange(x0+1,x1,1)for z in np.arange(z0+1,z1,1)];candidates.sort(key=lambda q:((q[0]-x0)**2+(q[1]-z1)**2,q));found=None
   for x,z in candidates:
    c=xform([float(x),float(z)],center,yaw);poly=transform([local_box(a,.4)],c,yaw)[0]
    if abs(geo.intersection_area(poly,court)-geo.polygon_area(poly))>1e-6:continue
    rm=raster([poly],True)
    if np.any(rm&(route_mask|roof_mask|reserved)):continue
    found=c;reserved|=rm;break
   if found:placed.append(place(h['id']+':COURT:'+str(j+1),key,h,found,yaw,role)['id'])
   else:skipped.append(dict(holding_id=h['id'],equipment=key,reason='Preserve all actual door approaches and useful work space; no isolated or obstructive prop placement.'))
  # Tight parcel edge enclosure: omit every segment touching buildings or any
  # full access ribbon. The omissions are real open gate intervals, not leaves.
  boundary_count=0;hp=h['holding_polygon_xz_m'];gate_gaps=[]
  for edge,(a,bp)in enumerate(zip(hp,hp[1:]+hp[:1])):
   length=math.dist(a,bp);ux,uz=(bp[0]-a[0])/length,(bp[1]-a[1])/length;ryaw=math.atan2(-uz,ux);n=max(0,int((length-.5)/2));start=(length-n*2)/2
   for j in range(n):
    sign=1 if geo.signed_polygon_area(hp)>0 else -1;c=[a[0]+ux*(start+j*2+1)-uz*.35*sign,a[1]+uz*(start+j*2+1)+ux*.35*sign];poly=transform([local_box(assets['district_r01_boundary_2m'],.15)],c,ryaw)[0];rm=raster([poly],True)
    if np.any(rm&(route_mask|roof_mask|reserved)):gate_gaps.append(dict(edge=edge,start_m=start+j*2,end_m=start+(j+1)*2,reason='native frontage or full-width access clearance'));continue
    place(h['id']+f':BOUNDARY:{edge}:{j:02}','district_r01_boundary_2m',h,c,ryaw,'low_private_parcel_boundary');boundary_count+=1;reserved|=rm
  own=[p for p in fixtures if p['holding_id']==h['id']];holes=b['native_foundation_polygons_xz_m']+[q for p in own for q in p['native_foundation_polygons_xz_m']];ground=terrain_common.subtract([hp],holes)
  grounds.append(dict(id=h['id']+':GROUND',holding_id=h['id'],finished_floor_y_m=h['floor_y_m'],polygon_parts_xz_m=ground,original_holding_polygon_xz_m=hp,native_hole_polygons_xz_m=holes,base_material='ground_earth',court_material='ground_stone'if not domestic else'ground_earth',core_court_polygons_xz_m=h['core_court_polygons_xz_m'],purpose='Shared domestic washing, drying and household repair court'if domestic else'Craft assembly, dry-goods sorting and manual repair court',equipment_placement_ids=placed,boundary_segments=boundary_count,open_boundary_intervals=gate_gaps,remaining_ground_use='Private threshold apron, fuel-handling space and usable shared circulation; preserve all native door widths.',implementation_tier='exterior_only',limits=['No simulated commerce, water supply, drainage or open interior claim.','Material regions retain exact old ground planes; no native paving plate or raised full-block platform.']))
 out=dict(schema='riverstone.district_fabric.court_equipment.v1',layout=ref(HERE/'selected_layout.json'),access=ref(HERE/'access_handoff.json'),assets=assets,placements=fixtures,holding_grounds=grounds,omitted_equipment=skipped,summary=dict(holdings=len(grounds),native_equipment=sum(p['role']!='low_private_parcel_boundary'for p in fixtures),native_boundary_segments=sum(p['role']=='low_private_parcel_boundary'for p in fixtures),deliberate_open_boundary_intervals=sum(len(g['open_boundary_intervals'])for g in grounds),native_new_compiles=0));write(HERE/'court_equipment.json',out);print(json.dumps(out['summary'],indent=2));return out
if __name__=='__main__':run()
