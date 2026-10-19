import sys,pathlib,json,math,hashlib,traceback
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r09_training_access.recovery_support import author as src,approaches as a,landings as l
bounds=[-530,-530,530,656];seen=set();out=[];failures=[];counts=0
for r in a.supplemental_surface_domains(bounds):
 ps=r['vertices_xyz_m']
 for av,bv in zip(ps,ps[1:]+ps[:1]):
  p=[av[0],av[2]];q=[bv[0],bv[2]];L=math.dist(p,q)
  if L<1e-7:continue
  key=tuple(sorted(tuple(round(v,7) for v in t) for t in (p,q)))
  if key in seen:continue
  seen.add(key);m=[(p[k]+q[k])/2 for k in (0,1)];n=[-(q[1]-p[1])/L*1e-5,(q[0]-p[0])/L*1e-5]
  if not any(l.inside(*(m[k]+s*n[k] for k in (0,1))) for s in (1,-1)):continue
  states=[a.inside(*(m[k]+s*n[k] for k in (0,1))) for s in (1,-1)]
  if states[0]==states[1]:continue
  sign=-1 if states[0] else 1;query=[m[k]+sign*n[k] for k in (0,1)];o=src.owner_at(*query);counts+=1
  try:ys=[src.source_surface_height_at(o,*t) for t in (p,q)]
  except Exception as e:
   f=dict(source=r,edge_xyz_m=[av,bv],outside_query_xz_m=query,outside_owner=o,normal_xz_m=[sign*x for x in n],error=repr(e),endpoint_details=[])
   for t in [p,q]:
    own=src.owner_at(*(t[k]+sign*n[k] for k in (0,1)));tri=[i for i in l.INDEX.candidates([t]) if a.geo.point_in_convex_polygon(t,l.TRIANGLES[i]['polygon_xz_m'],1e-7)];f['endpoint_details'].append(dict(point=t,offset_owner=own,inside_landing_mask=l.inside(*t),triangle_ids=tri))
   failures.append(f);print('FAIL',len(failures),p,q,o['owner_id'],flush=True)
   if len(failures)>=3:break
  else:out.append(dict(edge_xyz_m=[av,bv],outside_owner=o,bottom_ys_m=ys))
 if len(failures)>=3:break
report=dict(status='original_failed',bounds_xz_m=bounds,checked_boundary_edges=counts,failures=failures,preceding_unaffected_edges=out,inputs={str(pathlib.Path(m.__file__).relative_to(ROOT)):hashlib.sha256(pathlib.Path(m.__file__).read_bytes()).hexdigest() for m in [src,a,l]},source_profile_sha256=a.SHA)
(H/'targeted_original_endpoint_failures.json').write_text(json.dumps(report,indent=2)+'\n');print('DONE',counts,len(failures))
