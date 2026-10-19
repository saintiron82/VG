"""Small v3 water/terrace source modules. No scene placement or new engine.

All dimensions are explicit game-design contracts, not image measurements.
Wet volumes stay owned by the separate water field, never opaque part geometry.
"""
from __future__ import annotations
import copy,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
HERE=Path(__file__).resolve().parent
from world_city.runtime_city.parts.author import Source,extrusion,approved_palette
from world_city.concept_city_v3.assemblies.landmarks.author import ref,write,source_bounds

AUTHOR='world_city/concept_city_v3/assemblies/waterworks/author.py'
CANDIDATE_CAP=400000
OUTPUT_CAP=120000
KINDS=('spring_intake','covered_wellhouse','reservoir_lining_segment','sluice_bay','covered_clean_conduit','service_channel_segment','undershot_mill_wheel','mill_bank_interface','canal_footbridge','stone_road_bridge_bay','drain_outfall','retaining_stair_landing')
HEAD_CONTRACT={
 'spring':{'wet_width_m':2,'heads_y_m':[24,22,17,16],'bed_below_water_m':.6,'normal_bank_above_water_m':.6,'network':'raw_clean_source'},
 'reservoir':{'wet_size_xz_m':[96,46],'water_y_m':16,'bed_y_m':13.6,'bank_y_m':18,'bank_reserve_size_xz_m':[120,70]},
 'service_canal':{'wet_width_m':6,'reserved_width_m':14,'bed_below_water_m':.8,'normal_bank_above_water_m':1.2,'network':'industrial_nonpotable'},
 'bridge':{'deck_above_matching_water_head_m':2.08,'earth_support_above_water_m':2,'approach_grade':.08},
 'mill_candidates':[{'id':'MILL_01','xz_m':[360,320],'forebay_y_m':.5,'tailwater_y_m':-.3,'gross_head_m':.8},{'id':'MILL_02','xz_m':[400,355],'forebay_y_m':-.4,'tailwater_y_m':-1.2,'gross_head_m':.8}],
 'stairs':{'width_m':2.4,'tread_m':.3,'maximum_design_riser_m':.15,'examples':[{'risers':14,'total_rise_m':2},{'risers':26,'total_rise_m':3.84}],'gameplay_design_not_historical':True},
 'hydraulics_validated':False,'quality':'No source or network is certified potable.'}


def base(kind,network,datum):
 a=Source(kind,[-1,-1,-1],[1,1,1]);a.design += ['Source local coordinates only; whole-city location, hydrology, collision and visual review remain pending.']
 a.network=network;a.datum=datum;a.parameters={};a.smoke_pitch=.2
 return a


def finish(a):
 m=a.finish();m['id']='v3_waterworks_'+a.kind;m['materials']=approved_palette('slate_gray')
 m['provenance'].update(author=ref(AUTHOR),source_grammar=ref('world_city/runtime_city/parts/author.py'),
   concept=ref('world_city/reference/revision_03/city_social_water_concept.png'),prompt=ref('world_city/reference/revision_03/prompt.txt'),
   terrain_contract=ref('world_city/concept_city_v3/topography/author.py'),new_engine=False,new_mesher=False,
   image_basis='Approved v3 concept establishes facility roles only; dimensions are explicit source/head contracts or provisional module design.',
   inferred='All geometry, mechanical dimensions, lining thicknesses, clearances and bridge arch shape are authored game design.')
 m['provenance']['source_files']=[ref('voxel_character/common/assets/house/master.json'),ref('world_city/runtime_city/revisions/r2/city_history.r2.candidate.json')]
 b=source_bounds(m);e=m['extensions'];e['local_bounds_m']=b;e['footprint_xz_m']=[[b['min'][0],b['min'][2]],[b['max'][0],b['min'][2]],[b['max'][0],b['max'][2]],[b['min'][0],b['max'][2]]]
 e.update(network=a.network,datum=a.datum,authored_parameters=a.parameters,source_present=True,compiled_sample='See hash-verified inventory.json and evidence/compile_report.json',actual_placed=False,visually_reviewed=False,fluid_surface_owner='Separate terrain/water source. This master contains no solid water volume.',status='local_source_prototype_pending_art_and_placement')
 e['lod']['candidate_visual_pitches_m']=[a.smoke_pitch,.4];e['lod']['thin_rope_policy']='No ropes in these modules. All small members are explicit source geometry.'
 return m


