"""Bounded, additive common-voxel landmark dressings over sealed final110.

This is an author/placement script, not another mesher, terrain builder or engine.
Only new files under this directory are emitted. Native core sources stay intact.
"""
from __future__ import annotations
import copy, hashlib, json, math, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT))
from world_city.runtime_city.landmarks.author import _Author, _extrusion, _box
from voxel_character.common import coordinate_planes, core, render_data
BASE=ROOT/'world_city/concept_city_v3/evidence/r8_final110_runtime_r01/scene.json'
BASE_SHA='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(d,separators=(',',':'),allow_nan=False)+'\n')
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def author(name,w,d,h):return _Author(dict(asset_id=name,kind='wall_tower',width_m=w,depth_m=d,height_m=h))
def finish(a,colors):
 m=a.finish();m['materials'].update(colors)
 m['extensions'].update(additive_attachment=True,ground_route_geometry=False,entry_or_core_replacement=False,
  sampling_policy='Existing common coordinate_planes + core + render_data. No postcompile cell surgery.')
 m['provenance']['r9_author']=ref(Path(__file__))
 return m

def hip_roof(a,w,base,top):
 r=w/2
 a.op('roof','native_hip_roof',_extrusion([[-r,base],[0,top],[r,base]],-r,r),'slate')
 for side in (-1,1):
  a.op('roof','native_hip_cut_'+str(side),_extrusion([[0,top],[side*r,base],[side*r,top+1],[0,top+1]],-r-.01,r+.01),action='cut',transform={'basis':[[0,0,1],[0,1,0],[-1,0,0]],'translation':[0,0,0]})

def turret(name,w,body,roof,corbel):
 a=author(name,w,w,body+roof);r=w/2
 # Stepped load-bearing corbel intersects the retained wall cap at its narrow foot.
 for i in range(4):
  lo=corbel*i/4;hi=corbel*(i+1)/4
  across=1.5+(r-1.5)*(i+1)/4
  a.box('corbel','corbel_'+str(i),[-r+.5,lo,-across],[r-.5,hi,across],'stone_light')
 a.box('masonry','turret_floor',[-r,corbel-.5,-r],[r,corbel+.5,r],'stone_dark')
 a.shell('watch_chamber',-r,r,-r,r,corbel,body,t=.65)
 a.belt('lower_belt',-r-.25,r+.25,-r-.25,r+.25,corbel,corbel+.6,.65)
 a.belt('cornice',-r-.25,r+.25,-r-.25,r+.25,body-.75,body,.65)
 for side in ('front','rear','east','west'):
  a.window('watch_'+side,0,corbel+2,r if side in ('front','east') else -r,2.4,3.4,side)
 hip_roof(a,w+.5,body,body+roof)
 a.features=['roofed_wall_watch_chamber','attached_corbel','four_sided_pointed_windows','native_hip_roof']
 return finish(a,{'slate':'a16b51','slate_dark':'80523f'})

def merlons(name,length,depth,n):
 a=author(name,length,depth,2.5)
 a.box('bearing','cap',[-length/2,0,-depth/2],[length/2,.5,depth/2],'stone_light')
 step=length/n
 for i in range(n):
  x=-length/2+(i+.5)*step
  a.box('battlements','merlon_'+str(i),[x-1,.5,-depth/2],[x+1,2.5,depth/2],'stone_light')
 return finish(a,{})

def cathedral_face():
 a=author('r9_cathedral_gothic_face',14,1.5,70)
 # The local datum is the tower's 28 m stage. Every part is an external relief.
 for x in (-5.5,5.5):
  a.box('dressings','pilaster_'+str(x),[x-.5,0,0],[x+.5,68,1.0],'stone_light')
 for i,(y,depth) in enumerate(((7,1.0),(30,1.25),(42,1.0),(65,1.5),(68,1.5))):
  a.box('dressings','stage_belt_'+str(i),[-6.5,y,0],[6.5,y+.75,depth],'stone_light')
 for stage,(y,h,w) in enumerate(((13,14,2.5),(33,8,2.5),(45,16,3.5))):
  for x in (-2.5,2.5):
   a.window('raised_lancet_'+str(stage)+'_'+str(x),x,y,1,w,h,'front',pointed=True)
   # Projected mullions/louvre bars remain robust at the native exterior pitch.
   a.box('tracery','mullion_'+str(stage)+'_'+str(x),[x-.25,y+.5,.5],[x+.25,y+h-1,1.5],'stone_light')
   if stage==2:
    for j in range(6):
     yy=y+1.5+j*1.65
     a.box('tracery','louvre_'+str(x)+'_'+str(j),[x-w/2+.5,yy,.5],[x+w/2-.5,yy+.5,1.25],'timber_dark')
 a.features=['four_side_repeatable_gothic_belfry_relief','projecting_mullions','belfry_louvres','stage_cornices']
 return finish(a,{'slate':'646f73','slate_dark':'4a565c'})

