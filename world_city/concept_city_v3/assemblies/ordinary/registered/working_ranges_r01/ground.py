"""Bounded exact triangle audit against the frozen actual R5 scene. No export."""
import json,math,sys
import numpy as np
from collections import Counter
from .design import *
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.registered_topography.revisions.r14_precinct_merchant import author as terrain
BOUNDS=[150,125,282,214]

def prepare():
 selection=load(HERE/'selection.json');scene=load(R5/'scene.json');records=[];x0,z0,x1,z1=BOUNDS
 assert scene['terrain_contract']['revision'].startswith('r14') or scene['terrain_contract'].get('author_sha256')==ref(Path(terrain.__file__))['sha256']
 for material,vertices in scene['surfaces'].items():
  if material=='water':continue
  triangles=np.array(vertices).reshape(-1,3,3);lo=triangles.min(axis=1);hi=triangles.max(axis=1);ix=np.where((hi[:,0]>=x0)&(lo[:,0]<=x1)&(hi[:,2]>=z0)&(lo[:,2]<=z1))[0]
  for i in ix:
   t=triangles[i].tolist();p=[[q[0],q[2]]for q in t]
   if geo.polygon_area(p)>1e-10:records.append(dict(material=material,source_triangle_index=int(i),vertices_m=t))
 snapshot=dict(schema='riverstone.working_ranges.r5_bounded_triangles.v1',scene=ref(R5/'scene.json'),bounds_xz_m=BOUNDS,records=records,scope='Only frozen visible terrain triangles intersecting the selected cluster bbox; not a new terrain export.',terrain_author=ref(Path(terrain.__file__)),terrain_contract=ref(CITY/'registered_topography/revisions/r14_precinct_merchant/contract.json'))
 write(HERE/'evidence/frozen_r5_local_triangles.json',snapshot);return snapshot

class ActualGround:
 def __init__(self):
  p=HERE/'evidence/frozen_r5_local_triangles.json';self.snapshot=load(p) if p.exists()else prepare();self.records=self.snapshot['records'];self.index=geo._SpatialIndex(8)
  for i,r in enumerate(self.records):self.index.add(i,[[p[0],p[2]]for p in r['vertices_m']])
 def audit(self,polys):
  expected=0;covered=0;ys=[];materials=Counter();pieces=[]
  for pi,p in enumerate(polys):
   expected+=geo.polygon_area(p)
   for ti in sorted(self.index.candidates(p)):
    r=self.records[ti];tri=r['vertices_m'];q=geo.convex_intersection(p,[[v[0],v[2]]for v in tri]);area=geo.polygon_area(q)
    if area<1e-8:continue
    a,b,c=tri;den=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2]);heights=[]
    for x,z in q:
     u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/den;v=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/den;heights.append(u*a[1]+v*b[1]+(1-u-v)*c[1])
    ys+=heights;covered+=area;materials[r['material']]+=area;pieces.append(dict(polygon_index=pi,local_snapshot_triangle_index=ti,area_m2=area,min_y_m=min(heights),max_y_m=max(heights)))
  return dict(projected_area_m2=expected,frozen_triangle_covered_area_m2=covered,coverage_error_m2=covered-expected,min_y_m=min(ys)if ys else None,max_y_m=max(ys)if ys else None,materials_area_m2=dict(materials),triangle_piece_count=len(pieces),pieces=pieces,fully_covered=abs(covered-expected)<max(1e-5,expected*1e-8))

def run():
 snap=prepare();ground=ActualGround();selection=load(HERE/'selection.json');m=np.load(PLAN/'review_masks.npz');results=[]
 # Conservative existing planning raster is read-only; bound only the selected parcel.
 sys.path.insert(0,str(PLAN.parent/'coverage_r5_draft_01'))
 from account_coverage import layer_from
 for p in selection['placements']:
  env=p['source_parcel']['building_envelope_xz_m'];touch=layer_from([env],False)[2];clear=bool(np.all(m['BLOCK_015'][touch]));a=ground.audit([env]);assert clear and a['fully_covered'],(p['id'],a);assert abs(a['min_y_m']-2.5)<1e-7 and abs(a['max_y_m']-2.5)<1e-7,(p['id'],a)
  samples=[]
  for q in env+[p['source_parcel']['center_xz_m']]:
   o=terrain.owner_at(*q);y=terrain.land_height_at(*q);assert abs(y-2.5)<1e-8 and o['kind']in('terrace','ground');samples.append(dict(xz_m=q,y_m=y,owner_id=o['owner_id'],owner_kind=o['kind']))
  results.append(dict(parcel_id=p['id'],preserved_owner_clearance_pass=clear,actual_r5_triangles=a,r14_crosscheck=samples,finished_floor_y_m=2.5,native_bottom_y_m=2.0,foundation_policy='0.5 m native stone plinth embeds into the existing +2.5 m terrain; remove exact native bottom mask at integration. No broad holding pad, fill or unbounded support.',new_stepped_support_required=False))
 out=dict(schema='riverstone.working_ranges.source_ground_review.v1',selection=ref(HERE/'selection.json'),snapshot=ref(HERE/'evidence/frozen_r5_local_triangles.json'),all_source_envelopes_clear=True,all_actual_floors_exactly_2_5=True,ranges=results,limits=['Only four selected range envelopes checked here; exact native bottom masks and full-width routes are a separate subsequent check.','No scene, terrain or source ownership has been changed.']);write(HERE/'source_ground_review.json',out);print(json.dumps({k:v for k,v in out.items()if k!='ranges'},indent=2));return out
if __name__=='__main__':run()
