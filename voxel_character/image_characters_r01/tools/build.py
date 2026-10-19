"""One data-driven generator for both reference characters. No asset-ID branching.

Images -> human observations/presets -> one master per asset -> semantic/pitch
partitions -> unchanged common compiler -> unchanged surface mesher/renderer.
All generated writes remain under this revision. No full-resolution resampling.
"""
from pathlib import Path
import argparse,copy,gzip,hashlib,json,math,sys,time
ROOT=Path(__file__).resolve().parents[1]
COMMON=ROOT.parent/'common'
sys.path.insert(0,str(COMMON));sys.path.insert(0,str(COMMON/'animation'))
from core import compile_master,digest
from render_data import make_render_data
from build_render import bindings_from,isolate

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v,pretty=True):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2 if pretty else None,separators=None if pretty else (',',':'))+'\n')
def read(p):return json.loads(Path(p).read_text())
def rnd(v):return [round(x,7) for x in v]
def polygon_ribbon(points,width):
 return [[x-width/2,y] for x,y in points]+[[x+width/2,y] for x,y in reversed(points)]

class Author:
 def __init__(self,p,r):self.p=p;self.r=r;self.ops=[];self.details=set();self.micro=set();self.serial=0
 def add(self,part,name,mat,shape,detail=False,transform=None):
  op={'id':name,'part':part,'action':'paint','material':mat,'shape':shape}
  if transform:op['transform']=transform
  self.ops.append(op)
  if detail:self.details.add(name)
 def box(self,part,name,mat,lo,hi,detail=False):
  self.add(part,name,mat,{'kind':'box','min':rnd(lo),'max':rnd(hi),'minimum_cells':[1,1,1]},detail)
 def poly(self,part,name,mat,pts,zlo,zhi,detail=False,transform=None):
  self.add(part,name,mat,{'kind':'extrusion','polygon':[rnd(p) for p in pts],'z_min':round(zlo,7),'z_max':round(zhi,7),'minimum_cells':1},detail,transform)
 def tube(self,part,name,mat,points,radius,detail=False):
  # Small per-segment bounds avoid large sparse bounding-box scans.
  for i,(a,b) in enumerate(zip(points,points[1:])):
   self.add(part,name+'_%02d'%i,mat,{'kind':'tube','points':[rnd(a),rnd(b)],'radius':radius,'minimum_radius_cells':.55},detail)
 def bloom(self,part,name,center,radius,material='flower',detail=True):
  x,y,z=center;n=self.r['bouquet']['petal_count'];pr=self.r['bouquet']['petal_radius_m']
  self.tube(part,name+'_core','flower_shadow',[[x,y,z-.022],[x,y,z+.012]],radius*.72,detail)
  for j in range(n):
   a=j*math.tau/n;px=x+math.sin(a)*radius*.75;py=y+math.cos(a)*radius*.75
   self.tube(part,name+'_petal_'+str(j),material,[[px,py,z],[px,py,z+.02]],pr,detail)
  self.box(part,name+'_center','flower_center',[x-.009,y-.009,z+.019],[x+.009,y+.009,z+.031],detail)
 def ellipse_slice(self,part,name,mat,ylo,yhi,rx,rz,zcenter=0,detail=False):
  points=[[math.cos(i*math.tau/20)*rx,math.sin(i*math.tau/20)*rz] for i in range(20)]
  self.poly(part,name,mat,points,ylo,yhi,detail,{'basis':[[1,0,0],[0,0,1],[0,-1,0]],'translation':[0,0,zcenter]})
 def cut(self,part,name,shape):
  self.ops.append({'id':name,'part':part,'action':'cut','shape':shape,'selector':{'part':part}})
 def base(self):
  mods=(ROOT/'data'/self.r['source_modules']).resolve()
  body=read(mods/'adult_base.json');face=read(mods/'soft_taper.json')
  for op in body['operations']:
   if any(w in op['part'] for w in ['arm','hand']):continue
   self.ops.append(copy.deepcopy(op))
  f=self.r['face'];profile=f['profile_y_width_depth'];step=f['slice_height_m']
  for j in range(math.ceil((profile[-1][0]-profile[0][0])/step)):
   y=profile[0][0]+j*step;mid=y+step/2
   for a,b in zip(profile,profile[1:]):
    if a[0]<=mid<=b[0]:
     t=(mid-a[0])/(b[0]-a[0]);rx=a[1]+(b[1]-a[1])*t;rz=a[2]+(b[2]-a[2])*t;break
   self.ellipse_slice('head','oval_cranium_'+str(j),'skin',y,min(y+step,profile[-1][0]),rx,rz,0,True)
  for op in face['operations']:
   if op['id'] in ['face_cranium','face_soft_plane'] or op['id'].startswith(('eye_white_','iris_','iris_lower_','pupil_','glint_','upper_lash_','soft_brow_')):continue
   op=copy.deepcopy(op)
   if op['id'].startswith('lid_'):
    op['shape']['z_min'],op['shape']['z_max']=self.r['fit']['eyelid_rest_z']
   if op['id'].startswith(('eye_white_','iris_','iris_lower_','pupil_','glint_','upper_lash_')):
    cx=-.074 if op['id'].endswith('left') else .074
    shape=op['shape']
    for v in shape.get('polygon',[]):v[0]=cx+(v[0]-cx)*f['eye_width_scale'];v[1]=1.617+(v[1]-1.617)*f['eye_height_scale']
    for key in ['min','max']:
     if key in shape:shape[key][0]=cx+(shape[key][0]-cx)*f['eye_width_scale'];shape[key][1]=1.617+(shape[key][1]-1.617)*f['eye_height_scale']
   self.ops.append(op);self.details.add(op['id'])
  self.eyes()
  self.cut('torso','remove_hidden_torso_under_bodice',{'kind':'box','min':[-.3,1.005,-.2],'max':[.3,self.r['fit']['body_under_bodice_cut_top_y'],.2]})
  b=self.r['body']
  for sign,label in [(-1,'left'),(1,'right')]:
   points=[[sign*v[0],v[1],v[2]] for v in [b['shoulder'],b['elbow'],b['wrist']]]
   self.tube('upper_arm_'+label,'posed_upper_arm_'+label,'skin',points[:2],b['arm_radius'])
   self.tube('forearm_'+label,'posed_forearm_'+label,'dress' if self.p['gloves'] else 'skin',points[1:],b['forearm_radius'])
   x,y,z=points[-1];self.box('hand_'+label,'posed_hand_'+label,'dress' if self.p['gloves'] else 'skin',[x-.039,y-.037,z-.024],[x+.039,y+.027,z+.033])
   if self.p['gloves']:
    self.tube('upper_arm_'+label,'long_glove_'+label,'dress',[[sign*.211,1.21,.065],points[1]],.047)
   lx=sign*.105
   self.poly('shin_'+label,'stocking_'+label,'dress_shadow',[[lx-.039,.12],[lx+.039,.12],[lx+.054,.53],[lx-.054,.53]],-.045,.054)
   self.box('foot_'+label,'shoe_'+label,'shoe',[lx-.055,.025,-.055],[lx+.055,.115,.150])
   self.box('foot_'+label,'heel_'+label,'shoe',[lx-.026,.002,-.045],[lx+.026,.055,-.007])
  self.poly('dress_bodice','white_bodice','dress',[[-.138,1.005],[.138,1.005],[.185,1.25],[.162,1.345],[.10,1.325],[0,1.29],[-.10,1.325],[-.162,1.345],[-.185,1.25]],-.105,.112)
  for sign in [-1,1]:
   self.poly('dress_bodice','bodice_seam_'+str(sign),'dress_shadow',polygon_ribbon([[sign*.07,1.02],[sign*.08,1.13],[sign*.12,1.25],[sign*.15,1.32]],.0125),.112,.125,True)
   for j in range(5):
    x=sign*(.04+j*.025);y=1.295+j*.009
    self.bloom('dress_bodice','neckline_lace_%s_%s'%(sign,j),[x,y,.122],.014,'dress_light',True)
  for j in range(5):
   self.box('dress_bodice','rear_buttons_'+str(j),'jewel',[-.009,1.06+j*.04,-.127],[.009,1.075+j*.04,-.107],True)
 def eyes(self):
  f=self.p['face_design']
  for sign,label in [(-1,'left'),(1,'right')]:
   x=sign*.071;y=1.617;w=f['eye_half_width_m'];h=f['eye_half_height_m'];tilt=sign*f['eye_outward_tilt']
   def point(u,v):return [x+u,y+v+tilt*u]
   start=len(self.ops)
   upper=[point(-w,0),point(-w*.55,h*.9),point(w*.55,h),point(w,.1*h)]
   lower=[point(w*.60,-h*.85),point(-w*.55,-h)]
   self.poly('head','almond_white_'+label,'eye_white',upper+lower,.117,.135,True)
   iw=f['iris_half_width_m']
   self.poly('head','narrow_iris_'+label,'iris',[[x-iw,y-h*.82],[x+iw,y-h*.82],[x+iw,y+h*.8],[x-iw,y+h*.8]],.135,.148,True)
   self.box('head','narrow_pupil_'+label,'pupil',[x-.004,y-h*.6,.148],[x+.004,y+h*.65,.155],True)
   self.box('head','small_glint_'+label,'eye_white',[x-.010,y+.001,.155],[x-.003,y+.008,.162],True)
   self.tube('head','slanted_upper_lash_'+label,'lash',[[a,b,.156] for a,b in upper],.0038,True)
   outer=point(sign*w,0);wing=point(sign*(w+.012),h*.5)
   self.tube('head','outer_lash_'+label,'lash',[[outer[0],outer[1],.155],[wing[0],wing[1],.155]],.0036,True)
   brow=[[x-.033,1.661-tilt*.03,.113],[x+.033,1.661+tilt*.03,.113]]
   self.tube('brow_'+label,'fine_brow_'+label,'hair_shadow',brow,f['brow_thickness_m']/2,True)
   self.micro.update(op['id'] for op in self.ops[start:])
 def cloth_triangle(self,part,name,a,b,c,material,zlo,zhi):
  def sub(x,y):return [x[i]-y[i] for i in range(3)]
  def dot(x,y):return sum(x[i]*y[i] for i in range(3))
  def cross(x,y):return [x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0]]
  def unit(v):
   length=math.sqrt(dot(v,v));return [x/length for x in v]
  u=unit(sub(b,a));n=unit(cross(u,sub(c,a)))
  if n[2]<0:b,c=c,b;u=unit(sub(b,a));n=unit(cross(u,sub(c,a)))
  v=cross(n,u);points=[[0,0],[dot(sub(b,a),u),dot(sub(b,a),v)],[dot(sub(c,a),u),dot(sub(c,a),v)]]
  center=[sum(p[i] for p in points)/3 for i in range(2)];scale=self.r['skirt']['triangle_overlap_scale']
  points=[[center[i]+(p[i]-center[i])*scale for i in range(2)] for p in points]
  self.poly(part,name,material,points,zlo,zhi,False,{'basis':[[u[i],v[i],n[i]] for i in range(3)],'translation':a})
 def cloth_panel(self,panel,index,underlay=False):
  s=self.r['skirt'];n=s['longitudinal_samples'];m=s['transverse_samples'];centers=panel['centerline_xyz'];widths=panel['half_widths_m'];axis=panel['transverse_axis_xyz'];length=math.sqrt(sum(x*x for x in axis));axis=[x/length for x in axis]
  def sample(values,t):
   q=t*(len(values)-1);j=min(len(values)-2,int(q));u=q-j
   a=values[max(0,j-1)];b=values[j];c=values[j+1];d=values[min(len(values)-1,j+2)]
   return .5*(2*b+(-a+c)*u+(2*a-5*b+4*c-d)*u*u+(-a+3*b-3*c+d)*u*u*u)
  grid=[]
  for j in range(n+1):
   t=j/n;center=[sample([p[k] for p in centers],t) for k in range(3)];w=max(.02,sample(widths,t));row=[]
   for i in range(m+1):
    u=-1+2*i/m;v=[center[k]+axis[k]*u*w for k in range(3)]
    v[2]+=panel['cross_cup_m']*(u*u-.33)*math.sin(t*math.pi/2)
    v[1]+=panel['hem_lift_m']*u*u*t**6
    row.append(v)
   grid.append(row)
  for j in range(n):
   for i in range(m):
    a,b,c,d=grid[j][i],grid[j][i+1],grid[j+1][i+1],grid[j+1][i]
    for k,tri in enumerate([(a,b,c),(a,c,d)]):
     part='skirt_left' if sum(p[0] for p in tri)<0 else 'skirt_right';name='cloth_%s_%02d_%02d_%s'%(index,j,i,k)
     self.cloth_triangle(part,name+'_lining',*tri,'lining',-s['lining_thickness_m'],.002)
     self.cloth_triangle(part,name+'_white',*tri,panel['white_material'],0,s['white_thickness_m'])
 def skirt(self):
  # Independent 3D cloth sweeps. There is deliberately no radial shell or lathe.
  # A recessed rear overlap sheet and compact waist join close hidden seams only.
  self.cloth_panel(self.p['cloth_underlay'],'rear_underlay',True)
  for i,panel in enumerate(self.p['dress_panels']):self.cloth_panel(panel,i)
  for side,sign in [('left',-1),('right',1)]:
   self.poly('skirt_'+side,'waist_join_'+side,'dress',[[-.17,1.05],[.17,1.05],[.17,.88],[-.17,.88]],-.14,.14)
   self.cut('skirt_'+side,'waist_join_half_'+side,{'kind':'box','min':[0 if sign<0 else -.19,.86,-.15],'max':[.19 if sign<0 else 0,1.06,.15]})
  self.poly('skirt_left','front_fold_left','dress',[[-.155,1.05],[.02,1.05],[.02,.89],[-.06,.82],[-.18,.86],[-.25,.95]],.12,.18)
  self.poly('skirt_right','front_fold_right','dress_light',[[.005,1.05],[.155,1.05],[.28,.96],[.22,.84],[.115,.89],[.04,.84]],.12,.19)
 def hair(self):
  h=self.r['hair'];flow=self.p['hair_flow_sign']
  cap=h['cap_profile_y_width_depth'];step=.025
  for j in range(math.ceil((cap[-1][0]-cap[0][0])/step)):
   y=cap[0][0]+j*step;mid=y+step/2
   for a,b in zip(cap,cap[1:]):
    if a[0]<=mid<=b[0]:
     t=(mid-a[0])/(b[0]-a[0]);rx=a[1]+(b[1]-a[1])*t;rz=a[2]+(b[2]-a[2])*t;break
   self.ellipse_slice('hair','rounded_hair_cap_'+str(j),'hair',y,min(y+step,cap[-1][0]),rx,rz,-.015)
  self.cut('hair','cap_face_window',{'kind':'box','min':[-.145,1.45,-.025],'max':[.145,1.715,.3]})
  for j in range(10):
   y=1.30+j*.04;rx=.12+.028*math.sin(j*.3)
   self.ellipse_slice('hair_tail_back','rear_mantle_'+str(j),'hair_shadow',y,y+.042,rx,.055,-.155)
  for j,pts in enumerate(self.p['front_bang_points']):
   pts=copy.deepcopy(pts)
   for p in pts:
    crown=h['bang_crown_center_y']+h['bang_crown_radius_y']*math.sqrt(max(0,1-(p[0]/h['bang_crown_radius_x'])**2))
    p[1]=min(p[1],crown)
   self.poly('hair','bang_'+str(j),'hair',pts,.118,.176+(j%3)*.003,True)
   self.micro.add('bang_'+str(j))
  for j in range(h['strand_count']):
   u=(j-(h['strand_count']-1)/2)/((h['strand_count']-1)/2);start=u*.14
   reach=flow*h['fan_reach_m']*(.60+.40*(j%4)/3);z=h['rear_depth_m']-(j%5)*h['strand_depth_spacing_m']
   pts=[[start,1.69],[start+flow*.04,1.48],[flow*.27+start*.20,1.33+(j%3)*.025],[reach*.65,1.27+(j%5)*.035],[reach*.9,1.36+(j%4)*.015],[reach+flow*.08,1.23-(j%6)*.07]]
   width=h['width_m']*(.8+(j%3)*.20)
   part='hair_tail_back' if j<7 else ('hair_tail_left' if start<0 else 'hair_tail_right')
   # Volumetric curved locks with depth variation, rather than flat extruded cards.
   controls=[[x,y,z-.045*math.sin(k*1.1+j*.2)] for k,(x,y) in enumerate(pts)]
   p3=[];subdiv=h['curve_subdivisions']
   for seg in range(len(controls)-1):
    a=controls[max(0,seg-1)];b=controls[seg];c=controls[seg+1];d=controls[min(len(controls)-1,seg+2)]
    for k in range(subdiv):
     t=k/subdiv
     p3.append([.5*((2*b[n])+(-a[n]+c[n])*t+(2*a[n]-5*b[n]+4*c[n]-d[n])*t*t+(-a[n]+3*b[n]-3*c[n]+d[n])*t*t*t) for n in range(3)])
   p3.append(controls[-1])
   for segment,(a,b) in enumerate(zip(p3,p3[1:])):
    taper=1-.84*segment/(len(p3)-2)
    self.tube(part,'flowing_lock_%s_%s'%(j,segment),'hair' if j%3 else 'hair_shadow',[a,b],width*.36*taper)
    if j%2==0 and segment<len(p3)-5:
     ridge=[[x-width*.09,y,zz+width*.30*taper] for x,y,zz in [a,b]]
     self.tube(part,'flowing_ridge_%s_%s'%(j,segment),'hair_light',ridge,.0075)
  # Temple strands connect crown to the side/rear hair volumes.
  for sign,label in [(-1,'left'),(1,'right')]:
   pts=[[sign*.15,1.67],[sign*.19,1.48],[sign*.18,1.31],[sign*.23,1.19]]
   self.poly('hair_tail_'+label,'temple_lock_'+label,'hair',polygon_ribbon(pts,.045),.04,.097)
 def ornaments(self):
  h=self.r['halo'];cx,cy,cz=h['center_m']
  for level in ['outer','inner']:
   radius=h[level+'_radius_m']
   for j,(start,end) in enumerate(h[level+'_arc_degrees']):
    n=math.ceil((end-start)/h['arc_step_deg']);points=[]
    for i in range(n+1):
     a=math.radians(start+(end-start)*i/n);points.append([cx+math.sin(a)*radius,cy+math.cos(a)*radius,cz])
    self.tube('halo',level+'_arc_'+str(j),'halo',points,h['line_radius_m']*(1.25 if level=='outer' else .60),True)
  for j,degrees in enumerate(h['rays_degrees']):
   a=math.radians(degrees);points=[[cx+math.sin(a)*r,cy+math.cos(a)*r,cz] for r in [h['inner_radius_m']-.025,h['outer_radius_m']+.015]]
   self.tube('halo','halo_ray_'+str(j),'halo',points,.0065,True)
  if self.p['crown']:
   for i in range(8):
    a=i*math.tau/8;x=.12+math.sin(a)*.066;z=.015+math.cos(a)*.055
    self.tube('ornament','crown_base_'+str(i),'jewel',[[x,1.766,z],[.12+math.sin(a+math.tau/8)*.066,1.766,.015+math.cos(a+math.tau/8)*.055]],.008,True)
    self.tube('ornament','crown_point_'+str(i),'dress_light',[[x,1.77,z],[x+math.sin(a)*.023,1.84+(i%2)*.035,z+math.cos(a)*.018],[.12+math.sin(a+math.tau/8)*.066,1.77,.015+math.cos(a+math.tau/8)*.055]],.007,True)
  if self.p['hairpin']:
   for i in range(3):self.bloom('ornament','hairpin_flower_'+str(i),[.135+i*.016,1.70-i*.027,.139],.016,'jewel',True)
  if self.p['neck_flower']:self.bloom('ornament','neck_flower',[0,1.415,.092],.031,'dress_light',True)
  b=self.r['bouquet'];cx,cy,cz=b['center_m']
  self.tube('bouquet','stems','stem',[[cx,cy-.16,cz-.065],[cx,cy+.10,cz]],.034,True)
  n=b['flower_count']
  for i in range(n):
   a=i*2.399963;rad=.14*math.sqrt((i+.5)/n);x=cx+math.cos(a)*rad;y=cy+math.sin(a)*rad
   z=cz+.045*math.sqrt(max(0,1-rad/.16))
   self.bloom('bouquet','flower_%02d'%i,[x,y,z],b['flower_radius_m'],'flower' if i%4 else 'flower_shadow',True)
  for i in range(b['leaf_count']):
   a=i*math.tau/b['leaf_count'];x=cx+math.cos(a)*.15;y=cy+math.sin(a)*.14
   self.poly('bouquet','leaf_'+str(i),'leaf' if i%2 else 'leaf_light',[[x,y],[x+.025,y+.045],[x+.035,y+.012],[x+.019,y-.02]],cz-.035,cz-.015,True)
  self.box('bouquet','bouquet_binding','dress_shadow',[-.043,.89,.25],[.043,.925,.32],True)
  points=[];turn=self.p['ribbon_turns']
  for i in range(100):
   t=i/99;a=t*math.tau*turn;radius=.28+.59*t
   points.append([math.sin(a)*radius,1.10-self.p['ribbon_slope']*t,math.cos(a)*radius*.80])
  self.tube('ribbon','floating_ribbon','ribbon',points,.0095,True)

 def create(self):
  self.base();self.skirt();self.hair();self.ornaments()
  frame=self.r['frame'];anchor=frame['upper_body_y_anchor']
  def ymap(y):return y if y<=anchor else anchor+(y-anchor)*frame['upper_body_y_scale']-frame.get('neck_shortening_m',0)*min(1,(y-anchor)/.16)
  for op in self.ops:
   sh=op['shape'];part=op['part'];head_part=part in ['head','hair','halo','ornament','brow_left','brow_right','eyelid_left','eyelid_right','mouth','mouth_corner_left','mouth_corner_right']
   sx=frame['head_width_scale'] if head_part else frame['neck_width_scale'] if op['id']=='neck' else 1
   if sh['kind']=='box':
    for key in ['min','max']:sh[key][0]*=sx;sh[key][1]=ymap(sh[key][1])
   elif sh['kind']=='tube':
    for v in sh['points']:v[0]*=sx;v[1]=ymap(v[1])
   elif sh['kind']=='extrusion':
    horizontal=op.get('transform',{}).get('basis')==[[1,0,0],[0,0,1],[0,-1,0]]
    for v in sh['polygon']:
     v[0]*=sx
     if not horizontal:v[1]=ymap(v[1])
    if horizontal:sh['z_min']=ymap(sh['z_min']);sh['z_max']=ymap(sh['z_max'])
   elif sh['kind']=='lathe':
    for v in sh['profile']:v[1]=ymap(v[1])
  assert len({o['id'] for o in self.ops})==len(self.ops),'Duplicate operation ID'
  rig=read((ROOT/'data'/self.r['source_rig']).resolve());used={o['part'] for o in self.ops}
  base={q['id']:q for q in rig['parts']}
  extra=[('hair_tail_back','hair',[0,1.5,-.18],'hair_secondary'),('hair_tail_left','hair',[-.14,1.5,-.1],'hair_secondary'),('hair_tail_right','hair',[.14,1.5,-.1],'hair_secondary'),('halo','head',[0,1.83,-.14],'ornament'),('ornament','head',[0,1.7,0],'ornament'),('bouquet','hand_left',[0,1.035,.335],'equipment'),('ribbon','pelvis',[0,.94,0],'ornament'),('dress_bodice','torso',[0,1.05,0],'costume')]
  for pid,parent,pivot,role in extra:base[pid]={'id':pid,'parent':parent,'pivot_m':pivot,'role':role}
  for sign,label in [(-1,'left'),(1,'right')]:
   for name,key in [('upper_arm','shoulder'),('forearm','elbow'),('hand','wrist')]:
    p=self.r['body'][key];base[name+'_'+label]['pivot_m']=[sign*p[0],p[1],p[2]]
  for q in base.values():
   q['pivot_m'][1]=ymap(q['pivot_m'][1])
   if q['id'].startswith(('brow','mouth','eyelid')):q['pivot_m'][0]*=frame['head_width_scale']
  parts=[];remaining=[base[k] for k in base if k in used]
  while remaining:
   ready=[q for q in remaining if q['parent'] is None or q['parent'] in {x['id'] for x in parts}]
   assert ready,'Part hierarchy missing parent or cyclic'
   for q in ready:parts.append(q);remaining.remove(q)
  provenance={'reference':{'file':self.p['reference_file'],'sha256':self.p['reference_sha256']},'design_sha256':sha(ROOT/'data/design.json'),'rules_sha256':sha(ROOT/'data/rules.json'),'preset_sha256':sha(ROOT/'data/presets'/(self.p['id']+'.json')),'generator_sha256':sha(__file__),'original_lily_authoring_convention':'semantic layers + immutable master/rig/bind + common compiler; source modules read only','source_modules':{str(p.relative_to(ROOT.parent)):sha(p) for p in [(ROOT/'data'/self.r['source_modules']/'adult_base.json').resolve(),(ROOT/'data'/self.r['source_modules']/'soft_taper.json').resolve(),(ROOT/'data'/self.r['source_rig']).resolve()]},'new_interpretations':self.p['new_interpretations'],'observations':self.p['observations']}
  master={'schema':'riverstone.voxel.master.v1','id':'image_character_r01__'+self.p['id'],'revision':self.r['version'],'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':self.p['palette'],'components':[{'id':'character','parts':[{'id':q['id'],'pivot':q['pivot_m'],'metadata':{'parent_part':q['parent'],'role':q['role']}} for q in parts],'operations':self.ops}],'instances':[{'id':'character','component':'character'}],'constraints':[],'extensions':{'provenance':provenance,'sampling':{'bulk_m':self.r['sampling']['bulk_m'],'detail_m':self.r['sampling']['detail_m'],'detail_operation_ids':sorted(self.details),'micro_operation_ids':sorted(self.micro),'micro_m':self.r['sampling']['micro_m'],'policy':'Each operation sampled once at data-selected pitch; no global fine resampling.'}}}
  mh=digest(master);rig['parts']=parts;rig['source_id']=master['id'];rig['master_hash']=mh;rig['motion_channels']={'bind':[q['id'] for q in parts]};rig['sockets']['bouquet']={'part':'hand_left','offset_m':[.065,.01,.085]};rig['sockets']['halo']={'part':'head','offset_m':[0,ymap(1.83)-ymap(1.405),-.14]};rig['sockets']['head_look']['offset_m'][1]*=frame['upper_body_y_scale'];rig['limits']=self.r['sampling'];rig['status']='Static rest-pose rig compatibility only. Locomotion/expression retargeting not yet verified.'
  tracks=[{'id':q['id'],'type':'rigid_transform','selector':{'instance':'character','part':q['id']},'axis':[1,0,0],'space':'part','interpolation':'smoothstep','keys':[{'time':t,'rotation_degrees':0,'translation':[0,0,0]} for t in [0,1]]} for q in parts]
  bind={'schema':'riverstone.voxel.transform_animation.v1','id':'all_parts_rest','source_id':master['id'],'master_hash':mh,'duration':1,'loop':True,'tracks':tracks}
  return master,rig,bind

