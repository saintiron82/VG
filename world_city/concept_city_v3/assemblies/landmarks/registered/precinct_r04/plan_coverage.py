"""Recover the approved six functional compounds in the registered precincts."""
import json,math,sys
from recovered_range_factory import HERE,ROOT,ref,write
from world_city.runtime_city.checks import placement as geo
from world_city.runtime_city.urban_fabric.author import rect
from world_city.runtime_city.urban_fabric.revisions.r3.probe import offset
from world_city.runtime_city.urban_fabric.revisions.r3.author_overlay import polygon_covered_by_union
from world_city.concept_city_v3.registered_source.geometry import triangulate
from world_city.concept_city_v3.review_geometry import DomainCut,clean
from world_city.concept_city_v3.assemblies.property.registered import author as prop
CITY=ROOT/'world_city/concept_city_v3';SPEC=json.loads((HERE/'reconstruction_spec.json').read_text());SOURCE=CITY/'registered_source/plan.json';LAND=CITY/'assemblies/landmarks/registered/repairs/r02_connected_finials/resolved_placements.json';GARDEN=CITY/'assemblies/landscape/registered/resolved_placements.json';ORDINARY=CITY/'assemblies/ordinary/registered/resolved_placements.json'
def load(p):return json.loads(p.read_text())
def circle(p,r,n=16):return [[p[0]+r/math.cos(math.pi/n)*math.cos(2*math.pi*i/n),p[1]+r/math.cos(math.pi/n)*math.sin(2*math.pi*i/n)]for i in range(n)]
def world(p,c,yaw):
 a=math.radians(yaw);return[c[0]+p[0]*math.cos(a)+p[1]*math.sin(a),c[1]-p[0]*math.sin(a)+p[1]*math.cos(a)]
def reserve():
 source=load(SOURCE);land=load(LAND);garden=load(GARDEN);obs=[]
 def add(poly,kind,id):
  if len(poly)<3:return
  for i,p in enumerate(triangulate(poly)):obs.append({'id':id+':'+str(i),'kind':kind,'polygon_xz_m':p})
 for road in source['roads']:
  for i,(a,b) in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):add(geo.road_ribbon(a,b,road['width_m']+4),'public_road_and_support',road['id']+str(i))
 for f in land['owned_floors']:add(f['polygon_xz_m'],'landmark_owned_floor',f['id'])
 for s in garden['sites']:add(s['polygon_xz_m'],'sealed_garden',s['id'])
 for route in garden['internal_routes']+garden['external_connections']:
  for i,p in enumerate(route.get('ribbon_polygons_xz_m',[])):add(offset(p,-.25),'sealed_garden_route',route['id']+str(i))
  for i,p in enumerate(route.get('polyline_xz_m',[])):add(circle(p,route.get('width_m',1.8)/2+.25),'sealed_garden_route_join',route['id']+str(i))
 for p in load(ORDINARY)['placements']:add(p['actual_outer_footprint_xz_m'],'ordinary_native_body',p['id'])
 # Recovery surface reservation is loaded separately when validator seals it.
 recovered=HERE/'recovered_access_reservations.json';access_status='PENDING recovered exact ramp/landing reservation'
 if recovered.exists():
  r=load(recovered);access_status='Recovered exact rendered surface union, not original route IDs';
  for i,p in enumerate(r['polygons_xz_m']):
   margin=r.get('additional_clearance_m',.9);xs=[v[0]for v in p];zs=[v[1]for v in p];q=[[min(xs)-margin,min(zs)-margin],[max(xs)+margin,min(zs)-margin],[max(xs)+margin,max(zs)+margin],[min(xs)-margin,max(zs)+margin]];obs.append({'id':'recovered_access:'+str(i),'kind':'recovered_landmark_access','polygon_xz_m':q})
 return source,land,garden,obs,access_status

def main():
 source,land,garden,obs,access_status=reserve();cutter=DomainCut(obs);sites={s['id']:s for s in source['spaces']if s['id']in ('SITE_CLERGY','SITE_MONASTERY')};compounds=[]
 for id,site,c,w,d,yaw,role,count in SPEC['compound_specs']:
  frame=rect(c,w,d,math.radians(yaw));pieces=[]
  for tri in triangulate(sites[site]['polygon_xz_m']):
   p=clean(geo.convex_intersection(frame,tri))
   if p:pieces+=cutter.subtract(p)
  compounds.append({'id':id,'site_id':site,'center_xz_m':c,'width_m':w,'depth_m':d,'yaw_degrees':yaw,'function':role,'expected_buildings':count,'finished_floor_y_m':sites[site]['finished_floor_y_m'],'requested_frame_xz_m':frame,'available_regions_xz_m':pieces,'area_m2':sum(geo.polygon_area(p)for p in pieces),'real_boundary_and_gate_status':'to_be_authored'})
 site_rows=[]
 for id,s in sites.items():
  avail=[q for t in triangulate(s['polygon_xz_m'])for q in cutter.subtract(t)];cc=DomainCut([{'polygon_xz_m':p}for c in compounds if c['site_id']==id for p in c['available_regions_xz_m']]);remain=[q for p in avail for q in cc.subtract(p)];a=geo.polygon_area(s['polygon_xz_m']);free=sum(geo.polygon_area(p)for p in avail);ca=sum(c['area_m2']for c in compounds if c['site_id']==id);ra=sum(geo.polygon_area(p)for p in remain);assert abs(free-ca-ra)<1e-4
  assignments=[]
  for i,p in enumerate(remain):
   x,z=prop.centre(p)
   role=('cemetery_boundary_and_expansion'if z< -270 else 'canons_food_and_service_garden'if x<230 else 'procession_and_chapel_void'if z< -170 else 'guest_kitchen_and_food_plots')if id=='SITE_CLERGY'else('infirmary_nursery_belt'if z<60 else 'cloister_procession_void'if x< -260 and z<180 else 'working_court_and_harvest_yard'if x> -250 else 'orchard_service_belt')
   assignments.append({'id':id+':remaining:'+str(i),'function':role,'polygon_xz_m':p,'area_m2':geo.polygon_area(p),'status':'finite_source_reservation_not_native_facility'})
  site_rows.append({'id':id,'polygon_xz_m':s['polygon_xz_m'],'area_m2':a,'existing_reserved_area_m2':a-free,'new_compounds_area_m2':ca,'remaining_source_subareas_area_m2':ra,'remaining_subareas':assignments})
 value={'schema':'riverstone.city.registered_precinct_coverage_plan.v2','status':'reconstructed_approved_plan_access_reservation_pending'if access_status.startswith('PENDING')else'reconstructed_finite_source_plan','source_plan':ref(SOURCE),'landmarks':ref(LAND),'gardens':ref(GARDEN),'reconstruction_spec':ref(HERE/'reconstruction_spec.json'),'access_reservation_status':access_status,'sites':site_rows,'compounds':compounds,'reserved_records':obs,'conditions':['Preserve all sealed garden polygons and305native placements.','Six functional compounds; native dimensions and distinct roof/facade families.','Every remainder is a finite program reservation; no source label means finished geometry.','Preserve procession and chapel voids.']};write(HERE/'coverage_plan.json',value);print([(x['id'],round(x['area_m2'],2))for x in compounds]);print(access_status)
if __name__=='__main__':main()
