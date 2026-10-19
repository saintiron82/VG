"""Second art revision of the shared humanoid source, keeping its semantic rig.
These are source shapes, not runtime detail overlays or per-person generators.
"""
import copy

def refine(master, rig_parts):
 c=master['components'][0]; old=c['operations']; ops=[]
 def box(part,id,mat,lo,hi):
  ops.append({'id':id,'part':part,'action':'paint','material':mat,'shape':{'kind':'box','min':lo,'max':hi,'minimum_cells':[1,1,1]}})
 def prism(part,id,mat,poly,zlo,zhi):
  ops.append({'id':id,'part':part,'action':'paint','material':mat,'shape':{'kind':'extrusion','polygon':poly,'z_min':zlo,'z_max':zhi,'minimum_cells':1}})
 # Keep the known slots and dimensions. Rewrite broad block silhouettes with
 # beveled, tapered source volumes and actual surface relief.
 replaced_prefixes=('sleeve_','shoulder_wool_','lower_sleeve_','palm_','thumb_','lip_corner_')
 for op in old:
  if op['part'] in ('head','hair','braid') or op['id'] in ('belt_buckle_brass','belt_buckle_inset','short_shoulder_mantle','satchel_body','satchel_flap'):continue
  if op['id'].startswith(replaced_prefixes):continue
  item=copy.deepcopy(op)
  if item['id']=='tailored_wool_bodice':item['shape']['polygon']=[[-.155,1.02],[.155,1.02],[.18,1.12],[.205,1.28],[.18,1.37],[.10,1.40],[-.10,1.40],[-.18,1.37],[-.205,1.28],[-.18,1.12]]
  if item['part'].startswith('eyelid_'):
   sign=-1 if item['part'].endswith('left') else 1;dx=sign*(-.025)
   item['shape']['min'][0]+=dx;item['shape']['max'][0]+=dx
   # The original lid front was coplanar with the eye glint. Real thickness
   # now occludes it, without changing the shared .08 m blink track.
   if item['id'].startswith('upper_lid_'):
    center=sign*.08
    item['shape']['min']=[center-.04,1.64,.18]
    item['shape']['max']=[center+.04,1.74,.24]
   else:
    center=sign*.08;item['material']='pupil'
    item['shape']['min']=[center-.04,1.64,.24]
    item['shape']['max']=[center+.04,1.66,.26]
  if item['part'].startswith('brow_'):
   sign=-1 if item['part'].endswith('left') else 1;dx=sign*(-.025)
   item['shape']['min'][0]+=dx;item['shape']['max'][0]+=dx
   item['shape']['min'][2]=.24;item['shape']['max'][2]=.26
  ops.append(item)
 # Cheek/jaw/chin contours are separate-depth slices of one rigid head.
 prism('head','face_shape','skin',[[-.055,1.44],[.055,1.44],[.115,1.47],[.15,1.53],[.16,1.63],[.135,1.69],[.08,1.72],[-.08,1.72],[-.135,1.69],[-.16,1.63],[-.15,1.53],[-.115,1.47]],-.10,.12)
 prism('head','face_front_cheek_plane','skin',[[-.055,1.45],[.055,1.45],[.115,1.49],[.14,1.55],[.14,1.65],[.10,1.69],[-.10,1.69],[-.14,1.65],[-.14,1.55],[-.115,1.49]],.12,.14)
 prism('head','chin_rounding','skin_light',[[-.045,1.44],[.045,1.44],[.075,1.46],[.065,1.48],[-.065,1.48],[-.075,1.46]],.10,.14)
 box('head','nose_bridge','skin_light',[-.02,1.55,.14],[.02,1.62,.18])
 prism('head','nose_tip','skin',[[-.03,1.55],[.03,1.55],[.02,1.58],[-.02,1.58]],.16,.20)
 for sign,label in [(-1,'l'),(1,'r')]:
  x=sign*.08
  prism('head','ear_'+label,'skin_shadow',[[sign*.15,1.55],[sign*.18,1.57],[sign*.18,1.62],[sign*.15,1.64]],-.04,.035)
  box('head','ear_inner_'+label,'skin',[sign*.16-.01,1.58,-.015],[sign*.16+.01,1.62,.015])
  box('head','eye_white_'+label,'eye_white',[x-.04,1.58,.14],[x+.04,1.64,.16])
  box('head','iris_'+label,'iris',[x-.02,1.58,.16],[x+.02,1.64,.18])
  box('head','iris_light_'+label,'iris_light',[x-.02,1.58,.18],[x,1.60,.20])
  box('head','pupil_'+label,'pupil',[x-.01,1.60,.18],[x+.01,1.64,.20])
  box('head','eye_glint_'+label,'eye_white',[x-.02,1.62,.20],[x,1.64,.22])
  prism('head','cheek_contour_'+label,'skin_light',[[x-.035,1.53],[x+.025,1.53],[x+.035,1.55],[x-.02,1.56]],.14,.16)
 # Round the crown in both width and depth using seven independently shaped
 # cross-section slabs. The front remains open below the swept fringe.
 bands=[(-.20,-.16,.12,1.53,1.70),(-.16,-.12,.17,1.55,1.74),(-.12,-.08,.19,1.62,1.76),(-.08,0,.20,1.67,1.76),(0,.08,.19,1.69,1.76),(.08,.14,.16,1.70,1.74),(.14,.18,.10,1.70,1.72)]
 for i,(z0,z1,w,low,high) in enumerate(bands):
  edge=min(.03,(high-low)/3)
  prism('hair',f'crown_layer_{i}','silver' if i%3 else 'silver_shadow',[[-w+edge,low],[w-edge,low],[w,low+edge],[w,high-edge],[w-edge,high],[-w+edge,high],[-w,high-edge],[-w,low+edge]],z0,z1)
 # Recognizable feature IDs remain available for the cropped/loose presets.
 prism('hair','hair_rear_mass','silver_shadow',[[-.12,1.43],[.10,1.43],[.16,1.49],[.18,1.64],[.13,1.70],[-.13,1.70],[-.18,1.64],[-.16,1.49]],-.17,-.11)
 for i,(x,w,bottom) in enumerate([(-.18,.05,1.50),(-.13,.05,1.65),(-.08,.05,1.68),(-.03,.05,1.69),(.02,.05,1.67),(.07,.05,1.64),(.12,.055,1.50)]):
  prism('hair',f'fringe_lock_{i}','silver_light' if i in [1,4] else 'silver',[[x,bottom+.035],[x+w*.55,bottom],[x+w,bottom+.025],[x+w,1.72],[x+.02,1.745],[x,1.72]],.12,.19+(i%2)*.02)
  if i not in [0,6]:
   prism('hair',f'fringe_ridge_{i}','silver_light',[[x+.01,bottom+.045],[x+.025,bottom+.025],[x+.025,1.72],[x+.01,1.73]],.19+(i%2)*.02,.21+(i%2)*.02)
 for s,label in [(-1,'left'),(1,'right')]:
  # Side hair broadens near temples, then tapers to individual pointed ends.
  poly=[[s*.13,1.45],[s*.17,1.48],[s*.19,1.56],[s*.185,1.66],[s*.15,1.71],[s*.13,1.65]]
  prism('hair','temple_lock_'+label,'silver',poly,-.10,.10)
  prism('hair','side_layer_'+label,'silver_light',[[s*.15,1.48],[s*.18,1.53],[s*.19,1.65],[s*.17,1.69],[s*.16,1.59]],-.01,.12)
 for i,x in enumerate([-.14,-.08,-.02,.04,.10]):
  low=1.43+(.02 if i%2 else 0)
  prism('hair','rear_silver_strand_'+str(x),'silver' if i%2 else 'silver_light',[[x,low+.025],[x+.025,low],[x+.05,low+.04],[x+.045,1.68],[x+.02,1.72],[x,1.68]],-.20,-.16)
 for i in range(8):
  x=.13+(i%2)*.018;y=1.45-i*.055
  prism('braid',f'braid_segment_{i}','silver' if i%2 else 'silver_light',[[x-.015,y+.012],[x+.035,y-.010],[x+.025,y-.040],[x-.01,y-.060],[x-.038,y-.025]],-.22,-.13)
 box('braid','braid_tie','teal_light',[.095,1.02,-.225],[.18,1.06,-.125])
 prism('braid','braid_tail','silver',[[.11,1.03],[.17,1.03],[.155,.98],[.12,.96]],-.205,-.14)
 # Tapered sleeves, staggered finger tips and a separate thumb silhouette.
 for sign,label in [(-1,'left'),(1,'right')]:
  x=sign*.27
  prism('upper_arm_'+label,'sleeve_'+label,'linen',[[x-.055,1.10],[x+.055,1.10],[x+.07,1.18],[x+.065,1.30],[x+.045,1.34],[x-.045,1.34],[x-.065,1.30],[x-.07,1.18]],-.075,.08)
  prism('upper_arm_'+label,'shoulder_wool_'+label,'teal_shadow',[[x-.065,1.26],[x+.065,1.26],[x+.08,1.30],[x+.055,1.35],[x-.055,1.35],[x-.08,1.30]],-.09,.10)
  prism('upper_arm_'+label,'shoulder_piping_'+label,'teal_light',[[x-.065,1.27],[x+.065,1.27],[x+.065,1.29],[x-.065,1.29]],.10,.12)
  prism('forearm_'+label,'lower_sleeve_'+label,'linen',[[x-.045,.88],[x+.045,.88],[x+.055,.98],[x+.065,1.06],[x+.05,1.12],[x-.05,1.12],[x-.065,1.06],[x-.055,.98]],-.065,.07)
  for j,y in enumerate([.97,1.03,1.09]):
   prism('forearm_'+label,f'sleeve_relief_{label}_{j}','linen_shadow',[[x-.05,y],[x+.03,y+.015],[x+.045,y+.035],[x-.045,y+.02]],.07,.09)
  prism('hand_'+label,'palm_'+label,'skin',[[x-.04,.80],[x+.04,.80],[x+.055,.83],[x+.045,.885],[x-.045,.885],[x-.055,.83]],-.05,.05)
  for i,(dx,low) in enumerate([(-.04,.785),(-.02,.765),(0,.77),(.02,.79)]):
   box('hand_'+label,f'finger_{label}_{i}','skin' if i%2 else 'skin_light',[x+dx,low,-.04],[x+dx+.02,.825,.04])
  tx=x-sign*.06
  prism('hand_'+label,'thumb_'+label,'skin_light',[[tx-sign*.025,.81],[tx+sign*.01,.82],[tx+sign*.025,.865],[tx,.88]],.005,.06)
  box('hand_'+label,'knuckle_plane_'+label,'skin_light',[x-.035,.825,.05],[x+.035,.845,.07])
  # Bodice, skirt and cuff detail is real relief, not only recolouring.
  seamx=sign*.125
  prism('torso','bodice_seam_'+label,'teal_shadow',[[seamx-.01,1.07],[seamx+.01,1.07],[sign*.17+.01,1.28],[sign*.17-.01,1.28]],.14,.16)
  prism('torso','waist_fold_'+label,'teal_light',[[sign*.04,1.055],[sign*.15,1.055],[sign*.17,1.11]],.14,.18)
  skirt='skirt_'+label
  for j,dx in enumerate([.075,.145,.215]):
   sx=sign*dx
   prism(skirt,f'pleat_ridge_{label}_{j}','teal_shadow' if j==1 else 'teal_light',[[sx-.01,.68],[sx+.01,.68],[sign*(dx*.72)+.01,.97],[sign*(dx*.72)-.01,.97]],.15,.175+(j%2)*.005)
  for j,y in enumerate([.73,.79,.85,.91]):
   sx=sign*.21
   box(skirt,f'hem_stitch_{label}_{j}','linen_shadow',[sx-.01,y,.16],[sx+.01,y+.02,.18])
  shin='shin_'+label;lx=sign*.105
  for j,y in enumerate([.20,.27,.34]):
   box(shin,f'boot_lacing_{label}_{j}','leather_dark',[lx-.045,y,.09],[lx+.045,y+.02,.12])
  box(shin,'ankle_strap_'+label,'leather_dark',[lx-.085,.15,-.085],[lx+.085,.19,.105])
  box(shin,'ankle_buckle_'+label,'brass',[lx-.02,.15,.105],[lx+.02,.19,.125])
  mx=sign*.04
  box('mouth_corner_'+label,'lip_corner_'+label,'lip',[mx-.02,1.495,.14],[mx+.02,1.515,.18])
 # A real four-bar buckle aperture leaves the belt behind it.
 for id,lo,hi in [('left',[-.05,1.00,.17],[-.03,1.06,.20]),('right',[.03,1.00,.17],[.05,1.06,.20]),('top',[-.03,1.04,.17],[.03,1.06,.20]),('bottom',[-.03,1.00,.17],[.03,1.02,.20])]:box('pelvis','buckle_frame_'+id,'brass',lo,hi)
 box('pelvis','belt_tongue','brass',[-.01,1.025,.16],[.04,1.035,.19])
 prism('cape','short_shoulder_mantle','teal_shadow',[[-.18,1.00],[.18,1.00],[.23,1.05],[.235,1.28],[.14,1.38],[-.14,1.38],[-.235,1.28],[-.23,1.05]],-.20,-.13)
 for i,x in enumerate([-.15,-.05,.05,.15]):
  prism('cape','mantle_fold_'+str(i),'teal_wool',[[x-.01,1.04],[x+.01,1.04],[x*.55+.01,1.31],[x*.55-.01,1.31]],-.225,-.20)
 prism('satchel','satchel_body','leather',[[-.30,.82],[-.20,.80],[-.18,.83],[-.18,.97],[-.20,1.00],[-.29,1.00],[-.31,.97]],-.08,.10)
 prism('satchel','satchel_flap','leather_light',[[-.31,.95],[-.27,.92],[-.22,.92],[-.18,.95],[-.18,1.015],[-.31,1.015]],.08,.12)
 box('satchel','satchel_hanging_strap','leather_dark',[-.27,.98,-.06],[-.23,1.08,-.02])
 for i,y in enumerate([.84,.88,.92]):box('satchel','satchel_stitch_'+str(i),'linen_shadow',[-.30,y,.10],[-.28,y+.02,.12])
 c['operations']=ops
 for p in c['parts']:
  if p['id'].startswith(('eyelid_','brow_')):p['pivot'][0]=-.08 if p['id'].endswith('left') else .08
 for p in rig_parts:
  if p['id'].startswith(('eyelid_','brow_')):p['pivot_m'][0]=-.08 if p['id'].endswith('left') else .08
 master['revision']=3
 master['extensions']['art_revision']={'id':'layered_volume_r3_blink','changes':['rounder cross-section crown and cheek/jaw slices','swept overlapping fringe, layered temples, pointed rear strands and braided links','tapered sleeves, staggered fingers and shaped thumb','raised pleats, seams, stitches, mantle folds and real buckle aperture','eyelid front moved ahead of eye glint with closure margins; open lids retract inside head to avoid visible bars'],'palette_changed':False,'rig_part_ids_changed':False}
 return master
