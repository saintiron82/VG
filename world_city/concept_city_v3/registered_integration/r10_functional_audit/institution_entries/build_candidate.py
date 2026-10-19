"""Bounded abbey public arrival patch; existing native court and ward remain intact."""
from __future__ import annotations
import json,math,hashlib,sys
from pathlib import Path
import numpy as np
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;ROOT=H.parents[4];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import DomainCut,fan,clean
from world_city.concept_city_v3.registered_integration.r9.landward_gates.build_corridors import Ground,plane,ph,up,area3,cut3,xz
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles,transform
C=ROOT/'world_city/concept_city_v3';BASE=C/'evidence/r8_final110_runtime_r01/scene.json';SHA='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def ch(v):return hashlib.sha256(json.dumps(v,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def write(n,x):(H/n).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def rect(a,b,c,d):return [[a,b],[c,b],[c,d],[a,d]]
def circle(p,r):return [[p[0]+r*math.cos(k*math.pi/8),p[1]+r*math.sin(k*math.pi/8)]for k in range(16)]
def ribbons(pts,w):return [geo.road_ribbon(a,b,w)for a,b in zip(pts,pts[1:])]+[circle(p,w/2)for p in pts[1:-1]]
def unique(polys):
 seen=[]
 for p in polys:
  for q in DomainCut([dict(polygon_xz_m=z)for z in seen]).subtract(p):seen.append(q)
 return seen

