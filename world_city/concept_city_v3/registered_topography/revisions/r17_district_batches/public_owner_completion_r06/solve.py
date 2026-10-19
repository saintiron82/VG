"""Compact public domains with only actual incident public planes in the solve."""
import json,math,time
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write,index
from ..public_owner_completion_r05.solve import solve
HERE=Path(__file__).resolve().parent
SOURCE=HERE/'actual_public_inputs.json';REQUEST=a.HERE/'contour_bulk_r01/exact_public_reservations.json'
def touch(p,q,eps=1e-8):
 for poly,other in [(p,q),(q,p)]:
  sign=1 if a.geo.signed_polygon_area(poly)>0 else -1
  for u,v in zip(poly,poly[1:]+poly[:1]):
   length=math.dist(u,v)
   if length<1e-12:continue
   if max(sign*a.geo._cross(u,v,x)/length for x in other)<-eps:return False
 return True
def run():
 entries={r['holding_id']:r for r in json.loads(SOURCE.read_bytes())['entries']};requests={r['holding_id']:r for r in json.loads(REQUEST.read_bytes())['entries']};groups=json.loads((a.HERE/'contour_bulk_r01/shared_private_groups_r03.json').read_bytes())['groups'];rows=[]
 for g in groups:
  if not set(g['holding_ids'])&set(entries):continue
  start=time.monotonic();public=[r for h in g['holding_ids']for r in entries[h]['profile_regions']];masks=[p for h in g['holding_ids']for p in requests[h]['public_union_parts_xz_m']];full=a.common.disjoint_union([p for h in g['source_holding_records']for p in h['external_route_polygons_xz_m']]);domains=a.common.subtract(full,masks);di=a.geo._SpatialIndex(4)
  for j,p in enumerate(domains):di.add(j,p)
  incident=[r for r in public if a.geo.polygon_area(r['polygon_xz_m'])>1e-12 and any(touch(r['polygon_xz_m'],domains[j])for j in di.candidates(r['polygon_xz_m']))];print('Solving',g['holding_ids'],'domains',len(domains),'incident',len(incident),'full public',len(public),flush=True);target=lambda p:min(g['gate_targets'],key=lambda r:math.dist(p,r['point_xz_m']))['floor_y_m']
  try:res=solve(domains,g['gate_fixed_regions']+incident,target,pitch=1.,seam_points=[p for r in incident for p in r['polygon_xz_m']])
  except Exception as e:res=dict(status='SOLVER_EXCEPTION_HOLD',type=type(e).__name__,message=str(e))
  path=HERE/(g['holding_ids'][0].replace(':','_')+'_profile.json');d=dict(id=g['id'],holding_ids=g['holding_ids'],source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=a.sha(SOURCE)),public_domain_source=dict(path=str(REQUEST.relative_to(a.ROOT)),sha256=a.sha(REQUEST)),private_domain_polygons_xz_m=domains,public_fixed_regions=public,incident_public_fixed_regions=incident,court_fixed_regions=g['gate_fixed_regions'],result=res,elapsed_s=time.monotonic()-start,activation=False);write(path,d);row=dict(holding_ids=g['holding_ids'],status=res['status'],maximum_gradient=res.get('maximum_gradient'),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path));rows.append(row);print(row,flush=True)
 write(HERE/'summary.json',dict(rows=rows,activation=False))
if __name__=='__main__':run()