def lining(a,width,length,bed,bank,wall=.4):
 a.box('bed_liner',[-width/2-wall,bed-.3,-length/2],[width/2+wall,bed,length/2],'stone_dark',component='lining')
 for side in (-1,1):
  lo,hi=(-width/2-wall,-width/2) if side<0 else (width/2,width/2+wall)
  a.box('bank_'+str(side),[lo,bed,-length/2],[hi,bank,length/2],'stone',component='lining')
 a.socket('upstream',[0,0,-length/2],'water_inlet_head',(0,0,-1));a.socket('downstream',[0,0,length/2],'water_outlet_head',(0,0,1))
 a.support('liner_base',[-width/2-wall,bed-.3,-length/2],[width/2+wall,bed-.2,length/2],'Excavated bearing ground and exterior bank fill; matching wet domain must remain empty.')


def make_master(kind,spec=None):
 spec=spec or {}
 if kind not in KINDS:raise ValueError(kind)
 if kind=='spring_intake':
  a=base(kind,'raw_clean_source','Y=0 inlet water head; align with source node, not ground.');lining(a,2,4,-.6,.6)
  a.box('headwall',[-1.4,-.6,-2],[1.4,1.2,-1.6],component='headwall')
  a.box('inlet_opening',[-.65,-.5,-2.01],[.65,.5,-1.59],component='headwall',action='cut')
  a.box('covered_intake',[-1.4,1.2,-2],[1.4,1.5,-.4],'stone_light',component='cover')
  a.clearance('wet_outlet',[-.95,-.55,-1.5],[.95,.55,2.01],'Continuous 2 m spring feeder connection.')
  a.socket('spring', [0,0,-2],'raw_source_head',(0,0,-1));a.parameters={'wet_width_m':2,'bed_y_m':-.6,'outlet_head_y_m':0}
 elif kind=='covered_wellhouse':
  a=base(kind,'protected_supply','Y=0 dry draw platform; nominal water head Y=-2 is an adjustable interface, not a new aquifer.')
  a.box('platform',[-2,-.3,-2],[2,0,2],component='platform')
  a.op('shaft_opening',{'kind':'annulus','inner_radius':0,'outer_radius':.7,'y_min':-.31,'y_max':.01},component='platform',action='cut')
  a.op('lined_shaft',{'kind':'annulus','inner_radius':.7,'outer_radius':1.05,'y_min':-2.4,'y_max':1.0},'stone_light',component='shaft')
  for x in (-1.4,1.4):
   for z in (-1.4,1.4):a.box(f'post_{x}_{z}',[x-.15,0,z-.15],[x+.15,3,z+.15],'timber',component='frame')
  for side in (-1,1):
   poly=[[-2,3],[0,4.2],[0,3.9],[-2,2.7]] if side<0 else [[0,4.2],[2,3],[2,2.7],[0,3.9]]
   a.op('roof_'+str(side),extrusion(poly,-1.9,1.9),'slate',component='roof')
  a.beam('windlass',[-1.4,1.6,0],[1.4,1.6,0],.16,'timber_dark',component='windlass',part='drum',pivot=(0,1.6,0))
  a.hook('draw_windlass','windlass','drum',[0,1.6,0],[1,0,0],'rotation_degrees',[0,360])
  a.socket('water_head',[0,-2,0],'covered_supply_or_local_cistern');a.socket('draw_point',[0,1.1,0],'manual_bucket_draw')
  a.clearance('shaft_clear',[-.45,-2.3,-.45],[.45,1.0,.45],'Open shaft below windlass.')
  a.support('platform_ground',[-2,-.3,-2],[2,-.2,2],'Dry level ground; shaft requires a reserved excavation.')
  a.parameters={'dry_platform_m':4,'nominal_head_below_platform_m':2,'shaft_clear_diameter_m':1.4,'roof_top_m':4.2}
 elif kind=='reservoir_lining_segment':
  a=base(kind,'raw_clean_source','Y=0 reservoir water (+16 world in current candidate); bank +2, bed -2.4.');a.parameters={'repeat_length_m':8,'wet_side':'+Z','bank_y_m':2,'bed_y_m':-2.4}
  a.box('retaining_lining',[-4,-2.7,-.6],[4,1.7,0],component='lining')
  a.box('coping',[-4,1.7,-.7],[4,2,.1],'stone_light',component='coping')
  a.box('bed_apron',[-4,-2.7,0],[4,-2.4,2],'stone_dark',component='lining')
  a.socket('repeat_left',[-4,0,0],'reservoir_lining_join',(-1,0,0));a.socket('repeat_right',[4,0,0],'reservoir_lining_join',(1,0,0))
  a.socket('bank',[0,2,-.6],'dry_bank_edge');a.support('base',[-4,-2.7,-.6],[4,-2.6,2],'Excavated base at/below water-2.7; exterior soil support required.')
  a.clearance('stored_water',[-4,-2.39,.11],[4,1.5,2],'Keep reservoir water and storage volume free of opaque solids.')
 elif kind=='sluice_bay':
  a=base(kind,'industrial_nonpotable','Y=0 upstream water head; local outlet head -0.2 is a candidate control step.');lining(a,2,3,-.8,1.2)
  for x in (-1.25,1.25):a.box('gate_post_'+str(x),[x-.18,-.8,-.3],[x+.18,2.6,.3],'timber_dark',component='gate_frame')
  a.box('crosshead',[-1.6,2.35,-.35],[1.6,2.7,.35],'timber',component='gate_frame')
  a.box('raised_gate',[-1.02,.4,-.15],[1.02,1.8,.15],'timber',component='gate',part='leaf',pivot=(0,.4,0))
  a.box('lift_stem',[-.11,1.8,-.11],[.11,3.5,.11],'iron',component='stem',part='stem',pivot=(0,1.8,0))
  a.hook('gate_lift','gate','leaf',[0,.4,0],[0,1,0],'translation_metres',[-1.2,.6]);a.hook('stem_lift','stem','stem',[0,1.8,0],[0,1,0],'translation_metres',[-1.2,.6])
  a.clearance('open_under_gate',[-.9,-.7,-1.4],[.9,.3,1.4],'Raised sample gate preserves a wet opening; shut state remains unimplemented.')
  a.socket('downstream_head',[0,-.2,1.5],'candidate_outlet_head');a.parameters={'clear_gate_width_m':2,'sample_gate_bottom_y_m':.4,'upstream_head_y_m':0,'candidate_downstream_head_y_m':-.2}
  a.connections.append({'id':'gate_rig','parts':['gate.leaf','stem.stem'],'status':'Translate together; synchronized runtime controller not implemented.'})
  a.design += ['This 2 m control bay needs a separately authored taper or bypass to join the 6 m canal. It is not the full-width city floodgate.']
 elif kind=='covered_clean_conduit':
  a=base(kind,'protected_supply','Y=0 invert; requires downhill alignment or explicit engineered pressure design.')
  a.box('casing',[-.6,-.3,-2],[.6,1.1,2],component='conduit');a.box('bore',[-.3,0,-2.01],[.3,.8,2.01],component='conduit',action='cut')
  a.clearance('wet_bore',[-.29,.01,-2.01],[.29,.79,2.01],'Separate protected supply bore; never connect storm/industrial nodes.')
  a.socket('inlet',[0,0,-2],'protected_supply_invert',(0,0,-1));a.socket('outlet',[0,0,2],'protected_supply_invert',(0,0,1));a.support('base',[-.6,-.3,-2],[.6,-.2,2],'Buried supported conduit bed, sealed joints and independent network alignment required.')
  a.parameters={'bore_width_m':.6,'bore_height_m':.8,'repeat_length_m':4};a.design+=['Cover is source geometry; seals, pressure rating and potable quality are unverified.']
 elif kind=='service_channel_segment':
  a=base(kind,'industrial_nonpotable','Y=0 local channel water head; longitudinal grades require source placement design.');lining(a,6,6,-.8,1.2)
  a.clearance('wet_channel',[-2.99,-.79,-3.01],[2.99,1.19,3.01],'6 m open nonpotable canal.');a.parameters={'wet_width_m':6,'bed_y_m':-.8,'bank_top_y_m':1.2,'repeat_length_m':6,'reserved_total_width_m':14}
 elif kind=='undershot_mill_wheel':
  a=base(kind,'industrial_nonpotable','Y=0 forebay head; tailwater -0.8; wheel axle +0.8. Flow along +Z, axle along X.')
  # Annulus native Y axis is rotated to X; all rotating members share one part/pivot.
  rot={'basis':[[0,1,0],[-1,0,0],[0,0,1]],'translation':[0,.8,0]}
  for x in (-.6,.6):
   shape={'kind':'annulus','inner_radius':1.22,'outer_radius':1.5,'y_min':x-.12,'y_max':x+.12}
   a.op('rim_'+str(x),shape,'timber_dark',component='wheel',part='rotor',pivot=(0,.8,0),transform=rot)
  for i in range(12):
   angle=2*math.pi*i/12;y=.8+1.42*math.cos(angle);z=1.42*math.sin(angle)
   a.box('paddle_'+str(i),[-.8,-.16,-.13],[.8,.16,.13],'timber',component='wheel',part='rotor',pivot=(0,.8,0),transform={'translation':[0,y,z],'basis':[[1,0,0],[0,math.cos(angle),-math.sin(angle)],[0,math.sin(angle),math.cos(angle)]]})
   for x in (-.6,.6):a.beam(f'spoke_{i}_{x}',[x,.8,0],[x,y,z],.1,'timber',component='wheel',part='rotor',pivot=(0,.8,0))
  a.beam('axle',[-1.6,.8,0],[1.6,.8,0],.18,'timber_dark',component='wheel',part='rotor',pivot=(0,.8,0))
  a.hook('wheel_rotation','wheel','rotor',[0,.8,0],[1,0,0],'rotation_degrees',[0,360]);a.socket('drive_axle',[-1.6,.8,0],'millhouse_drive',(-1,0,0));a.socket('bearing_axle',[1.6,.8,0],'outer_bearing',(1,0,0))
  a.clearance('rotor_sweep',[-.95,-.85,-1.65],[.95,2.45,1.65],'Reserve moving sweep from banks, pedestrians and house solids.',False)
  a.support('axle_bearings',[-1.6,.65,-.2],[1.6,.95,.2],'Two external supported bearings at X±1.6, Y+.8; never support only the wheel rim.')
  a.parameters={'wheel_radius_m':1.5,'paddle_width_m':1.6,'axle_y_m':.8,'candidate_gross_head_m':.8,'forebay_y_m':0,'tailwater_y_m':-.8};a.design+=['Undershot/low-breast visual candidate for 0.8 m gross head; wheel power, velocity and machinery are unvalidated.']
 elif kind=='mill_bank_interface':
  a=base(kind,'industrial_nonpotable','Y=0 forebay head; bank-side work floor +1.2, axle +0.8. House occupies X<=-1.8.')
  a.box('bank_bearing',[-5,-1.2,-2.5],[-1.8,1.2,2.5],'stone_dark',component='bank_support')
  a.box('drive_wall',[-2.2,1.2,-2.5],[-1.8,4.2,2.5],component='drive_wall')
  # Low axle tunnel below floor joins protected mill interior machinery envelope.
  a.box('axle_tunnel',[-5,.5,-.35],[-1.79,1.1,.35],component='bank_support',action='cut')
  for x in (-1.6,1.6):
   a.box('bearing_pier_'+str(x),[x-.3,-1.2,-.45],[x+.3,.55,.45],component='bearings');a.box('bearing_cap_'+str(x),[x-.3,.55,-.4],[x+.3,.65,.4],'timber_dark',component='bearings')
  a.socket('axle_left',[-1.6,.8,0],'wheel_drive_bearing',(-1,0,0));a.socket('axle_right',[1.6,.8,0],'wheel_outer_bearing',(1,0,0));a.socket('house_floor',[-3.4,1.2,0],'bank_side_millhouse_host')
  a.clearance('wheel_sweep',[-.95,-.85,-1.65],[.95,2.45,1.65],'Leave rotor sweep empty; put the house on the bank, not in the canal.')
  a.support('footings',[-5,-1.2,-2.5],[1.9,-1.1,2.5],'Bearing footings must reach actual excavated bed or bank. Full support under gaps is not assumed.')
  a.parameters={'bank_floor_y_m':1.2,'axle_y_m':.8,'required_wheel_part':'undershot_mill_wheel','house_side':'negative X','complete_millhouse_present':False}
 elif kind=='canal_footbridge':
  a=base(kind,'crossing','Y=0 deck; matching water head -2.08. Span along X over 6 m canal.');a.parameters={'span_m':9,'walk_width_m':2.4,'water_y_m':-2.08,'abutment_x_m':[-4.2,4.2]}
  a.box('deck',[-4.5,-.3,-1.5],[4.5,0,1.5],'timber',component='deck')
  for x in (-4.2,4.2):a.box('abutment_'+str(x),[x-.3,-1.2,-1.6],[x+.3,-.3,1.6],component='abutments')
  for z in (-1.4,1.4):
   a.box('rail_'+str(z),[-4.5,.9,z-.1],[4.5,1.15,z+.1],'timber',component='rail')
   for x in (-4.3,-2.2,0,2.2,4.3):a.box(f'post_{x}_{z}',[x-.1,0,z-.1],[x+.1,1.15,z+.1],'timber_dark',component='rail')
  a.clearance('pedestrian_deck',[-4.5,.01,-1.2],[4.5,2.3,1.2],'2.4 m clear walking width; abutments remain outside wet width.')
  a.clearance('wet_channel',[-3,-2.8,-1.6],[3,-.31,1.6],'Canal remains open below the crossing.')
  for x in (-4.5,4.5):a.socket('landing_'+str(x),[x,0,0],'pedestrian_path',(1 if x>0 else -1,0,0))
  a.support('banks',[-4.5,-1.2,-1.6],[4.5,-1.1,1.6],'Two end abutments only; terrain/approach support must be authored outside canal wet domain.')
 elif kind=='stone_road_bridge_bay':
  a=base(kind,'crossing','Y=0 deck; matching normal river water head -2.08, candidate bed -5.08. Repeat along X.');a.parameters={'repeat_length_m':16,'road_clear_width_m':7,'water_y_m':-2.08,'candidate_bed_y_m':-5.08,'foundation_y_m':-5.5}
  a.box('stone_bay',[-8,-5.5,-4],[8,0,4],component='arch')
  arch=[[-7,-5.51],[7,-5.51],[7,-3],[6,-2.3],[4,-1.3],[2,-.8],[0,-.65],[-2,-.8],[-4,-1.3],[-6,-2.3],[-7,-3]]
  a.op('barrel_opening',extrusion(arch,-4.01,4.01),component='arch',action='cut')
  for z in (-3.8,3.8):a.box('parapet_'+str(z),[-8,0,z-.2],[8,1.1,z+.2],'stone_light',component='parapet')
  a.clearance('road_deck',[-8,.01,-3.5],[8,3.5,3.5],'7 m clear roadway between parapets.')
  a.clearance('center_waterway',[-3,-4.9,-4.01],[3,-1.31,4.01],'Real under-arch void; navigation clearance is not certified.')
  for x in (-8,8):a.socket('repeat_'+str(x),[x,0,0],'stone_bridge_repeat',(1 if x>0 else -1,0,0))
  a.support('pier_bases',[-8,-5.5,-4],[8,-5.4,4],'Two 1 m half-piers at X[-8,-7] and [7,8]; adjoining bays form piers. Foundation/riverbed matching is required.')
  a.design+=['Arch is a source cut through a bounded mass; no fake dark arch or full river bridge has been placed. Flow, scour, flooding and structural adequacy remain unverified.']
 elif kind=='drain_outfall':
  a=base(kind,'storm','Y=0 outlet invert; receiver head must be below this or an explicit backwater control is required.')
  a.box('headwall',[-1.4,-.4,-.5],[1.4,2,.5],component='headwall');a.box('drain_opening',[-.6,0,-.51],[.6,1.2,.51],component='headwall',action='cut')
  for x in (-1.2,1.2):a.box('wingwall_'+str(x),[x-.2,-.4,.5],[x+.2,.6,2.5],component='wings')
  a.box('erosion_apron',[-1.4,-.4,.5],[1.4,0,2.5],'stone_dark',component='apron')
  a.clearance('outlet_bore',[-.59,.01,-.51],[.59,1.19,2.4],'Storm-only outfall; no protected water connection.')
  a.socket('drain_inlet',[0,0,-.5],'storm_invert',(0,0,-1));a.socket('receiving_water',[0,0,2.5],'receiver_level_check',(0,0,1))
  a.support('headwall_base',[-1.4,-.4,-.5],[1.4,-.3,2.5],'Bearing ground and erosion treatment beyond apron required.');a.parameters={'clear_bore_m':[1.2,1.2],'invert_y_m':0,'backflow_prevention_implemented':False}
 elif kind=='retaining_stair_landing':
  n=int(spec.get('risers',8));rise=float(spec.get('rise_m',1.2));r=rise/n if n else 0
  if not 1<=n<=48 or not 0<r<=.15000001:raise ValueError('Stair needs 1..48 risers with 0 < rise/count <= .15 m')
  half=n*.3/2;end=half+1.2
  a=base(kind,'pedestrian_terrace','Y=0 lower landing, Y=total_rise upper landing. Exact authored game-design risers.');a.smoke_pitch=.15
  a.box('lower_landing',[-1.5,-.3,-end],[1.5,0,-half],component='paving')
  for i in range(n):
   z=-half+i*.3;a.box('step_'+str(i),[-1.5,-.3,z],[1.5,(i+1)*r,z+.3],component='steps')
  a.box('upper_landing',[-1.5,-.3,half],[1.5,rise,end],component='paving')
  for x in (-1.4,1.4):a.box('edge_'+str(x),[x-.1,-.3,-end],[x+.1,rise+.15,end],component='edges')
  a.socket('lower_path',[0,0,-end],'pedestrian_lower_landing',(0,0,-1));a.socket('upper_path',[0,rise,end],'pedestrian_upper_landing',(0,0,1))
  a.support('stair_bed',[-1.5,-.3,-end],[1.5,-.2,end],'Continuous compacted stepped terrace support; do not cantilever across open voids.')
  a.clearance('headroom',[-1.2,rise+.16,-end],[1.2,rise+2.3,end],'2.4 m width protected above the highest adjacent edge. Lower tread clearance is checked per tread.')
  a.parameters={'riser_m':r,'riser_count':n,'tread_m':.3,'total_rise_m':rise,'clear_width_m':2.6,'required_path_width_m':2.4,'landings_each_m':1.2,'historical_measurement':False}
 return finish(a)


def author_all():
 for kind in KINDS:write(HERE/'masters'/f'{kind}.json',make_master(kind))
 write(HERE/'head_contract.json',{'terrain_source':ref('world_city/concept_city_v3/topography/author.py'),'dimensions':HEAD_CONTRACT,'status':'Local interface contract only; no placements or hydraulic certification.'})
 print(json.dumps({'source_masters':len(KINDS),'candidate_cap':CANDIDATE_CAP,'output_cap':OUTPUT_CAP}))
if __name__=='__main__':author_all()
