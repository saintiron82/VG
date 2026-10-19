import json,sys,math
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;ROOT=H.parents[4];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import DomainCut,fan
from world_city.concept_city_v3.registered_integration.r9.landward_gates.build_corridors import Ground,xz
D=json.loads((H/'context.json').read_text())['sites'];A=D['abbey'];g=Ground(A['surface_rows']);bs=A['bodies'];fs=A['floors'];cut=DomainCut(fs)
route=[[-247.49131238451622,-7.333062439626094],[-259,-7.823607],[-291,-7.823607],[-298,-8],[-311.5,-8],[-311.5,-13.5],[-324,-13.5],[-324,-17.25]]
def at(g,p):
 try:return g.at(p)
 except ValueError:return None
print('ABBey center support',[(p,at(g,p),[f['id']for f in fs if geo.point_in_convex_polygon(p,f['polygon_xz_m'],0)])for p in route])
for n,(a,b) in enumerate(zip(route,route[1:])):
 q=geo.road_ribbon(a,b,1.5);hits=[(r['id'],round(geo.intersection_area(q,r['polygon_xz_m']),6))for r in bs if geo.intersection_area(q,r['polygon_xz_m'])>1e-8];missing=sum(geo.polygon_area(p)for p in cut.subtract(q));print(n,'hits',hits,'no_nativefloor',missing)
for x in [-260,-259.5,-259,-258.5,-258,-257,-255,-253,-250,-247.5]:
 p=[x,-7.823607];print('GATE',x,'terrain',at(g,p),'native', [f['id']for f in fs if geo.point_in_convex_polygon(p,f['polygon_xz_m'],0)])
C=D['clergy'];cg=Ground(C['surface_rows'])
for p in [[172.928,-198.194],[187.9,-174],[188.5,-166],[187.5,-158],[190,-148],[195,-138],[204.18,-129.89],[199.54,-109.20]]:
 print('CLERGY',p,at(cg,p),[(r['id'])for r in C['bodies']if geo.point_in_convex_polygon(p,r['polygon_xz_m'],0)])
clergy_route=[[172.9278912093672,-198.19427223270506],[187.9,-174],[189.5,-168],[188.5,-157],[193.0,-146.5],[198.0,-137.5],[204.18127359,-129.88806654],[205.87179725,-130.95677125],[208.407582739,-132.559828315]]
for n,(a,b)in enumerate(zip(clergy_route,clergy_route[1:])):
 q=geo.road_ribbon(a,b,2);hits=[(r['id'],round(geo.intersection_area(q,r['polygon_xz_m']),6))for r in C['bodies']if geo.intersection_area(q,r['polygon_xz_m'])>1e-8];print('CLERGYSEG',n,'hits',hits)
print('ABBEYEXT')
a,b=route[:2]
for j in range(49):
 t=j/48;p=[a[k]+t*(b[k]-a[k])for k in [0,1]];print(j,round(p[0],3),round(g.at(p),6))