def main():
 assert sha(BASE)==SHA
 ctx=read(H/'context.json')['sites']['abbey'];ground=Ground(ctx['surface_rows']);nativefloor=DomainCut(ctx['floors']);rows=ctx['surface_rows']
 gate=[-259.,-7.823607];road=[-247.49131238451622,-7.333062439626094];arrival=[road,[-253.,-7.568],gate];ward=[gate,[-291.,-7.823607],[-298.,-8.],[-311.5,-8.],[-311.5,-13.5],[-324.,-13.5],[-324.,-17.25]]
 width=2.5;wait=rect(-257,-5.5,-253,-1.5);link=rect(-256.25,-7.8,-253.75,-4.5)
 cores=unique(ribbons(arrival,width)+[wait,link]);outer=unique(ribbons(arrival,width+2)+[rect(-258,-6.5,-252,-.5),rect(-257.25,-8.8,-252.75,-3.5)])
 # Never duplicate or flatten the existing native court; gate contact is exact.
 edge=rect(-259.,-20.,-240.,10.)
 coreparts=unique([q for p in cores for q in nativefloor.subtract(clean(geo.convex_intersection(p,edge))) if q]);owners=unique([q for p in outer for q in nativefloor.subtract(clean(geo.convex_intersection(p,edge))) if q])
 print('Owner pieces',len(coreparts),len(owners),flush=True)
 ccut=DomainCut([dict(polygon_xz_m=p)for p in coreparts]);mcut=DomainCut([dict(polygon_xz_m=p)for p in owners]);appended={};covered=[];float_skips=[]
 def target(p):
  # Continuous ramp replaces the old ~0.49m road/bench lip. Public road centre
  # and cross-section use the actual source plane, tapering to the level bench.
  t=max(0,min(1,(p[0]+253)/(road[0]+253)))
  if t<=0:return 8.
  v=[road[0],p[1]];return 8*(1-t)+ground.at(v)*t
 def emit(mat,poly,fn):
  for tt in fan(poly):
   t=up([[x,fn([x,z]),z]for x,z in tt]);a=np.asarray(t,dtype=np.float32);n=np.cross(a[1]-a[0],a[2]-a[0])
   if area3(t)<=1e-10:continue
   if np.dot(n,n)==0:float_skips.append(dict(material=mat,triangle=t,area_m2=area3(t)));continue
   appended.setdefault(mat,[]).extend(t)
 # Source-face subdivision preserves the finite source support provenance and
 # original-plane boundary heights, including shoulders at the existing road.
 for oi,o in enumerate(owners):
  print('Owner',oi,flush=True)
  candidates=[ground.rows[i]for i in ground.idx.candidates(o)];candidates.sort(key=lambda r:(r['material']=='road',sum(v[1]for v in r['triangle'])),reverse=True);done=[]
  for r in candidates:
   q=clean(geo.convex_intersection(o,r['polygon']))
   if not q:continue
   for part in DomainCut([dict(polygon_xz_m=p)for p in done]).subtract(q):
    core=[p for p in coreparts if geo.positive_area_overlap(p,part)]
    for c in core:
     inter=clean(geo.convex_intersection(part,c))
     if inter:emit('road',inter,target)
    for sh in ccut.subtract(part):
     def blended(p,r=r):
      dist=min(geo.point_segment_distance(p,a,b)for c in coreparts for a,b in zip(c,c[1:]+c[:1]));f=min(1.,dist)
      return target(p)*(1-f)+ph(r['plane'],p)*f
     emit(r['material'],sh,blended)
    done.append(part)
  missing=DomainCut([dict(polygon_xz_m=p)for p in done]).subtract(o)
  assert sum(geo.polygon_area(p)for p in missing)<1e-6,('missing_source_ground',missing)
  covered+=done
 edits=[];source_mats=set();wet=[]
 for r in rows:
  t=r['triangle'];p=[xz(v)for v in t];inds=mcut.index.candidates(p)
  if not inds:continue
  if r['material']=='water':
   if any(geo.positive_area_overlap(p,owners[i])for i in inds):wet.append(r)
   continue
  parts=[t]
  for k in inds:parts=[v for q in parts for v in cut3(q,owners[k])]
  repl=[tt for q in parts for tt in fan(q)if area3(tt)>1e-10]
  if area3(t)-sum(area3(q)for q in repl)<1e-8:continue
  edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_xyz_m=t,source_triangle_sha256=ch(t),replacement_triangles_xyz_m=repl));source_mats.add(r['material'])
 assert not wet
 # Reuse unchanged common masters: a small seat and two low rails identify the
 # public waiting pocket. No new building or altered institution geometry.
 s=read(BASE);keys=['registered_precinct_r06_park_bench','district_r01_boundary_2m'];assets={k:s['common_assets'][k]for k in keys};adds=[]
 for iid,key,pos,yaw in [('WAIT_BENCH',keys[0],[-255.,8.,-2.45],math.pi),('WAIT_BOUNDARY_W',keys[1],[-256.,8.25,-1.8],0),('WAIT_BOUNDARY_E',keys[1],[-254.,8.25,-1.8],0)]:
  adds.append(dict(id='R10_ABBEY_PUBLIC:'+iid,asset_key=key,position_m=pos,yaw_rad=yaw,scale=[1,1,1],palette_id='native_abbey_public_arrival_r10',palette_override={},source_pack='r10_institution_entries'))
 pack=dict(schema='riverstone.city.visual_addendum.v1',base_scene_sha256=SHA,common_assets=assets,add_instances=adds,remove_instance_ids=[]);write('pack.json',pack)
 owner=dict(id='R10_ABBEY_PUBLIC_ARRIVAL',core_polygons_xz_m=coreparts,ownership_polygons_xz_m=owners,access='unrestricted_public',court_gate_id='ABBEY_NORTH_WORK:main_gate',native_court_owner='R06_ABBEY_GATE_R05:herb',public_road_id='WEST_MONASTERY_EDGE',waiting_pocket_area_m2=16.,source_policy='Only exterior terrain; existing native court floors, doors, walls and private garden are retained.')
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R10_ABBEY_PUBLIC_ARRIVAL_FINITE_R01',status='source_ready_runtime_pending',base_scene=ref(BASE),base_scene_sha256=SHA,source_surface_hashes={m:ch(s['surfaces'][m])for m in source_mats},surface_edits=edits,appended_surfaces=appended,removed_foundation_proxy_ids=[],ownership=[owner],summary=dict(source_triangle_edits=len(edits),appended_triangles=sum(len(v)//3 for v in appended.values()),owned_area_m2=sum(geo.polygon_area(p)for p in owners),waiting_pocket_area_m2=16,water_edits=0,native_building_edits=0,retirements=0,float32_degenerate_skips=len(float_skips)))
 write('surface_patch.json',patch);write('ground_ownership.json',dict(owners=[owner],native_court_route_policy='admitted_patient_staff; never an ordinary public through-link',public_private_transition=dict(point_xyz_m=[*gate[:1],8,gate[1]],existing_gate_clear_width_m=4,inside_access='admitted_patient_staff',outside_access='unrestricted_public',private_herb_garden_retained=True)))
 from filter_float32 import main as filter_tiny
 filter_tiny()
 from validate_candidate import main as validate
 validate()
if __name__=='__main__':main()
