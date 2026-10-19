#!/usr/bin/env python3
"""Check travel-road ribbons against wall centerline and explicit planned openings.
This is 2D reservation evidence, not a mesh, tunnel or gate-clearance test.
"""
from pathlib import Path
import json, math
from validate_layout_v2 import point_segment
ROOT=Path(__file__).resolve().parents[2]
def intersection(a,b,c,d):
    u=[b[i]-a[i]for i in(0,1)];v=[d[i]-c[i]for i in(0,1)];w=[c[i]-a[i]for i in(0,1)];den=u[0]*v[1]-u[1]*v[0]
    if abs(den)<1e-8:return None
    t=(w[0]*v[1]-w[1]*v[0])/den;s=(w[0]*u[1]-w[1]*u[0])/den
    if -1e-5<=t<=1+1e-5 and -1e-5<=s<=1+1e-5:return [a[i]+t*u[i]for i in(0,1)]
def check_wall(d):
    n={n['id']:[n['position_m'][0],n['position_m'][2]]for n in d['road_nodes']};wall=d['wall_outline_xz_m']
    openings=[(b['id'],b['name'],b['road_access']['connection_xz_m'],b['opening_required_m']['width']/2)for b in d['building_plans']if b['functional_role']=='gatehouse']+[(f['id'],f['id'],[f['position_m'][0],f['position_m'][2]],f['opening_required_m']['width']/2)for f in d['site_features']if f['kind']=='water_postern']
    checks=[]
    for r in d['roads']:
        if r['kind']=='wall_walk' or r['id'].startswith('WALL_ACCESS'):continue
        a,b=n[r['from_node']],n[r['to_node']];L=math.dist(a,b);v=[-(b[1]-a[1])/L*r['width_m']/2,(b[0]-a[0])/L*r['width_m']/2]
        poly=[[a[i]+v[i]for i in(0,1)],[b[i]+v[i]for i in(0,1)],[b[i]-v[i]for i in(0,1)],[a[i]-v[i]for i in(0,1)]]
        for wi,(c,e)in enumerate(zip(wall,wall[1:]+wall[:1])):
            pp=[p for aa,bb in zip(poly,poly[1:]+poly[:1])if(p:=intersection(aa,bb,c,e))]
            pp += [p for p in(a,b) if point_segment(p,c,e)<.005]
            if not pp:continue
            associations=[]
            for p in pp:
                g=min(openings,key=lambda g:math.dist(p,g[2]));dist=math.dist(p,g[2]);associations.append({'opening_id':g[0],'name':g[1],'distance_along_wall_m':round(dist,4),'allowed_half_span_m':g[3],'passed':dist<=g[3]+.005})
            checks.append({'road_id':r['id'],'route_id':r['route_id'],'wall_edge':wi,'points':associations,'passed':all(p['passed']for p in associations)})
    expected={g[0]for g in openings};seen={p['opening_id']for c in checks for p in c['points']}
    return {'passed':all(c['passed']for c in checks)and expected==seen,'unreferenced_openings':sorted(expected-seen),'crossing_or_touching_segments':len(checks),'checks':checks,'scope':'2D travel-road ribbons versus wall centerline; excludes wall walk/stair links; 3D gate opening construction and cart swept-path untested'}
if __name__=='__main__':
    result=check_wall(json.loads((ROOT/'world_city/data/city_brief.v2.json').read_text()));(ROOT/'world_city/checks/wall_crossings_v2.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['passed']else 1)
