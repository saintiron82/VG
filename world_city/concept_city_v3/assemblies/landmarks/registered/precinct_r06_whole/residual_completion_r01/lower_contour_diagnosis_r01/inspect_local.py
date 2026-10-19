from pathlib import Path
import json,numpy as np,hashlib
OUT=Path(__file__).resolve().parent;ROOT=next(p for p in OUT.parents if(p/'world_city/concept_city_v3').is_dir());CITY=ROOT/'world_city/concept_city_v3';T=CITY/'traversal_r5/revisions/r06_r8_precinct/public_network_r18_runtime_r01';P=T/'evidence/lower_market_failure_handoff_r01.json'
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
d=json.loads(P.read_text());f=next(r for r in d['failures']if r['result']['id']=='ROAD:LOWER_CONTOUR');a=f['assets']['SCENE:PUBLIC_NETWORK:ROAD:LOWER_CONTOUR'];g=json.loads((ROOT/a['render_path']).read_text());ts=np.array(g['triangles']);q=ts.astype(np.float32);n=np.cross(ts[:,1]-ts[:,0],ts[:,2]-ts[:,0]);nf=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);point=np.array(f['result']['end_position']);xmin,xmax=point[0]-1.5,point[0]+1.5;zmin,zmax=point[2]-1.5,point[2]+1.5;mask=(ts[:,:,0].max(1)>=xmin)&(ts[:,:,0].min(1)<=xmax)&(ts[:,:,2].max(1)>=zmin)&(ts[:,:,2].min(1)<=zmax);rows=[]
for i in np.where(mask)[0]:
 t=ts[i];nn=n[i];ff=nf[i].astype(float);l=float(np.linalg.norm(nn));lf=float(np.linalg.norm(ff));rows.append(dict(collision_triangle_index=int(i),source_face=g['source_face_indices'][i],vertices_xyz_m=t.tolist(),float32_vertices_xyz_m=q[i].tolist(),normal64=(nn/l).tolist()if l else[0,0,0],normal32=(ff/lf).tolist()if lf else[0,0,0],area64_m2=l/2,area32_m2=lf/2,centroid=t.mean(0).tolist(),plane_y_xz_m=[-nn[0]/nn[1],-nn[2]/nn[1],float(nn@t[0])/nn[1]]if abs(nn[1])>1e-16 else None))
report=dict(source_handoff=ref(P),collision_asset=ref(ROOT/a['render_path']),forward_stop=f['result']['end_position'],reverse_stop=next(r['result']['end_position']for r in d['failures']if 'LOWER_CONTOUR' in r['result']['id'] and r['result']['id']!='ROAD:LOWER_CONTOUR'),window_xz_m=[xmin,zmin,xmax,zmax],actual_local_scene_faces=rows)
(OUT/'local_faces.json').write_text(json.dumps(report,indent=2)+'\n')
print('local',len(rows));
for r in sorted(rows,key=lambda r:r['area32_m2'])[:20]:print(r['collision_triangle_index'],r['source_face'],'area64/32',r['area64_m2'],r['area32_m2'],'n64',r['normal64'],'n32',r['normal32'],'verts',r['vertices_xyz_m'])
