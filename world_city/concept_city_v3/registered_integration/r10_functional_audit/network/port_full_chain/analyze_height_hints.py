"""Compare unchanged cart ray intervals against exact bound contract faces."""
import json,pathlib,hashlib,numpy as np
O=pathlib.Path(__file__).resolve().parent;ROOT=O.parents[5]
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
C=ROOT/'world_city/concept_city_v3/traversal_r5/revisions/r06_r8_precinct/primary_goals_authored_r01/geometry/contract_NORTH_APPROACH_R04_CONTINUOUS_ROAD_GOAL:PORT_TO_MARKET.json'
P=O/'replay_r01/evidence/runtime_r02/cart.json';tri=np.array(read(C)['triangles']);rows=[]
def heights(x,z):
 out=[]
 for i,t in enumerate(tri):
  a,b,c=t;M=np.array([[b[0]-a[0],c[0]-a[0]],[b[2]-a[2],c[2]-a[2]]])
  if abs(np.linalg.det(M))<1e-12:continue
  u,v=np.linalg.solve(M,np.array([x-a[0],z-a[2]]))
  if min(u,v,1-u-v)>=-1e-7:out.append({'triangle_index':i,'y_m':float(a[1]+u*(b[1]-a[1])+v*(c[1]-a[1])),'barycentric':[float(1-u-v),float(u),float(v)]})
 return out
for r in read(P)['routes']:
 if r['pass']:continue
 f=r['first_failure'];p=f['point'];supports=[]
 for i,s in enumerate(f['support']):
  x,y,z=s['position'];hits=heights(x,z);top=max(hits,key=lambda a:a['y_m']);start=p[1]+.75;end=p[1]-1.5
  supports.append({'index':i,'xz_m':[x,z],'recorded_hit_y_m':y,'recorded_hit_source_id':s['source_id'],'unchanged_ray_start_y_m':start,'unchanged_ray_end_y_m':end,'exact_contract_surface':top,'contract_surface_above_ray_start_m':top['y_m']-start,'ray_starts_below_contract':top['y_m']>start,'observed_hit_below_contract_m':top['y_m']-y})
 center=heights(p[0],p[2]);rows.append({'id':r['id'],'first_failure':f['failure'],'original_pose_hint_xyz_m':p,'exact_contract_center_height':max(center,key=lambda a:a['y_m']),'supports':supports})
out={'schema':'riverstone.r10.cart_support_hint_diagnostic.v1','sources':{'cart_report':{'path':str(P.relative_to(ROOT)),'sha256':sha(P)},'unchanged_contract_mesh':{'path':str(C.relative_to(ROOT)),'sha256':sha(C)}},'controller_ray_rule':'Each support ray starts at authored pose point Y +0.75 and ends at Y -1.5; unchanged.','status':'INPUT_HEIGHT_HINT_ERROR_CONFIRMED_AT_FIRST_FAILURES','results':rows,'interpretation':'Forward two rear rays and reverse one ray begin below the already existing continuous contract surface and hit lower native stair geometry. The reported first cart failures do not establish an actual road step. All original failures retained; corrected-height replay required.','limits':['Analytical exact-source triangle interpolation, not a new runtime hit.','Does not prove the rest of the whole route cart-capable.','No geometry, contract, support-ray span, cart clearance or controller change.']};(O/'height_hint_diagnostic.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps([{'id':r['id'],'center_y':r['exact_contract_center_height']['y_m'],'supports_above_start_m':[round(s['contract_surface_above_ray_start_m'],6) for s in r['supports']]}for r in rows],indent=2))
