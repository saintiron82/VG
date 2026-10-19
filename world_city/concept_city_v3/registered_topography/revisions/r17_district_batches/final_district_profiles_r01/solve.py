import json,time
from pathlib import Path
from .. import author as a
from ..bounded_profile_r01 import finite
from ..incident_risers_r01.solve import write
HERE=Path(__file__).resolve().parent
SOURCE=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/hard_core_native_refit_r02/source_candidates.json'
def run():
 data=json.loads(SOURCE.read_bytes());rows=[]
 for c in data['records']:
  path=HERE/(c['holding_id'].replace(':','_')+'.json')
  if path.exists():d=json.loads(path.read_bytes())
  else:
   start=time.monotonic();public=c['fixed_public_regions'];flat=[dict(id=c['holding_id']+':FLAT_CORE:'+str(i),polygon_xz_m=p,plane_y_xz_m=[0,0,c['floor_y_m']])for i,p in enumerate(c['flat_owner_polygons_xz_m'])];domains=a.common.subtract(c['profile_domain_polygons_xz_m'],[r['polygon_xz_m']for r in public]);result=finite.solve(domains,flat+public,lambda p:c['floor_y_m'],pitch=1.,seam_points=[p for r in public+flat for p in r['polygon_xz_m']]+[p for s in c['shared_inner_seams_xz_m']for p in s['endpoints_xz_m']]);d=dict(holding_id=c['holding_id'],candidate_index=c['candidate_index'],source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=a.sha(SOURCE)),candidate=c,private_domain_polygons_xz_m=domains,public_fixed_regions=public,court_fixed_regions=flat,result=result,elapsed_s=time.monotonic()-start,activation=False);write(path,d)
  row=dict(holding_id=c['holding_id'],status=d['result']['status'],maximum_gradient=d['result'].get('maximum_gradient'),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path),elapsed_s=d['elapsed_s']);rows.append(row);print(row,flush=True)
 write(HERE/'summary.json',dict(source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=a.sha(SOURCE)),rows=rows,activation=False))
if __name__=='__main__':run()
