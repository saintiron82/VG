"""Four finite road crossings, dimension-authored from the common footbridge."""
import copy,json,math
from .audit import HERE,CITY,ROOT,ref,write,pose
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.concept_city_v3.assemblies.waterworks.registered_mill_r01.select_site import pose as xzpose
from world_city.runtime_city.checks import placement as g
from voxel_character.common import coordinate_planes,render_data

def box(id,mn,mx,material='timber'):return dict(id=id,action='paint',material=material,part='solid',shape=dict(kind='box',min=mn,max=mx))
def component(id,ops):return dict(id=id,parts=[dict(id='solid',pivot=[0,0,0])],operations=ops)
def poly(lo,hi,half,o,yaw):return[xzpose(v,o,yaw)for v in [[lo,-half],[hi,-half],[hi,half],[lo,half]]]
def run():
 s=a.load_scene();sites=json.loads((HERE/'crossing_probes.json').read_text())['candidates'];basepath=HERE.parent/'masters/canal_footbridge.json';base=json.loads(basepath.read_text());assets=[];placements=[];interfaces=[]
 for site in sites:
  rid=site['id'];o=site['position_xz_m'];yaw=site['yaw_rad'];width=site['road_width_m'];half=math.ceil(width/2/.2-1e-9)*.2;outside=half+.4;window=poly(-30,30,outside,o,yaw);wet=[];xs=[]
  for j in range(0,len(s['surfaces']['water']),3):
   t=s['surfaces']['water'][j:j+3];q=g.convex_intersection(window,[[v[0],v[2]]for v in t])
   if g.polygon_area(q)<1e-9:continue
   xs.extend(xzpose([p[0]-o[0],p[1]-o[1]],[0,0],-yaw)[0]for p in q);wet.append(dict(triangle_index=j//3,source_triangle_sha256=a.canonical_sha(t),plane_y_xz_m=a.common.plane(t),polygon_xz_m=q))
  lo=math.floor((min(xs)-1)*5)/5;hi=math.ceil((max(xs)+1)*5)/5;floor=15.6 if 'NORTH'in rid else 2.5;foot=poly(lo,hi,outside,o,yaw);traffic=poly(lo,hi,width/2,o,yaw)
  master=copy.deepcopy(base);master['id']='registered_water_crossing_'+rid.lower();master['revision']=1;ops=[box('deck',[lo,-.4,-outside],[hi,0,outside])]
  comps=[component('deck',ops),component('abutments',[box('abutment_'+str(k),[x,-2,-outside],[x+.6,-.4,outside],'stone')for k,x in enumerate([lo,hi-.6])])]
  rail=[]
  for side in [-1,1]:
   z=side*(half+.2);rail.append(box('rail_'+str(side),[lo,.8,z-.2],[hi,1.2,z+.2]));stations=[lo+.2+i*(hi-lo-.4)/max(1,math.ceil((hi-lo-.4)/2))for i in range(max(1,math.ceil((hi-lo-.4)/2))+1)]
   for k,x in enumerate(stations):rail.append(box('post_'+str(side)+'_'+str(k),[x-.1,0,z-.2],[x+.1,1.2,z+.2],'timber_dark'))
  comps.append(component('rail',rail));beams=[]
  for side in [-1,1]:
   z=side*(half+.2);beams.append(box('longitudinal_beam_'+str(side),[lo,-.6,z-.2],[hi,-.4,z+.2],'timber_dark'))
  comps.append(component('beams',beams));master['components']=comps;master['instances']=[dict(id=q['id'],component=q['id'])for q in comps];master['constraints']=[dict(id=q['id']+'_present',kind='nonempty',selector=dict(component=q['id']))for q in comps]+[dict(id='traffic_clear',kind='empty_region',selector={},shape=dict(kind='box',min=[lo,.01,-width/2],max=[hi,2.8,width/2]))]
  master['provenance']=dict(reused_source=ref(basepath),actual_scene=ref(a.SCENE_PATH),policy='Dimension-authored native variation of existing common timber canal bridge: road-width deck, stone abutments beyond wet domain, rails and side beams. No mesh scale or core change.')
  master['extensions']=dict(road_id=rid,canal_id=site['canal_id'],road_width_m=width,actual_clear_width_m=2*half,span_m=hi-lo,deck_y_m=floor,water_source_refs=wet,limits=['Static geometry only; structural capacity, traffic loading, fluid flow and flood performance are unbuilt simulation.','Dry public-road approaches require the separately coordinated canonical finite road patch.'])
  mp=HERE/('masters/'+rid.lower()+'.json');mp.parent.mkdir(exist_ok=True);mp.write_text(json.dumps(master,separators=(',',':'))+'\n');c=coordinate_planes.compile_master(master,{'pitch':.2},max_candidate_cells=500000,max_output_cells=180000);assert c['valid'],c.get('constraints');r=render_data.make_render_data(c);rp=HERE/('cache/'+rid.lower()+'.render.json');rp.parent.mkdir(exist_ok=True);rp.write_text(json.dumps(r,separators=(',',':'))+'\n')
  pid='REGISTERED_WATER_CROSSING:'+rid;p=dict(id=pid,asset_key=master['id'],position_m=[o[0],floor,o[1]],yaw_rad=yaw,scale=[1,1,1],palette_id='native_water_crossing');placements.append(p);assets.append(dict(id=master['id'],source=ref(mp),cache=ref(rp),pitch_m=.2,candidate_cells=c['candidate_cells'],output_cells=len(c['cells']),quad_count=r['quad_count']))
  seams=[]
  for end,x in [('start',lo),('end',hi)]:
   seams.append(dict(id=rid+':'+end,xyz_m=[[q[0],floor,q[1]]for q in[xzpose([x,-width/2],o,yaw),xzpose([x,width/2],o,yaw)]],full_native_width_xyz_m=[[q[0],floor,q[1]]for q in[xzpose([x,-outside],o,yaw),xzpose([x,outside],o,yaw)]],road_id=rid,road_segment=site['road_segment']))
  interfaces.append(dict(id=rid,placement_id=pid,position_m=p['position_m'],yaw_rad=yaw,road_width_m=width,actual_clear_width_m=2*half,local_x_limits_m=[lo,hi],native_ownership_polygon_xz_m=foot,traffic_polygon_xz_m=traffic,deck_top_y_m=floor,deck_underside_y_m=floor-.4,side_beam_bottom_y_m=floor-.6,abutment_bottom_y_m=floor-2,abutment_polygons_xz_m=[poly(lo,lo+.6,outside,o,yaw),poly(hi-.6,hi,outside,o,yaw)],wet_projection_local_x_range_m=[min(xs),max(xs)],actual_water=wet,approach_seams=seams,source=ref(mp),cache=ref(rp),terrain_handoff='Canonical public-road producer owns finite approach regeneration and dry-top removal within native deck ownership. Preserve underwater banks/bed and all water vertices. Retained bank obstacles may be removed only above the native deck underside, with native deck replacing that finite volume.',status='NATIVE_SOURCE_READY_APPROACH_PATCH_PENDING'))
  print(rid,'span',hi-lo,'width',width,'floor',floor,'cells',len(c['cells']),'quads',r['quad_count'],flush=True)
 for i,x in enumerate(interfaces):
  for y in interfaces[:i]:assert g.polygon_area(g.convex_intersection(x['native_ownership_polygon_xz_m'],y['native_ownership_polygon_xz_m']))<1e-7,(x['id'],y['id'])
 write('crossing_interfaces.json',dict(schema='riverstone.water_crossings.canonical_road_handoff.v1',base_scene=ref(a.SCENE_PATH),source_canal_footbridge=ref(basepath),crossings=interfaces,old_water_unchanged=True,old_submerged_bed_and_banks_unchanged=True))
 write('resolved_placements.json',dict(schema='riverstone.r8.registered_water_completion.v1',base_scene=ref(a.SCENE_PATH),assets=assets,placements=placements,replaced_placement_ids=[],source_refs=[ref(HERE/'crossing_interfaces.json')],limits=['Activation needs the canonical public road patch and independent integrated clearance checks.','These four public crossings have no automatic bridge movement or hydraulic simulation.']))
if __name__=='__main__':run()
