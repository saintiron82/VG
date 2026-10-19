import json,math,collections
import numpy as np
from pathlib import Path
from ..north_junction_transition_r01.author import ROOT,CITY,g,a,dump,ref
from .trace_sources import key
HERE=Path(__file__).resolve().parent

def main():
 bp=HERE.parent/'north_junction_transition_r01/activation_binding.json';binding=json.loads(bp.read_bytes());patches=[json.loads((ROOT/r['path']).read_bytes())for r in binding['patches']];outputs=[]
 for file,road in [('lower_market_failure_handoff_r01.json','MARKET_NORTH'),('main_west_failure_handoff_r01.json','CENTRAL_WEST_RADIAL')]:
  hp=CITY/'traversal_r5/revisions/r06_r8_precinct/public_network_r18_runtime_r01/evidence'/file;h=json.loads(hp.read_bytes());f=next(r for r in h['failures']if r['result']['id']=='ROAD:'+road+'_REVERSE');pt=f['result']['end_position'];asset=next(v for k,v in f['assets'].items()if k.startswith('SCENE:'));ap=ROOT/asset['render_path'];d=json.loads(ap.read_bytes());rows=[]
  for i,t in enumerate(d['triangles']):
   arr=np.array(t);bb=[arr[:,0].min(),arr[:,2].min(),arr[:,0].max(),arr[:,2].max()]
   if bb[0]>pt[0]+.6 or bb[2]<pt[0]-.6 or bb[1]>pt[2]+.6 or bb[3]<pt[2]-.6:continue
   if arr[:,1].max()<pt[1]-1.1 or arr[:,1].min()>pt[1]+.9:continue
   n=np.cross(arr[1]-arr[0],arr[2]-arr[0]);a32=arr.astype(np.float32);n32=np.cross(a32[1]-a32[0],a32[2]-a32[0]);L=np.linalg.norm(n);L32=np.linalg.norm(n32)
   rows.append(dict(collider_triangle_index=i,source_face_key=d['source_face_indices'][i],triangle_xyz_m=t,normal64=(n/L).tolist()if L else[],normal32=(n32/L32).tolist()if L32 else[],area3d64_m2=float(L/2),xz_area64_m2=float(abs(n[1])/2),grade64=float(math.hypot(n[0],n[2])/abs(n[1]))if n[1]else None))
  targets={key(r['triangle_xyz_m']):r for r in rows if r['xz_area64_m2']<1e-5};matches=[]
  for pi,patch in enumerate(patches):
   for ei,e in enumerate(patch['surface_edits']):
    for ri,t in enumerate(e['replacement_triangles_xyz_m']):
     if key(t)in targets:matches.append(dict(patch_index=pi,patch=binding['patches'][pi],source_edit_index=ei,original_source_triangle_index=e['triangle_index'],original_material=e['material'],replacement_index=ri,replacement_count=len(e['replacement_triangles_xyz_m']),triangle_xyz_m=t,collision_source=targets[key(t)]))
  out=dict(status='READ_ONLY_CONTACT_CANDIDATES_NOT_YET_CAUSALLY_CONFIRMED',sources=[ref(hp),ref(ap),ref(bp)],route_id=f['result']['id'],feet_xyz_m=[pt[0],pt[1]-.9,pt[2]],rows=rows,source_matches=matches);op=HERE/(road.lower()+'_local_faces.json');dump(op,out);print(road,'faces',len(rows),'needles',len(targets),'source',[(m['patch_index'],m['source_edit_index'],m['original_source_triangle_index'],m['collision_source']['source_face_key'],m['collision_source']['xz_area64_m2'],m['collision_source']['grade64'])for m in matches],flush=True)
if __name__=='__main__':main()
