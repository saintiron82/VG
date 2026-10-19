import json,time
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write
from ..public_owner_completion_r05.solve import solve
from ..public_owner_completion_r06.solve import touch
HERE=Path(__file__).resolve().parent
rows=[]
for hid in ['BLOCK_005:R8_C003','BLOCK_005:R8_C008']:
 src=a.HERE/'public_owner_completion_r08'/(hid.replace(':','_')+'.json');d=json.loads(src.read_bytes());domains=d['private_domain_polygons_xz_m'];incident=[r for r in d['public_fixed_regions']if a.geo.polygon_area(r['polygon_xz_m'])>1e-12 and any(a.intersects(a.bounds(r['polygon_xz_m']),a.bounds(p))and touch(r['polygon_xz_m'],p)for p in domains)];floor=d['source_holding']['floor_y_m']
 for limit in [.15,.25]:
  start=time.monotonic();result=solve(domains,d['court_fixed_regions']+incident,lambda p:floor,pitch=1.,limit=limit,seam_points=[p for r in incident for p in r['polygon_xz_m']]);path=HERE/(hid.replace(':','_')+'_'+str(int(limit*100))+'.json');write(path,dict(d,result=result,source=dict(path=str(src.relative_to(a.ROOT)),sha256=a.sha(src)),grade_limit=limit,elapsed_s=time.monotonic()-start,design_policy='Explicit bounded pedestrian profile candidate; public knots and court remain exact. Runtime and cart suitability are separate.'));row=dict(holding_id=hid,grade_limit=limit,status=result['status'],maximum_gradient=result.get('maximum_gradient'),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path));rows.append(row);print(row,flush=True)
  if result['status']=='PASSED_FINITE_TRIANGLE_GRADE':break
write(HERE/'summary.json',dict(rows=rows,activation=False))
