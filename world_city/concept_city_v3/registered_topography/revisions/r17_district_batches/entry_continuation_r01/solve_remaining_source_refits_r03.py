"""Bounded follow-on source candidates; sealed earlier batches are read-only."""
import json,math,time
from pathlib import Path
from .. import author as a
from ..contour_bulk_r01 import profile_mesh
HERE=Path(__file__).resolve().parent
SOURCE=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/hard_core_native_refit_r01/entry_candidates/source_candidate_batch.json'
EXPECTED='b00e8feabe84e044e01c87169983023a10357611e56c61c97654adfab0d8809a'
OUT=HERE/'source_refit_profiles_r03'
def write(p,d):
 assert not p.exists();p.write_text(json.dumps(d,separators=(',',':'))+'\n')
def run():
 assert a.sha(SOURCE)==EXPECTED
 source=json.loads(SOURCE.read_bytes());layout=json.loads((a.CITY/'assemblies/ordinary/registered/district_fabric_r01/hard_core_native_refit_r01/selected_layout_candidate.json').read_bytes());holdings=layout['holdings'];idx=a.geo._SpatialIndex(16)
 for i,h in enumerate(holdings):idx.add(i,h['holding_polygon_xz_m'])
 OUT.mkdir(exist_ok=True);rows=[]
 for record in source['holdings']:
  trials=[]
  for candidate in sorted(record['candidates'],key=lambda c:(c['candidate_index']!=2,c['candidate_index'])):
   path=OUT/(record['holding_id'].replace(':','_')+'_'+str(candidate['candidate_index'])+'.json')
   if path.exists():result=json.loads(path.read_bytes())
   else:
    start=time.monotonic();public=candidate['fixed_public_regions'];full=a.common.disjoint_union(candidate['polygons_xz_m']+candidate['internal_court_link_polygons_xz_m']);domains=a.common.subtract(full,[r['polygon_xz_m']for r in public]);court=[]
    for i in sorted({i for p in full for i in idx.candidates(p)}):
     h=holdings[i]
     if not any(a.clip(p,h['holding_polygon_xz_m'])for p in full):continue
     y=candidate['floor_y_m']if h['id']==record['holding_id']else h['floor_y_m'];court.append(dict(id=h['id']+':COURT_DATUM',polygon_xz_m=h['holding_polygon_xz_m'],plane_y_xz_m=[0,0,y]))
    res=profile_mesh.solve(domains,court+public,lambda p:candidate['floor_y_m'],pitch=1.,seam_points=[p for r in public for p in r['polygon_xz_m']])
    result=dict(holding_id=record['holding_id'],candidate_index=candidate['candidate_index'],candidate=candidate,private_domain_polygons_xz_m=domains,public_fixed_regions=public,court_fixed_regions=court,result=res,elapsed_s=time.monotonic()-start,source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=EXPECTED),activation=False);write(path,result)
   row=dict(candidate_index=candidate['candidate_index'],status=result['result']['status'],maximum_gradient=result['result'].get('maximum_gradient'),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path),elapsed_s=result['elapsed_s']);trials.append(row);print(record['holding_id'],row,flush=True)
   if row['status']=='PASSED_FINITE_TRIANGLE_GRADE':break
  rows.append(dict(holding_id=record['holding_id'],trials=trials))
 write(HERE/'source_refit_profile_summary_r03.json',dict(source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=EXPECTED),rows=rows,activation=False))
if __name__=='__main__':run()
