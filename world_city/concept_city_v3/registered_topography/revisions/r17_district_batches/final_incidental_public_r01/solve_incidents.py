"""Keep literal retained-public millimetre incidents as separate fixed sectors."""
import json,types,time
from .solve import HERE,write,ref
from .. import author as a,regeneration
from ..incident_risers_r01 import solve as sectors
from ..incident_risers_r02.solve import interval
from ..bounded_profile_r01.finite import inside

def run():
 geo=types.SimpleNamespace(**vars(a.geo));geo.point_in_convex_polygon=inside;proxy=types.SimpleNamespace(**vars(a));proxy.geo=geo
 for hid in ['BLOCK_003:R8_C001','BLOCK_006:R8_C001']:
  old=json.loads((HERE/(hid.replace(':','_')+'_12.json')).read_bytes());source=dict(old,private_domain_polygons_xz_m=a.common.disjoint_union(old['private_domain_polygons_xz_m']));floor=old['candidate']['floor_y_m'];group=dict(holding_ids=[hid],gate_fixed_regions=old['court_fixed_regions'],gate_targets=[dict(point_xz_m=old['candidate'].get('gate_point_xz_m',old['candidate'].get('gate_xz_m',[0,0])),floor_y_m=floor)])
  for limit in [.12,.15,.25]:
   def field(pts,tris,fixed,target,limit=.12,_limit=limit):return regeneration.solve_field(pts,tris,fixed,target,limit=_limit)
   solve=types.FunctionType(sectors.solve_one.__code__,dict(sectors.solve_one.__globals__,a=proxy,interval=interval,regeneration=types.SimpleNamespace(solve_field=field)));start=time.monotonic();result=solve(group,source);write(hid.replace(':','_')+'_incidents_'+str(int(limit*100))+'.json',dict(source,result=result,grade_limit=limit,elapsed_s=time.monotonic()-start,prior_profile=ref(HERE/(hid.replace(':','_')+'_12.json'))));print(hid,limit,result['status'],result.get('maximum_step_m'),result.get('result',{}).get('maximum_gradient'),flush=True)
   if result['status']=='PASSED_FINITE_PROFILE_WITH_DECLARED_INCIDENT_RISERS' or not result['status'].startswith('NO_FEASIBLE'):break
if __name__=='__main__':run()
