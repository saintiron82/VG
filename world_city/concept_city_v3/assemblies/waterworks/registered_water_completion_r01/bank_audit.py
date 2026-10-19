"""Exact vertical-plane coverage of declared canal banks by actual R7 bank faces."""
from .audit import *
def run():
 s=a.load_scene();c=json.loads(CONTRACT.read_text());rows=[];ix=g._SpatialIndex(16);vs=s['surfaces']['bank']
 for j in range(0,len(vs),3):
  t=vs[j:j+3]
  if abs(a.normal_y(t))>1e-8:continue
  p=[[v[0],v[2]]for v in t];ix.add(len(rows),p);rows.append((j//3,t))
 out=[];degenerate=[]
 for j,b in enumerate(c['water_support']['exterior_banks']):
  if b['surface_id']not in('SPRING_VISIBLE','NORTHERN_CHANNEL_VISIBLE','CRAFT_CANAL_VISIBLE','EAST_CHANNEL_VISIBLE'):continue
  u,v=b['from_xz_m'],b['to_xz_m'];length=math.dist(u,v)
  if length<1e-8:degenerate.append(j);continue
  tx,tz=(v[0]-u[0])/length,(v[1]-u[1])/length
  target=[[0,b['bottom_y_m'][0]],[length,b['bottom_y_m'][1]],[length,b['top_y_m'][1]],[0,b['top_y_m'][0]]];covers=[];owners=[]
  for k in ix.candidates([u,v]):
   ti,t=rows[k]
   if max(abs((x[0]-u[0])*tz-(x[2]-u[1])*tx)for x in t)>1e-5:continue
   p=[[(x[0]-u[0])*tx+(x[2]-u[1])*tz,x[1]]for x in t];q=g.convex_intersection(target,p)
   if g.polygon_area(q)<1e-8:continue
   covers.append(a.common.clean(q));owners.append(dict(triangle_index=ti,source_triangle_sha256=a.canonical_sha(t)))
  remaining=a.common.subtract([target],covers);assert sum(g.polygon_area(p)for p in remaining)<=g.polygon_area(target)+1e-7;out.append(dict(contract_bank_index=j,surface_id=b['surface_id'],length_m=length,area_m2=g.polygon_area(target),missing_area_m2=sum(g.polygon_area(p)for p in remaining),actual_bank_owners=owners,uncovered_vertical_polygons_distance_y_m=remaining))
 summary={}
 for rid in sorted(set(r['surface_id']for r in out)):
  rr=[r for r in out if r['surface_id']==rid];summary[rid]=dict(segments=len(rr),area_m2=sum(r['area_m2']for r in rr),missing_area_m2=sum(r['missing_area_m2']for r in rr),missing_segments=[r['contract_bank_index']for r in rr if r['missing_area_m2']>1e-6])
 write('bank_continuity.json',dict(base_scene=ref(a.SCENE_PATH),water_contract=ref(CONTRACT),method='Exact positive-area coverage in each contract bank vertical plane by hash-bound actual bank triangles; source top/bottom bounds retained.',summary=summary,zero_length_contract_bank_indices=degenerate,banks=out));print(json.dumps(summary,indent=2))
if __name__=='__main__':run()
