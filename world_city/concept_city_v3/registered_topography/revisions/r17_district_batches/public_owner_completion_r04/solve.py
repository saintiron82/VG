"""Exact signed cell partitions for source-bound public/private interfaces."""
import json,math,time,types
from pathlib import Path
from .. import author as a
from ..bounded_profile_r01 import finite
from ..contour_bulk_r01 import profile_mesh
from ..final_profile_audit_r01.exact_clip import clip,difference
from ..incident_risers_r01.solve import write
HERE=Path(__file__).resolve().parent
SOURCE=a.HERE/'public_owner_completion_r03/actual_public_inputs.json'
def subtract(ps,masks):
 for m in masks:ps=[v for p in ps for v in difference(p,m)]
 return ps
def grid(domains,fixed,pitch=1.):
 di=a.geo._SpatialIndex(4*pitch);fi=a.geo._SpatialIndex(4*pitch);cells=set()
 for i,p in enumerate(domains):
  di.add(i,p);x0,z0,x1,z1=a.bounds(p);cells.update((x,z)for x in range(math.floor(x0/pitch),math.ceil(x1/pitch))for z in range(math.floor(z0/pitch),math.ceil(z1/pitch)))
 for i,r in enumerate(fixed):fi.add(i,r['polygon_xz_m'])
 pieces=[];checks=[]
 for x,z in sorted(cells):
  cell=[[x*pitch,z*pitch],[(x+1)*pitch,z*pitch],[(x+1)*pitch,(z+1)*pitch],[x*pitch,(z+1)*pitch]];parts=[]
  for i in sorted(di.candidates(cell)):
   p=clip(cell,domains[i])
   if a.geo.polygon_area(p)>1e-12:parts.extend(subtract([p],parts))
  before=sum(a.geo.polygon_area(p)for p in parts);remaining=parts;assigned=[]
  for i in sorted(fi.candidates(cell)):
   mask=fixed[i]['polygon_xz_m'];new=[]
   for p in remaining:
    q=clip(p,mask)
    if a.geo.polygon_area(q)>1e-12:assigned.append(q)
    new.extend(difference(p,mask))
   remaining=new
  final=[p for p in assigned+remaining if a.geo.polygon_area(p)>1e-12];after=sum(a.geo.polygon_area(p)for p in final)
  if abs(before-after)>1e-7:raise ValueError('Exact finite cell partition mismatch '+str((x,z,before,after)))
  pieces+=final;checks.append(dict(cell=[x,z],area_m2=before,residual_area_m2=before-after))
 return pieces,checks
proxy=types.SimpleNamespace(**vars(profile_mesh));proxy.grid_parts=grid
solve=types.FunctionType(finite.solve.__code__,dict(finite.solve.__globals__,profile_mesh=proxy),argdefs=finite.solve.__defaults__)
def run():
 data=json.loads(SOURCE.read_bytes());entries={e['holding_id']:e for e in data['entries']};groups=json.loads((a.HERE/'contour_bulk_r01/shared_private_groups_r03.json').read_bytes())['groups'];rows=[]
 for g in groups:
  if not set(g['holding_ids'])&set(entries)or 'BLOCK_017:R8_I004'in g['holding_ids']:continue
  path=HERE/(g['holding_ids'][0].replace(':','_')+'_profile.json');start=time.monotonic();public=[r for h in g['holding_ids']for r in entries[h]['profile_regions']];full=a.common.disjoint_union([p for h in g['source_holding_records']for p in h['external_route_polygons_xz_m']]);domains=a.common.subtract(full,[r['polygon_xz_m']for r in public]);target=lambda p:min(g['gate_targets'],key=lambda r:math.dist(p,r['point_xz_m']))['floor_y_m']
  try:res=solve(domains,g['gate_fixed_regions']+public,target,pitch=1.,seam_points=[p for r in public for p in r['polygon_xz_m']])
  except Exception as e:res=dict(status='SOLVER_EXCEPTION_HOLD',type=type(e).__name__,message=str(e))
  d=dict(id=g['id'],holding_ids=g['holding_ids'],source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=a.sha(SOURCE)),private_domain_polygons_xz_m=domains,public_fixed_regions=public,court_fixed_regions=g['gate_fixed_regions'],result=res,elapsed_s=time.monotonic()-start,activation=False);write(path,d);row=dict(holding_ids=g['holding_ids'],status=res['status'],maximum_gradient=res.get('maximum_gradient'),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path));rows.append(row);print(row,flush=True)
 write(HERE/'summary.json',dict(rows=rows,activation=False))
if __name__=='__main__':run()
