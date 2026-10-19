"""Shorten overextended court cross-lines to actual free yard, retaining width/connectivity.
No geometry is moved and no reservation is dropped. Output is a revision overlay.
"""
from pathlib import Path
import copy,json,math,hashlib,sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import revision2 as audit
from world_city.runtime_city.checks import placement as g
OUT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def repair(scene,fabric):
 result=copy.deepcopy(fabric); buildings={};index=g._SpatialIndex(); changes=[]
 for item in scene['instances']:
  bounds=audit.union_bounds([item['local_bounds']]+[a['bounds'] for _,a in audit._resources(scene['assets'][item['asset_key']])])
  poly=g.transformed_aabb_xz_m(bounds,item['position_m'],item['yaw_rad']);buildings[item['id']]=poly;index.add(item['id'],poly)
 for res in result['access_reservations']:
  if res['kind']!='cross_courtyard':continue
  assert len(res['polyline_xz_m'])==2
  a,b=res['polyline_xz_m'];width=res['width_m'];ribbon=g.road_ribbon(a,b,width)
  candidates=list(index.candidates(ribbon));blockers=[i for i in candidates if g.positive_area_overlap(ribbon,buildings[i],g.CAD_TOLERANCE_M)]
  if not blockers:continue
  length=math.dist(a,b);direction=[(b[k]-a[k])/length for k in range(2)];best=None
  for steps in range(121):
   for left_steps in range(max(0,steps-60),min(60,steps)+1):
    right_steps=steps-left_steps;l=left_steps*.05;r=right_steps*.05
    if length-l-r<max(4.0,.65*length):continue
    aa=[a[k]+direction[k]*l for k in range(2)];bb=[b[k]-direction[k]*r for k in range(2)];poly=g.road_ribbon(aa,bb,width)
    if any(g.positive_area_overlap(poly,buildings[i],0.0) for i in candidates):continue
    best=(aa,bb,poly,l,r);break
   if best:break
  if best is None:raise ValueError(('No bounded endpoint trim preserves meaningful court cross-route',res['id'],blockers))
  aa,bb,poly,l,r=best;original=copy.deepcopy(res)
  res['polyline_xz_m']=[aa,bb];res['ribbon_polygons_xz_m']=[poly]
  res['revision_provenance']={'source_reservation':original,'reason':'Original internal cross-line endpoint extended into sampled building envelope. Stop at actual free-yard edge; keep width and cross-court connection.','trim_start_m':l,'trim_end_m':r,'blocking_buildings':blockers}
  assert g.convex_polygon_contains(ribbon,poly,1e-8)
  changes.append({'id':res['id'],'owner_id':res['owner_id'],'blockers':blockers,'width_m':width,'before_length_m':length,'after_length_m':math.dist(aa,bb),'trim_start_m':l,'trim_end_m':r,'geometry_delta':'subset of existing reserved ribbon; no newly occupied space'})
 # For each changed court: keep both crossing axes connected to the declared public road link.
 access=result['access_reservations'];connectivity=[]
 for owner in sorted(set(x['owner_id'] for x in changes)):
  rows=[r for r in access if r.get('owner_id')==owner and r['kind'] in ('cross_courtyard','court_to_public_road')]
  def polygons(r):return [g.road_ribbon(a,b,r['width_m']) for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])]
  graph={r['id']:set() for r in rows}
  for a in rows:
   for b in rows:
    if a['id']!=b['id'] and any(g.intersection_area(p,q)>1e-8 for p in polygons(a) for q in polygons(b)):graph[a['id']].add(b['id'])
  reached={r['id'] for r in rows if r['kind']=='court_to_public_road'};todo=list(reached)
  while todo:
   n=todo.pop()
   for other in graph[n]-reached:reached.add(other);todo.append(other)
  missing=set(graph)-reached
  if missing:raise ValueError(('Repaired court disconnected from public-road reservation',owner,sorted(missing)))
  connectivity.append({'owner_id':owner,'reservation_ids':sorted(graph),'road_link_connected':True})
 result['revision']='r3_internal_access_repaired_pre_fabric';result['access_repair_ledger']=changes;result['access_repair_connectivity']=connectivity
 return result

def main():
 scene_path=ROOT/'world_city/runtime_city/generated/r2/scene.flat_property.json';fabric_path=ROOT/'world_city/runtime_city/generated/r2/urban_fabric.json'
 out=repair(json.loads(scene_path.read_text()),json.loads(fabric_path.read_text()));out['access_repair_sources']={'scene_sha256':sha(scene_path),'fabric_sha256':sha(fabric_path)}
 p=OUT/'urban_fabric.access_repaired.json';p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'path':str(p),'repaired_reservations':len(out['access_repair_ledger']),'connected_courts':len(out['access_repair_connectivity']),'changes':out['access_repair_ledger']},indent=2))
if __name__=='__main__':main()
