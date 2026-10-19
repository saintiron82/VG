import json,math,hashlib
from pathlib import Path
import numpy as np
from ..north_junction_transition_r01.author import ROOT,CITY,g,a,dump,ref
HERE=Path(__file__).resolve().parent

def main():
 hp=CITY/'traversal_r5/revisions/r06_r8_precinct/public_network_r18_runtime_r01/evidence/upper_contour_failure_handoff_r01.json';h=json.loads(hp.read_bytes());f=h['failures'][1];pt=f['result']['end_position'];asset=f['assets']['SCENE:PUBLIC_NETWORK:ROAD:UPPER_CONTOUR'];ap=ROOT/asset['render_path'];d=json.loads(ap.read_bytes());rows=[]
 for i,t in enumerate(d['triangles']):
  arr=np.array(t);bb=[arr[:,0].min(),arr[:,2].min(),arr[:,0].max(),arr[:,2].max()]
  if bb[0]>pt[0]+.6 or bb[2]<pt[0]-.6 or bb[1]>pt[2]+.6 or bb[3]<pt[2]-.6:continue
  if arr[:,1].max()<pt[1]-1.1 or arr[:,1].min()>pt[1]+.9:continue
  n=np.cross(arr[1]-arr[0],arr[2]-arr[0]);a32=arr.astype(np.float32);n32=np.cross(a32[1]-a32[0],a32[2]-a32[0]);L=np.linalg.norm(n);L32=np.linalg.norm(n32)
  r=dict(collider_triangle_index=i,source_face_key=d['source_face_indices'][i],triangle_xyz_m=t,triangle_sha256=a.canonical_sha(t),normal64=(n/L).tolist()if L else[],normal32=(n32/L32).tolist()if L32 else[],area3d64_m2=float(L/2),xz_area64_m2=float(abs(n[1])/2),xz_area32_m2=float(abs(n32[1])/2),grade64=float(math.hypot(n[0],n[2])/abs(n[1]))if n[1]else None)
  rows.append(r)
 out=dict(sources=[ref(hp),ref(ap)],feet_xyz_m=[pt[0],pt[1]-.9,pt[2]],rows=rows);dump(HERE/'upper_contour_local_faces.json',out);print('count',len(rows))
 for r in rows:
  if r['xz_area64_m2']<1e-4 or r['grade64']is None or r['grade64']>1:print(r)
if __name__=='__main__':main()
