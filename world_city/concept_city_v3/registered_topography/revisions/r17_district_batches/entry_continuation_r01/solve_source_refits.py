"""Bounded source-route alternatives against sealed exact public planes."""
import json,math,time,collections
from pathlib import Path
from .. import author as a
from ..contour_bulk_r01 import profile_mesh
HERE=Path(__file__).resolve().parent
SOURCE=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/held_private_entry_refit_r01/source_candidate_batch.json'
SOURCE_SHA='bf07fccf13df5f1b3483198cec512f346e0d148e65c0cd4bc88c7ca13fa1066e'
OUT=HERE/'source_refit_profiles_r01'

def write(p,d):
 if p.exists():raise ValueError('Refusing to overwrite '+str(p))
 p.write_text(json.dumps(d,separators=(',',':'),allow_nan=False)+'\n')

def run():
 assert a.sha(SOURCE)==SOURCE_SHA
 src=json.loads(SOURCE.read_bytes());layout=json.loads((HERE.parent/'coherent_batch18_r01/effective_source_layout_r03.json').read_bytes())
 holdings=layout['holdings'];hi=a.geo._SpatialIndex(16)
 for i,h in enumerate(holdings):hi.add(i,h['holding_polygon_xz_m'])
 OUT.mkdir(exist_ok=True);rows=[]
 for record in src['holdings']:
  if not record['candidates']:continue
  trials=[]
  for candidate in record['candidates']:
   p=OUT/(record['holding_id'].replace(':','_')+'_'+str(candidate['candidate_index'])+'.json')
   if p.exists():d=json.loads(p.read_bytes())
   else:
    t=time.monotonic();public=candidate['fixed_public_regions'];full=a.common.disjoint_union(candidate['polygons_xz_m']+candidate['internal_court_link_polygons_xz_m']);domains=a.common.subtract(full,[r['polygon_xz_m']for r in public]);ids={i for q in full for i in hi.candidates(q)}
    court=[dict(id=holdings[i]['id']+':COURT_DATUM',polygon_xz_m=holdings[i]['holding_polygon_xz_m'],plane_y_xz_m=[0,0,holdings[i]['floor_y_m']])for i in sorted(ids)if any(a.clip(q,holdings[i]['holding_polygon_xz_m'])for q in full)]
    try:res=profile_mesh.solve(domains,court+public,lambda p:candidate['floor_y_m'],pitch=1.,seam_points=[v for r in public for v in r['polygon_xz_m']])
    except Exception as e:res=dict(status='SOLVER_EXCEPTION_HOLD',type=type(e).__name__,message=str(e))
    d=dict(holding_id=record['holding_id'],candidate_index=candidate['candidate_index'],candidate=candidate,private_domain_polygons_xz_m=domains,public_fixed_regions=public,court_fixed_regions=court,result=res,elapsed_s=time.monotonic()-t,source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=SOURCE_SHA),activation=False);write(p,d)
   brief=dict(candidate_index=candidate['candidate_index'],status=d['result']['status'],maximum_gradient=d['result'].get('maximum_gradient'),elapsed_s=d['elapsed_s'],path=str(p.relative_to(a.ROOT)),sha256=a.sha(p));trials.append(brief);print(record['holding_id'],brief,flush=True)
   if d['result']['status']=='PASSED_FINITE_TRIANGLE_GRADE':break
  rows.append(dict(holding_id=record['holding_id'],trials=trials,selected_candidate_index=next((r['candidate_index']for r in trials if r['status']=='PASSED_FINITE_TRIANGLE_GRADE'),None)))
 summary=dict(rows=rows,passed=sum(r['selected_candidate_index']is not None for r in rows),source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=SOURCE_SHA),scope='Independent profile proposals only. Cross-route intersections and exact native gate/addendum binding must pass before promotion.',activation=False);write(HERE/'source_refit_profile_summary_r01.json',summary);print('SUMMARY',summary['passed'],len(rows),flush=True)
if __name__=='__main__':run()
