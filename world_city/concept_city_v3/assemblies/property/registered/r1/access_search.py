"""Bounded full-width hillside gate/road search. No source plan mutation."""
from __future__ import annotations
import json,math,time
from collections import Counter
from pathlib import Path
from .. import author as a
from ..ownership import bounds,boxes_touch
from world_city.concept_city_v3.registered_topography import author as terrain
HERE=Path(__file__).resolve().parent;OUT=HERE/'generated';WIDTH=3.;MAX_GRADE=.10

def hull(points):return terrain._hull(points)
def nearest(point,a0,b0):return a.near(a0,b0,point)[0]
def bbox_distance(bb,p):return math.hypot(max(bb[0]-p[0],0,p[0]-bb[2]),max(bb[1]-p[1],0,p[1]-bb[3]))
class World:
 def __init__(self,plan,recipes):
  self.objects={};self.index=a.geom._SpatialIndex(24);self.roads={};self.road_index=a.geom._SpatialIndex(24);self.segments=[]
  def add(key,poly,kind,owner=None):
   if a.geom.polygon_area(poly)<1e-6:return
   self.objects[key]=dict(id=key,polygon=poly,bounds=bounds(poly),kind=kind,owner=owner);self.index.add(key,poly)
  for p in plan['plots']:add(p['id'],p['polygon_xz_m'],'private_parcel',p['id'])
  for s in plan['spaces']:
   if s['id'] not in ('SITE_COMMON','SITE_MARKET'):add(s['id'],s['polygon_xz_m'],'reserved_institution',s['id'])
  for i,w in enumerate(plan['water_reservations']['finite_water_polygons']):add('water:'+str(i),w['polygon_xz_m'],'water')
  for r in plan['roads']:
   for i,(u,v) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):
    if math.dist(u,v)<1e-7:continue
    poly=a.geom.road_ribbon(u,v,r['width_m']);key=r['id']+':'+str(i);q=dict(id=key,road_id=r['id'],a=u,b=v,width=r['width_m'],polygon=poly,bounds=bounds(poly));self.roads[key]=q;self.road_index.add(key,poly);self.segments.append(q)
  self.boundary=plan['boundary_xz_m']
 def obstacle_hits(self,poly,owner):
  bb=bounds(poly);hits=[]
  for k in self.index.candidates(poly):
   q=self.objects[k]
   if q['owner']==owner or not boxes_touch(bb,q['bounds']):continue
   if a.overlap(poly,q['polygon']):hits.append(k)
  return hits
 def road_hits(self,poly,target):
  hits=[];bb=bounds(poly)
  for k in self.road_index.candidates(poly):
   r=self.roads[k]
   if not boxes_touch(bb,r['bounds']):continue
   for tri in a.triangulate(poly):
    p=a.geom.convex_intersection(tri,r['polygon'])
    if a.geom.polygon_area(p)>1e-6 and any(math.dist(x,target)>5.0 for x in p):hits.append(k)
  return sorted(set(hits))

def gate_candidates(recipe):
 poly=recipe['plot']['polygon_xz_m'];solids=[p['footprint_xz_m'] for p in recipe['placements']];shared={int(k) for k in recipe['shared_edge_ownership']};out=[]
 for i,(u,v) in enumerate(zip(poly,poly[1:]+poly[:1])):
  if i in shared:continue
  length=math.dist(u,v);t=a.unit(u,v);n=[-t[1],t[0]]
  for step in range(3,math.floor(length/2)-2):
   d=step*2;center=a.add(u,t,d);inner=a.add(center,n,6);outside=a.add(center,n,-2);corridor=a.geom.road_ribbon(center,a.add(center,n,7),5)
   if not a.contained(corridor,poly) or any(a.overlap(corridor,p) for p in solids):continue
   out.append(dict(edge_index=i,edge_t=d/length,center_xz_m=center,inside_point_xz_m=inner,outside_point_xz_m=outside,inward_xz=n,width_m=5))
 return out

