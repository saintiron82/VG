"""Separate a continuous 2 m pedestrian band from incidental public adjacency.

This does not activate a narrowed route or grant a cart-width pass. The full
private surface retains its existing finite domain; only nonwalking side
boundaries outside the stated band may have explicit retaining closure.
"""
import json,time,math,collections
from pathlib import Path
from .. import author as a
from ..contour_bulk_r01 import profile_mesh
from ...r01_ownership import author as ownership
HERE=Path(__file__).resolve().parent;SOURCE=HERE.parent/'contour_bulk_r01'

def run():
 summary=json.loads((SOURCE/'private_profiles_summary_r02.json').read_bytes());groups={r['id']:r for r in json.loads((SOURCE/'shared_private_groups_r03.json').read_bytes())['groups']};rows=[];out=HERE/'pedestrian_profiles';out.mkdir(exist_ok=True)
 for row in summary['groups']:
  if row['status']!='INFEASIBLE_FIXED_FINITE_PROFILE':continue
  target=out/(row['id'].replace(':','_')+'.json')
  if target.exists():d=json.loads(target.read_bytes());rows.append(dict(id=d['id'],holding_ids=d['holding_ids'],status=d['result']['status'],path=str(target.relative_to(a.ROOT))));continue
  start=time.monotonic();data=json.loads((a.ROOT/row['path']).read_bytes());group=groups[row['id']];bands=a.common.disjoint_union([p for h in group['source_holding_records']for p in ownership.corridor(h['external_route'],2.)]);bi=a.geo._SpatialIndex(4)
  for i,p in enumerate(bands):bi.add(i,p)
  fixed=[]
  for r in data['public_fixed_regions']:
   for j in bi.candidates(r['polygon_xz_m']):
    p=a.clip(r['polygon_xz_m'],bands[j])
    if p:fixed.append(dict(r,id=r['id']+':PEDESTRIAN:'+str(j),polygon_xz_m=p))
  def height(p):return min(group['gate_targets'],key=lambda r:math.dist(p,r['point_xz_m']))['floor_y_m']
  try:result=profile_mesh.solve(data['private_domain_polygons_xz_m'],group['gate_fixed_regions']+fixed,height,pitch=1.,seam_points=[p for r in fixed for p in r['polygon_xz_m']])
  except ValueError as exc:result=dict(status='TOPOLOGY_HOLD',message=str(exc))
  d=dict(id=row['id'],holding_ids=row['holding_ids'],pedestrian_clear_width_m=2.,original_service_reservation_width_m=3.5,walking_band_polygons_xz_m=bands,private_domain_polygons_xz_m=data['private_domain_polygons_xz_m'],fixed_public_regions=fixed,result=result,elapsed_s=time.monotonic()-start,scope='Candidate only. Any unequal public/private boundary outside the walking band needs exact nonwalking retaining/guard geometry. Cart-width continuity and integrated collision remain unapproved.',activation=False);target.write_text(json.dumps(d,separators=(',',':'))+'\n');r=dict(id=d['id'],holding_ids=d['holding_ids'],status=result['status'],maximum_gradient=result.get('maximum_gradient'),path=str(target.relative_to(a.ROOT)),sha256=a.sha(target),elapsed_s=d['elapsed_s']);rows.append(r);print(r,flush=True)
 p=HERE/'pedestrian_interface_summary_r01.json';assert not p.exists();p.write_text(json.dumps(dict(rows=rows,summary=dict(holding_counts=dict(collections.Counter(status for r in rows for status in[r['status']]*len(r['holding_ids'])))),activation=False),separators=(',',':'))+'\n')
if __name__=='__main__':run()
