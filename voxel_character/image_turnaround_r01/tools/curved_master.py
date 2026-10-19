"""Shared multi-view curved master authoring; no image column extrusion.

Elliptic lofts, tapered 3D strand lofts, and independent curved cloth panels
adapt to existing common polygon-extrusion/tube grammar. The continuous design
preview and compiled voxel surface are explicitly different artifacts.
"""
from pathlib import Path
import argparse,gzip,hashlib,json,math,sys
import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator
from refine_head import refine_head
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT.parent/'common'))
from core import digest
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rounded(v):return np.round(v,7).tolist()
def dump(p,d):p.write_text(json.dumps(d,separators=(',',':'))+'\n')

class Author:
 def __init__(self,r,p):self.r=r;self.p=p;self.ops=[];self.groups={};self.n=0;self.profiles=[];self.panel_surfaces={}
 def quad(self,mat,points):self.groups.setdefault(mat,[]).append(rounded(points))
 def op(self,part,mat,shape,transform=None):
  self.n+=1;o={'id':part+'_'+str(self.n),'part':part,'action':'paint','material':mat,'shape':shape}
  if transform:o['transform']=transform
  self.ops.append(o)
 def ellipse_loft(self,part,mat,centers,widths,depths,step=None):
  centers=np.asarray(centers,float);widths=np.asarray(widths);depths=np.asarray(depths);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(centers,axis=0),axis=1))]
  count=max(3,int(arc[-1]/(step or self.r['surface_samples']['curve_step']))+1);s=np.linspace(0,arc[-1],count);points=np.column_stack([PchipInterpolator(arc,centers[:,i])(s) for i in range(3)]);rw=PchipInterpolator(arc,widths)(s);rd=PchipInterpolator(arc,depths)(s);rings=[];previous_u=np.array([1.,0.,0.]);angles=np.arange(self.r['surface_samples']['ellipse_sides'])*math.tau/self.r['surface_samples']['ellipse_sides']
  for i,c in enumerate(points):
   tangent=points[min(i+1,len(points)-1)]-points[max(i-1,0)];tangent/=np.linalg.norm(tangent)
   if part in ['head','neck','torso','scalp_top']:tangent=np.array([0.,1.,0.])
   u=previous_u-tangent*(previous_u@tangent)
   if np.linalg.norm(u)<.01:u=np.cross(tangent,[0,0,1])
   u/=np.linalg.norm(u);v=np.cross(tangent,u);previous_u=u
   polygon=np.column_stack([np.cos(angles)*rw[i],np.sin(angles)*rd[i]]);ring=c+polygon[:,0,None]*u+polygon[:,1,None]*v;rings.append(ring)
   length=(s[min(i+1,len(s)-1)]-s[max(i-1,0)])/2
   if i in [0,len(s)-1]:length*=2
   basis=np.stack([u,v,tangent],axis=1)
   color=mat if not isinstance(mat,list) else mat[min(len(mat)-1,int(i/max(1,len(s)-1)*len(mat)))]
   self.op(part,color,{'kind':'extrusion','polygon':rounded(polygon),'z_min':-max(.006,length*.62),'z_max':max(.006,length*.62),'minimum_cells':1},{'translation':rounded(c),'basis':basis.tolist()})
   if i:
    for j in range(len(angles)):self.quad(color,[rings[i-1][j],rings[i-1][(j+1)%len(angles)],ring[(j+1)%len(angles)],ring[j]])
  for index,flip in [(0,True),(-1,False)]:
   ring=rings[index];c=points[index]
   for j in range(len(ring)):
    q=[c,ring[j],ring[(j+1)%len(ring)],c]
    self.quad(mat[0] if isinstance(mat,list) else mat,q[::-1] if flip else q)
 def triangle_prism(self,part,points,thickness,outer='dress',inner='lining'):
  a,b,c=np.asarray(points);u=b-a;u/=np.linalg.norm(u);normal=np.cross(b-a,c-a)
  if np.linalg.norm(normal)<1e-9:return
  normal/=np.linalg.norm(normal);v=np.cross(normal,u);basis=np.stack([u,v,normal],axis=1);polygon=np.array([[0,0],[float((b-a)@u),float((b-a)@v)],[float((c-a)@u),float((c-a)@v)]]);centroid=polygon.mean(0);polygon=(centroid+(polygon-centroid)*1.025).tolist()
  self.op(part,outer,{'kind':'extrusion','polygon':polygon,'z_min':-thickness/2,'z_max':thickness/2,'minimum_cells':1},{'translation':rounded(a),'basis':basis.tolist()})
  self.op(part,inner,{'kind':'extrusion','polygon':polygon,'z_min':-thickness/2-.003,'z_max':-thickness*.30,'minimum_cells':0},{'translation':rounded(a),'basis':basis.tolist()})
  self.quad(outer,[a,b,c,c]);self.quad(inner,[c,b,a,a])
 def panel(self,p):
  rows=np.array(p['profile']);tt=np.linspace(0,len(rows)-1,self.r['surface_samples']['panel_t']);uu=np.linspace(-1,1,self.r['surface_samples']['panel_u']);prof=np.column_stack([PchipInterpolator(np.arange(len(rows)),rows[:,i])(tt) for i in range(3)]);angle_value=p['angle_deg']
  if p['id']=='left_petal':angle_value=self.p['cloth_fit']['left_angle_degrees']
  elif p['id']=='right_petal':angle_value=self.p['cloth_fit']['right_angle_degrees']
  angle=math.radians(angle_value);radial=np.array([math.sin(angle),0,math.cos(angle)]);cross=np.array([math.cos(angle),0,-math.sin(angle)]);surface=[]
  for i,(y,r,w) in enumerate(prof):
   t=i/(len(prof)-1);row=[]
   for u in uu:
    # Curved cross-section and a turning hem create a true surface in XYZ.
    bend=p['bow']*math.sin(math.pi*t)*(1-u*u)+p['curl']*t**5*math.cos(u*math.pi/2)
    point=radial*(r+bend)+cross*(u*w);point[1]=y+p['hem_wave']*t**3*(u*u-.35)+.04*math.sin(t*math.pi*3+u*1.2)*t
    if p['id']=='front_short_panel':point[1]+=self.p['front_hem_offset']*t
    point[0]*=1+(self.p['cloth_fit']['width_scale']-1)*t;point[2]*=1+(self.p['cloth_fit']['depth_scale']-1)*t
    row.append(point)
   surface.append(row)
  surface=np.array(surface);self.panel_surfaces[p['id']]=surface;thick=self.r['surface_samples']['cloth_thickness_m']
  for i in range(len(tt)-1):
   for j in range(len(uu)-1):
    a,b,c,d=surface[i,j],surface[i,j+1],surface[i+1,j+1],surface[i+1,j]
    self.triangle_prism(p['id'],[a,c,b],thick);self.triangle_prism(p['id'],[a,d,c],thick)
 def tube(self,part,mat,points,radius):
  for a,b in zip(points,points[1:]):self.op(part,mat,{'kind':'tube','points':[rounded(a),rounded(b)],'radius':radius,'minimum_radius_cells':.6})
  self.ellipse_loft(part,mat,points,[radius]*len(points),[radius]*len(points),step=.025)

