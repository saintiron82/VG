"""Retain the measured institutional incident steps as explicit private risers."""
import json,time,types
from pathlib import Path
from .. import author as a,regeneration
from ..incident_risers_r01 import solve as old
from ..incident_risers_r02.solve import interval
from ..bounded_profile_r01.finite import inside
from ..public_owner_completion_r05.solve import proxy as mesh
HERE=Path(__file__).resolve().parent
SOURCE=a.HERE/'public_owner_completion_r06/BLOCK_008_R8_C003_profile.json'
def run():
 source=json.loads(SOURCE.read_bytes());g=next(g for g in json.loads((a.HERE/'contour_bulk_r01/shared_private_groups_r03.json').read_bytes())['groups']if g['holding_ids']==['BLOCK_008:R8_C003']);geom=types.SimpleNamespace(**vars(a.geo));geom.point_in_convex_polygon=inside;aa=types.SimpleNamespace(**vars(a));aa.geo=geom;rows=[]
 for limit in [.12,.15,.20]:
  sf=lambda points,tris,fixed,targets,limit=limit:regeneration.solve_field(points,tris,fixed,targets,limit=limit)
  fn=types.FunctionType(old.solve_one.__code__,dict(old.solve_one.__globals__,a=aa,profile_mesh=mesh,interval=interval,regeneration=types.SimpleNamespace(solve_field=sf)));start=time.monotonic()
  try:result=fn(g,dict(source,public_fixed_regions=source['incident_public_fixed_regions']))
  except Exception as e:result=dict(status='SOLVER_EXCEPTION_HOLD',type=type(e).__name__,message=str(e))
  path=HERE/('BLOCK_008_R8_C003_'+str(int(limit*100))+'.json');out=dict(source,result=result,source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=a.sha(SOURCE)),grade_limit=limit,elapsed_s=time.monotonic()-start,design_policy='Measured retained public incident heights stay separate; explicit vertical private sheets close their interfaces. Pedestrian runtime acceptance remains pending.');old.write(path,out);row=dict(limit=limit,status=result['status'],maximum_gradient=result.get('result',{}).get('maximum_gradient'),maximum_step_m=result.get('maximum_step_m'),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path));rows.append(row);print(row,flush=True)
  if result['status'].startswith('PASSED')or result['status']not in ['INFEASIBLE_GRADE_CONSTRAINTS','FINITE_GRADE_INFEASIBLE']:break
 old.write(HERE/'summary.json',dict(rows=rows,activation=False))
if __name__=='__main__':run()