def evaluate(recipe,gate,segment,world):
 pid=recipe['id'];floor=recipe['plot']['pad_floor_y_m'];start=gate['outside_point_xz_m'];center=nearest(start,segment['a'],segment['b']);toward=a.unit(center,start);end=a.add(center,toward,segment['width']/2);length=math.dist(start,end)
 if not 5<=length<=125:return None,'length'
 # External movement must leave, rather than cut back across, the owned parcel.
 if sum((end[i]-start[i])*gate['inward_xz'][i] for i in (0,1))>0:return None,'inward_target'
 direction=a.unit(start,end)
 # A real level turning pocket ends on a cross-section wholly beyond the gate.
 base=list(start);apron=a.geom.road_ribbon(gate['center_xz_m'],base,5)
 advance=max(0.,max(sum((p[i]-base[i])*direction[i] for i in (0,1)) for p in apron)+.5)
 start=a.add(base,direction,advance);length=math.dist(start,end)
 if length<5:return None,'turning_pocket_leaves_short_ramp'
 terminal=a.geom.road_ribbon(end,a.add(end,direction,.5),WIDTH)
 if not a.polygon_covered_by_union(terminal,[world.roads[k]['polygon'] for k in world.road_index.candidates(terminal)],1e-6):return None,'terminal_not_fully_on_public_road'
 right=[-direction[1],direction[0]];edges=[a.add(end,right,s*WIDTH/2) for s in (-1,1)];ys=[terrain.dry_height_at(*p) for p in edges];mean=sum(ys)/2;rail_grades=[abs(y-floor)/length for y in ys];cross=abs(ys[1]-ys[0])/WIDTH;grade=math.hypot(max(rail_grades),cross)
 if grade>MAX_GRADE+1e-8:return None,'grade'
 ramp=a.geom.road_ribbon(start,end,WIDTH);landing=hull(apron+[ramp[0],ramp[3]]);landing_end=a.geom.road_ribbon(end,a.add(end,direction,.5),WIDTH)
 for poly in (ramp,landing,landing_end):
  if not a.contained(poly,world.boundary):return None,'city_boundary'
  hits=world.obstacle_hits(poly,pid)
  if hits:return None,'ownership:'+hits[0]
  if world.road_hits(poly,end):return None,'intervening_road'
 # No outside ramp part can pass back through this estate, beyond its own gate landing.
 if any(a.inside(p,recipe['plot']['polygon_xz_m']) for p in (a.add(start,direction,1),end)):return None,'own_property_reentry'
 samples=[];max_fill=0
 for j in range(math.ceil(length/2)+1):
  t=j/math.ceil(length/2)
  for side in (-1,0,1):
   p=a.add(a.add(start,direction,t*length),right,side*WIDTH/2);y=floor+t*(mean-floor)+t*side*(ys[1]-ys[0])/2;existing=terrain.land_height_at(*p);delta=y-existing;max_fill=max(max_fill,abs(delta));samples.append([p[0],y,p[1],existing,delta])
 for p in landing+[a.centre(landing)]:
  existing=terrain.land_height_at(*p);delta=floor-existing;max_fill=max(max_fill,abs(delta));samples.append([p[0],floor,p[1],existing,delta])
 if max_fill>4:return None,'support_over_4m'
 return dict(property_id=pid,gate=gate,road_id=segment['road_id'],road_segment_id=segment['id'],finished_floor_y_m=floor,external_centerline_xz_m=[gate['center_xz_m'],start,end],road_connection_xz_m=end,road_center_connection_xz_m=center,road_connection_rail_y_m=ys,clear_width_m=WIDTH,source_gate_width_m=5,turning_pocket_width_m=5,maximum_full_width_grade=grade,maximum_rail_grade=max(rail_grades),cross_slope_at_road=cross,ramp_run_m=length,owned_ramp_polygon_xz_m=ramp,gate_landing_polygon_xz_m=landing,road_landing_polygon_xz_m=landing_end,source_road_landing_override=dict(road_id=segment['road_id'],bounded_polygon_xz_m=landing_end,policy='same shared terrain datum at terminal full-width edge; junction ownership must be explicit'),support_samples_xyz_existing_delta=samples,maximum_cut_fill_m=max_fill,ownership_status='proposed_finite_public_or_common_ground_reservation; no private parcel or institution intersection',actual_road_grade_api_sha256=a.file_sha(Path(terrain.__file__)),status='geometrically_clear_candidate_pending_independent_full_chain_review'),None

def run():
 OUT.mkdir(exist_ok=True);plan=json.loads((a.CITY/'registered_source/plan.json').read_text());recipes=[json.loads((a.HERE/'generated'/(i+'.recipe.json')).read_text()) for i in a.IDS];world=World(plan,recipes);records=[]
 for r in recipes:
  started=time.monotonic();gates=gate_candidates(r);candidates=[];rejects=Counter();seen=set()
  for gate in gates:
   for seg in world.segments:
    if bbox_distance(seg['bounds'],gate['center_xz_m'])>130:continue
    # Adjacent short source segments can produce an identical projection target.
    key=(gate['edge_index'],round(gate['edge_t'],5),tuple(round(x,2) for x in nearest(gate['outside_point_xz_m'],seg['a'],seg['b'])))
    if key in seen:continue
    seen.add(key);c,reason=evaluate(r,gate,seg,world)
    if c:candidates.append(c)
    else:rejects[reason]+=1
  candidates.sort(key=lambda c:(c['ramp_run_m']+10*c['maximum_cut_fill_m'],c['maximum_full_width_grade']))
  # Keep distinct gate locations so later internal routing can select a feasible bay.
  selected=[]
  for c in candidates:
   if any(math.dist(c['gate']['center_xz_m'],p['gate']['center_xz_m'])<4 for p in selected):continue
   selected.append(c)
   if len(selected)==8:break
  row=dict(property_id=r['id'],gate_positions_tested=len(gates),gate_road_pairs_tested=len(seen),accepted_finite_candidates=len(candidates),rejections=dict(rejects),candidates=selected,elapsed_s=round(time.monotonic()-started,3));records.append(row);print(json.dumps(dict(property=r['id'],gate_positions=len(gates),pairs=len(seen),clear_candidates=len(candidates),best_run_m=selected[0]['ramp_run_m'] if selected else None,best_grade=selected[0]['maximum_full_width_grade'] if selected else None,elapsed_s=row['elapsed_s'])),flush=True)
  (OUT/'search_report.json').write_text(json.dumps(dict(schema='riverstone.registered_property.access_search.v1',source_plan_sha256=a.file_sha(a.CITY/'registered_source/plan.json'),old_candidate_pack_sha256=a.file_sha(a.HERE/'resolved_placements.json'),maximum_grade=MAX_GRADE,clear_width_m=WIDTH,records=records,status='partial' if len(records)<7 else 'complete_bounded_search_not_activated'),indent=2)+'\n')
 return records
if __name__=='__main__':run()
