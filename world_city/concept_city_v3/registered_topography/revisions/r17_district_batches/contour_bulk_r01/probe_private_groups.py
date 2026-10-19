"""Bounded gate-only feasibility screen; public constraints deliberately pending."""
import json,time,math,argparse
from .screen import HERE,write
from . import profile_mesh

def run():
 p=argparse.ArgumentParser();p.add_argument('--max-area',type=float,default=250.);p.add_argument('--min-area',type=float,default=0.);args=p.parse_args();data=json.loads((HERE/'shared_private_groups_r02.json').read_bytes());rows=[]
 for group in data['groups']:
  if len(group['holding_ids'])<2 or group['private_area_m2']>args.max_area or group['private_area_m2']<=args.min_area:continue
  started=time.monotonic();targets=group['gate_targets']
  def target(q):return min(targets,key=lambda t:math.dist(t['point_xz_m'],q))['floor_y_m']
  try:r=profile_mesh.solve(group['source_private_route_polygons_xz_m'],group['gate_fixed_regions'],target,pitch=1.)
  except ValueError as exc:r=dict(status='TOPOLOGY_HOLD',message=str(exc))
  row=dict(id=group['id'],holding_ids=group['holding_ids'],private_area_m2=group['private_area_m2'],result=r,elapsed_s=time.monotonic()-started,scope='Only fixed private court gates. Actual public edge profiles, support depths and retained-side clearance still required.',activation=False);rows.append(row);print(row['id'],r['status'],r.get('maximum_gradient'),row['elapsed_s'],flush=True)
 write('gate_only_groups_'+str(int(args.max_area))+'.json',dict(groups=rows,activation=False))
if __name__=='__main__':run()
