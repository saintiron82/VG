from build_ground_patch import *
OUT=Path(__file__).resolve().parent
p=load(OUT/'resolved_native_candidate.json');d=load(OUT/'native_ground_candidate_audit.json');rows=[]
for e in d['side_closure']['unknown_exterior_segments']:
 eid=e['owner_id'].split(':')[1]
 owner=next(r for r in d['new_native_undersides']if r['id']==e['owner_id']);edge=e['edge_xz_m'];matches=[]
 for pl in p['placements']:
  if pl['owner_id']!=eid or pl['role']!='retained_base':continue
  for gi,g in enumerate(load(ROOT/pl['cache']['path'])['groups']):
   for qi,q in enumerate(g['quads']):
    if abs(terrain.normal_y(q[:3]))>1e-9:continue
    vs=[[v[k]+pl['position_m'][k]for k in range(3)]for v in q];xz=[]
    for v in vs:
     if [v[0],v[2]]not in xz:xz.append([v[0],v[2]])
    if len(xz)!=2:continue
    a,c=np.array(xz[0]),np.array(xz[1]);vec=c-a;L=float(vec@vec)
    if L<1e-12:continue
    ts=[float((np.array(v)-a)@vec/L)for v in edge];dist=[float(np.linalg.norm(np.array(v)-(a+tt*vec)))for v,tt in zip(edge,ts)]
    if max(dist)<1e-7 and min(ts)>-1e-7 and max(ts)<1+1e-7:matches.append(dict(native_id=pl['id'],group_index=gi,quad_index=qi,world_quad_xyz_m=vs,minimum_y_m=min(v[1]for v in vs),maximum_y_m=max(v[1]for v in vs)))
 rows.append(dict(**e,native_bottom_y_m=owner['plane_y_xz_m'][2],actual_retained_native_side_faces=matches))
(OUT/'native_edge_diagnosis.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