def pinnacle():
 a=author('r9_stone_pinnacle',3,3,12)
 a.box('masonry','root',[-1.25,0,-1.25],[1.25,1,1.25],'stone_light')
 a.shell('shaft',-1,1,-1,1,.5,6.5,t=.5)
 a.belt('cap',-1.25,1.25,-1.25,1.25,6,7,.5)
 a.spire('pinnacle',0,0,1.5,7,12)
 for c in a.components.values():
  for op in c['operations']:
   if op.get('material','').startswith('slate'):op['material']='stone_light'
 # 0.5 m thick connected tip instead of a floating finial.
 a.box('roof','connected_tip',[-.25,10.5,-.25],[.25,12,.25],'stone_light')
 return finish(a,{})

def point(parent,x,y,z):
 c,s=math.cos(parent['yaw_rad']),math.sin(parent['yaw_rad']);p=parent['position_m']
 return [p[0]+c*x+s*z,p[1]+y,p[2]-s*x+c*z]
def bounds_world(b,p):
 pts=[point(p,x,y,z) for x in (b['min'][0],b['max'][0]) for y in (b['min'][1],b['max'][1]) for z in (b['min'][2],b['max'][2])]
 return {'min':[min(q[i] for q in pts)for i in range(3)],'max':[max(q[i]for q in pts)for i in range(3)]}

