"""CPU drawing of actual common-compiler bounded ROI quads, not invented detail."""
import math
from PIL import Image,ImageDraw
import author_facility_roofs as a
import extend_roof_shapes as x
from preview_roi import dot,norm
CASES=[('registered_castle_rear_square_tower','hip_slope_course','Hip / coursed slope',[-1,1,-.4]),('registered_castle_rear_square_tower','hip_diagonal_cap','Hip / diagonal cap',[1,1,1]),('registered_castle_rear_square_tower','hip_eave','Hip / segmented eave',[-1,.7,-.4]),('cathedral_bell_tower_128m_r02','cone_curved_course','Spire / curved courses',[1,.4,1]),('cathedral_bell_tower_128m_r02','cone_apex_cap','Spire / original tapered cap',[1,.15,1]),('cathedral_bell_tower_128m_r02','cone_eave','Spire / eave collar',[1,.4,1]),('c3_property_ordinary_r2_9dbcfa8560a201ce','flat_cover_courses','Gallery / tile cover',[1,1,-1]),('c3_property_ordinary_r2_9dbcfa8560a201ce__wood_shingle','flat_cover_courses','Gallery / wood shingle cover',[1,1,-1])]
def panel(draw,origin,w,h,key,name,title,cam):
 rd=a.read(x.OUT/'roi'/(key+'.'+name+'.render.json'));cam=norm(cam);right=norm([cam[2],0,-cam[0]]);up=norm(x.cross(cam,right));light=norm([1,2,-1]);faces=[];allp=[]
 for group in rd['groups']:
  rgb=tuple(int(rd['materials'][group['material']][i:i+2],16) for i in (0,2,4))
  for q in group['quads']:
   u=[q[1][i]-q[0][i] for i in range(3)];v=[q[2][i]-q[0][i] for i in range(3)];normal=norm(x.cross(u,v))
   if dot(normal,cam)<=0:continue
   pts=[(dot(right,p),-dot(up,p)) for p in q];allp+=pts;shade=.56+.44*max(0,dot(normal,light));faces.append((sum(dot(cam,p) for p in q)/4,pts,tuple(int(c*shade) for c in rgb)))
 x0=min(p[0] for p in allp);x1=max(p[0] for p in allp);y0=min(p[1] for p in allp);y1=max(p[1] for p in allp);scale=min((w-60)/(x1-x0),(h-110)/(y1-y0));ox=origin[0]+(w-(x1-x0)*scale)/2;oy=origin[1]+70+(h-110-(y1-y0)*scale)/2
 draw.rounded_rectangle([origin[0]+7,origin[1]+7,origin[0]+w-7,origin[1]+h-7],radius=10,fill='#d9ddd6')
 for _,points,color in sorted(faces):draw.polygon([(ox+(u-x0)*scale,oy+(v-y0)*scale) for u,v in points],fill=color)
 draw.text((origin[0]+20,origin[1]+20),title,fill='#20383b');draw.text((origin[0]+20,origin[1]+40),'Actual 0.05 m voxels; '+str(rd['quad_count'])+' ROI quads',fill='#354d51')
def main():
 im=Image.new('RGB',(1600,920),'#edf0e9');draw=ImageDraw.Draw(im)
 for j,c in enumerate(CASES):panel(draw,((j%4)*400,(j//4)*440),400,440,*c)
 draw.text((20,890),'Bounded geometry QA only. Original colors preserved. Cut-open ROI edges are sample boundaries. Whole roofs and runtime remain pending.',fill='#243c3d');im.save(x.OUT/'actual_roi_geometry.v4.png')
if __name__=='__main__':main()
