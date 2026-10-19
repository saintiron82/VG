"""Bounded software rasterization of the actual common-mesher quads.

These are geometry inspection images, not Godot screenshots or image generation.
The fixed front camera and measurement metrics live in build_volume.py.
"""
from pathlib import Path
import hashlib,json,math
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def render(aid,yaw,pitch,name):
 d=ROOT/'generated'/aid;r=json.loads((d/'character.render.json').read_text());size=720
 camera=np.array([math.sin(yaw)*math.cos(pitch),math.sin(pitch),math.cos(yaw)*math.cos(pitch)])
 right=np.cross([0,1,0],camera);right/=np.linalg.norm(right);up=np.cross(camera,right)
 basis=np.stack([right,up,camera],axis=1);center=np.array(r['frame']['camera_center_m']);scale=size/2.28
 rgb=np.full((size,size,3),246,np.uint8);zbuf=np.full((size,size),-np.inf)
 light=np.array([-.4,.7,.6]);light/=np.linalg.norm(light)
 for group in r['groups']:
  hx=r['materials'][group['material']]['color'];color=np.array([int(hx[i:i+2],16) for i in (1,3,5)])
  for quad in group['quads']:
   q=np.asarray(quad);n=np.cross(q[1]-q[0],q[2]-q[0]);n/=np.linalg.norm(n)
   if n@camera<=0:continue
   color_shaded=np.clip(color*(.55+.45*max(0,n@light)),0,255).astype(np.uint8)
   p=(q-center)@basis;p[:,0]=size/2+p[:,0]*scale;p[:,1]=size/2-p[:,1]*scale
   for tri in ((0,1,2),(0,2,3)):
    t=p[list(tri)];lo=np.maximum(np.floor(t[:,:2].min(axis=0)).astype(int),0);hi=np.minimum(np.ceil(t[:,:2].max(axis=0)).astype(int)+1,size)
    if np.any(hi<=lo):continue
    x,y=np.meshgrid(np.arange(lo[0],hi[0])+.5,np.arange(lo[1],hi[1])+.5)
    a,b,c=t;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(den)<1e-8:continue
    wa=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den
    wb=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den;wc=1-wa-wb
    depth=wa*a[2]+wb*b[2]+wc*c[2];zs=zbuf[lo[1]:hi[1],lo[0]:hi[0]]
    valid=(wa>=-1e-7)&(wb>=-1e-7)&(wc>=-1e-7)&(depth>zs)
    zs[valid]=depth[valid];rgb[lo[1]:hi[1],lo[0]:hi[0]][valid]=color_shaded
 im=Image.fromarray(rgb);draw=ImageDraw.Draw(im);draw.rectangle((0,0,size,37),fill='white');draw.text((12,8),aid+' | common voxel mesh | '+name+' | DEPTH IS ASSUMED',fill='black')
 im.save(d/(name+'.png'))
 return {'view':name,'image':name+'.png','image_sha256':sha(d/(name+'.png')),'yaw_degrees':math.degrees(yaw),'pitch_degrees':math.degrees(pitch),'camera_center_m':center.tolist(),'orthographic_height_m':2.28,'renderer':'deterministic CPU triangle z-buffer, not Godot','render_input_sha256':sha(d/'character.render.json'),'renderer_code_sha256':sha(Path(__file__))}

def sheet(aid):
 a=next(a for a in json.loads((ROOT/'data/annotations.json').read_text())['assets'] if a['id']==aid)
 d=ROOT/'generated'/aid;source=(ROOT/'data'/a['source']).resolve();panels=[]
 for p,title in [(source,'Source image'),(d/'projected_compiled_albedo.png','Compiled voxels: fixed front'),(d/'projection_overlay.png','Source / voxel contour overlay')]:
  im=Image.open(p).convert('RGB');im.thumbnail((375,415));panel=Image.new('RGB',(385,450),'white');panel.paste(im,((385-im.width)//2,30));ImageDraw.Draw(panel).text((10,8),title,fill='black');panels.append(panel)
 out=Image.new('RGB',(1155,480),'white')
 for i,p in enumerate(panels):out.paste(p,(i*385,0))
 ImageDraw.Draw(out).text((12,458),'Single-view image-constrained volume prototype. Front fit does NOT validate depth/back reconstruction.',fill='black');out.save(d/'source_projection_comparison.png')

if __name__=='__main__':
 for aid in ['violet','cyan']:
  views=[render(aid,math.radians(40),math.radians(8),'three_quarter'),render(aid,math.radians(90),0,'side'),render(aid,math.pi,0,'rear')]
  (ROOT/'generated'/aid/'software_render_provenance.json').write_text(json.dumps(views,indent=2)+'\n');sheet(aid)
