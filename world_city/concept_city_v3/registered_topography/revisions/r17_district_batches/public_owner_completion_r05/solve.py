"""Preserve the existing 1 nm weld while measuring collapsed arithmetic parts."""
import inspect,types,json,time,math
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write
from ..bounded_profile_r01 import finite
from ..contour_bulk_r01 import profile_mesh
from ..public_owner_completion_r04.solve import grid
HERE=Path(__file__).resolve().parent
SOURCE=a.HERE/'public_owner_completion_r03/actual_public_inputs.json'
text=inspect.getsource(profile_mesh.topology).replace('triangles=[];part_areas=[]','triangles=[];part_areas=[];collapsed=[]').replace("  if len(conformed)<3:raise ValueError('Lost finite source polygon')", "  if len(conformed)<3:\n   ar=a.geo.polygon_area(source)\n   if ar>1e-8:raise ValueError('Lost material finite source polygon '+str(ar))\n   collapsed.append(dict(polygon_xz_m=source,area_m2=ar,reason='Existing 1 nm topology weld collapses all independent vertices'))\n   continue").replace('source_parts=len(pieces),part_area_checks=part_areas','source_parts=len(pieces),part_area_checks=part_areas,collapsed_arithmetic_parts=collapsed,collapsed_area_m2=sum(r[\'area_m2\']for r in collapsed)')
ns=dict(profile_mesh.topology.__globals__);exec(text,ns);proxy=types.SimpleNamespace(**vars(profile_mesh));proxy.grid_parts=grid;proxy.topology=ns['topology'];solve=types.FunctionType(finite.solve.__code__,dict(finite.solve.__globals__,profile_mesh=proxy),argdefs=finite.solve.__defaults__)
def run():
 entries={r['holding_id']:r for r in json.loads(SOURCE.read_bytes())['entries']};groups=json.loads((a.HERE/'contour_bulk_r01/shared_private_groups_r03.json').read_bytes())['groups'];rows=[]
 for g in groups:
  if not set(g['holding_ids'])&set(entries)or 'BLOCK_017:R8_I004'in g['holding_ids']:continue
  p=a.HERE/'public_owner_completion_r04'/(g['holding_ids'][0].replace(':','_')+'_profile.json')
  if p.exists():d=json.loads(p.read_bytes());domains=d['private_domain_polygons_xz_m'];public=d['public_fixed_regions']
  else:
   public=[r for h in g['holding_ids']for r in entries[h]['profile_regions']];domains=a.common.subtract(a.common.disjoint_union([p for h in g['source_holding_records']for p in h['external_route_polygons_xz_m']]),[r['polygon_xz_m']for r in public])
  target=lambda p:min(g['gate_targets'],key=lambda r:math.dist(p,r['point_xz_m']))['floor_y_m'];start=time.monotonic()
  try:res=solve(domains,g['gate_fixed_regions']+public,target,pitch=1.,seam_points=[p for r in public for p in r['polygon_xz_m']])
  except Exception as e:res=dict(status='SOLVER_EXCEPTION_HOLD',type=type(e).__name__,message=str(e))
  path=HERE/(g['holding_ids'][0].replace(':','_')+'_profile.json');out=dict(id=g['id'],holding_ids=g['holding_ids'],source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=a.sha(SOURCE)),private_domain_polygons_xz_m=domains,public_fixed_regions=public,court_fixed_regions=g['gate_fixed_regions'],result=res,elapsed_s=time.monotonic()-start,activation=False);write(path,out);row=dict(holding_ids=g['holding_ids'],status=res['status'],maximum_gradient=res.get('maximum_gradient'),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path));rows.append(row);print(row,flush=True)
 write(HERE/'summary.json',dict(rows=rows,activation=False))
if __name__=='__main__':run()
