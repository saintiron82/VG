"""Solve the ready finite private groups against released actual public planes.

The public regions stay outside new private emission. Their exact vertices seed
private boundary topology, and every incident private vertex uses that plane.
"""
import json,math,time,collections,argparse
from .screen import HERE,write
from . import profile_mesh
from .. import author as a

def run():
 parser=argparse.ArgumentParser();parser.add_argument('--max-groups',type=int,default=1000);args=parser.parse_args()
 profiles=json.loads((HERE/'resolved_public_inputs_r01.json').read_bytes());entries={r['holding_id']:r for r in profiles['entries']};groups=json.loads((HERE/'shared_private_groups_r03.json').read_bytes())['groups'];outdir=HERE/'private_profiles_r01';outdir.mkdir(exist_ok=True);rows=[]
 for group in groups:
  holds=[r for hid in group['holding_ids']if(r:=entries[hid])['status']!='READY_SHARED_PUBLIC_PLANES']
  if holds:
   rows.append(dict(id=group['id'],holding_ids=group['holding_ids'],status='HELD_PUBLIC_DEPENDENCY',public_holds=[dict(id=r['holding_id'],reasons=r['hold_reasons'])for r in holds]));continue
  name=group['id'].replace(':','_')+'.json';path=outdir/name
  if path.exists():row=json.loads(path.read_bytes());rows.append(row);continue
  if sum('result' in r for r in rows)>=args.max_groups:continue
  started=time.monotonic();regions=[];seen=set()
  for hid in group['holding_ids']:
   for r in entries[hid]['profile_regions']:
    key=a.canonical_sha([r['polygon_xz_m'],r['plane_y_xz_m']])
    if key not in seen:seen.add(key);regions.append(r)
  masks=[r['polygon_xz_m']for r in regions];full=a.common.disjoint_union([p for h in group['source_holding_records']for p in h['external_route_polygons_xz_m']]);domains=a.common.subtract(full,masks);fixed=group['gate_fixed_regions']+regions;targets=group['gate_targets'];seed=[p for r in regions for p in r['polygon_xz_m']]
  def target(q):return min(targets,key=lambda t:math.dist(t['point_xz_m'],q))['floor_y_m']
  try:result=profile_mesh.solve(domains,fixed,target,pitch=1.,seam_points=seed)
  except ValueError as exc:result=dict(status='TOPOLOGY_HOLD',message=str(exc))
  row=dict(id=group['id'],holding_ids=group['holding_ids'],status=result['status'],private_domain_polygons_xz_m=domains,public_fixed_regions=regions,result=result,elapsed_s=time.monotonic()-started,source_public_profiles=profiles['source_public_profiles'],activation=False)
  path.write_text(json.dumps(row,separators=(',',':'))+'\n');rows.append(row);print(group['id'],result['status'],result.get('maximum_gradient'),row['elapsed_s'],flush=True)
 summary=dict(groups=len(rows),holding_counts=dict(collections.Counter(s for r in rows for s in [r['status']]*len(r['holding_ids']))),group_counts=dict(collections.Counter(r['status']for r in rows)))
 write('private_profiles_summary_r01.json',dict(summary=summary,groups=[dict(id=r['id'],holding_ids=r['holding_ids'],status=r['status'],path=str((outdir/(r['id'].replace(':','_')+'.json')).relative_to(a.ROOT))if'result'in r else None)for r in rows],activation=False));print(summary,flush=True)
if __name__=='__main__':run()
