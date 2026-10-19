"""Small source-bound inlet, sluice and dry-bank protected-supply assembly."""
import copy,json,math
from author_reservoir import *
CISTERN_ORIGIN=[-36.,18.,-335.7167708839214]

def source_record(s,kind,origin,role):
 s['id']='registered_reservoir_'+kind;s['provenance'].update(registered_interface_author=ref(Path(__file__)),registered_water_contract=ref(CONTRACT));s['extensions'].update(network_role=role,registered_source_origin_xyz_m=origin,actual_scene_loaded=False,actual_visual_review=False);s['extensions']['local_bounds_m']=source_bounds(s);return s

def physical_supply():
 # The retained staged wellhouse provides the shaft, frame, roof and windlass.
 s=staged.make_master('covered_wellhouse');platform=next(c for c in s['components'] if c['id']=='platform');platform['operations'][0]['shape']={'kind':'box','min':[-4,-4.7,-4],'max':[10.4,0,6]}
 platform['operations'].insert(1,{'id':'covered_cistern_chamber','action':'cut','part':'solid','shape':{'kind':'box','min':[-3.2,-4.4,-3.2],'max':[3.2,-.3,2.2]}})
 platform['operations'].append({'id':'protected_inlet_bore','action':'cut','part':'solid','shape':{'kind':'box','min':[-.4,-3,-4.01],'max':[.4,-1.8,-3.19]}})
 road=next(r for r in DATA['roads'] if r['id']=='RESERVOIR_SERVICE');road_keepouts=[]
 for i,(p,q) in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
  u=[(q[j]-p[j])/math.dist(p,q) for j in (0,1)];p=[p[j]-.16*u[j] for j in (0,1)];q=[q[j]+.16*u[j] for j in (0,1)];poly=geo.road_ribbon(p,q,3.32);local=[[x-CISTERN_ORIGIN[0],-(z-CISTERN_ORIGIN[2])] for x,z in poly];platform['operations'].append({'id':'preserve_service_lane_'+str(i),'part':'solid','action':'cut','shape':extrusion(local,-4.71,.01),'transform':{'basis':[[1,0,0],[0,0,1],[0,-1,0]]}});road_keepouts.append(poly)
 s['extensions']['native_road_keepouts_xz_m']=road_keepouts
 shaft=next(c for c in s['components'] if c['id']=='shaft');shaft['operations'][0]['shape']['y_min']=-4.4
 for q in s['extensions']['sockets']:
  if q['id']=='water_head':q['position_m'][1]=-2.5
 s['extensions']['sockets'].append({'id':'covered_conduit_inlet','position_m':[0,-3,-4],'outward_normal':[0,0,-1],'role':'protected_supply_invert','coordinate_space':'asset_local_metres'})
 # Keep dry floor and tank as one union; the large finite body closes cut/fill to land.
 s=source_record(s,'covered_cistern_drawpoint',CISTERN_ORIGIN,'protected_supply');s['extensions'].update(logical_node_id='COVERED_CISTERN',logical_node_xz_m=[-30.050779741957584,-365.97947492968893],physical_head_y_m=15.5,physical_water_surface_status='Reserved chamber only; no new fluid simulation or opaque water geometry.',owned_floor_local_rect_m=[-4,-4,10.4,6],floor_y_m=18,support_bottom_y_m=13.3,protected_inlet_invert_y_m=15.0,service_endpoint_xz_m=[-29.69020213390713,-329.7167708839214]);return s

def protected_conduit():
 # Reuse the canonical casing/bore grammar with a finite locally authored length.
 s=staged.make_master('covered_clean_conduit');c=s['components'][0];length=6.6
 c['operations'][0]['shape']={'kind':'box','min':[-.7,-.3,-length/2],'max':[.7,1.5,length/2]};c['operations'][1]['shape']={'kind':'box','min':[-.4,0,-length/2-.01],'max':[.4,1.2,length/2+.01]}
 s['constraints']=[q for q in s['constraints'] if q['kind']!='empty_region'];s=source_record(s,'protected_bank_conduit',[-36.,15.,-341.0167708839214],'protected_supply');s['extensions'].update(inlet_world_xyz_m=[-36,15,-344.3167708839214],outlet_world_xyz_m=[-36,15,-337.7167708839214],upstream_head_y_m=16,downstream_head_y_m=15.5,bore_size_m=[.8,1.2],head_difference_m=.5,capacity_validated=False);return s

