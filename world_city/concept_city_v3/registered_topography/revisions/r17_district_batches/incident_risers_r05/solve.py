"""Normalized fixed-region incidence plus coherent datum audit continuation."""
import json,time,types,inspect,math
from pathlib import Path
from .. import author as a
from ..incident_risers_r01 import solve as first
from ..incident_risers_r02 import solve as second
from ..bounded_profile_r01.finite import inside
HERE=Path(__file__).resolve().parent

def run():
 groups=json.loads((a.HERE/'contour_bulk_r01/shared_private_groups_r03.json').read_bytes())['groups'];budgets={r['id']:r for r in json.loads((a.HERE/'contour_bulk_r01/required_core_budget.json').read_bytes())['rows']};rows=[]
 geo=types.SimpleNamespace(**vars(a.geo));geo.point_in_convex_polygon=inside;proxy=types.SimpleNamespace(**vars(a));proxy.geo=geo
 for hid in ['BLOCK_003:R8_C001']:
  group=next(g for g in groups if g['holding_ids']==[hid]);p=first.INPUT/'private_profiles'/(group['id'].replace(':','_')+'.json');source=json.loads(p.read_bytes());out=HERE/(hid.replace(':','_')+'.json')
  normalized=[];kept=[]
  for poly in source['private_domain_polygons_xz_m']:
   area=a.geo.polygon_area(poly);diam=max(math.dist(p,q)for p in poly for q in poly);width=2*area/diam if diam else 0
   matches=[r for r in source['public_fixed_regions']if all(inside(p,r['polygon_xz_m'],2e-9)for p in poly)]if width<=2e-9 else[]
   if matches:normalized.append(dict(polygon_xz_m=poly,area_m2=area,maximum_equivalent_width_m=width,retained_public_owner_ids=[r['id']for r in matches]))
   else:kept.append(poly)
  source['private_domain_polygons_xz_m']=kept
  if out.exists():d=json.loads(out.read_bytes())
  else:
   start=time.monotonic();solver_gen=types.FunctionType(second.variable_solver.__code__,dict(second.variable_solver.__globals__,a=proxy));base_variable=solver_gen(group,source,budgets);variable=lambda pts,tris,fixed,target_heights,limit=.12:base_variable(pts,tris,fixed,target_heights,limit=.15)
   namespace=dict(first.solve_one.__globals__,a=proxy,interval=second.interval,regeneration=types.SimpleNamespace(solve_field=variable))
   code=inspect.getsource(first.solve_one).replace(" faces=result['triangles'];ys=result['heights_m'];edges=collections.defaultdict(list)"," datums={r['holding_id']:r['candidate_floor_y_m']for r in result.get('datum_changes',[])}\n fixed_regions=[dict(r,plane_y_xz_m=[0,0,datums[r['id'].split(':COURT_DATUM')[0]]])if r['id'].split(':COURT_DATUM')[0]in datums else r for r in fixed_regions]\n faces=result['triangles'];ys=result['heights_m'];edges=collections.defaultdict(list)")
   exec(code,namespace);res=namespace['solve_one'](group,source);d=dict(id=group['id'],holding_ids=[hid],private_domain_polygons_xz_m=source['private_domain_polygons_xz_m'],public_fixed_regions=source['public_fixed_regions'],source=dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p)),normalized_public_boundary_slivers=normalized,result=res,elapsed_s=time.monotonic()-start,grade_limit=.15,design_status='EXPLORATORY_LOCAL_SERVICE_GRADE_EXCEPTION_REQUIRES_PARENT_REVIEW_AND_UNCHANGED_CONTROLLER',policy='Distance-normalized 1 nm incidence follows documented topology welding. Each incident retained public height remains separate. Coherent court-variable values are used by the final seam audit.',activation=False);first.write(out,d)
  brief=dict(holding_id=hid,status=d['result']['status'],path=str(out.relative_to(a.ROOT)),sha256=a.sha(out),elapsed_s=d['elapsed_s']);rows.append(brief);print(brief,flush=True)
 first.write(HERE/'summary.json',dict(rows=rows,activation=False))
if __name__=='__main__':run()
