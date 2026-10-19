"""Bind public heights only to their actual positive-length private incidences."""
import inspect,json,time,types,math
from pathlib import Path
from .. import author as a,regeneration
from ..incident_risers_r01 import solve as old
from ..incident_risers_r02.solve import interval
from ..bounded_profile_r01.finite import inside
from ..public_owner_completion_r05.solve import proxy as mesh
HERE=Path(__file__).resolve().parent
SOURCE=a.HERE/'public_owner_completion_r06/BLOCK_008_R8_C003_profile.json'
def run():
 source=json.loads(SOURCE.read_bytes());g=next(g for g in json.loads((a.HERE/'contour_bulk_r01/shared_private_groups_r03.json').read_bytes())['groups']if g['holding_ids']==['BLOCK_008:R8_C003']);geom=types.SimpleNamespace(**vars(a.geo));geom.point_in_convex_polygon=inside;aa=types.SimpleNamespace(**vars(a));aa.geo=geom;rows=[]
 code=inspect.getsource(old.solve_one).replace('original_tris=[t[:]for t in tris];ix=index(fixed_regions);fixed={};conflicts={};candidates={}', 'original_tris=[t[:]for t in tris];ix=index(fixed_regions);fixed={};conflicts={};candidates={};vertex_neighbors=collections.defaultdict(set)\n for tri in tris:\n  for i in tri:vertex_neighbors[i].update(j for j in tri if i!=j)')
 code=code.replace('  if not matches:continue',"  kept=[]\n  for j in matches:\n   if j<len(group['gate_fixed_regions']):kept.append(j);continue\n   intervals=[]\n   for k in vertex_neighbors[i]:\n    span=interval(p,points[k],fixed_regions[j]['polygon_xz_m'])\n    if span and (span[1]-span[0])*math.dist(p,points[k])>1e-7:intervals.append(dict(other_vertex=k,span=span))\n   if intervals:kept.append(j)\n   else:point_contacts.append(dict(point_xz_m=p,region_id=fixed_regions[j]['id'],height_m=a.common.height(fixed_regions[j]['plane_y_xz_m'],p),reason='No positive-length incident private edge belongs to this region; a point-only contact is not assigned to the opposite sector'))\n  matches=kept\n  if not matches:continue")
 for limit in [.12,.15,.20,.25]:
  points=[];sf=lambda points,tris,fixed,targets,limit=limit:regeneration.solve_field(points,tris,fixed,targets,limit=limit);ns=dict(old.solve_one.__globals__,a=aa,profile_mesh=mesh,interval=interval,point_contacts=points,regeneration=types.SimpleNamespace(solve_field=sf));exec(code,ns);start=time.monotonic()
  try:result=ns['solve_one'](g,dict(source,public_fixed_regions=source['incident_public_fixed_regions']))
  except Exception as e:result=dict(status='SOLVER_EXCEPTION_HOLD',type=type(e).__name__,message=str(e))
  path=HERE/('BLOCK_008_R8_C003_'+str(int(limit*100))+'.json');out=dict(source,result=result,source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=a.sha(SOURCE)),point_only_contact_ledger=points,grade_limit=limit,elapsed_s=time.monotonic()-start,design_policy='Every positive-length public/private boundary preserves its own exact plane. Point-only cross-sector contacts are documented rather than incorrectly constraining another sector. Explicit vertical sheets retain actual incident steps.');old.write(path,out);row=dict(limit=limit,status=result['status'],maximum_gradient=result.get('result',{}).get('maximum_gradient'),maximum_step_m=result.get('maximum_step_m'),point_only_contacts=len(points),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path));rows.append(row);print(row,flush=True)
  if result['status'].startswith('PASSED')or result['status']!='INFEASIBLE_FIXED_FINITE_PROFILE':break
 old.write(HERE/'summary.json',dict(rows=rows,activation=False))
if __name__=='__main__':run()