def cut_bank_offtake():
 s=json.loads((HERE/'masters/registered_reservoir_basin_perimeter.json').read_text());s['id']='registered_reservoir_basin_perimeter_supply_opening_r02';s['revision']=2
 # Exact finite protected bore through the south lining; coping and guard remain.
 c=next(c for c in s['components'] if c['id']=='lining');c['operations'].append({'id':'protected_supply_wall_opening','part':'solid','action':'cut','shape':{'kind':'box','min':[-6.4,-1,21.5],'max':[-5.6,.2,28.3]}})
 s['provenance'].update(registered_interface_author=ref(Path(__file__)),base_perimeter=ref(HERE/'masters/registered_reservoir_basin_perimeter.json'));s['extensions']['protected_supply_opening_world_bounds_m']={'min':[-36.4,15,-344.5],'max':[-35.6,16.2,-337.7]};s['extensions']['local_bounds_m']=source_bounds(s);return s

def sluice():
 s=staged.make_master('sluice_bay');lining=next(c for c in s['components'] if c['id']=='lining')
 for op in lining['operations']:
  if op['id']=='bed_liner':op['shape']['min'][1]=-.9;op['shape']['max'][1]=-.6
  elif op['id'].startswith('bank_'):op['shape']['min'][1]=-.6;op['shape']['max'][1]=2
 s['constraints']=[q for q in s['constraints'] if q['kind']!='empty_region'];s=source_record(s,'overflow_sluice',None,'one_way_overflow');s['extensions'].update(actual_head_binding='Exact NORTHERN_CHANNEL_VISIBLE mouth head16; source bed15.4, control frame at raised sample state.',bank_y_above_water_m=2,bed_y_above_water_m=-.6,controller_implemented=False);return s

def intake():
 s=staged.make_master('spring_intake');w=next(w for w in DATA['water_surfaces'] if w['id']=='SPRING_VISIBLE');a,b=w['polyline_xz_m'][:2];slope=(w['levels_m'][1]-w['levels_m'][0])/math.dist(a,b)
 cosa=1/math.sqrt(1+slope*slope);sina=slope*cosa
 for c in s['components']:
  for op in c['operations']:op['transform']={'basis':[[1,0,0],[0,cosa,sina],[0,-sina,cosa]],'translation':[0,0,0]}
 for socket in s['extensions']['sockets']:
  x,y,z=socket['position_m'];socket['position_m']=[x,cosa*y+sina*z,-sina*y+cosa*z]
 s['constraints']=[q for q in s['constraints'] if q['kind']!='empty_region'];s=source_record(s,'graded_spring_intake',None,'raw_source');s['extensions'].update(head_slope_per_m=slope,source_node_id='RAW_SPRING',head_binding='Upstream socket is24; each source operation follows the existing first feeder grade.');return s

def main():
 rows=[]
 for s in [physical_supply(),protected_conduit(),cut_bank_offtake(),sluice(),intake()]:
  p=HERE/'masters'/f"{s['id']}.json";write(p,s);n=estimate_candidates(s,.2)['candidate_cells_exact_aabb_visits'];assert n<600000;rows.append({'id':s['id'],'source':ref(p),'candidate_cells':n,'pitch_m':.2})
 write(HERE/'interface_preflight.json',{'schema':'riverstone.city.reservoir_interface_preflight.v1','sources':rows,'candidate_cap_each':600000,'output_cap_each':200000,'sequential':True,'cistern_origin_xyz_m':CISTERN_ORIGIN,'physical_placement_inference':True,'road_graph_unchanged':True,'hydraulics_validated':False});print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
