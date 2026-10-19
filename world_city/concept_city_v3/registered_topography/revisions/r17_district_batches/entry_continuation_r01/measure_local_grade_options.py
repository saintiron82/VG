"""Measure bounded 15%/20% private-entry options; no acceptance is implied."""
import json,time,collections
from pathlib import Path
from . import solve_coherent_datums as solver
from .. import author as a
HERE=Path(__file__).resolve().parent;SOURCE=HERE.parent/'contour_bulk_r01'
def run():
 summary=json.loads((HERE/'coherent_datum_summary_r01.json').read_bytes());groups={r['id']:r for r in json.loads((SOURCE/'shared_private_groups_r03.json').read_bytes())['groups']};profiles={r['id']:r for r in json.loads((SOURCE/'private_profiles_summary_r02.json').read_bytes())['groups']};budgets={r['id']:r for r in json.loads((SOURCE/'required_core_budget.json').read_bytes())['rows']};out=HERE/'local_grade_options';out.mkdir(exist_ok=True);rows=[]
 for row in summary['rows']:
  if row['status']!='NO_FEASIBLE_COHERENT_DATUM':continue
  group=groups[row['id']];source=profiles[row['id']];data=json.loads((a.ROOT/source['path']).read_bytes());attempts=[]
  for limit in(.15,.20):
   path=out/(row['id'].replace(':','_')+'_'+str(round(limit*100))+'.json')
   if path.exists():d=json.loads(path.read_bytes())
   else:
    t=time.monotonic();result=solver.solve(group,data,budgets,limit);d=dict(id=row['id'],holding_ids=row['holding_ids'],source_profile=dict(path=source['path'],sha256=a.sha(a.ROOT/source['path'])),result=result,elapsed_s=time.monotonic()-t,scope='Measured full-width exception candidate. Exact public planes remain fixed. Native datum rebind, visible stair or slope design choice, support/side audit and unchanged-controller replay are required before activation.',activation=False);path.write_text(json.dumps(d,separators=(',',':'))+'\n')
   r=dict(limit=limit,status=d['result']['status'],maximum_gradient=d['result'].get('maximum_gradient'),datum_changes=d['result'].get('datum_changes'),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path));attempts.append(r);print(row['id'],r['limit'],r['status'],flush=True)
   if r['datum_changes']:break
  rows.append(dict(id=row['id'],holding_ids=row['holding_ids'],attempts=attempts))
 path=HERE/'local_grade_options_r01.json';assert not path.exists();path.write_text(json.dumps(dict(rows=rows,activation=False),separators=(',',':'))+'\n')
if __name__=='__main__':run()
