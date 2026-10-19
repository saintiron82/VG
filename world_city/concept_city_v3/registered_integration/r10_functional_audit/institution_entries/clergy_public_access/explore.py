"""Bounded clergy high-level access exploration, read-only original context."""
import json,sys,math,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;ROOT=H.parents[5];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.review_geometry import DomainCut,fan
from world_city.concept_city_v3.registered_integration.r9.landward_gates.build_corridors import Ground,ph,xz
D=json.loads((H.parent/'context.json').read_text())['sites']['clergy'];GROUND=Ground(D['surface_rows']);MOVED=['FIELD_SITE_CLERGY_035:12:bed:0','FIELD_SITE_CLERGY_035:12:bed:1']
def circle(p,r):return [[p[0]+r*math.cos(k*math.pi/8),p[1]+r*math.sin(k*math.pi/8)]for k in range(16)]
def polys(pts,w):return [g.road_ribbon(a,b,w)for a,b in zip(pts,pts[1:])]+[circle(p,w/2)for p in pts[1:-1]]
def hits(qs,bodies):
 out=[]
 for n,q in enumerate(qs):
  for b in bodies:
   ar=g.intersection_area(q,b['polygon_xz_m'])
   if ar>1e-8:out.append(dict(piece=n,id=b['id'],area_m2=ar))
 return out

def main():
 pts=[[172.9278912093672,-198.19427223270506],[187.9,-174],[189,-168],[188.1,-161],[186.7,-158.5],[190.7,-150],[194.5,-143],[199,-136],[204.1812735904962,-129.88806654024248],[205.87179725,-130.95677125],[208.40758273925567,-132.5598283146363]]
 bodies=[dict(b,polygon_xz_m=[[x-2,z]for x,z in b['polygon_xz_m']])if b['id']in MOVED else b for b in D['bodies']]
 qs=polys(pts,2);before=hits(qs,D['bodies']);after=hits(qs,bodies);print('before',before);print('after',after)
 floorrows=[r for r in GROUND.rows if max(abs(v[1]-14)for v in r['triangle'])<1e-6];flat=DomainCut([dict(polygon_xz_m=r['polygon'])for r in floorrows]+D['floors']);missing=sum(g.polygon_area(p)for q in qs for p in flat.subtract(q));print('FLAT SUPPORT MISSING',missing)
 # Preserve private holdings as entire domains rather than only treating their walls as obstacles.
 priv=[]
 for i in D['instances']:
  ins=i['instance'];a=i['asset'];b=a.get('bounds')
  if ins['id'].startswith('R06_SITE_CLERGY_')and ':boundary_'in ins['id']:
   pp=g.transformed_aabb_xz_m(b,ins['position_m'],ins['yaw_rad']);priv.append(dict(id=ins['id'],polygon_xz_m=pp))
 print('privateholdinghits',hits(qs,priv))
 out=dict(points=pts,width_m=2.,length_m=sum(math.dist(a,b)for a,b in zip(pts,pts[1:])),before_contacts=before,after_contacts=after,flat14_support_missing_area_m2=missing,private_holding_contacts=hits(qs,priv),moved_crop_bed_ids=MOVED,proposed_translation_xyz_m=[-2,0,0]);(H/'exploration.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
