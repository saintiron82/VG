import json,time,types
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write
from ..bounded_profile_r01.finite import inside
from ..entry_continuation_r01 import solve_coherent_datums as old
from ..public_owner_completion_r05.solve import proxy as mesh
from ..public_owner_completion_r06.solve import touch
HERE=Path(__file__).resolve().parent
P=a.HERE/'public_owner_completion_r08/BLOCK_005_R8_C003.json';d=json.loads(P.read_bytes());hid='BLOCK_005:R8_C003';h=d['source_holding'];court=[dict(r,id=hid+':COURT_DATUM')for r in d['court_fixed_regions']];group=dict(holding_ids=[hid],source_holding_records=[h],gate_fixed_regions=court,gate_targets=[dict(point_xz_m=h['gate_position_xz_m'],floor_y_m=h['floor_y_m'])]);budgets={r['id']:r for r in json.loads((a.HERE/'contour_bulk_r01/required_core_budget.json').read_bytes())['rows']};geom=types.SimpleNamespace(**vars(a.geo));geom.point_in_convex_polygon=inside;aa=types.SimpleNamespace(**vars(a));aa.geo=geom;solve=types.FunctionType(old.solve.__code__,dict(old.solve.__globals__,a=aa,profile_mesh=mesh),argdefs=old.solve.__defaults__);incident=[r for r in d['public_fixed_regions']if a.geo.polygon_area(r['polygon_xz_m'])>1e-12 and any(a.intersects(a.bounds(r['polygon_xz_m']),a.bounds(p))and touch(r['polygon_xz_m'],p)for p in d['private_domain_polygons_xz_m'])];rows=[]
for limit in [.12,.15,.25]:
 start=time.monotonic();result=solve(group,dict(d,public_fixed_regions=incident),budgets,limit);path=HERE/('BLOCK_005_R8_C003_'+str(int(limit*100))+'.json');write(path,dict(d,result=result,source=dict(path=str(P.relative_to(a.ROOT)),sha256=a.sha(P)),grade_limit=limit,elapsed_s=time.monotonic()-start,design_policy='Coherent bounded court datum; actual native transforms must rebind atomically. Exact public planes remain unchanged.'));row=dict(holding_id=hid,status=result['status'],grade_limit=limit,maximum_gradient=result.get('maximum_gradient'),datum_changes=result.get('datum_changes'),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path));rows.append(row);print(row,flush=True)
 if result['status']=='FINITE_PROFILE_WITH_COHERENT_DATUM_CANDIDATE':break
write(HERE/'summary.json',dict(rows=rows,activation=False))
