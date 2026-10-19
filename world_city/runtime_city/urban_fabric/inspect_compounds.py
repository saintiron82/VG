from pathlib import Path
import json,math,sys,itertools
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks.placement import positive_area_overlap,road_ribbon,_SpatialIndex,polygon_area

def hull(points):
 p=sorted(set(tuple(a) for a in points))
 def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
 lo=[]
 for x in p:
  while len(lo)>1 and cross(lo[-2],lo[-1],x)<=0:lo.pop()
  lo.append(x)
 hi=[]
 for x in reversed(p):
  while len(hi)>1 and cross(hi[-2],hi[-1],x)<=0:hi.pop()
  hi.append(x)
 return [list(x) for x in lo[:-1]+hi[:-1]]

def center(p):return [sum(q[i] for q in p)/len(p) for i in (0,1)]
def candidates(plan):
 nodes={n['id']:[n['position_m'][0],n['position_m'][2]] for n in plan['road_nodes']}
 obstacles={b['id']:b['footprint_xz_m'] for b in plan['building_plans']}
 obstacles.update({r['id']:road_ribbon(nodes[r['from_node']],nodes[r['to_node']],r['width_m']+.6) for r in plan['roads']})
 si=_SpatialIndex()
 for k,v in obstacles.items():si.add(k,v)
 plots=plan['plots'];out=[];used=set()
 for did,target in [('D04',[180,40]),('D04',[110,185]),('D07',[-290,-90]),('D08',[-80,-330])]:
  ps=[p for p in plots if p['district_id']==did and p['id'] not in used]
  best=[]
  for a in sorted(ps,key=lambda p:math.dist(center(p['footprint_xz_m']),target))[:90]:
   close=sorted((q for q in ps if q!=a),key=lambda p:math.dist(center(p['footprint_xz_m']),center(a['footprint_xz_m'])))[:7]
   for b,c in itertools.combinations(close,2):
    group=[a,b,c]; ids={p['front_building_id'] for p in group}; h=hull([v for p in group for v in p['footprint_xz_m']]);ar=polygon_area(h)
    if ar<900 or ar>3500:continue
    if any(positive_area_overlap(h,obstacles[k],.01) for k in si.candidates(h) if k not in ids):continue
    # Joined holdings should be neighboring, not vast hulls of isolated parcels.
    if ar>sum(polygon_area(p['footprint_xz_m']) for p in group)*1.6:continue
    score=math.dist(center(h),target)+abs(ar-1800)/30
    best.append((score,group,h,ar))
  if best:
   _,group,h,ar=min(best,key=lambda q:q[0]);used.update(p['id'] for p in group)
   out.append({'district_id':did,'source_plot_ids':[p['id'] for p in group],'source_building_ids':[p['front_building_id'] for p in group],'footprint_xz_m':h,'area_m2':round(ar,2),'center_xz_m':center(h)})
 return out
if __name__=='__main__':
 p=json.loads((ROOT/'world_city/data/city_brief.v2.json').read_text()); print(json.dumps(candidates(p),indent=2))
