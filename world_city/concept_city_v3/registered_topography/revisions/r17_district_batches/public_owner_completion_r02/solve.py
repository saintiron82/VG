import json,time,math
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write
from ..bounded_profile_r01 import finite
HERE=Path(__file__).resolve().parent
SOURCE=HERE/'actual_public_inputs.json'
def run():
 inputs=json.loads(SOURCE.read_bytes());entries={e['holding_id']:e for e in inputs['entries']};groups=json.loads((a.HERE/'contour_bulk_r01/shared_private_groups_r03.json').read_bytes())['groups'];rows=[]
 for g in groups:
  if not set(g['holding_ids'])&set(entries):continue
  hid=g['holding_ids'][0];path=HERE/(hid.replace(':','_')+'_profile.json')
  if path.exists():out=json.loads(path.read_bytes())
  else:
   start=time.monotonic();public=[r for h in g['holding_ids'] for r in entries[h]['profile_regions']];full=a.common.disjoint_union([p for h in g['source_holding_records']for p in h['external_route_polygons_xz_m']]);domains=a.common.subtract(full,[r['polygon_xz_m']for r in public]);target=lambda p:min(g['gate_targets'],key=lambda r:math.dist(p,r['point_xz_m']))['floor_y_m']
   if any(entries[h]['uncovered_area_m2']>1e-7 for h in g['holding_ids']):res=dict(status='HELD_FINITE_PUBLIC_OWNER_GAP')
   else:
    try:res=finite.solve(domains,g['gate_fixed_regions']+public,target,pitch=1.,seam_points=[p for r in public for p in r['polygon_xz_m']])
    except Exception as e:res=dict(status='SOLVER_EXCEPTION_HOLD',type=type(e).__name__,message=str(e))
   out=dict(id=g['id'],holding_ids=g['holding_ids'],source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=a.sha(SOURCE)),private_domain_polygons_xz_m=domains,public_fixed_regions=public,court_fixed_regions=g['gate_fixed_regions'],result=res,elapsed_s=time.monotonic()-start,activation=False);write(path,out)
  row=dict(holding_ids=g['holding_ids'],status=out['result']['status'],maximum_gradient=out['result'].get('maximum_gradient'),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path));rows.append(row);print(row,flush=True)
 write(HERE/'profile_summary.json',dict(rows=rows,activation=False))
if __name__=='__main__':run()
