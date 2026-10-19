import json,math,time
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write
from ..public_owner_completion_r05.solve import solve
from ..public_owner_completion_r06.solve import touch
HERE=Path(__file__).resolve().parent
SOURCE=a.HERE/'public_owner_completion_r06/actual_public_inputs.json';REQUEST=a.HERE/'contour_bulk_r01/exact_public_reservations.json'
def run():
 entries={e['holding_id']:e for e in json.loads(SOURCE.read_bytes())['entries']};req={e['holding_id']:e for e in json.loads(REQUEST.read_bytes())['entries']};g=next(g for g in json.loads((a.HERE/'contour_bulk_r01/shared_private_groups_r03.json').read_bytes())['groups']if 'BLOCK_005:R8_C003'in g['holding_ids']);rows=[]
 for hid in ['BLOCK_005:R8_C003','BLOCK_005:R8_C008']:
  h=next(h for h in g['source_holding_records']if h['id']==hid);public=entries[hid]['profile_regions'];court=[r for r in g['gate_fixed_regions']if r['id'].startswith(hid+':')];domains=a.common.subtract(a.common.disjoint_union(h['external_route_polygons_xz_m']),req[hid]['public_union_parts_xz_m']);incident=[r for r in public if a.geo.polygon_area(r['polygon_xz_m'])>1e-12 and any(a.intersects(a.bounds(r['polygon_xz_m']),a.bounds(p))and touch(r['polygon_xz_m'],p)for p in domains)];start=time.monotonic();result=solve(domains,court+incident,lambda p:h['floor_y_m'],pitch=1.,seam_points=[p for r in incident for p in r['polygon_xz_m']]);path=HERE/(hid.replace(':','_')+'.json');write(path,dict(id='FINAL_PRIVATE:'+hid,holding_ids=[hid],source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=a.sha(SOURCE)),source_holding=h,private_domain_polygons_xz_m=domains,public_fixed_regions=public,court_fixed_regions=court,result=result,elapsed_s=time.monotonic()-start,activation=False,retired_route_policy='C006 long loop is superseded by its separate source route; these unchanged neighboring routes retain their exact public bindings.'));row=dict(holding_id=hid,status=result['status'],maximum_gradient=result.get('maximum_gradient'),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path));rows.append(row);print(row,flush=True)
 write(HERE/'summary.json',dict(rows=rows,activation=False))
if __name__=='__main__':run()
