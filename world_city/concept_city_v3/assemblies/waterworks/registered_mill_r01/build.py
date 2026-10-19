"""Source-authored small canal mill: reused native wheel, bank support, one coherent house."""
import copy,json,math
from .select_site import HERE,CITY,pose
from voxel_character.common import coordinate_planes,render_data
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a,side_clearance
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import frozen_r6 as f
from world_city.runtime_city.checks import placement as g
ROOT=CITY.parents[1]
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,separators=(',',':'),allow_nan=False)+'\n')
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=a.sha(p))
def box(id,mn,mx,mat='stone',action='paint'):return dict(id=id,action=action,material=mat,part='solid',shape=dict(kind='box',min=mn,max=mx))
def fan(p,plane):return f.fan_upward(f.lift(p,plane))
def transform():return {'basis':[[1,0,0],[0,1,0],[0,0,1]],'translation':[0,0,0]}
def build():
 site=json.loads((HERE/'site_candidates.json').read_text())['selected'];assert site;scene=a.load_scene();o=site['position_xz_m'];floor=site['ground_y_m'];water=[]
 for j in range(0,len(scene['surfaces']['water']),3):
  tri=scene['surfaces']['water'][j:j+3];p=[[v[0],v[2]]for v in tri]
  if g.point_in_convex_polygon(o,p):water.append(dict(material='water',triangle_index=j//3,source_triangle_sha256=a.canonical_sha(tri),plane_y_xz_m=a.common.plane(tri),head_y_m=a.common.height(a.common.plane(tri),o)))
 assert len(water)==1;head=water[0]['head_y_m'];dy=head+.2-floor
 wheelpath=HERE.parent/'masters/undershot_mill_wheel.json';bankpath=HERE.parent/'masters/mill_bank_interface.json';wheel=json.loads(wheelpath.read_text());bank=json.loads(bankpath.read_text());master=copy.deepcopy(wheel);master['id']='registered_east_canal_small_mill_r01';master['revision']=1;master['components']=copy.deepcopy(wheel['components'])+copy.deepcopy(bank['components']);master['instances']=[]
 for comp in master['components']:
  t=transform();t['translation'][1]=dy;master['instances'].append(dict(id=comp['id'],component=comp['id'],transform=t))
 # Dimension-author spoke thickness for a connected retained rotor at the chosen native pitch.
 for comp in master['components']:
  if comp['id']=='wheel':
   for op in comp['operations']:
    if op['id'].startswith('spoke_'):op['shape']['radius']=.16
 # Existing support parameter is authored to the measured dry datum; wheel/axle remain their source radius and span.
 floor_local=-dy
 for comp in master['components']:
  if comp['id']=='bank_support':comp['operations'][0]['shape']['max'][1]=floor_local
  if comp['id']=='drive_wall':
   comp['operations'][0]['shape']['min'][1]=floor_local;comp['operations'][0]['shape']['max'][1]=floor_local+3.4
 house=[]
 house.append(box('bank_floor',[-7,-.4,-3],[-1.8,0,3]))
 house.append(box('basement_shaft_void',[-7,-.8,-.35],[-1.79,-.2,.35],action='cut'))
 house.append(box('north_wall',[-7,0,-3],[-1.8,3.4,-2.6]))
 house.append(box('south_wall',[-7,0,2.6],[-1.8,3.4,3]))
 house.append(box('west_gable_wall',[-7,0,-3],[-6.6,3.4,3]))
 house.append(box('door_opening',[-7.01,0,-1.2],[-6.59,2.4,1.2],action='cut'))
 # Open static timber leaf beside a2.4m doorway; no door animation is asserted.
 house.append(box('open_timber_door',[-6.95,0,1.1],[-5.2,2.3,1.3],mat='timber_dark'))
 for z in [-2.4,2.4]:house.append(box('eave_timber_'+str(z),[-7,3.1,z-.1],[-1.8,3.4,z+.1],mat='timber'))
 for z in [-3.01,2.59]:
  house.append(box('window_void_'+str(z),[-5.7,1.25,z],[-4.3,2.55,z+.42],action='cut'));house.append(box('window_shutter_'+str(z),[-5.7,1.25,z+.06],[-4.3,2.55,z+.18],mat='timber_dark'))
 for z in [-3,2.6]:
  house.append(dict(id='gable_'+str(z),action='paint',material='stone',part='solid',shape=dict(kind='extrusion',polygon=[[-7,3.3],[-4.4,4.65],[-1.8,3.3]],z_min=z,z_max=z+.4)))
 for side in [-1,1]:
  polygon=[[-7.4,3.25],[-4.4,4.9],[-4.4,4.55],[-7.4,2.9]] if side<0 else [[-4.4,4.9],[-1.4,3.25],[-1.4,2.9],[-4.4,4.55]]
  house.append(dict(id='slate_roof_'+str(side),action='paint',material='slate',part='solid',shape=dict(kind='extrusion',polygon=polygon,z_min=-3.4,z_max=3.4)))
 # Source-authored connected submerged footing. Its bank end is embedded under the dry support.
 house.append(box('submerged_connected_footing',[-3,-2.6,-.6],[2.0,-2.2,.6],mat='stone_dark'))
 house.append(dict(id='drive_extension',action='paint',material='timber_dark',part='solid',shape=dict(kind='tube',points=[[-5.5,dy+.8,0],[-1.5,dy+.8,0]],radius=.18,minimum_radius_cells=0)))
 master['components'].append(dict(id='millhouse',parts=[dict(id='solid',pivot=[0,0,0])],operations=house));master['instances'].append(dict(id='millhouse',component='millhouse'))
 master['constraints']=[dict(id='native_nonempty',kind='nonempty',selector={})]+[dict(id=c['id']+'_present',kind='nonempty',selector=dict(component=c['id']))for c in master['components']]
 master['provenance']=dict(reused_sources=[ref(wheelpath),ref(bankpath)],actual_scene=dict(path=str(a.SCENE_PATH.relative_to(ROOT)),sha256=a.SCENE_SHA256),hydrology=ref(CITY/'registered_topography/revisions/r14_precinct_merchant/contract.json'),policy='Existing common coordinate-plane native compilation; dimension-authored attached house and explicit measured datum translation. Unit-scale placement; no new core, mesher, or hydraulic engine.')
 master['extensions']=dict(status='source_complete_pending_actual_view',canal_id=site['canal_id'],actual_water=water[0],ground_y_m=floor,wheel_origin_offset_y_m=dy,axis='Rigid static original1.5m-radius undershot wheel and axle span; spokes dimension-authored from0.10to0.16m radius for connected0.2m native occupancy; bearings retained',mechanical_status='Static exterior; no rotation, torque, flow or power simulation claim.',navigation='Opposite side retains an explicit 2.4m navigation ribbon; only geometric clearance is claimed.',fluid_surface_owner='Existing R7 transparent canal surface remains unchanged.',structural_status='Native connected geometry only, not structural certification.',scope='Exterior house, wet wheel, axle, masonry/timber bearings, connected submerged footing, dry street approach')
 mp=HERE/'masters/small_canal_mill.json';write(mp,master);c=coordinate_planes.compile_master(master,{'pitch':.2},max_candidate_cells=500000,max_output_cells=160000);assert c['valid'];render=render_data.make_render_data(c);rp=HERE/'cache/small_canal_mill.render.json';write(rp,render)
 edited={};paint=[]
 for key,pieces in [('ground',site['ground']['source_pieces']),('access',site['access_source_pieces'])]:
  for r in pieces:
   if key=='access'and r['material']in('road','alley'):continue
   k=(r['material'],r['triangle_index']);entry=edited.setdefault(k,dict(cuts=[],walks=[]))
   entry['cuts'if key=='ground'else'walks'].append(site['body_polygon_xz_m']if key=='ground'else r['polygon_xz_m'])
 edits=[]
 for (material,j),masks in edited.items():
  tri=scene['surfaces'][material][j*3:j*3+3];p=[[v[0],v[2]]for v in tri];plane=a.common.plane(tri);parts=a.common.subtract([p],masks['cuts']+masks['walks']);edits.append(dict(material=material,triangle_index=j,source_triangle_sha256=a.canonical_sha(tri),replacement_triangles_xyz_m=[t for p in parts for t in fan(p,plane)]));done=[]
  for walk in masks['walks']:
   chunks=a.common.subtract([walk],masks['cuts']+done);done.append(walk)
   for p in chunks:paint.extend(v for t in fan(p,plane)for v in t)
 patch=dict(schema='riverstone.frozen_scene.local_surface_patch.v1',id='R8_REGISTERED_EAST_CANAL_MILL',base_scene_sha256=a.SCENE_SHA256,source_surface_hashes={m:a.canonical_sha(scene['surfaces'][m])for m in set(k[0]for k in edited)},surface_edits=edits,appended_surfaces={'ground_stone':paint},removed_foundation_proxy_ids=[],summary=dict(native_dry_platform_m2=31.2,source_triangles=len(edits),old_water_unchanged=True,old_banks_unchanged=True))
 write(HERE/'surface_patch.json',patch)
 asset=dict(id=master['id'],source=ref(mp),cache=ref(rp),pitch_m=.2,candidate_cells=c['candidate_cells'],output_cells=len(c['cells']),quad_count=render['quad_count']);placement=dict(id='REGISTERED_MILL:EAST_CANAL',asset_key=master['id'],position_m=[o[0],floor,o[1]],yaw_rad=site['yaw_rad'],scale=[1,1,1],palette_id='slate_gray',function='static_industrial_watermill_exterior')
 pack=dict(schema='riverstone.r8.registered_canal_mill.v1',base_scene=ref(a.SCENE_PATH),assets=[asset],placements=[placement],replaced_placement_ids=[],source_refs=[ref(HERE/'site_candidates.json'),ref(CITY/'registered_topography/revisions/r14_precinct_merchant/contract.json')],limits=['Static wheel; fluid flow, torque, milling interaction and interior traversal unimplemented.','No claim of hydraulic capacity, structural certification or potable water.'])
 write(HERE/'resolved_placements.json',pack);write(HERE/'interface_contract.json',dict(base_scene_sha256=a.SCENE_SHA256,site=site,actual_water=water[0],head_y_m=head,ground_y_m=floor,wheel_origin_y_m=head+.2,axle_y_m=head+1.,nominal_wheel_low_y_m=head-.58,canal_bed_contract_y_m=site['water_head_y_m']-.9,dry_floor_owned_polygon_xz_m=site['body_polygon_xz_m'],navigation_polygon_xz_m=[pose(p,o,site['yaw_rad'])for p in [[2.2,-5],[4.6,-5],[4.6,5],[2.2,5]]],navigation_width_m=2.4,source_refs=[ref(HERE/'masters/small_canal_mill.json'),ref(HERE/'cache/small_canal_mill.render.json')],limits=['Canal bed datum is source contract; no rendered bed exists at pier point. A native submerged footing connects pier to the embedded dry bank support.']))
 print(json.dumps(dict(cells=len(c['cells']),quads=render['quad_count'],bounds=render['bounds'],terrain_edits=len(edits),public_road=site['public_road_id'],actual_water_head=head,old_water_changed=False)))
if __name__=='__main__':build()
