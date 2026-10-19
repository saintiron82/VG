"""Six finite noble tails with retained public step heights kept separate."""
import json,math,time,types,inspect
from pathlib import Path
from .. import author as a,regeneration
from ..bounded_profile_r01.finite import inside
from ..incident_risers_r01 import solve as first
from ..incident_risers_r02.solve import interval
from ..noble_terminal_assist_r02.solve import point_distance
HERE=Path(__file__).resolve().parent
SOURCE=a.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_entry_batch_r02/tail_solve_inputs.json'
SHA='6254994dd9e6bdaabfb51b19dc521376187c4070853cfe1a3fa06b03855a9785'
def run():
 assert a.sha(SOURCE)==SHA;data=json.loads(SOURCE.read_bytes());rows=[]
 geo=types.SimpleNamespace(**vars(a.geo));geo.point_in_convex_polygon=inside;proxy=types.SimpleNamespace(**vars(a));proxy.geo=geo
 for entry in sorted([r for r in data['owners']if r['owner_id']!='E3'],key=lambda r:['E1','E2','E5','E4','E6','E7'].index(r['owner_id'])):
  path=HERE/(entry['owner_id']+'_proposal.json')
  if path.exists():d=json.loads(path.read_bytes())
  else:
   start=time.monotonic();source_profile=a.ROOT/entry['target_profile']['path'];assert a.sha(source_profile)==entry['target_profile']['sha256'];old=json.loads(source_profile.read_bytes())['top_pieces'];oi=first.index(old);fallback=[]
   def target(p):
    hits=[r for i in sorted(oi.candidates([p]))if inside(p,(r:=old[i])['polygon_xz_m'])]
    if hits:return a.common.height(hits[0]['plane_y_xz_m'],p)
    i,dist=min(((i,point_distance(p,r['polygon_xz_m']))for i,r in enumerate(old)),key=lambda t:t[1]);fallback.append(dict(point_xz_m=p,extrapolation_distance_m=dist,source_piece_index=i));return a.common.height(old[i]['plane_y_xz_m'],p)
   zero=[r for r in entry['fixed_regions']if a.geo.polygon_area(r['polygon_xz_m'])<=1e-12];regions=[r for r in entry['fixed_regions']if a.geo.polygon_area(r['polygon_xz_m'])>1e-12];public=[r for r in regions if r.get('kind')=='fixed_public_priority'];inner=[r for r in regions if r.get('kind')=='unchanged_private_inner_profile'];domains=[];normalized=[]
   for p in entry['private_domain_polygons_xz_m']:
    area=a.geo.polygon_area(p);diam=max(math.dist(u,v)for u in p for v in p);width=2*area/diam if diam else 0
    matches=[r['id']for r in public if all(inside(v,r['polygon_xz_m'],2e-9)for v in p)]if width<=2e-9 else[]
    if area<=1e-12 or matches:normalized.append(dict(polygon_xz_m=p,area_m2=area,width_m=width,public_owner_ids=matches))
    else:domains.append(p)
   inner_point=inner[0]['polygon_xz_m'][0];group=dict(gate_fixed_regions=inner,gate_targets=[dict(point_xz_m=inner_point,floor_y_m=a.common.height(inner[0]['plane_y_xz_m'],inner_point))]);source=dict(public_fixed_regions=public,private_domain_polygons_xz_m=domains)
   def solve_field(points,triangles,fixed,targets,limit=.12):return regeneration.solve_field(points,triangles,fixed,[fixed[i]if i in fixed else target(p)for i,p in enumerate(points)],limit)
   namespace=dict(first.solve_one.__globals__,a=proxy,interval=interval,regeneration=types.SimpleNamespace(solve_field=solve_field))
   code=inspect.getsource(first.solve_one)
   stop="  if set(anchors.values())!=set(range(len(clusters))):return dict(status='HELD_UNANCHORED_INCIDENT_SOURCE',point_xz_m=points[v],clusters=clusters,anchors=anchors)"
   replacement="""  if set(anchors.values())!=set(range(len(clusters))):
   kept=sorted(set(anchors.values()));omitted=[c for j,c in enumerate(clusters)if j not in kept]
   sector_ledger.append(dict(point_xz_m=original_points[v],kind='PUBLIC_POINT_CONTACT_WITHOUT_POSITIVE_PRIVATE_EDGE',unbound_private_clusters=omitted,policy='Public heights remain with the source public riser ledger. No positive-length private boundary meets these source regions; every emitted private boundary edge is checked separately.'))
   if not kept:continue
   remap={j:i for i,j in enumerate(kept)};clusters=[clusters[j]for j in kept];anchors={j:remap[c]for j,c in anchors.items()}
"""
   assert stop in code;code=code.replace(stop,replacement);exec(code,namespace);solver=namespace['solve_one']
   try:result=solver(group,source)
   except Exception as e:result=dict(status='SOLVER_EXCEPTION_HOLD',type=type(e).__name__,message=str(e))
   d=dict(owner_id=entry['owner_id'],source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=SHA),target_source=entry['target_profile'],private_domain_polygons_xz_m=domains,fixed_public_regions=public,fixed_inner_regions=inner,normalized_numerical_fragments=normalized,zero_area_fixed_regions=zero,result=result,soft_target_extrapolations=fallback,elapsed_s=time.monotonic()-start,activation=False,runtime_approval=False);first.write(path,d)
  result=d['result'];brief=dict(owner_id=entry['owner_id'],status=result['status'],maximum_grade=result.get('result',{}).get('maximum_gradient'),maximum_step_m=result.get('maximum_step_m'),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path),elapsed_s=d['elapsed_s']);rows.append(brief);print(brief,flush=True)
 first.write(HERE/'summary.json',dict(rows=rows,activation=False))
if __name__=='__main__':run()
