"""Read-only pixel-ray classification of frozen r3 terrain triangles."""
import json,math,hashlib
from pathlib import Path
import numpy as np
from ..r11_ground_materials import author as terrain
HERE=Path(__file__).resolve().parent;CITY=terrain.CITY;SCENE=CITY/'evidence/visual_registered_common_r3/camera_scene.json'
D=json.loads(SCENE.read_bytes());W,H=1536,1024

def inspect(view,pixels):
 camera=D['inspection_cameras'][view];eye=np.array(camera['position_m'],float);f=np.array(camera['target_m'])-eye;f/=np.linalg.norm(f);right=np.cross(f,[0,1,0]);right/=np.linalg.norm(right);up=np.cross(right,f);fy=H/2/math.tan(math.radians(31));out=[]
 for px,py in pixels:
  direction=f+right*(px-W/2)/fy-up*(py-H/2)/fy;direction/=np.linalg.norm(direction);hits=[]
  for material,flat in D['surfaces'].items():
   ts=np.array(flat,float).reshape((-1,3,3));e1=ts[:,1]-ts[:,0];e2=ts[:,2]-ts[:,0];p=np.cross(direction,e2);det=np.einsum('ij,ij->i',e1,p);valid=np.abs(det)>1e-10;inv=np.divide(1,det,out=np.zeros_like(det),where=valid);tv=eye-ts[:,0];u=np.einsum('ij,ij->i',tv,p)*inv;q=np.cross(tv,e1);v=np.einsum('j,ij->i',direction,q)*inv;t=np.einsum('ij,ij->i',e2,q)*inv;valid &= (u>=0)&(v>=0)&(u+v<=1)&(t>0)
   ids=np.nonzero(valid)[0]
   if len(ids):
    i=ids[np.argmin(t[ids])];point=eye+direction*t[i];tri=ts[i];cent=tri.mean(axis=0);r=terrain.prior.owner_at(float(point[0]),float(point[2]));h=terrain.prior.source_surface_height_at(r,float(point[0]),float(point[2]));hits.append(dict(material=material,triangle_index=int(i),distance_m=float(t[i]),vertices_xyz_m=tri.tolist(),point_xyz_m=point.tolist(),source_owner_id=r['owner_id'],source_kind=r['kind'],source_point_y_m=h,point_height_error_m=float(point[1]-h),centroid_xyz_m=cent.tolist(),max_edge_length_m=max(float(np.linalg.norm(tri[i]-tri[(i+1)%3])) for i in range(3))))
  out.append(dict(pixel_xy=[px,py],nearest_terrain_hit=min(hits,key=lambda x:x['distance_m']) if hits else None))
 return out
report=dict(scene_path=str(SCENE.relative_to(CITY)),scene_sha256=hashlib.sha256(SCENE.read_bytes()).hexdigest(),camera_fov_degrees=62,method='Ray/triangle intersection against actual frozen rendered terrain; native building triangles are not considered, so only unobstructed ground pixels are interpreted.',cathedral=inspect('cathedral_close',[[606,813],[627,813],[575,750],[589,750],[648,921],[672,921],[1379,886],[1360,886]]),training=inspect('training_close',[[394,700],[372,700],[534,568],[557,568],[602,688],[604,663],[760,700],[772,682]]))
(HERE/'visible_triangle_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
