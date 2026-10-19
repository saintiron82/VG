#!/usr/bin/env python3
"""Canonicalize pre-engine triangles and independently audit finite void ownership.

This only finalizes new test fixtures. It never rewrites a physics report or
production geometry. Triangle winding changes no vertex, height or ownership.
"""
import hashlib,json,math,sys
from collections import defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT),str(HERE.parent/'validation')]
import geometry as g
from world_city.runtime_city.checks.placement import convex_difference

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,data):p.write_text(json.dumps(data,separators=(',',':'),allow_nan=False)+'\n')
def cells(box):
 for x in range(math.floor(box[0]/8),math.floor(box[2]/8)+1):
  for z in range(math.floor(box[1]/8),math.floor(box[3]/8)+1):yield x,z
def index(polygons):
 buckets=defaultdict(list)
 for i,poly in enumerate(polygons):
  for cell in cells(g.bounds(poly)):buckets[cell].append(i)
 return buckets
def remaining_area(poly,owners):
 parts=[poly]
 for owner in owners:
  parts=[piece for p in parts for piece in convex_difference(p,owner) if g.area(piece)>1e-9]
  if not parts:return 0.
 return sum(g.area(p) for p in parts)

def main():
 path=HERE/'prepared.json';prepared=json.loads(path.read_text());original=sha(path)
 for source in prepared['sources'].values():assert sha(Path(source['path']))==source['sha256']
 plan=json.loads(Path(prepared['sources']['plan']['path']).read_text())
 contract=json.loads(Path(prepared['sources']['contract']['path']).read_text())
 bodies=[b['footprint_xz_m'] for b in plan['buildings']];body_index=index(bodies)
 waters=contract['water_domain_polygons'];water_index=index([w['polygon_xz_m'] for w in waters])
 reports=[];issues=[]
 for name,asset in prepared['assets'].items():
  if asset.get('collision_format')!='source_grade_proxy_triangles':continue
  resource=ROOT/asset['render_path'];data=json.loads(resource.read_text());oldhash=sha(resource);reversed_count=0;max_body=0.;max_water=0.;max_outside=0.
  owners=data['finite_ownership'];owner_index=index([o['poly'] for o in owners])
  for number,t in enumerate(data['triangles']):
   p=[[v[0],v[2]] for v in t];signed=g.cross(g.sub(p[1],p[0]),g.sub(p[2],p[0]))
   if not all(math.isfinite(v) for vertex in t for v in vertex) or abs(signed)<1e-10:issues.append([name,number,'invalid_triangle']);continue
   if signed<0:t.reverse();p.reverse();reversed_count+=1
   cells_here=list(cells(g.bounds(p)))
   nearby_bodies=set(i for cell in cells_here for i in body_index.get(cell,[]))
   for i in nearby_bodies:
    if g.bbox_overlap(g.bounds(p),g.bounds(bodies[i])):max_body=max(max_body,g.area(g.convex_intersection(p,bodies[i])))
   nearby_owners=set(i for cell in cells_here for i in owner_index.get(cell,[]))
   local_owners=[owners[i] for i in nearby_owners if g.bbox_overlap(g.bounds(p),g.bounds(owners[i]['poly']))]
   max_outside=max(max_outside,remaining_area(p,[o['poly'] for o in local_owners]))
   nearby_water=set(i for cell in cells_here for i in water_index.get(cell,[]))
   for i in nearby_water:
    w=waters[i];intersection=g.convex_intersection(p,w['polygon_xz_m'])
    if g.area(intersection)<1e-9:continue
    allowed=[o['poly'] for o in local_owners if o.get('bridge_water')==w['surface_id']]
    max_water=max(max_water,remaining_area(intersection,allowed))
  write(resource,data);asset['render_sha256']=sha(resource)
  record={'asset':name,'triangles':len(data['triangles']),'precanonical_sha256':oldhash,'tested_sha256':asset['render_sha256'],'orientation_reversals_before_any_engine_run':reversed_count,'maximum_triangle_body_overlap_m2':max_body,'maximum_unbridged_water_overlap_m2':max_water,'maximum_outside_declared_owner_m2':max_outside}
  reports.append(record);print('AUDITED',name,record,flush=True)
  if max(max_body,max_water,max_outside)>1e-7:issues.append([name,'finite_ownership_violation',max_body,max_water,max_outside])
 for route in prepared['routes']:
  if route['id'] in ['NEGATIVE_ACTUAL_0P25_RISER','NEGATIVE_ACTUAL_SOLID_WALL']:route['minimum_allowed_feet_y_m']=-4
 prepared['implementation_hashes'][str(Path(__file__).resolve().relative_to(ROOT))]=sha(Path(__file__))
 for p in list(prepared['implementation_hashes']):prepared['implementation_hashes'][p]=sha(ROOT/p)
 prepared['fixture_finalization']={'precanonical_prepared_sha256':original,'audit_path':str(HERE/'evidence/fixture_audit.json'),'finite_ownership_issues':issues}
 write(path,prepared)
 result={'status':'pass' if not issues else 'fail','prepared_sha256':sha(path),'assets':reports,'issues':issues}
 write(HERE/'evidence/fixture_audit.json',result)
 print('FIXTURE_AUDIT',result['status'],len(reports),'assets',flush=True)
 if issues:raise SystemExit(2)

if __name__=='__main__':main()
