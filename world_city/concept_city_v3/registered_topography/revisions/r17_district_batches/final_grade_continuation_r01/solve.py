import json
from pathlib import Path
from .. import author as a
from ..bounded_profile_r01 import finite
from ..incident_risers_r01.solve import write
HERE=Path(__file__).resolve().parent
P=a.HERE/'final_district_profiles_r04/BLOCK_004_R8_C004.json';d=json.loads(P.read_bytes());c=d['candidate'];rows=[]
for limit in [.15,.20,.25]:
 result=finite.solve(d['private_domain_polygons_xz_m'],d['court_fixed_regions']+d['public_fixed_regions'],lambda p:c['floor_y_m'],pitch=1.,limit=limit,seam_points=[p for r in d['court_fixed_regions']+d['public_fixed_regions']for p in r['polygon_xz_m']]);path=HERE/('BLOCK_004_R8_C004_'+str(int(limit*100))+'.json');write(path,dict(d,result=result,grade_limit=limit,design_policy='Candidate bounded pedestrian slope/stepped lane; no cart access claim',prior_profile=dict(path=str(P.relative_to(a.ROOT)),sha256=a.sha(P))));rows.append(dict(limit=limit,status=result['status'],maximum_gradient=result.get('maximum_gradient'),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path)));print(rows[-1],flush=True)
 if result['status']=='PASSED_FINITE_TRIANGLE_GRADE':break
write(HERE/'summary.json',dict(rows=rows,activation=False))
