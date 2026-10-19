import sys,json,math,collections,hashlib
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[5]
sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r15_merchant_local_patch import author as a
from world_city.concept_city_v3.review_geometry import fan
C=json.loads((HERE.parent/'source_contract.json').read_text())
SCENE=a.CITY/'evidence/visual_registered_common_r5/bridge_scene.json'
assert a.sha(SCENE)=='a78e1b56bd59b06ec30d4bebec9f6da9d686dca87e6ef87f1d4da181f717a01a'
assert a.sha(HERE.parent/'source_contract.json')=='f4cc65e37809887ee616369b5d9a3a86bd346e28e77ad2d0c641f498dc9a1cdf'
REF=json.loads((HERE.parent/'frozen_local_reference.json').read_text());assert REF['base_scene_sha256']==a.sha(SCENE)
LOCAL=REF['local_triangles'];LOCAL_INDEX=a.geo._SpatialIndex(8)
for _i,_r in enumerate(LOCAL):LOCAL_INDEX.add(_i,_r['polygon_xz_m'])
def envelope(g,side=5,forward=6):
 p,q=g['gate_edge_xz_m'];n0=g['polygon_xz_m'][3];n1=g['polygon_xz_m'][2];t=np.array(q)-p;t=t/np.linalg.norm(t);n=np.array(n0)+n1-np.array(p)-q;n=n/np.linalg.norm(n);O=np.array(p);depth=max(np.dot(np.array(r)-O,n) for r in (n0,n1));lo=min(0,*[np.dot(np.array(r)-O,t) for r in(n0,n1)])-side;hi=max(math.dist(p,q),*[np.dot(np.array(r)-O,t) for r in(n0,n1)])+side
 return [(O+t*x+n*y).tolist() for x,y in [(lo,0),(hi,0),(hi,depth+forward),(lo,depth+forward)]]
def candidates(poly):
 for k in sorted(LOCAL_INDEX.candidates(poly)):
  r=LOCAL[k];yield r['material'],r['triangle_index'],r['vertices_xyz_m'],r['polygon_xz_m']

def run():
 out=[]
 for num,(g,r) in enumerate(zip(C['gate_profiles'],C['gate_risk_screen'])):
  xx,zz=zip(*g['polygon_xz_m']);x0=8*math.floor((min(xx)-4)/8);x1=8*math.ceil((max(xx)+4)/8);z0=8*math.floor((min(zz)-4)/8);z1=8*math.ceil((max(zz)+4)/8);poly=[[x0,z0],[x1,z0],[x1,z1],[x0,z1]];xs,zs=zip(*poly);bounds=[min(xs),min(zs),max(xs),max(zs)]
  ds=a.base.surface_domains(bounds,False); kinds=collections.Counter();protected=[]
  for d in ds:
   cut=a.polygon(a.geo.convex_intersection(poly,d['polygon_xz_m']))
   if not cut:continue
   kinds[d['kind']]+=a.geo.polygon_area(cut)
   if d['kind'] not in ('ground','terrace','road','road_shoulder') and not a.base.R04.prior.is_excluded(d,a.RETIRED):protected.append(dict(owner_id=d['owner_id'],kind=d['kind'],polygon_xz_m=cut))
  intersections=[]
  for mat,i,t,p in candidates(poly):
   q=a.polygon(a.geo.convex_intersection(poly,p))
   if q:intersections.append((mat,i,a.geo.polygon_area(q)))
  out.append(dict(index=num,gate_id=g['id'],property_id=g['property_id'],road_id=g['road_id'],envelope_polygon_xz_m=poly,bounds_xz_m=bounds,gate_polygon_xz_m=g['polygon_xz_m'],needs_collar=r['needs_shared_public_transition'],owner_areas_m2=dict(kinds),protected=protected,frozen_material_areas_m2=dict(collections.Counter({m:sum(t[2] for t in intersections if t[0]==m) for m in {t[0] for t in intersections}})),frozen_triangle_count=len(intersections)))
  print(num,g['road_id'],dict(kinds),'protected',len(protected),'triangles',len(intersections),flush=True)
 (HERE/'proposed_grid_extents.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':run()