def measured_body(a,r,p,source,measurement):
 # Pixel spans from annotated semantic search strips, not manually set radii.
 im=np.asarray(Image.open(source).convert('RGB'));h,w=im.shape[:2];records=[];front_scale=(p['front_floor_y']-p['front_scalp_y'])/(826-64);scale=1.82/(p['front_floor_y']-p['front_scalp_y']);profiles={}
 for section in r['body_sections']:
  y=round(p['front_scalp_y']+(section['y']-64)*front_scale);spans=[]
  for name,axis,oldaxis in [('front',p['front_axis_u'],333),('side',p['side_axis_u'],819)]:
   roi=section['front_roi' if name=='front' else 'side_roi'];x0=round(axis+(roi[0]-oldaxis)*front_scale);x1=round(axis+(roi[1]-oldaxis)*front_scale);crop=im[max(0,y-2):y+3,x0:x1].astype(float);bright=crop.mean(2);warm=(crop[:,:,0]>crop[:,:,2]+3)&(crop[:,:,0]>crop[:,:,1])&(bright>110)
   if section['kind']=='skin':take=warm
   elif section['kind']=='white':take=bright>222
   elif section['kind']=='skin_or_white':take=warm|(bright>222)
   else:
    bg=np.array([215,215,218]);take=np.linalg.norm(crop-bg,axis=2)>20
   xs=np.where(take.any(0))[0];observed=len(xs)>=4
   left=int(xs.min()+x0) if observed else x0;right=int(xs.max()+x0+1) if observed else x1;censored=(left<=x0 or right>=x1)
   spans.append({'view':name,'row_y':y,'search_interval':[x0,x1],'span':[left,right],'status':'pixel span' if observed and not censored else ('ROI-censored pixel span' if observed else 'occluded ROI prior')})
  (f0,f1),(s0,s1)=[q['span'] for q in spans];rx=max(.012,(f1-f0)*scale/2);rz=max(.014,(s1-s0)*scale/2);cx=((f0+f1)/2-p['front_axis_u'])*scale;cz=(p['side_axis_u']-(s0+s1)/2)*scale;wy=(p['front_floor_y']-y)*scale
  if section['part']=='head':
   rx*=.88;rz*=.87
   # The visible side face is not the complete skull depth; retain a rear cranium behind it.
   if section['id'] in ['cheek','temple']:
    # Rear boundary comes from the measured side cranium span with a stated hair allowance.
    cranium=next(v for v in records if v['id']=='cranium');rear_span=cranium['samples'][1]['span'][1];back=(p['side_axis_u']-rear_span)*scale+r['head_policy']['hair_allowance_m'];front=cz+rz;cz=(front+back)/2;rz=(front-back)/2
   if section['id']=='scalp_tip':rx=.018;rz=.018 # Explicit scalp shell allowance, not measured skin thickness.
  profiles.setdefault(section['part'],[]).append([cx,wy,cz,rx,rz]);records.append({'id':section['id'],'samples':spans,'world_section':[cx,wy,cz,rx,rz],'depth_evidence':'AI side-view pixel span; not original observed depth','scalp_shell_allowance':.88 if section['part']=='head' else 1})
 refinement=read(ROOT/'data/refinement_annotations.json')[p['id']];mask=np.load(ROOT/'measurements'/p['id']/'pixels.npz')['mask'];a.head_refinement=refine_head(profiles,records,im,mask,p,refinement)
 a.profiles=records
 for part,rows in profiles.items():
  rows=sorted(rows,key=lambda v:v[1])
  if part=='neck':
   rows[0][1]-=.035;rows[-1][1]+=.035
   for row in rows:row[2]=-.015;row[3]=min(.055,max(.035,row[3]));row[4]=max(.04,min(.055,row[4]))
  if part=='torso':rows=[[0,1.02,-.015,.125,.085],[0,1.13,-.01,.105,.08]]+rows
  mat=['dress']*9+['skin'] if part=='torso' else 'skin';a.ellipse_loft(part,mat,[v[:3] for v in rows],[v[3] for v in rows],[v[4] for v in rows],.018)
 return profiles

