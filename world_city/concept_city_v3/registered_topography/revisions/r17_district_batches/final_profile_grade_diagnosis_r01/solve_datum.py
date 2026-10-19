import json,types,time
from pathlib import Path
from .. import author as a
from ..bounded_profile_r01.finite import inside
from ..entry_continuation_r01 import solve_coherent_datums as old
from ..incident_risers_r01.solve import write
HERE=Path(__file__).resolve().parent
source=a.HERE/'final_district_profiles_r02/BLOCK_001_R8_C003.json';d=json.loads(source.read_bytes());c=d['candidate'];hid=c['holding_id'];floor=c['floor_y_m'];lo,hi=c['required_core_floor_interval_m'];group=dict(holding_ids=[hid],gate_fixed_regions=[dict(r,id=hid+':COURT_DATUM:'+str(i))for i,r in enumerate(d['court_fixed_regions'])],gate_targets=[dict(point_xz_m=c['gate_xz_m'],floor_y_m=floor)],source_holding_records=[dict(id=hid,floor_y_m=floor)]);budgets={hid:dict(floor_y_m=floor,maximum_required_core_cut_m=lo-floor+2.5,maximum_required_core_fill_m=floor+2.5-hi)};geo=types.SimpleNamespace(**vars(a.geo));geo.point_in_convex_polygon=inside;proxy=types.SimpleNamespace(**vars(a));proxy.geo=geo;solver=types.FunctionType(old.solve.__code__,dict(old.solve.__globals__,a=proxy),argdefs=old.solve.__defaults__)
rows=[]
for limit in [.12,.15,.20,.25]:
 result=solver(group,d,budgets,limit);out=dict(holding_id=hid,source=dict(path=str(source.relative_to(a.ROOT)),sha256=a.sha(source)),private_domain_polygons_xz_m=d['private_domain_polygons_xz_m'],public_fixed_regions=d['public_fixed_regions'],flat_owner_polygons_xz_m=c['flat_owner_polygons_xz_m'],grade_limit=limit,result=result,activation=False);path=HERE/('BLOCK_001_R8_C003_datum_'+str(int(limit*100))+'.json');write(path,out);rows.append(dict(limit=limit,status=result['status'],datum_changes=result.get('datum_changes'),maximum_gradient=result.get('maximum_gradient'),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path)));print(rows[-1],flush=True)
 if result['status']=='FINITE_PROFILE_WITH_COHERENT_DATUM_CANDIDATE':break
write(HERE/'datum_summary.json',dict(rows=rows))
