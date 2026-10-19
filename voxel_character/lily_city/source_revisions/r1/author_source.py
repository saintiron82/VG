"""Deterministic Lily r1 art authoring. All sampling is in the unchanged common core.
Run deliberately to rewrite owned source JSON; build.py only reads these sources.
"""
from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'common'))
from core import digest

PALETTE={
 'skin':'edc3ac','skin_shadow':'ce9b89','skin_light':'f8d7be',
 'silver':'c9d7df','silver_light':'ecf2ed','silver_shadow':'8397aa',
 'teal_wool':'285960','teal_light':'41777a','teal_shadow':'193e47',
 'linen':'e6ddc4','linen_shadow':'bbae92','leather':'654a3a',
 'leather_light':'8c6650','leather_dark':'3b302a','brass':'c4a15f',
 'eye_white':'f4efe2','iris':'299b98','iris_light':'70d5c4','pupil':'182e39',
 'lip':'a76562','lip_light':'d78b7b','sole':'302d2b'
}

def make_sources():
 parts=[];ops=[];rig=[]
 def part(name,pivot,parent=None,role='body'):
  parts.append({'id':name,'pivot':pivot,'metadata':{'parent_part':parent,'role':role}})
  rig.append({'id':name,'parent':parent,'pivot_m':pivot,'role':role})
 def box(part_id,feature,material,lo,hi):
  ops.append({'id':feature,'part':part_id,'action':'paint','material':material,
   'shape':{'kind':'box','min':lo,'max':hi,'minimum_cells':[1,1,1]}})
 def prism(part_id,feature,material,poly,zlo,zhi):
  ops.append({'id':feature,'part':part_id,'action':'paint','material':material,
   'shape':{'kind':'extrusion','polygon':poly,'z_min':zlo,'z_max':zhi,'minimum_cells':1}})
 part('pelvis',[0,.94,0]);part('torso',[0,1.05,0],'pelvis')
 prism('pelvis','tunic_hip','teal_wool',[[-.19,.85],[.19,.85],[.18,1.05],[-.18,1.05]],-.12,.13)
 prism('torso','tailored_wool_bodice','teal_wool',[[-.17,1.02],[.17,1.02],[.23,1.31],[.18,1.40],[-.18,1.40],[-.23,1.31]],-.13,.14)
 box('torso','neck','skin',[-.075,1.36,-.07],[.075,1.46,.08])
 for s,label in [(-1,'l'),(1,'r')]:
  x1,x2=sorted([s*.04,s*.13])
  prism('torso','ivory_collar_'+label,'linen',[[x1,1.35],[x2,1.38],[x2,1.41],[x1,1.39]],.14,.18)
 box('pelvis','belt','leather_dark',[-.195,.99,-.145],[.195,1.055,.16])
 box('pelvis','belt_buckle_brass','brass',[-.045,1.00,.16],[.045,1.055,.19])
 box('pelvis','belt_buckle_inset','leather',[-.022,1.015,.18],[.022,1.04,.20])
 for y in [1.12,1.18,1.24,1.30]:
  box('torso','front_lacing_'+str(y),'brass',[-.035,y,.14],[.035,y+.02,.16])
 # Silver hair is geometric layered planes and solid locks, not a face texture.
 part('head',[0,1.405,0],'torso','head')
 prism('head','face_shape','skin',[[-.14,1.46],[.14,1.46],[.18,1.52],[.18,1.69],[.14,1.73],[-.14,1.73],[-.18,1.69],[-.18,1.52]],-.12,.14)
 box('head','nose_bridge','skin_light',[-.02,1.55,.14],[.02,1.62,.18])
 box('head','nose_tip','skin',[-.035,1.54,.16],[.035,1.57,.20])
 for s,label in [(-1,'l'),(1,'r')]:
  x=s*.105
  box('head','ear_'+label,'skin_shadow',[s*.18-.02,1.55,-.035],[s*.18+.02,1.63,.04])
  box('head','eye_white_'+label,'eye_white',[x-.055,1.59,.14],[x+.055,1.65,.16])
  box('head','iris_'+label,'iris',[x-.025,1.59,.16],[x+.025,1.65,.18])
  box('head','iris_light_'+label,'iris_light',[x-.025,1.59,.18],[x+.005,1.61,.20])
  box('head','pupil_'+label,'pupil',[x-.01,1.61,.18],[x+.01,1.65,.20])
  box('head','eye_glint_'+label,'eye_white',[x-.02,1.63,.20],[x,1.65,.22])
  box('head','cheek_'+label,'skin_shadow',[x-.035,1.53,.14],[x+.035,1.55,.16])
 part('hair',[0,1.405,0],'head','hair')
 prism('hair','hair_crown','silver',[[-.20,1.63],[.20,1.63],[.20,1.73],[.16,1.77],[-.14,1.77],[-.20,1.73]],-.16,.12)
 box('hair','hair_rear_mass','silver_shadow',[-.20,1.42,-.18],[.20,1.70,-.12])
 for i,(x,width,bottom) in enumerate([(-.18,.06,1.48),(-.12,.06,1.67),(-.06,.06,1.69),(0,.06,1.71),(.06,.06,1.67),(.12,.04,1.65),(.16,.04,1.49)]):
  prism('hair',f'fringe_lock_{i}','silver_light' if i%3==0 else 'silver',[[x,bottom+.02],[x+width,bottom],[x+width,1.74],[x,1.74]],.10,.18)
 for x in [-.18,-.10,.02,.12]:
  box('hair','rear_silver_strand_'+str(x),'silver_light',[x,1.46,-.20],[x+.02,1.73,-.18])
 part('braid',[.14,1.48,-.16],'hair','secondary')
 for i in range(8):
  x=.13+(i%2)*.02;y=1.45-i*.055
  box('braid',f'braid_segment_{i}','silver' if i%2 else 'silver_light',[x-.045,y-.055,-.21],[x+.045,y+.015,-.13])
 box('braid','braid_tie','teal_light',[.09,1.03,-.22],[.20,1.07,-.12])
 # Independent upper/lower limbs use named joint pivots, true volume and overlap.
 for s,label in [(-1,'left'),(1,'right')]:
  x=s*.27
  part('upper_arm_'+label,[x,1.32,0],'torso')
  box('upper_arm_'+label,'sleeve_'+label,'linen',[x-.07,1.10,-.08],[x+.07,1.34,.09])
  box('upper_arm_'+label,'shoulder_wool_'+label,'teal_shadow',[x-.08,1.27,-.10],[x+.08,1.36,.10])
  box('upper_arm_'+label,'sleeve_fold_'+label,'linen_shadow',[x-.07,1.12,-.09],[x+.07,1.15,.10])
  part('forearm_'+label,[x,1.11,0],'upper_arm_'+label)
  box('forearm_'+label,'lower_sleeve_'+label,'linen',[x-.065,.88,-.075],[x+.065,1.12,.075])
  box('forearm_'+label,'leather_cuff_'+label,'leather',[x-.07,.87,-.08],[x+.07,.94,.085])
  box('forearm_'+label,'cuff_brass_'+label,'brass',[x-.015,.895,.085],[x+.015,.915,.105])
  part('hand_'+label,[x,.88,0],'forearm_'+label)
  box('hand_'+label,'palm_'+label,'skin',[x-.055,.78,-.055],[x+.055,.89,.055])
  box('hand_'+label,'thumb_'+label,'skin_light',[x-s*.07-.018,.815,.02],[x-s*.07+.018,.88,.065])
  lx=s*.105
  part('thigh_'+label,[lx,.92,0],'pelvis')
  box('thigh_'+label,'wool_trouser_'+label,'teal_shadow',[lx-.075,.50,-.085],[lx+.075,.94,.085])
  part('shin_'+label,[lx,.52,0],'thigh_'+label)
  box('shin_'+label,'boot_shaft_'+label,'leather',[lx-.08,.12,-.08],[lx+.08,.53,.09])
  box('shin_'+label,'boot_cuff_'+label,'leather_light',[lx-.09,.44,-.09],[lx+.09,.52,.10])
  box('shin_'+label,'boot_front_seam_'+label,'leather_light',[lx-.015,.16,.09],[lx+.015,.44,.11])
  part('foot_'+label,[lx,.12,0],'shin_'+label)
  box('foot_'+label,'boot_foot_'+label,'leather',[lx-.09,.035,-.095],[lx+.09,.15,.185])
  box('foot_'+label,'boot_toe_'+label,'leather_light',[lx-.08,.035,.15],[lx+.08,.10,.215])
  box('foot_'+label,'boot_sole_'+label,'sole',[lx-.095,0,-.10],[lx+.095,.04,.22])
  part('skirt_'+label,[s*.1,.99,0],'pelvis','cloth')
  poly=[[-.26,.62],[-.04,.62],[-.02,.99],[-.18,1.02]] if s<0 else [[.04,.62],[.26,.62],[.18,1.02],[.02,.99]]
  prism('skirt_'+label,'split_overskirt_'+label,'teal_wool',poly,-.14,.15)
  box('skirt_'+label,'hem_binding_'+label,'teal_light',[(-.26 if s<0 else .04),.62,.15],[(-.04 if s<0 else .26),.66,.17])
  for dx in [.09,.17]:
   xx=s*dx
   box('skirt_'+label,'skirt_embroidered_'+label+str(dx),'brass',[xx-.01,.68,.15],[xx+.01,.70,.17])
 part('cape',[0,1.32,-.13],'torso','cloth')
 prism('cape','short_shoulder_mantle','teal_shadow',[[-.24,.99],[.24,.99],[.24,1.31],[.14,1.39],[-.14,1.39],[-.24,1.31]],-.20,-.13)
 box('torso','mantle_clasp','brass',[-.03,1.33,.17],[.03,1.37,.20])
 part('satchel',[-.18,1.02,-.03],'pelvis','equipment')
 box('satchel','satchel_body','leather',[-.31,.80,-.08],[-.18,1.00,.10])
 box('satchel','satchel_flap','leather_light',[-.32,.93,-.09],[-.17,1.02,.12])
 box('satchel','satchel_buckle','brass',[-.27,.91,.10],[-.23,.95,.14])
 # Face controls are separately movable voxel volumes, always parented to head.
 for s,label in [(-1,'left'),(1,'right')]:
  x=s*.105
  part('eyelid_'+label,[x,1.675,.18],'head','blink')
  box('eyelid_'+label,'upper_lid_'+label,'skin',[x-.055,1.66,.18],[x+.055,1.72,.22])
  box('eyelid_'+label,'lash_'+label,'silver_shadow',[x-.055,1.66,.22],[x+.055,1.68,.24])
  part('brow_'+label,[x,1.68,.20],'head','expression')
  box('brow_'+label,'brow_voxels_'+label,'silver_shadow',[x-.055,1.68,.22],[x+.055,1.70,.24])
  part('mouth_corner_'+label,[s*.04,1.505,.16],'head','expression')
  box('mouth_corner_'+label,'lip_corner_'+label,'lip',[s*.04-.02,1.495,.14],[s*.04+.02,1.515,.18])
 part('mouth',[0,1.50,.16],'head','expression')
 box('mouth','lower_lip','lip_light',[-.025,1.485,.14],[.025,1.505,.18])
 box('mouth','mouth_line','lip',[-.025,1.505,.14],[.025,1.525,.18])
 master={'schema':'riverstone.voxel.master.v1','id':'lily_medieval_city_r1','revision':1,
 'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],
 'materials':PALETTE,'components':[{'id':'lily','parts':parts,'operations':ops}],
 'instances':[{'id':'lily','component':'lily'}],'constraints':[],
 'extensions':{'provenance':{'kind':'new_authored_character','not_recovered':'B7 character/animation is unavailable; this is a new compatible character using recovered common modules.'},
 'dimensions':{'standing_height_m':1.76,'reference_pitch_m':.02,'units':'m'},
 'style':{'hair':'layered silver, tied side braid','eyes':'teal','clothing':'ivory linen sleeves, teal wool split tunic and mantle, leather boots/belt/satchel; medieval fantasy'}}}
 h=digest(master)
 def track(pid,angles=None,translations=None,axis=[1,0,0],duration=1,times=None):
  angles=angles or [0,0];translations=translations or [[0,0,0] for _ in angles]
  times=times or [duration*i/(len(angles)-1) for i in range(len(angles))]
  return {'id':pid,'type':'rigid_transform','selector':{'instance':'lily','part':pid},'axis':axis,
   'space':'part','interpolation':'smoothstep','keys':[{'time':t,'rotation_degrees':a,'translation':tr} for t,a,tr in zip(times,angles,translations)]}
 def clip(name,tracks,duration=1,loop=True):return {'schema':'riverstone.voxel.transform_animation.v1','id':name,'source_id':master['id'],'master_hash':h,'duration':duration,'loop':loop,'tracks':tracks}
 bind=clip('all_parts_rest',[track(p['id']) for p in parts])
 body=[p['id'] for p in rig if p['role'] not in ['blink','expression']]
 idle=[];walk=[]
 for pid in body:
  idle.append(track(pid,[0,.8,0,-.8,0] if pid in ['head','braid','cape'] else [0,0,0,0,0],
   [[0,y,0] for y in [0,.004,.008,.004,0]] if pid=='torso' else None,duration=4))
  a=[0,0,0,0,0]
  if pid.startswith('thigh_'):a=[22,0,-22,0,22] if pid.endswith('left') else [-22,0,22,0,-22]
  elif pid.startswith('shin_'):a=[0,30,0,0,0] if pid.endswith('left') else [0,0,0,30,0]
  elif pid.startswith('upper_arm_'):a=[-18,0,18,0,-18] if pid.endswith('left') else [18,0,-18,0,18]
  elif pid.startswith('forearm_'):a=[-8,-16,-8,-5,-8] if pid.endswith('left') else [-8,-5,-8,-16,-8]
  elif pid.startswith('foot_'):a=[-5,0,5,0,-5] if pid.endswith('left') else [5,0,-5,0,5]
  elif pid.startswith('skirt_'):a=[5,0,-5,0,5] if pid.endswith('left') else [-5,0,5,0,-5]
  elif pid in ['braid','cape']:a=[-3,3,-3,3,-3]
  if pid=='pelvis':
   # Authored visual root compensation: keep the lowest boot near the sole
   # plane over the gait. It never moves the gameplay body or its collider.
   sole_y=[.001,.012,.030,.039,.040,.046,.017,.009,.001,.012,.030,.039,.040,.046,.017,.009,.001]
   walk.append(track(pid,[0]*len(sole_y),[[0,y,0] for y in sole_y],duration=.8))
  else:walk.append(track(pid,a,duration=.8))
 face=[p['id'] for p in rig if p['role']=='expression']
 expressions={}
 for name in ['neutral','happy','focused']:
  ts=[]
  for pid in face:
   s=-1 if pid.endswith('left') else 1;angle=0;dy=0
   if name=='happy':
    if pid.startswith('mouth_corner'):angle=s*18;dy=.018
    elif pid.startswith('brow_'):angle=s*5;dy=.008
   if name=='focused' and pid.startswith('brow_'):angle=-s*14;dy=-.008
   ts.append(track(pid,[angle,angle],[[0,dy,0],[0,dy,0]],axis=[0,0,1]))
  expressions[name]=clip(name,ts,loop=False)
 blink=clip('blink',[track('eyelid_'+label,[0]*5,[[0,y,0] for y in [0,0,-.08,0,0]],duration=4.2,times=[0,3.80,3.90,4.03,4.2]) for label in ['left','right']],4.2)
 contract={'schema':'riverstone.character.rig.v1','source_id':master['id'],'master_hash':h,'parts':rig,
 'coordinate_contract':{'units':'m','up':'+Y','front':'+Z','root':'feet at y=0, local origin on sole plane','pitch_is_not_scale':True},
 'capsule':{'radius_m':.23,'height_m':1.72,'center_m':[0,.86,0]},
 'locomotion':{'nominal_walk_speed_mps':1.65,'max_speed_mps':3.2,'walk_cycle_seconds':.8,'floor_snap_m':.20,'floor_max_angle_degrees':45,'safe_margin_m':.001,'gravity_mps2':18.0,'stair_policy':'authored collision surfaces only; no step teleport, auto-jump or waypoint snap'},
 'sockets':{'hand_left':{'part':'hand_left','offset_m':[0,-.05,.04]},'hand_right':{'part':'hand_right','offset_m':[0,-.05,.04]},'head_look':{'part':'head','offset_m':[0,.20,.12]}},
 'motion_channels':{'locomotion':body,'blink':['eyelid_left','eyelid_right'],'expression':face},
 'limits':{'maximum_parts':40,'maximum_candidate_cells_per_layer':1000000,'reference_max_cells':70000,'reference_max_quads':12000,'max_materials':32}}
 return {'master.json':master,'rig.json':contract,'bind.json':bind,'idle.json':clip('idle',idle,4),'walk.json':clip('walk',walk,.8),'blink.json':blink,**{'expression_'+k+'.json':v for k,v in expressions.items()}}

def main():
 ROOT.joinpath('data').mkdir(exist_ok=True)
 for name,data in make_sources().items():
  ROOT.joinpath('data',name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
 print('Authored source only:',len(make_sources()['master.json']['components'][0]['parts']),'parts')
if __name__=='__main__':main()
