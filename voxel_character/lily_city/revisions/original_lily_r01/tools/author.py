"""New authoring, not B7 recovery. Independent semantic layers, shared common rig.
Run from any directory; writes this revision's data only. Existing r5 is read-only.
"""
from pathlib import Path
import copy,hashlib,json,sys
HERE=Path(__file__).resolve().parents[1]
LILY=HERE.parents[1]
COMMON=LILY.parent/'common'
sys.path.insert(0,str(COMMON))
from core import digest

def dump(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def box(ops,part,id,mat,lo,hi):
 ops.append({'id':id,'part':part,'action':'paint','material':mat,'shape':{'kind':'box','min':lo,'max':hi,'minimum_cells':[1,1,1]}})
def poly(ops,part,id,mat,points,zlo,zhi):
 ops.append({'id':id,'part':part,'action':'paint','material':mat,'shape':{'kind':'extrusion','polygon':points,'z_min':zlo,'z_max':zhi,'minimum_cells':1}})
def ribbon(ops,part,id,mat,points,width,zlo,zhi):
 poly(ops,part,id,mat,[[x-width/2,y] for x,y in points]+[[x+width/2,y] for x,y in reversed(points)],zlo,zhi)
def module(id,layer,ops,parts=None,**metadata):
 return {'schema':'riverstone.character.module.v1','id':id,'layer':layer,'operations':ops,'parts':parts or [],'metadata':metadata}
def body_module():
 ops=[]
 poly(ops,'pelvis','body_hip','skin',[[-.16,.85],[.16,.85],[.16,1.05],[-.16,1.05]],-.09,.09)
 poly(ops,'torso','body_torso','skin',[[-.14,1.015],[.14,1.015],[.19,1.30],[.17,1.39],[-.17,1.39],[-.19,1.30]],-.095,.10)
 poly(ops,'torso','neck','skin',[[-.059,1.35],[.059,1.35],[.055,1.49],[-.055,1.49]],-.055,.060)
 for s,label in [(-1,'left'),(1,'right')]:
  x=s*.27;lx=s*.105
  poly(ops,'upper_arm_'+label,'body_upper_arm_'+label,'skin',[[x-.052,1.10],[x+.052,1.10],[x+.060,1.33],[x-.060,1.33]],-.054,.060)
  poly(ops,'forearm_'+label,'body_forearm_'+label,'skin',[[x-.036,.88],[x+.036,.88],[x+.048,1.12],[x-.048,1.12]],-.044,.050)
  poly(ops,'hand_'+label,'body_palm_'+label,'skin',[[x-.035,.79],[x+.035,.79],[x+.042,.87],[x-.042,.87]],-.029,.033)
  for i in range(4):
   xx=x-.031+i*.019;bottom=.766+abs(i-1.5)*.007
   box(ops,'hand_'+label,f'finger_{label}_{i}','skin',[xx,bottom,-.025],[xx+.015,.817,.029])
  poly(ops,'hand_'+label,'thumb_'+label,'skin_light',[[x-s*.025,.815],[x-s*.058,.83],[x-s*.052,.866],[x-s*.024,.866]],.004,.037)
  poly(ops,'thigh_'+label,'body_thigh_'+label,'skin',[[lx-.057,.51],[lx+.057,.51],[lx+.069,.94],[lx-.069,.94]],-.058,.064)
  poly(ops,'shin_'+label,'body_shin_'+label,'skin',[[lx-.039,.12],[lx+.039,.12],[lx+.053,.53],[lx-.053,.53]],-.043,.051)
  box(ops,'foot_'+label,'body_foot_'+label,'skin',[lx-.056,.026,-.052],[lx+.056,.145,.132])
 return module('adult_base','body',ops,anatomy='Modest unsexed body core; garments are independent rigid mesh parts; original portrait supports adult proportions only.')
def face_module(kind='soft_taper'):
 ops=[]
 if kind=='soft_taper': outline=[[-.027,1.466],[.027,1.466],[.071,1.487],[.112,1.525],[.141,1.58],[.145,1.66],[.117,1.712],[.065,1.739],[-.065,1.739],[-.117,1.712],[-.145,1.66],[-.141,1.58],[-.112,1.525],[-.071,1.487]]
 elif kind=='oval': outline=[[-.055,1.466],[.055,1.466],[.103,1.498],[.143,1.56],[.150,1.65],[.111,1.72],[.06,1.74],[-.06,1.74],[-.111,1.72],[-.150,1.65],[-.143,1.56],[-.103,1.498]]
 else: outline=[[-.084,1.47],[.084,1.47],[.133,1.505],[.151,1.585],[.15,1.67],[.104,1.73],[-.104,1.73],[-.15,1.67],[-.151,1.585],[-.133,1.505]]
 poly(ops,'head','face_cranium','skin_shadow',outline,-.085,.050)
 poly(ops,'head','face_soft_plane','skin',[[x*.96,y] for x,y in outline],.025,.101)
 poly(ops,'head','cheek_centre','skin_light',[[-.075,1.50],[.075,1.50],[.122,1.565],[.118,1.64],[-.118,1.64],[-.122,1.565]],.092,.109)
 poly(ops,'head','small_nose_bridge','skin',[[0,1.548],[.015,1.56],[.010,1.61],[-.010,1.61],[-.015,1.56]],.109,.128)
 box(ops,'head','small_nose_tip','skin_light',[-.009,1.556,.127],[.009,1.570,.141])
 for s,label in [(-1,'left'),(1,'right')]:
  x=s*.074
  poly(ops,'head','ear_'+label,'skin',[[(s*.143)-.014,1.554],[(s*.143)+.014,1.554],[(s*.143)+.016,1.620],[(s*.143)-.016,1.620]],-.012,.043)
  # Shaped almond eyes, real layered volumes. Final front lies at .15m.
  poly(ops,'head','eye_white_'+label,'eye_white',[[x-.044,1.610],[x-.026,1.596],[x+.026,1.596],[x+.045,1.619],[x+.026,1.638],[x-.024,1.638]],.107,.124)
  poly(ops,'head','iris_'+label,'iris',[[x-.020,1.601],[x+.020,1.601],[x+.024,1.625],[x+.013,1.638],[x-.013,1.638],[x-.024,1.625]],.124,.137)
  box(ops,'head','iris_lower_'+label,'iris_light',[x-.018,1.601,.137],[x+.018,1.614,.149])
  box(ops,'head','pupil_'+label,'pupil',[x-.007,1.613,.137],[x+.007,1.636,.150])
  box(ops,'head','glint_'+label,'eye_white',[x-.018,1.625,.149],[x-.005,1.638,.160])
  ribbon(ops,'head','upper_lash_'+label,'lash',[[x-.048,1.625],[x-.024,1.643],[x+.024,1.643],[x+.048,1.632]],.009,.126,.145)
  # Lid rest geometry sits above eye; blink retracts open lid into cranium.
  poly(ops,'eyelid_'+label,'lid_'+label,'skin',[[x-.051,1.653],[x+.051,1.653],[x+.051,1.714],[x-.051,1.714]],.137,.166)
  poly(ops,'brow_'+label,'soft_brow_'+label,'silver_shadow',[[x-.040,1.663],[x+.037,1.667],[x+.033,1.679],[x-.032,1.676]],.108,.122)
  box(ops,'mouth_corner_'+label,'lip_corner_'+label,'lip',[s*.028-.010,1.518,.108],[s*.028+.010,1.528,.123])
 poly(ops,'mouth','small_smile','lip',[[-.025,1.520],[0,1.514],[.025,1.520],[.025,1.529],[0,1.525],[-.025,1.529]],.111,.129)
 return module(kind,'face',ops,reference='Lily original neutral front identity' if kind=='soft_taper' else 'New resident variation of compatible adult head')
def hair_module(style='lily_long'):
 ops=[];parts=[]
 # Rounded, asymmetrical cross sections instead of a rectangular hair cap.
 for i,(zlo,zhi,ymod,w) in enumerate([(-.12,-.065,-.010,1),(-.065,.005,.004,1.04),(.005,.065,.009,1.02),(.065,.105,0,1)]):
  pts=[[-.160*w,1.610],[-.168*w,1.670],[-.142*w,1.716],[-.100*w,1.750],[-.030*w,1.773],[.034*w,1.775],[.105*w,1.748],[.148*w,1.713],[.166*w,1.656],[.155*w,1.609],[.126*w,1.655],[.105*w,1.690],[-.100*w,1.690],[-.126*w,1.655]]
  poly(ops,'hair','crown_'+str(i),'silver' if i%2 else 'silver_shadow',[[x,y+ymod] for x,y in pts],zlo,zhi)
 # Swept left-side curtain and narrow descending centre lock; the two eyes stay visible.
 locks=[([[-.035,1.765],[-.085,1.739],[-.119,1.692],[-.154,1.650],[-.143,1.623],[-.103,1.650],[-.061,1.694]],'silver_light'),
        ([[.011,1.770],[-.025,1.741],[-.040,1.701],[-.039,1.657],[-.017,1.634],[.010,1.677],[.037,1.738]],'silver'),
        ([[.039,1.768],[.083,1.749],[.117,1.714],[.143,1.672],[.150,1.640],[.121,1.658],[.091,1.699]],'silver_light')]
 for i,(pts,mat) in enumerate(locks):poly(ops,'hair','asymmetric_swept_bang_'+str(i),mat,pts,.103,.139+i*.005)
 ribbon(ops,'hair','bang_silver_ridge','silver_light',[[.004,1.751],[-.018,1.714],[-.024,1.677]],.010,.145,.155)
 if style=='lily_long':
  ribbon(ops,'hair','curved_cowlick','silver_light',[[-.110,1.748],[-.070,1.799],[-.005,1.817],[.044,1.796],[.050,1.771]],.014,-.015,.009)
  # Temple braid is on image-right when front camera looks toward +Z character.
  parts += [{'id':'hair_tail_back','parent':'hair','pivot_m':[0,1.50,-.19],'role':'hair_secondary'}, {'id':'hair_tail_left','parent':'hair','pivot_m':[-.125,1.50,-.12],'role':'hair_secondary'},{'id':'hair_tail_right','parent':'hair','pivot_m':[.125,1.50,-.12],'role':'hair_secondary'}]
  for i in range(7):
   x=(i-3)*.055;bot=.56+abs(i-3)*.025
   points=[[x,1.67],[x*1.25,1.46],[x*1.30,1.20],[x*1.72,1.02],[x*1.64,.79],[x*1.36,bot]]
   ribbon(ops,'hair_tail_back','rear_lock_'+str(i),'silver' if i%2 else 'silver_light',points,.070,-.257-(i%2)*.012,-.207-(i%2)*.012)
   ribbon(ops,'hair_tail_back','rear_ridge_'+str(i),'silver_shadow' if i%2 else 'silver',[[a-.017,b] for a,b in points],.012,-.279,-.258)
  for s,label in [(-1,'left'),(1,'right')]:
   part='hair_tail_'+label
   pts=[[s*.140,1.65],[s*.165,1.47],[s*.172,1.29],[s*.211,1.14],[s*.198,.995],[s*.154,.91]]
   ribbon(ops,part,'front_long_lock_'+label,'silver',pts,.053,.107,.151)
   ribbon(ops,part,'front_long_glint_'+label,'silver_light',[[x-s*.012,y+.005] for x,y in pts],.015,.150,.164)
   pts2=[[s*.157,1.62],[s*.199,1.42],[s*.214,1.20],[s*.294,.98],[s*.270,.75],[s*.223,.67]]
   ribbon(ops,part,'outer_long_lock_'+label,'silver',pts2,.065,-.17,-.117)
   ribbon(ops,part,'outer_long_glint_'+label,'silver_light',[[x+s*.013,y] for x,y in pts2],.015,-.186,-.170)
  for i in range(5):
   x=-.151-(i%2)*.007;y=1.671-i*.030
   poly(ops,'braid','temple_braid_link_'+str(i),'silver_light' if i%2 else 'silver_shadow',[[x-.021,y],[x,y-.025],[x+.022,y],[x,y+.020]],.035,.093)
 else:
  length=1.48 if style=='swept_bob' else 1.585
  for s,label in [(-1,'left'),(1,'right')]:
   ribbon(ops,'hair','resident_temple_'+label,'silver',[[s*.153,1.69],[s*.167,1.59],[s*.142,length]],.040,-.038,.065)
  poly(ops,'hair','resident_rear','silver_shadow',[[-.163,length],[.163,length],[.165,1.69],[.100,1.74],[-.100,1.74],[-.165,1.69]],-.142,-.078)
  for i in range(5):ribbon(ops,'hair','resident_rear_ridge_'+str(i),'silver',[[(-2+i)*.055,1.71],[(-2+i)*.052,length+.015]],.014,-.157,-.142)
  # Keep the semantic braid only when selected. Assembly removes unused nodes.
 return module(style,'hair',ops,parts,reference='Exact current-app front portrait; rear/side volume is a new 3D interpretation' if style=='lily_long' else 'New modular resident hair')
def ornament_module():
 ops=[]
 # Image-right ornament maps to character -X, explicitly recorded.
 poly(ops,'ornament','gold_hairpin_outline','brass',[[-.162,1.652],[-.136,1.697],[-.143,1.751],[-.166,1.722],[-.178,1.682]],.074,.106)
 poly(ops,'ornament','teal_hairpin_inlay','iris',[[-.159,1.672],[-.147,1.701],[-.150,1.731],[-.162,1.714],[-.168,1.688]],.106,.120)
 ribbon(ops,'ornament','teal_tassel','iris',[[ -.164,1.635],[-.173,1.555],[-.178,1.450]],.014,.062,.081)
 for s,l in [(-1,'left'),(1,'right')]:
  x=s*.141
  poly(ops,'ornament','earring_gold_'+l,'brass',[[x,1.568],[x+.017,1.535],[x,1.503],[x-.017,1.535]],.040,.059)
  poly(ops,'ornament','earring_teal_'+l,'iris',[[x,1.555],[x+.008,1.535],[x,1.518],[x-.008,1.535]],.059,.072)
 return module('lily_teal_gold','ornament',ops,[{'id':'ornament','parent':'head','pivot_m':[0,1.405,0],'role':'ornament'}],unique_to='lily',image_right='character negative X')
def main():
 base=json.loads((LILY/'data/master.json').read_text())
 dump(HERE/'data/reference.json',{'schema':'riverstone.character.reference.v1','original_path':'lily-sites-release-20261010/assets/avatar/neutral.png','original_sha256':'e75ba0827813bacaaf54ba72295068b04ae45e98e6ad16ac11e44316fcb8acaa','reference_view':'front portrait cropped at upper thighs','confirmed_identity':['long silver-lilac hair below waist','asymmetric swept bangs and curved cowlick','image-right temple braid and teal/gold ornament with long tassel','teal gradient eyes','small smile and soft tapered jaw','adult proportions'],'new_interpretation':['rear and side geometry','full legs and feet','voxel reduction','medieval clothing fit'],'art_acceptance':'pending; source authorization is not final art approval','preserved_costume_source':{'path':'../../data/master.json','sha256':hashlib.sha256((LILY/'data/master.json').read_bytes()).hexdigest(),'master_hash':digest(base),'cache':'../../generated/r5'}})
 modules=[body_module(),face_module(),face_module('oval'),face_module('square'),hair_module(),hair_module('swept_bob'),hair_module('short_crop'),ornament_module()]
 clothing_ops=[copy.deepcopy(o) for o in base['components'][0]['operations'] if o['part'] not in ['head','hair','braid','mouth','ornament'] and not o['part'].startswith(('eyelid_','brow_','mouth_corner_','hand_')) and o['id']!='neck']
 modules.append(module('medieval_traveller_r5','costume',clothing_ops,provenance={'source_master_hash':digest(base),'source_bytes_sha256':hashlib.sha256((LILY/'data/master.json').read_bytes()).hexdigest(),'operations':'Original r5 costume geometry retained without changing original source. Final fit is a documented frame transformation.'}))
 for m in modules:dump(HERE/'data/modules'/(m['id']+'.json'),m)
 presets=[{'id':'lily_original','body':'adult_slender','face':'soft_taper','hair':'lily_long','costume':'medieval_traveller_r5','ornaments':['lily_teal_gold'],'palette':{},'role':'lily','district':'any'}]
 dump(HERE/'data/presets/lily_original.json',{'schema':'riverstone.character.assembly.v1',**presets[0]})
 print('Authored',len(modules),'separate modules')
if __name__=='__main__':main()