def build():
 start=time.monotonic();assert sha(BASE)==BASE_SHA
 ctx=json.loads((HERE/'base_instance_context.json').read_text());assert ctx['base_scene_sha256']==BASE_SHA
 native={p['id']:p for p in ctx['common_instances']};assets={};reports=[]
 defs=[turret('r9_city_roofed_bartizan',8,12,6,3.5),turret('r9_castle_roofed_bartizan',6,10,5,2),merlons('r9_city_merlon_rhythm',16,3,4),merlons('r9_castle_merlon_rhythm',12,1.5,3),cathedral_face(),pinnacle()]
 for m in defs:
  before=core.digest(m);t=time.monotonic();c=coordinate_planes.compile_master(m,{'pitch':.5},max_candidate_cells=250000,max_output_cells=100000)
  assert c['valid'],c['constraints'];assert before==core.digest(m)
  rd=render_data.make_render_data(c);sp=HERE/'masters'/(m['id']+'.json');rp=HERE/'cache'/(m['id']+'.pitch_0.5.render.json');write(sp,m);write(rp,rd)
  assets[m['id']]={'master_path':ref(sp)['path'],'master_sha256':sha(sp),'render_path':ref(rp)['path'],'render_sha256':sha(rp),'pitch_m':.5,'quad_count':rd['quad_count'],'bounds':rd['bounds'],'source':ref(sp),'cache':ref(rp)}
  reports.append({'id':m['id'],'valid':True,'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells']),'quad_count':rd['quad_count'],'bounds':rd['bounds'],'constraints':c['constraints'],'seconds':round(time.monotonic()-t,3)})
  print(json.dumps({k:v for k,v in reports[-1].items() if k!='constraints'}),flush=True)
 add=[];attachment=[]
 def place(key,id,parent,offset=(0,0,0),dyaw=0,floor=None,reason='upper masonry attachment'):
  p={'id':'R9_LANDMARK:'+id,'asset_key':key,'position_m':point(parent,*offset),'yaw_rad':parent['yaw_rad']+dyaw,'scale':[1,1,1],'palette_id':'r9_landmark_native','palette_override':{},'source_pack':'r9_landmark_silhouettes','collision_policy':'native_common_mesh'}
  b=bounds_world(assets[key]['bounds'],p);floor=parent['position_m'][1] if floor is None else floor
  row={'id':p['id'],'native_parent_id':parent['id'],'native_parent_asset':parent['asset_key'],'local_attachment_offset_m':list(offset),'world_bounds_m':b,'native_ground_datum_m':floor,'minimum_clearance_above_native_ground_m':b['min'][1]-floor,'intentional_overlap':reason,'ground_route_encroachment':False}
  assert row['minimum_clearance_above_native_ground_m']>=5.49,(id,row)
  add.append(p);attachment.append(row)
 # All regular retained 16 m wall segments acquire legible, real merlon silhouettes.
 regular=[p for p in native.values() if p['id'].startswith('FORT_CURTAIN_') and p['asset_key']=='registered_curtain16_h14']
 for p in regular:place('r9_city_merlon_rhythm','MERLONS:'+p['id'],p,(0,14.5,0),reason='Cap overlaps existing 14–15 m parapet; XY core unchanged.')
 # One small watch chamber on the central regular module of most wall runs.
 # Original principal gate/large tower groups stay visually dominant.
 skip={'04','17','19','22','23'};groups={}
 for p in regular:groups.setdefault(p['id'].split('_')[2],[]).append(p)
 selected=[]
 for group,ls in sorted(groups.items()):
  if group in skip:continue
  # Adjacent roof exclusions found during conservative bbox review.
  p=native[{'05':'FORT_CURTAIN_05_0_01','09':'FORT_CURTAIN_09_0_01'}[group]] if group in ('05','09') else ls[len(ls)//2]
  if any(math.dist([p['position_m'][0],p['position_m'][2]],[q['position_m'][0],q['position_m'][2]])<28 for q in native.values() if q['id'].startswith('FORT_TOWER:') and ':FOOTING' not in q['id']):continue
  place('r9_city_roofed_bartizan','WATCH:'+group,p,(0,10.5,0),reason='Corbel foot bears on the existing wall centre; lowest geometry is 10.5 m above its native ground.')
  selected.append(p['id'])
 # Four corner turrets and a gate crown on the retained castle curtain quadrilateral.
 for side in ('rear','front'):
  p=native['castle_registered:'+side+'_curtain']
  for x in (-51,51):place('r9_castle_roofed_bartizan','CASTLE:'+side+':'+str(x),p,(x,5.5,0),reason='Corbel root overlaps upper castle curtain at its corner, above the ground circulation band.')
 p=native['castle_registered:front_curtain'];place('r9_castle_roofed_bartizan','CASTLE:gate_crown',p,(0,5.5,0),reason='High crown above retained gate; lower edge at +5.5 m preserves its existing pedestrian/vehicle throat.')
 for side in ('rear','front','east','west'):
  p=native['castle_registered:'+side+'_curtain']
  for x in range(-42,43,12):place('r9_castle_merlon_rhythm','CASTLE_MERLONS:'+side+':'+str(x),p,(x,6,0),reason='New merlons bear on retained castle parapet at +6 m; no core or entrance cuts.')
 # Four repeated facade skins anchored outside the native 12 m tower, all above +28 m.
 tower=native['cathedral_registered:single_bell_tower']
 for n,(x,z,ang) in enumerate(((0,6,0),(6,0,math.pi/2),(0,-6,math.pi),(-6,0,-math.pi/2))):
  place('r9_cathedral_gothic_face','CATHEDRAL:face:'+str(n),tower,(x,28,z),ang,reason='External relief directly touches retained tower face; no substitution or widening of the ground core.')
 for x in (-5.5,5.5):
  for z in (-5.5,5.5):place('r9_stone_pinnacle','CATHEDRAL:pinnacle:'+str(x)+':'+str(z),tower,(x,90,z),reason='Pinnacle foot overlaps tower corner and high cornice; central 128 m spire retained.')
 for p in native.values():
  if p['id'].startswith('cathedral_registered:flying_'):
   place('r9_stone_pinnacle','CATHEDRAL:buttress:'+p['id'].split(':')[-1],p,(5.35,23.5,0),reason='Pinnacle root overlaps native flying-buttress pier/cap, +23.5 m above precinct circulation.')
 pack={'schema':'riverstone.city.visual_addendum.v1','base_scene_sha256':BASE_SHA,'common_assets':assets,'add_instances':add,'remove_instance_ids':[],
  'inspection_cameras':{'r9_castle_silhouette':{'position_m':[-150,170,-75],'target_m':[-290,44,-290]},'r9_cathedral_belfry':{'position_m':[277,141,-97],'target_m':[209,101,-210]}}}
 write(HERE/'pack.json',pack);write(HERE/'attachment_ledger.json',{'schema':'riverstone.city.additive_upper_geometry_ledger.v1','rows':attachment,'minimum_clearance_above_native_ground_m':min(p['minimum_clearance_above_native_ground_m']for p in attachment)})
 write(HERE/'compile_report.json',{'status':'pass','base_scene_sha256':BASE_SHA,'assets':reports,'new_assets':len(assets),'instances':len(add),'city_watch_turrets':len(selected),'native_wall_attachment_ids':selected,'retired_ids':[],'whole_city_compile':False,'new_engine':False,'source_files_unchanged':sha(BASE)==BASE_SHA,'seconds':round(time.monotonic()-start,3),'runtime_visual_review':'Parent integration required; not claimed by compile tests.'})
 print('PACK',len(assets),'assets',len(add),'instances',len(selected),'city watch turrets',flush=True)
if __name__=='__main__':build()
