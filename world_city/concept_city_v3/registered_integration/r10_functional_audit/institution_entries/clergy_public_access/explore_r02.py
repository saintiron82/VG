"""Precise high-bench route candidate; pinned geometry helpers, no shared edits."""
import json,sys,math,hashlib,importlib.util
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;ROOT=H.parents[5];sys.path.insert(0,str(ROOT))
p=H.parent/'abbey_repair_r02/candidate_r02/source_snapshot/finite_helpers_frozen.py';s=importlib.util.spec_from_file_location('clergy_frozen_helpers',p);hh=importlib.util.module_from_spec(s);s.loader.exec_module(hh);Ground=hh.Ground
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.review_geometry import DomainCut
D=json.loads((H.parent/'context.json').read_text())['sites']['clergy'];GROUND=Ground(D['surface_rows']);MOVED=['FIELD_SITE_CLERGY_035:12:bed:0','FIELD_SITE_CLERGY_035:12:bed:1']
def circle(p,r):return [[p[0]+r*math.cos(k*math.pi/16),p[1]+r*math.sin(k*math.pi/16)]for k in range(32)]
def polys(pts,w):return [g.road_ribbon(a,b,w)for a,b in zip(pts,pts[1:])]+[circle(p,w/2)for p in pts[1:-1]]
def hits(qs,bodies):
 return [dict(piece=n,id=b['id'],area_m2=ar)for n,q in enumerate(qs)for b in bodies if(ar:=g.intersection_area(q,b['polygon_xz_m']))>1e-8]
def main():
 start=[[172.9278912093672,-198.19427223270506],[187.9,-174],[189,-168],[188.2,-161],[188.1,-159],[187.5,-157.8]];tail=[[190.7,-150],[194.5,-143],[199,-136],[204.1812735904962,-129.88806654024248],[205.87179725,-130.95677125],[208.40758273925567,-132.5598283146363]];pts=start+tail
 bodies=[dict(b,polygon_xz_m=[[x-2,z]for x,z in b['polygon_xz_m']])if b['id']in MOVED else b for b in D['bodies']];qs=polys(pts,2)
 flat=DomainCut([dict(polygon_xz_m=r['polygon'])for r in GROUND.rows if max(abs(v[1]-14)for v in r['triangle'])<1e-6]+D['floors']);miss=[dict(piece=n,polygon_xz_m=p,area_m2=g.polygon_area(p))for n,q in enumerate(qs)for p in flat.subtract(q)if g.polygon_area(p)>1e-8]
 priv=[]
 for r in D['instances']:
  i=r['instance'];a=r['asset']
  if i['id'].startswith('R06_SITE_CLERGY_')and ':boundary_'in i['id']:priv.append(dict(id=i['id'],polygon_xz_m=g.transformed_aabb_xz_m(a['bounds'],i['position_m'],i['yaw_rad'])))
 out=dict(points=pts,width_m=2.,length_m=sum(math.dist(a,b)for a,b in zip(pts,pts[1:])),before_contacts=hits(qs,D['bodies']),after_contacts=hits(qs,bodies),flat14_support_missing=miss,private_holding_contacts=hits(qs,priv),moved_crop_bed_ids=MOVED,proposed_translation_xyz_m=[-2,0,0]);(H/'exploration_r02.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
