"""Finite functional holdings and native-dimension parcel candidates. No compilation."""
from prepare import *
from scipy import ndimage

def frame(cx,cz,w,d,yaw=0):
 a=math.radians(yaw);c=math.cos(a);s=math.sin(a)
 return [[cx+c*x+s*z,cz-s*x+c*z]for x,z in [(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]]
def rects(a):
 # Exact disjoint rectangles of this planning raster, not cache bounds.
 out=[];active={}
 for z,row in enumerate(a):
  edges=np.flatnonzero(np.diff(np.r_[False,row,False]));runs=list(zip(edges[::2],edges[1::2]));new={}
  for run in runs:new[run]=active.pop(run,z)
  for (x0,x1),z0 in active.items():out.append(rect(BOUNDS[0]+x0*PITCH,BOUNDS[1]+z0*PITCH,BOUNDS[0]+x1*PITCH,BOUNDS[1]+z*PITCH))
  active=new
 for (x0,x1),z0 in active.items():out.append(rect(BOUNDS[0]+x0*PITCH,BOUNDS[1]+z0*PITCH,BOUNDS[0]+x1*PITCH,BOUNDS[1]+SHAPE[0]*PITCH))
 return out

def spec(id,site,role,box,building=None,n=0,yaw=0,why='',priority=2):
 return dict(id=id,site_id=site,function=role,requested_frame_xz_m=rect(*box),native_range_dimensions_m=building,maximum_range_parcels=n,range_yaw_degrees=yaw,adjacency_rationale=why,review_priority=priority)
REQ=[
 spec('B15_MARKET_LODGING','BLOCK_015','dense_court_housing',(125,116,205,168),(24,9),3,-48,'Lower market adjacency supports short attached lodging and craft courts, with rear work space.',1),
 spec('B15_UPPER_BANK_WORK','BLOCK_015','canal_workyard',(165,145,295,213),(30,10),3,-48,'Visible industrial water spine and low workshop roofs; exact craft is inferred.',1),
 spec('B15_MIDDLE_BANK_WORK','BLOCK_015','canal_workyard',(192,213,311,276),(30,10),3,-48,'Contiguous dry work compounds beside the industrial canal, with a clear tow/service edge.',1),
 spec('B15_WEST_REAR_COURTS','BLOCK_015','dense_court_housing',(109,218,209,325),(24,9),4,-48,'Rear courts behind poorer attached frontage. Keep shared pedestrian lanes and household work grounds.',1),
 spec('B15_SOUTH_CRAFT_CLOSE','BLOCK_015','dense_court_housing',(188,277,310,354),(24,9),3,-48,'South gate and port-related small trades; compact rows around intentional shared courts.',1),
 spec('B15_EAST_COOPERS','BLOCK_015','working_compound',(310,154,379,231),(24,10),2,12,'Dry cooper/storage yard behind existing east frontage, no new discharge into the clean-water network.',1),
 spec('B15_EAST_REPAIR','BLOCK_015','working_compound',(310,233,363,307),(24,10),2,12,'Repair sheds, stock and cart-turning yard adjoining existing east service circulation.',2),
 spec('B03_NORTH_ORCHARDS','BLOCK_003','estate_productive_gardens',(-227,-395,-48,-327),None,0,0,'Noble uphill setting in the concept has terraced orchards and walled greens, not continuous urban frontage.'),
 spec('B03_NOBLE_EAST_SERVICE','BLOCK_003','estate_service_compound',(-56,-314,13,-204),(24,10),2,0,'Shared estate maintenance and kitchen-garden edge beside E3/E6, retaining all existing estate ownership.'),
 spec('B03_ESTATE_GARDEN_LINKS','BLOCK_003','estate_productive_gardens',(-226,-327,-52,-72),None,0,0,'Connected garden/service grounds between separately owned noble plots; no new household count inferred.'),
 spec('B03_TRAIN_COMMON_SERVICE','BLOCK_003','working_compound',(-396,-154,-255,-77),(30,10),3,0,'Training yard and public common adjacency calls for supply/stable ranges with enclosed working courts.'),
 spec('B03_UPPER_TRADE_CLOSE','BLOCK_003','dense_court_housing',(-108,-195,-13,-97),(24,9),2,-42,'Selective ordinary service housing on the upper contour beyond noble boundary reservations.'),
 spec('B03_ABBEY_EDGE','BLOCK_003','institutional_edge_garden',(-181,69,-112,199),None,0,0,'A narrow abbey/public-road edge is service planting and retained path ground, not a housing infill target.'),
 spec('B03_PORT_SUPPLY','BLOCK_003','working_compound',(-208,275,-110,327),(24,10),2,-24,'Finite dry supply yards between abbey and quay. Preserve the public wall-service route and port ownership.'),
 spec('B05_NORTH_TERRACES','BLOCK_005','institutional_edge_garden',(45,-401,278,-315),None,0,0,'Northern retaining terraces and waterkeeper/service greens around the cathedral precinct.'),
 spec('B05_UPPER_SERVICE_ROWS','BLOCK_005','dense_court_housing',(60,-315,126,-165),(24,9),3,0,'Limited clergy-client lodging and service rows along the existing north approach, preserving its head and lane.'),
 spec('B05_CATHEDRAL_FRONT_GARDENS','BLOCK_005','institutional_edge_garden',(125,-170,355,-40),None,0,0,'The south cathedral apron is a terraced precinct edge, with existing shops retained; do not convert all into roofs.'),
 spec('B05_EAST_WALL_TERRACES','BLOCK_005','wall_service_garden',(350,-230,436,155),None,0,0,'Continuous wall inspection, drainage and productive terrace strip behind the east street.'),
 spec('B05_SOUTH_WALL_WORK','BLOCK_005','wall_service_garden',(322,155,434,338),None,0,0,'Keep the wall/industrial-drain margin legible and accessible. No extra gate or wall opening is implied.'),
 spec('C_NORTH_CANONS_GARDEN','SITE_CLERGY','institutional_productive',(109,-369,245,-292),None,0,0,'Productive gardens behind the new canons close and adjacent cemetery; existing burial rows remain intact.'),
 spec('C_CHAPTER_GARDEN','SITE_CLERGY','institutional_productive',(193,-308,299,-236),None,0,0,'A coherent chapter/kitchen garden between nave, school and canons close rather than residual lawn.'),
 spec('C_WEST_CEMETERY_EDGE','SITE_CLERGY','cemetery_expansion',(102,-295,173,-190),None,0,0,'Reserved burial expansion and quiet boundary path. Graves need a later approved row recipe, not trees hiding emptiness.'),
 spec('C_SCHOOL_SERVICE','SITE_CLERGY','institutional_workyard',(297,-279,351,-226),(18,8),1,32.3,'School kitchen/fuel service court, dimension-authored small range, with gates to the preserved service route.'),
 spec('C_EAST_MEDICINAL','SITE_CLERGY','institutional_productive',(322,-226,368,-111),None,0,0,'Long medicinal/fruit plots along the east enclosure with a maintenance lane, distinct from procession ground.'),
 spec('C_SOUTH_ORCHARD','SITE_CLERGY','institutional_productive',(231,-166,364,-81),None,0,0,'Continuous southern orchard/kitchen plots join the existing productive enclosures and guest range.'),
 spec('C_PROCESSION_CLOSE','SITE_CLERGY','ceremonial_open_ground',(131,-224,245,-121),None,0,0,'Open processional and guest forecourt is intentional; keep it connected to the recovered approach surface.'),
 spec('A_WEST_BOUNDARY','SITE_MONASTERY','institutional_productive',(-406,-43,-339,83),None,0,0,'Productive nursery and kitchen plots continue the visible western abbey gardens.'),
 spec('A_NORTH_WORK_EXTENSION','SITE_MONASTERY','institutional_workyard',(-340,8,-275,45),(24,10),1,0,'Grain/fuel preparation ground behind the north working range, no duplicate ordinary house pattern.'),
 spec('A_EAST_GUEST_GARDEN','SITE_MONASTERY','institutional_productive',(-241,3,-166,87),None,0,0,'Guest/infirmary garden with a quiet path, retaining the church and cloister silhouette.'),
 spec('A_CLOISTER_PROCESSION','SITE_MONASTERY','ceremonial_open_ground',(-328,80,-233,157),None,0,0,'Preserve the church-to-work-range procession and cart-free cloister setting as useful open ground.'),
 spec('A_WEST_STACK_YARD','SITE_MONASTERY','institutional_workyard',(-358,178,-318,231),(18,8),1,0,'Enclosed dry grain/wood stack yard associated with the existing south service range.'),
 spec('A_SOUTH_KITCHEN_PLOTS','SITE_MONASTERY','institutional_productive',(-318,157,-276,230),None,0,0,'Continuous garden strip between existing orchard and service court, with actual boundary/gate work still required.'),
 spec('A_EAST_ORCHARD_EDGE','SITE_MONASTERY','institutional_productive',(-232,158,-126,264),None,0,0,'Orchard expansion and service edge, keeping the guarded +8 path and old orchard floor.'),
 spec('A_SOUTH_FARM_GROUND','SITE_MONASTERY','institutional_productive',(-264,240,-155,283),None,0,0,'South orchard/vegetable rotation ground behind the service range; no blanket abbey flattening.'),
]

def fit_ranges(a,w,d,yaw,n):
 # Retain true authored dimensions. Greedy fitting uses distance to existing owners;
 # each parcel includes a 1.5 m reserved ring and 3 m separation from the next.
 free=a.copy();out=[];minimum=mask([frame(0,0,w+3,d+3,yaw)],0,False).sum()
 for _ in range(n):
  distance=ndimage.distance_transform_edt(free);found=None
  # Only a bounded, deterministic set of the largest-clearance candidate centers.
  candidates=np.flatnonzero(distance.ravel()>=min(w,d)/PITCH/2)
  candidates=candidates[np.argsort(distance.ravel()[candidates])[::-1]]
  for q in candidates[::max(1,len(candidates)//700)][:700]:
   iz,ix=np.unravel_index(q,SHAPE);cx=BOUNDS[0]+(ix+.5)*PITCH;cz=BOUNDS[1]+(iz+.5)*PITCH;pol=frame(cx,cz,w+3,d+3,yaw);m=mask([pol],2,False)
   if m.any()and np.all(free[m]):found=(cx,cz,m);break
  if found is None:break
  cx,cz,m=found;out.append({'center_xz_m':[cx,cz],'width_m':w,'depth_m':d,'yaw_degrees':yaw,'building_envelope_xz_m':frame(cx,cz,w,d,yaw),'parcel_with_clearance_xz_m':frame(cx,cz,w+3,d+3,yaw),'grammar':'native dimension-authored attached range; individual module widths 6–10 m, no whole-house scaling','status':'source envelope only; no master, cache, terrain platform or actual entrance yet'});free[m]=False
 return out

def main():
 r=np.load(HERE/'review_masks.npz');remaining={k:r[k].copy()for k in ['BLOCK_003','BLOCK_005','BLOCK_015','SITE_CLERGY','SITE_MONASTERY']};zones=[];labels=np.zeros(SHAPE,np.uint8);parcels=[];held=0
 for i,s in enumerate(REQ,1):
  a=remaining[s['site_id']]&mask([s['requested_frame_xz_m']],0,False)
  labs,n=ndimage.label(a);sizes=np.bincount(labs.ravel());components=[];accepted=np.zeros(SHAPE,bool)
  for j in np.argsort(sizes[1:])[::-1]+1:
   if sizes[j]*PITCH**2<120:continue
   comp=labs==j;z,x=np.where(comp);id=s['id']+':'+str(len(components)+1);ps=rects(comp);components.append({'id':id,'area_m2':float(sizes[j])*PITCH**2,'centroid_xz_m':[float(x.mean())*PITCH+BOUNDS[0]+PITCH/2,float(z.mean())*PITCH+BOUNDS[1]+PITCH/2],'polygon_parts_xz_m':ps,'connected_in_4_neighbour_grid':True,'native_implementation_status':'unimplemented planning ground'});accepted|=comp
  if not accepted.any():continue
  bs=fit_ranges(accepted,*s['native_range_dimensions_m'],s['range_yaw_degrees'],s['maximum_range_parcels'])if s['native_range_dimensions_m']else[]
  for n,b in enumerate(bs):b.update(id=s['id']+':RANGE:'+str(n+1),zone_id=s['id'],site_id=s['site_id']);parcels.append(b)
  remaining[s['site_id']] &=~accepted;labels[accepted]=i
  zones.append(dict(s,area_m2=float(accepted.sum())*PITCH**2,contiguous_holdings=components,range_parcel_ids=[b['id']for b in bs],access_policy='Reserve a rear service or foot lane to an existing public/precinct route. Exact gate and profile are unresolved until the separate route proposal passes.',boundary_policy='Continuous low stone/timber enclosure with real gates on the route, no isolated decorative props; retention follows actual sampled grades.'))
  print(s['id'],round(accepted.sum()*PITCH**2,2),'holdings',len(components),'ranges',len(bs),flush=True)
 leftovers=[]
 for k,a in remaining.items():
  labs,n=ndimage.label(a);sizes=np.bincount(labs.ravel());comps=[]
  for j in np.argsort(sizes[1:])[::-1]+1:
   comp=labs==j
   if sizes[j]*PITCH**2<10:continue
   z,x=np.where(comp);comps.append({'area_m2':float(sizes[j])*PITCH**2,'centroid_xz_m':[float(x.mean())*PITCH+BOUNDS[0]+PITCH/2,float(z.mean())*PITCH+BOUNDS[1]+PITCH/2],'polygon_parts_xz_m':rects(comp)})
  leftovers.append({'site_id':k,'area_m2':float(a.sum())*PITCH**2,'status':'Explicit unresolved remainder; narrow support edges and disconnected fragments are not labelled completed green space.','components_over_10_m2':comps})
 result={'schema':'riverstone.registered_city.remaining_land_plan.v1','status':'Source-only polygon draft for review before native authoring; no current snapshot edits.','inputs':load(HERE/'input_refs.json'),'concept_observation':{'source_image':ref(ROOT/'world_city/reference/revision_03/city_social_water_concept.png'),'controls':ref(CITY/'image_registration/controls.json'),'observed':['Dense lower ordinary streets and attached roof groups','Industrial canal with workshops and working yards in the eastern lower city','Large purposeful enclosed gardens around noble and religious precincts','Precinct paths and open forecourts separating major church buildings'],'inferred':['Exact new holding limits and gates','Specific trades, household functions and crop roles','All new range dimensions and future construction counts'],'no_concept_roof_pixel_segmentation':True},'method':{'planning_grid_pitch_m':PITCH,'boundary_grid_max_corner_offset_m':PITCH/math.sqrt(2),'new_program_geometry':'Exact union of listed 0.5 m planning cells, conservatively inset from source domains and excluded owners. This is not a native mesh or continuous terrain ownership result.','existing_owner_clearances':'Preserve existing plot frames; native roof +1 m, wet edge +4 m, public/private existing access +0.75 m, pending merchant +0.75 m. Wall centerline ±12 m is a conservative review reservation, not a changed wall width.','minimum_contiguous_holding_m2':120,'floor_policy':'Terrain-relative source envelopes. Future floors need finite supports, road handoffs and drainage; no global flat pad.'},'zones':zones,'range_parcels':parcels,'unresolved_remainder':leftovers,'summary':{'functional_zones':len(zones),'contiguous_holdings':sum(len(q['contiguous_holdings'])for q in zones),'range_parcels':len(parcels),'programmed_source_area_m2':sum(q['area_m2']for q in zones),'unresolved_source_area_m2':sum(q['area_m2']for q in leftovers),'native_assets_compiled':0,'scene_placements_added':0},'completion_gate':['Parent reviews polygons against actual R5 and concept adjacency.','Reserve accepted holdings and derive genuine gate/rear-lane links before dense native source authoring.','Bound each range to native grammar dimensions and finite terrain support.','Independent native access, support, water and visual review remain required.']};write(HERE/'remaining_land_plan.json',result);np.savez_compressed(HERE/'program_raster.npz',zone_labels=labels,**remaining);print(result['summary'])
if __name__=='__main__':main()
