"""Court-variable continuation for complete retained-public boundary inputs."""
import json,time,collections
from .review import HERE,OLD,write
from .. import author as a
from ..entry_continuation_r01.solve_coherent_datums import solve

def run():
 groups={g['id']:g for g in json.loads((OLD/'shared_private_groups_r03.json').read_bytes())['groups']};budgets={r['id']:r for r in json.loads((OLD/'required_core_budget.json').read_bytes())['rows']};summary=json.loads((HERE/'private_boundary_summary_r01.json').read_bytes());outdir=HERE/'datum_profiles';outdir.mkdir(exist_ok=True);rows=[]
 for r in summary['rows']:
  if r['status']!='INFEASIBLE_FIXED_FINITE_PROFILE':continue
  p=outdir/(r['id'].replace(':','_')+'.json');t=time.monotonic();data=json.loads((a.ROOT/r['path']).read_bytes())
  try:res=solve(groups[r['id']],data,budgets)
  except Exception as e:res=dict(status='SOLVER_EXCEPTION_HOLD',type=type(e).__name__,message=str(e))
  d=dict(id=r['id'],holding_ids=r['holding_ids'],private_domain_polygons_xz_m=data['private_domain_polygons_xz_m'],public_fixed_regions=data['public_fixed_regions'],result=res,source=dict(path=r['path'],sha256=a.sha(a.ROOT/r['path'])),elapsed_s=time.monotonic()-t,activation=False);write(p,d)
  brief=dict(id=r['id'],holding_ids=r['holding_ids'],status=res['status'],datum_changes=res.get('datum_changes'),maximum_gradient=res.get('maximum_gradient'),path=str(p.relative_to(a.ROOT)),sha256=a.sha(p));rows.append(brief);print(brief,flush=True)
 write(HERE/'datum_summary_r01.json',dict(rows=rows,activation=False))
if __name__=='__main__':run()
