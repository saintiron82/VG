"""Read-only context extraction; the sole output is beneath this candidate's directory."""
import copy,json,math
from pathlib import Path
from world_city.concept_city_v3.registered_integration.r9.port_market.author import *
OUT=Path(__file__).resolve().parent

def near(poly):
 return max(p[0] for p in poly)>12 and min(p[0] for p in poly)<185 and max(p[1] for p in poly)>-22 and min(p[1] for p in poly)<115

def build_context():
 assert sha(BASE)==BASE_SHA
 scene=load(BASE);world=World(scene)
 src=[BASE,PLAN,CATALOG,CERTIFIED,MARKET,WALK,PORT]
 solids=[dict(id=id,polygon=poly,y_min=a,y_max=b,source='base_scene') for id,poly,a,b in world.solids if near(poly) and not id.startswith('MARKET_stall')]
 R9=OUT.parent
 for packfile in [R9/'port_market/pack_r02.json',R9/'precinct_gardens/pack.json',R9/'landmarks/pack.json']:
  pack=load(packfile);src.append(packfile)
  for p in pack.get('add_instances',[]):
   b=pack.get('common_assets',{}).get(p['asset_key'],scene['common_assets'].get(p['asset_key']))['bounds'];poly=ring(b,p)
   if near(poly):solids.append(dict(id=p['id'],polygon=poly,y_min=p['position_m'][1]+b['min'][1],y_max=p['position_m'][1]+b['max'][1],source=rel(packfile)))
 old=[p for p in scene['common_instances'] if p['id'].startswith('MARKET_stall')]
 reserves=[r for r in world.reservations.rows if r['kind']!='market_customer_2.4m' and near(r['polygon'])]
 tris=[dict(vertices=t,key=k) for t,k in zip(world.tris,world.trikeys) if near([[p[0],p[2]] for p in t])]
 roads=load(PLAN)['roads'];replaced={r['id']:r for r in load(MARKET)['access_overlay']['replace_roads']};roads=[replaced.get(r['id'],r) for r in roads]
 roads=[r for r in roads if any(10<q[0]<190 and -25<q[1]<120 for q in r['polyline_xz_m'])]
 canopy=R9/'port_market/market_canopy/pack.json';src.append(canopy)
 data=dict(source_refs=[ref(p) for p in src],site=next(s for s in load(PLAN)['spaces'] if s['id']=='SITE_MARKET'),old_stalls=old,old_customer_routes=load(WALK)['stall_routes'],fountain=next(p for p in scene['common_instances'] if p['id']=='MARKET_FOUNTAIN'),solids=solids,reservations=reserves,triangles=tris,roads=roads,canopy_assets=load(canopy)['common_assets'])
 (OUT/'source_context.json').write_text(json.dumps(data,separators=(',',':'))+'\n')
 print('context',len(solids),'solids',len(reserves),'reservations',len(tris),'triangles')
if __name__=='__main__':build_context()