def author(aid):
 r=read(ROOT/'data/shared_rules.json');p=read(ROOT/'data'/(aid+'_fitted_preset.json'));annotation=next(x for x in read(ROOT/'data/measurement_annotations.json')['assets'] if x['id']==aid);measurement=read(ROOT/'measurements'/aid/'measurements.json');source=(ROOT/'data'/annotation['sheet']).resolve();assert sha(source)==annotation['sheet_sha256'];out=ROOT/'generated'/(aid+'_curved06b');out.mkdir(exist_ok=False);a=Author(r,p);profiles=measured_body(a,r,p,source,measurement)
 limb=r['limbs']
 for sign,label in [(-1,'left'),(1,'right')]:
  points=[[sign*v[0],v[1],v[2]] for v in [limb['shoulder'],limb['elbow'],limb['wrist']]];a.ellipse_loft('arm_'+label,'dress' if p['gloves'] else 'skin',points,limb['arm_radii'],limb['arm_radii']);a.ellipse_loft('hand_'+label,'dress' if p['gloves'] else 'skin',[points[-1],[sign*.035,1.065,.27]],[.030,.018],[.025,.018])
  x=sign*limb['leg_x'];leg=[[x,.99,0],[x,.82,.012],[x,.57,.012],[x,.32,0],[x,.105,0]];a.ellipse_loft('leg_'+label,'stocking',leg,[.063,.055,.040,.035,.024],[.067,.058,.043,.036,.026]);a.ellipse_loft('shoe_'+label,'shoe',[[x,.025,.08],[x,.070,.045],[x,.11,0]],[.025,.036,.024],[.07,.085,.036])
 for panel in r['panels']:a.panel(panel)
 # Rounded scalp backing and flowing, genuinely three-dimensional tapered locks.
 head=np.array(sorted(profiles['head'],key=lambda v:v[1]))
 def skull_z(x,y,front=True):
  cx,cz,rx,rz=[np.interp(y,head[:,1],head[:,j]) for j in [0,2,3,4]]
  return cz+(1 if front else -1)*rz*math.sqrt(max(.01,1-((x-cx)/rx)**2))
 hair=r['hair'];count=hair['lock_count'];hs=p['hair_scale']
 for i in range(count):
  f=i/(count-1);sign=-1 if f<.5 else 1;q=abs(f-.5)*2;xroot=(f-.5)*.20;tipx=sign*(.25+.33*q)*hs[0];tipy=(hair['tip_y']+.16*math.sin(i*1.7))*1/hs[1];tipz=(-.30-.23*(1-q))*hs[2]
  centers=[[xroot*.65,1.795,skull_z(xroot*.65,1.795,False)-.012],[xroot*1.05,1.70,skull_z(xroot*1.05,1.70,False)-.018],[xroot*1.3,1.60,skull_z(xroot*1.3,1.60,False)-.020],[sign*(.15+.08*q),1.38,-.19],[tipx*.92,1.13,-.34],[tipx,tipy+.02,tipz],[tipx*.86,tipy+.08,tipz-.03]]
  a.ellipse_loft('hair_lock_'+str(i),['hair','hair','hair_light'],centers,[.025,.043,.055,.070,.065,.035,.007],[.021,.033,.04,.045,.039,.022,.006])
 # Scalp cap is curved strip geometry, open over lower face, never a face plate.
 head=np.array(sorted(profiles['head'],key=lambda v:v[1]))
 def scalp_patch(yvalues,angles):
  rows=[]
  for y in yvalues:
   cx,cz,rx,rz=[np.interp(y,head[:,1],head[:,j]) for j in [0,2,3,4]]
   taper=1.0
   if y>=1.7316:
    cx,cz,rx,rz=[np.interp(1.7316,head[:,1],head[:,j]) for j in [0,2,3,4]];taper=math.sqrt(max(.0001,1-((y-1.7316)/(r['head_policy']['crown_tip_y']-1.7316))**2))
   row=[[cx+(rx+.018)*taper*math.sin(t),y,cz+(rz+.020)*taper*math.cos(t)] for t in angles];rows.append(row)
  for i in range(len(rows)-1):
   for j in range(len(rows[0])-1):
    a.triangle_prism('scalp_shell',[rows[i][j],rows[i][j+1],rows[i+1][j+1]],.025,'hair','hair');a.triangle_prism('scalp_shell',[rows[i][j],rows[i+1][j+1],rows[i+1][j]],.025,'hair','hair')
 scalp_patch(np.linspace(head[0,1],1.735,10),np.linspace(math.radians(60),math.radians(300),18))
 scalp_patch(np.linspace(1.72,r['head_policy']['crown_tip_y'],10),np.linspace(0,math.tau,25))
 for i in range(7):
  x=(i-3)*.025;yend=p['bang_tip_y'][i];endx=p['bang_tip_x'][i]
  points=[[x*.65,1.80,skull_z(x*.65,1.80)+.019],[x,1.735,skull_z(x,1.735)+.025],[endx,yend,skull_z(endx,yend)+.014]]
  a.ellipse_loft('bang_'+str(i),'hair',points,[.022,.027,.005],[.017,.021,.006])
 # Coarse face indicators are integrated small volumes on the curved skin surface.
 for index,eye in enumerate(measurement['visible_eyes']):
  scale=1.82/(p['front_floor_y']-p['front_scalp_y']);ex=(eye['pixel'][0]-p['front_axis_u'])*scale;ey=(p['front_floor_y']-eye['pixel'][1])*scale
  cx,cz,rx,rz=[np.interp(ey,head[:,1],head[:,j]) for j in [0,2,3,4]];ez=cz+rz*math.sqrt(max(.01,1-((ex-cx)/rx)**2))+.004
  a.ellipse_loft('eye_'+str(index),'iris',[[ex,ey-.006,ez],[ex,ey+.006,ez]],[.019,.018],[.006,.006],.012)

 bouquet=r['bouquet'];cx,cy,cz=bouquet['center'];a.ellipse_loft('bouquet_core','leaf',[[cx,cy-.12,cz],[cx,cy,cz],[cx,cy+.12,cz]],[.04,.145,.03],[.035,.105,.025])
 for i in range(22):
  t=i*2.39996;rr=.125*math.sqrt((i+.5)/22);x=rr*math.cos(t);y=cy+rr*math.sin(t);z=cz+.10*math.sqrt(max(0,1-(rr/.15)**2));a.ellipse_loft('flower_'+str(i),'flower',[[x,y-.026,z],[x,y-.012,z],[x,y+.012,z],[x,y+.026,z]],[.004,.028,.028,.004],[.003,.021,.021,.003],.014)
 if p['crown']:
  cx,cy,cz=.035,1.865,.015
  for j in range(7):
   t0=j*math.tau/7;t1=(j+1)*math.tau/7;tm=(t0+t1)/2
   a.triangle_prism('crown',[[cx+.065*math.cos(t0),cy,cz+.065*math.sin(t0)],[cx+.065*math.cos(t1),cy,cz+.065*math.sin(t1)],[cx+.078*math.cos(tm),cy+.070,cz+.078*math.sin(tm)]],.012,'shoe','white')
 if p['neck_flower']:
  a.ellipse_loft('neck_flower','flower',[[0,1.513,.045],[0,1.532,.045]],[.015,.012],[.013,.010],.012)
 mx=(p['mouth_pixel'][0]-p['front_axis_u'])*scale;my=(p['front_floor_y']-p['mouth_pixel'][1])*scale;mz=skull_z(mx,my)+.003
 a.ellipse_loft('mouth','dark',[[mx-.014,my,mz],[mx,my-.004,mz+.001],[mx+.014,my,mz]],[.003,.004,.003],[.003,.004,.003],.008)
 ring=[]
 for t in np.linspace(.1,math.tau*.85,40):ring.append([.065+.14*math.cos(t),1.865+.14*math.sin(t),-.005-.05*math.sin(t)])
 a.tube('halo','halo',ring,.0125)
 # Two open ribbons: bouquet/waist root, then surface-supported side-panel paths.
 ribbon_records=[]
 for sign,panel_name in [(-1,'left_petal'),(1,'right_petal')]:
  surface=a.panel_surfaces[panel_name];points=[[sign*.075,1.12,.285],[sign*.11,1.20,.11]]
  for row_index in range(1,len(surface)-2):
   row=surface[row_index];front_index=int(np.argmax(row[:,2]));point=row[front_index].copy();point[2]+=.018;point[0]+=sign*.012;points.append(point.tolist())
  a.tube('ribbon_'+panel_name,'ribbon',points,.008);ribbon_records.append({'part':'ribbon_'+panel_name,'support_panel':panel_name,'centerline':points,'attachment':'bouquet/waist root and front edge of named curved panel','inference':'manual hidden attachment reconciliation; not a measured wrap'})
 mats={k:{'color':v} for k,v in p['materials'].items()};parts=sorted({o['part'] for o in a.ops});master={'schema':'riverstone.voxel.master.v1','id':'turnaround_'+aid,'revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':mats,'components':[{'id':'character','parts':[{'id':v,'pivot':[0,0,0]} for v in parts],'operations':a.ops}],'instances':[{'id':'character','component':'character'}],'constraints':[],'extensions':{'original_sha256':annotation['original_sha256'],'turnaround_sha256':annotation['sheet_sha256'],'prompt_sha256':measurement['prompt_sha256'],'measurement_sha256':sha(ROOT/'measurements'/aid/'measurements.json'),'rules_sha256':sha(ROOT/'data/shared_rules.json'),'refinement_annotations_sha256':sha(ROOT/'data/refinement_annotations.json'),'head_refiner_sha256':sha(ROOT/'tools/refine_head.py'),'preset_sha256':sha(ROOT/'data'/(aid+'_fitted_preset.json')),'generator_sha256':sha(Path(__file__)),'geometry':'elliptic section lofts + tapered 3D curved hair lofts + six independent curved petal panels, adapted to existing common grammar','hidden_views':'AI-generated design hypotheses, not observed original anatomy','review_status':'coarse curved master awaiting multi-view inspection, not finished character'}}
 with gzip.GzipFile(filename=str(out/'master.json.gz'),mode='wb',mtime=0) as f:f.write(json.dumps(master,separators=(',',':')).encode())
 dump(out/'section_measurements.json',a.profiles);dump(out/'head_refinement.json',a.head_refinement);dump(out/'ribbon_attachment.json',ribbon_records);allpoints=np.array([pt for group in a.groups.values() for q in group for pt in q]);preview={'schema':'riverstone.voxel.render.v1','unit':'m','source_id':master['id'],'source_revision':1,'master_hash':digest(master),'pitch':r['pitch'],'grid_origin':[0,0,0],'materials':mats,'bounds':{'min':allpoints.min(0).tolist(),'max':allpoints.max(0).tolist()},'groups':[{'material':mat,'quads':qs} for mat,qs in a.groups.items()],'quad_count':sum(map(len,a.groups.values())),'cell_count':0,'frame':{'camera_center_m':[0,1.02,0]},'provenance':{'status':'continuous design surface before voxel compilation; not common compiled mesh','generator_sha256':sha(Path(__file__))}}
 
 with gzip.GzipFile(filename=str(out/'continuous_design.render.json.gz'),mode='wb',mtime=0) as f:f.write(json.dumps(preview,separators=(',',':')).encode())
 dump(out/'design_manifest.json',{'master_hash':digest(master),'master_file_sha256':sha(out/'master.json.gz'),'operations':len(a.ops),'preview_quads':preview['quad_count'],'original_sha256':annotation['original_sha256'],'turnaround_sha256':annotation['sheet_sha256'],'status':'curved design master, voxel compilation pending'});print(json.dumps({'id':aid,'operations':len(a.ops),'preview_quads':preview['quad_count'],'master_hash':digest(master)}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('asset',choices=['violet','cyan']);author(p.parse_args().asset)