def build(preset,output):
 start=time.monotonic();p=read(preset);r=read(ROOT/'data/rules.json')
 assert p['schema']=='riverstone.reference_character.preset.v1'
 assert sha(ROOT/p['reference_file'])==p['reference_sha256'],'Reference hash mismatch'
 assert output.is_relative_to(ROOT/'generated'),'Outputs must be local generated revisions'
 if output.exists():raise FileExistsError('Use a new immutable output directory')
 master,rig,bind=Author(p,r).create();output.mkdir(parents=True)
 dump(output/'master.json',master);dump(output/'rig.json',rig);dump(output/'bind.json',bind)
 bindings=bindings_from(master,bind);detail=set(master['extensions']['sampling']['detail_operation_ids']);layer_records=[];parts=[];renders=[];total=0
 for binding in bindings:
  part=binding['selector']['part'];sub=isolate(master,{('character',part)},True)
  for c in sub['components']:c['operations']=[o for o in c['operations'] if o['action']!='cut' or o.get('selector',{}).get('part',part)==part]
  part_groups=[];part_cells=0;part_hashes=[];part_renders=[]
  for tier in ['bulk','detail','micro']:
   layer=copy.deepcopy(sub)
   micro=set(master['extensions']['sampling']['micro_operation_ids'])
   for c in layer['components']:c['operations']=[o for o in c['operations'] if o['action']=='cut' or ('micro' if o['id'] in micro else 'detail' if o['id'] in detail else 'bulk')==tier]
   if not any(o['action']=='paint' for c in layer['components'] for o in c['operations']):continue
   pitch=r['sampling'][tier+'_m']
   compiled=compile_master(layer,{'pitch':pitch},max_candidate_cells=r['sampling']['maximum_candidate_cells_per_layer'],max_output_cells=r['sampling']['maximum_cells_per_layer'])
   assert compiled['cells'] and compiled['valid'],part
   render=make_render_data(compiled);renders.append(render);part_renders.append(render);part_groups.extend(render['groups']);part_cells+=len(compiled['cells']);total+=len(compiled['cells']);part_hashes.append(compiled['payload_hash'])
   name=part+'_'+tier;path=output/'cells'/ (name+'.json.gz');path.parent.mkdir(exist_ok=True)
   # Compact, deterministic compressed complete occupancy evidence.
   with gzip.GzipFile(filename=str(path),mode='wb',mtime=0,compresslevel=6) as f:f.write(json.dumps(compiled,separators=(',',':'),sort_keys=True).encode())
   layer_records.append({'part':part,'sampling':tier,'pitch_m':pitch,'derived_master_hash':compiled['master_hash'],'payload_hash':compiled['payload_hash'],'cell_count':len(compiled['cells']),'candidate_cells':compiled['candidate_cells'],'compiled_file':str(path.relative_to(output)),'compiled_sha256':sha(path),'common_provenance':render['provenance']})
  parts.append({**binding,'groups':part_groups,'bounds':{'min':[min(x['bounds']['min'][i] for x in part_renders) for i in range(3)],'max':[max(x['bounds']['max'][i] for x in part_renders) for i in range(3)]},'cell_count':part_cells,'payload_hash':digest(part_hashes)})
  assert total<=r['sampling']['maximum_total_cells'],'Total cell limit exceeded'
 render={'schema':'riverstone.voxel.render.v1','unit':'m','source_id':master['id'],'source_revision':master['revision'],'master_hash':digest(master),'payload_hash':digest([l['payload_hash'] for l in layer_records]),'pitch':r['sampling']['bulk_m'],'grid_origin':[0,0,0],'materials':master['materials'],'bounds':{'min':[min(x['bounds']['min'][i] for x in renders) for i in range(3)],'max':[max(x['bounds']['max'][i] for x in renders) for i in range(3)]},'cell_count':total,'quad_count':sum(x['quad_count'] for x in renders),'groups':[],'rigid_parts':parts,'geometry':'Genuine occupied 3D cells; selectively sampled independent semantic parts. Quads exported only by unchanged common render_data.py and tools/mesh.py. No 2D character impostors.','provenance':{'original_master_hash':digest(master),'rules_sha256':sha(ROOT/'data/rules.json'),'layers':layer_records}}
 assert render['quad_count']<=r['sampling']['maximum_quads'],'Quad limit exceeded'
 dump(output/'character.render.json',render,False)
 manifest={'schema':'riverstone.reference_character.cache.v1','id':p['id'],'reference_sha256':p['reference_sha256'],'master_hash':digest(master),'render_sha256':sha(output/'character.render.json'),'cell_count':total,'quad_count':render['quad_count'],'parts':len(parts),'operations':len(master['components'][0]['operations']),'bounds':render['bounds'],'sampling':r['sampling'],'seconds':round(time.monotonic()-start,2),'art_acceptance':'pending visual review','source_preservation':'Writes confined to image_characters_r01; read-only reuse of common and original_lily sources.','files':{str(x.relative_to(output)):sha(x) for x in sorted(output.rglob('*')) if x.is_file()}}
 dump(output/'manifest.json',manifest);print(json.dumps({k:v for k,v in manifest.items() if k not in ['files','sampling']},ensure_ascii=False),flush=True)
 return manifest
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--preset',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();build(a.preset.resolve(),a.output.resolve())
