"""CPU orthographic QA of actual compiled ROI quads, never synthetic mesh detail."""
import math
from PIL import Image,ImageDraw,ImageFont
import author_facility_roofs as a
import finish_roofs as f

def dot(x,y):return sum(v*w for v,w in zip(x,y))
def norm(x):
 s=math.sqrt(dot(x,x));return [v/s for v in x]
def panel(draw,origin,w,h,record,name,render_dir=None):
 key=record['asset_key'];d=a.read(a.ROOT/record['descriptor']['path']);rd=a.read((render_dir or f.OUT/'roi')/(key+'.'+name+'.render.json'));p=d['planes'][0];t=a.core.compose(p['component_instances'][0]['transform'],p['operation_transform']);right=norm([1,0,-1]);up=norm([.5,1,.5]);cam=norm([-1,1,-1]);light=norm([-1,2,-1]);faces=[];allp=[]
 for group in rd['groups']:
  rgb=tuple(int(rd['materials'][group['material']][i:i+2],16) for i in (0,2,4))
  for q in group['quads']:
   v=[a.core.inverse(t,x) for x in q];aa=[v[1][j]-v[0][j] for j in range(3)];bb=[v[2][j]-v[0][j] for j in range(3)];normal=norm([aa[1]*bb[2]-aa[2]*bb[1],aa[2]*bb[0]-aa[0]*bb[2],aa[0]*bb[1]-aa[1]*bb[0]])
   if dot(normal,cam)<=0:continue
   pts=[(dot(right,x),-dot(up,x)) for x in v];allp+=pts;shade=.57+.43*max(0,dot(normal,light));color=tuple(int(c*shade) for c in rgb);faces.append((sum(dot(cam,x) for x in v)/4,pts,color))
 x0=min(x for x,y in allp);x1=max(x for x,y in allp);y0=min(y for x,y in allp);y1=max(y for x,y in allp);scale=min((w-65)/(x1-x0),(h-110)/(y1-y0));ox=origin[0]+(w-(x1-x0)*scale)/2;oy=origin[1]+70+(h-105-(y1-y0)*scale)/2
 draw.rounded_rectangle([origin[0]+8,origin[1]+8,origin[0]+w-8,origin[1]+h-8],radius=12,fill='#d6d8d1')
 for depth,pts,color in sorted(faces):draw.polygon([(ox+(x-x0)*scale,oy+(y-y0)*scale) for x,y in pts],fill=color)
 title=('Cathedral' if 'cathedral' in key else 'Port loading shed')+' / '+('eave + verge + overlap' if name.startswith('eave') else 'segmented ridge caps')
 draw.text((origin[0]+24,origin[1]+22),title,fill='#202d31');draw.text((origin[0]+24,origin[1]+44),'Actual 0.05 m common-compiler ROI | '+str(rd['quad_count'])+' quads',fill='#445152')

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--native-bounds',action='store_true');args=parser.parse_args();render_dir=f.OUT/'post_cell_bounds' if args.native_bounds else f.OUT/'roi'
 cat=a.read(f.OUT/'layered_compile_catalog.json');im=Image.new('RGB',(1200,1040),'#edf0e9');draw=ImageDraw.Draw(im)
 for row,r in enumerate(cat['assets']):
  for col,name in enumerate(['eave_verge_tile_overlap','segmented_ridge_caps']):panel(draw,(col*600,row*500),600,500,r,name,render_dir)
 draw.text((20,1010),'Native cell bounds. Geometry QA only. Full roof/runtime/visual acceptance pending.' if args.native_bounds else 'Geometry QA only. Source color preserved. Full roof/runtime/visual acceptance still pending.',fill='#263b3b');im.save((render_dir if args.native_bounds else f.OUT)/'actual_roi_geometry.png')
