"""Exact visible-core budget and three bounded B07 datum proposals."""
import json,time,types,math
from pathlib import Path
from .. import author as a
from ..bounded_profile_r01.finite import inside
from ..entry_continuation_r01 import solve_coherent_datums as coherent
from .solve import HERE,LAYOUT,write

def run():
 budgets=json.loads((HERE/'required_core_budget.json').read_bytes())['rows'];lookup={r['id']:r for r in budgets};rows=[]
 geo=types.SimpleNamespace(**vars(a.geo));geo.point_in_convex_polygon=inside;proxy=types.SimpleNamespace(**vars(a));proxy.geo=geo;solver=types.FunctionType(coherent.solve.__code__,dict(coherent.solve.__globals__,a=proxy))
 for hid in ['BLOCK_007:R8_C001','BLOCK_007:R8_C003','BLOCK_007:R8_C005']:
  p=HERE/(hid.replace(':','_')+'.json');source=json.loads(p.read_bytes());h=source['source_holding'];court=[dict(r,id=r['id'].split(':COURT:')[0]+':COURT_DATUM')for r in source['court_fixed_regions']];group=dict(holding_ids=[hid],source_holding_records=[h],gate_fixed_regions=court,gate_targets=[dict(point_xz_m=h['gate_position_xz_m'],floor_y_m=h['floor_y_m'])]);start=time.monotonic();result=solver(group,source,lookup,.12);out=HERE/(hid.replace(':','_')+'_datum.json');write(out,dict(id='PRIVATE_GROUP:'+hid,holding_ids=[hid],private_domain_polygons_xz_m=source['private_domain_polygons_xz_m'],public_fixed_regions=source['public_fixed_regions'],result=result,source=dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p)),elapsed_s=time.monotonic()-start,activation=False));brief=dict(holding_id=hid,status=result['status'],datum_changes=result.get('datum_changes'),maximum_gradient=result.get('maximum_gradient'),path=str(out.relative_to(a.ROOT)),sha256=a.sha(out));rows.append(brief);print(brief,flush=True)
 write(HERE/'datum_summary.json',dict(rows=rows,activation=False))
if __name__=='__main__':run()
