"""Native compound unions with continuous court boundaries and real gates."""
import collections,copy
from pathlib import Path
from fit_native_buildings import assets
from plan_coverage import *
from recovered_range_factory import Source,extrusion,approved_palette,estimate_candidates,source_bounds
from world_city.concept_city_v3.assemblies.landmarks.author import Assembly

def boundary_loops(pieces):
 vertices={tuple(round(v,6)for v in p)for poly in pieces for p in poly};edges=collections.Counter()
 for poly in pieces:
  for aa,bb in zip(poly,poly[1:]+poly[:1]):
   a=tuple(round(v,6)for v in aa);b=tuple(round(v,6)for v in bb);dx,dz=b[0]-a[0],b[1]-a[1];den=dx*dx+dz*dz
   if den<1e-12:continue
   points=[]
   for p in vertices:
    t=((p[0]-a[0])*dx+(p[1]-a[1])*dz)/den
    if -1e-6<=t<=1+1e-6 and abs((p[0]-a[0])*dz-(p[1]-a[1])*dx)<1e-5*math.sqrt(den):points.append((max(0,min(1,t)),p))
   points=sorted(set(points))
   for (_,p),(_,q)in zip(points,points[1:]):
    if math.dist(p,q)>1e-6:edges[tuple(sorted((p,q)))]+=1
 remaining={e for e,n in edges.items()if n==1};loops=[]
 while remaining:
  a,b=next(iter(remaining));remaining.remove(tuple(sorted((a,b))));loop=[a,b]
  while loop[-1]!=loop[0]:
   candidates=[e for e in remaining if loop[-1]in e]
   if not candidates:raise ValueError('Open boundary at '+str(loop[-1]))
   e=min(candidates);remaining.remove(e);loop.append(e[1]if e[0]==loop[-1]else e[0])
  loops.append([list(q)for q in loop[:-1]])
 # Remove collinear subdivision points; source curve changes are forbidden.
 out=[]
 for loop in loops:
  changed=True
  while changed and len(loop)>3:
   changed=False
   for i,b in enumerate(loop):
    a=loop[i-1];c=loop[(i+1)%len(loop)]
    if geo.point_segment_distance(b,a,c)<2e-5:loop.pop(i);changed=True;break
  if geo.polygon_area(loop)>1e-4:out.append(loop)
 return sorted(out,key=geo.polygon_area,reverse=True)

def choose_gate(c,loops,buildings,roads):
 pieces=c['available_regions_xz_m'];candidates=[];existing_keepouts=[f['polygon_xz_m']for f in load(LAND)['owned_floors']]+[g['polygon_xz_m']for g in load(GARDEN)['sites']]
 def inside(p):return any(geo.point_in_convex_polygon(p,q,0)for q in pieces)
 for li,loop in enumerate(loops):
  if li>0:continue
  for edge,(a,b)in enumerate(zip(loop,loop[1:]+loop[:1])):
   length=math.dist(a,b)
   if length<8:continue
   u=[(b[j]-a[j])/length for j in(0,1)]
   for t in(.25,.5,.75):
    mid=[a[j]+(b[j]-a[j])*t for j in(0,1)];n=[-u[1],u[0]]
    if not inside([mid[0]+n[0],mid[1]+n[1]]):n=[-n[0],-n[1]]
    inner=[mid[0]+n[0]*3,mid[1]+n[1]*3];corr=geo.road_ribbon(mid,inner,4)
    if abs(sum(geo.intersection_area(corr,q)for q in pieces)-geo.polygon_area(corr))>1e-4:continue
    if any(geo.positive_area_overlap(corr,b['outer_footprint_xz_m'],0)for b in buildings):continue
    exterior=geo.road_ribbon(mid,[mid[0]-n[0]*4,mid[1]-n[1]*4],4)
    if any(geo.positive_area_overlap(exterior,p,0)for p in existing_keepouts):continue
    targets=[]
    for r in roads:
     for aa,bb in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:]):
      p,_=prop.near(aa,bb,mid);targets.append((math.dist(p,mid),r['id'],p))
    preferred={'ABBEY_EAST_SERVICE':[-247,120],'ABBEY_SOUTH_GARDEN_SERVICE':[-335,145]}.get(c['id'])
    if preferred:targets=[(math.dist(preferred,mid),'INTERNAL_APPROACH_NETWORK',preferred)]
    dist,rid,target=min(targets);candidates.append((dist,li,edge,t,mid,n,inner,rid,target))
 if not candidates:raise ValueError('No gate '+c['id'])
 _,li,edge,t,mid,n,inner,rid,target=min(candidates);return {'id':c['id']+':main_gate','loop_index':li,'edge_index':edge,'edge_t':t,'center_xz_m':mid,'inward_xz':n,'inside_xz_m':inner,'outside_xz_m':[mid[0]-n[0]*2,mid[1]-n[1]*2],'clear_width_m':4,'floor_y_m':c['finished_floor_y_m'],'public_target_id':rid,'public_target_xz_m':target,'exterior_status':'target only; exact exterior path and grade pending'}

def floor_source(c,loops,gate):
 cx,cz=c['center_xz_m'];a=Source('precinct_ground_'+c['id'],[-100,-.5,-100],[100,2.5,100])
 for i,p in enumerate(c['available_regions_xz_m']):a.plan('owned_court_'+str(i),[[x-cx,z-cz]for x,z in p],-.5,0,'stone_dark',component='ground')
 for li,loop in enumerate(loops):
  for i,(p,q)in enumerate(zip(loop,loop[1:]+loop[:1])):
   length=math.dist(p,q)
   if length<.3:continue
   u=[(q[j]-p[j])/length for j in(0,1)];mid=[(p[j]+q[j])/2 for j in(0,1)];n=[-u[1],u[0]]
   if not any(geo.point_in_convex_polygon([mid[0]+n[0]*.2,mid[1]+n[1]*.2],r,0)for r in c['available_regions_xz_m']):n=[-n[0],-n[1]]
   spans=[(0,length)]
   if li==gate['loop_index']and i==gate['edge_index']:
    center=gate['edge_t']*length;spans=[(0,center-2),(center+2,length)]
   spans=[(start+(end-start)*k/max(1,math.ceil((end-start)/8)),start+(end-start)*(k+1)/max(1,math.ceil((end-start)/8)))for start,end in spans for k in range(max(1,math.ceil((end-start)/8)))]
   for j,(start,end)in enumerate(spans):
    if end-start<.1:continue
    aa=[p[k]+u[k]*start for k in(0,1)];bb=[p[k]+u[k]*end for k in(0,1)];poly=[aa,bb,[bb[k]+n[k]*.6 for k in(0,1)],[aa[k]+n[k]*.6 for k in(0,1)]]
    a.plan(f'boundary_{li}_{i}_{j}',[[x-cx,z-cz]for x,z in poly],-.5,2.0,'stone',component='boundary')
 s=a.finish();s['provenance'].update(recovery_author=ref(Path(__file__)),revision02_prompt_status='Explicit reconstruction notice; original bytes unavailable.');return s

def main():
 plan=load(HERE/'coverage_plan.json');fit=load(HERE/'native_building_fit.json');roads=load(SOURCE)['roads'];rows=[];contracts=[]
 for c in plan['compounds']:
  buildings=[p for p in fit['placements']if p['compound_id']==c['id']];loops=boundary_loops(c['available_regions_xz_m']);gate=choose_gate(c,loops,buildings,roads);ground=floor_source(c,loops,gate);assembly=Assembly('precinct_'+c['id'],c['center_xz_m'],c['finished_floor_y_m'],c['requested_frame_xz_m']);assembly.add('court_and_boundary',ground)
  for p in buildings:
   source=load(ROOT/p['source']['path']);position=[p['position_m'][0]-c['center_xz_m'][0],p['position_m'][1]-c['finished_floor_y_m'],p['position_m'][2]-c['center_xz_m'][1]];assembly.add(p['id'].split(':')[-1],source,position,p['yaw_degrees'],roof='slate_gray'if p['role']=='school'else'clay_red',purpose=p['function'])
  s=assembly.finish();s['id']='registered_precinct_union_'+c['id'].lower();s['provenance'].update(recovered_author=ref(Path(__file__)),coverage_plan=ref(HERE/'coverage_plan.json'),native_fits=ref(HERE/'native_building_fit.json'));s['extensions'].update(real_gate=gate,existing_source_buildings=buildings,ground_domain_xz_m=c['available_regions_xz_m'],boundary_loops_xz_m=loops,finished_floor_y_m=c['finished_floor_y_m'],entire_building_scale=1);path=HERE/'masters'/f"{s['id']}.json";write(path,s);estimate=estimate_candidates(s,.5);assert estimate['candidate_cells_exact_aabb_visits']<600000,(c['id'],estimate);rows.append({'id':s['id'],'compound_id':c['id'],'source':ref(path),'estimate':estimate,'position_m':[c['center_xz_m'][0],c['finished_floor_y_m'],c['center_xz_m'][1]],'gate':gate});contracts.append({'compound_id':c['id'],'boundary_loops_xz_m':loops,'gate':gate,'logical_owned_floor_regions_xz_m':c['available_regions_xz_m'],'actual_native_floor_status':'extract after common compile','actual_building_count':len(buildings),'floor_y_m':c['finished_floor_y_m']});print(c['id'],len(loops),estimate['candidate_cells_exact_aabb_visits'],flush=True)
 write(HERE/'compound_preflight.json',{'schema':'riverstone.precinct.native_compound_preflight.v1','sources':rows,'candidate_cap_each':600000,'output_cap_each':180000,'pitch_m':.5,'sequential':True,'whole_city_compile':False});write(HERE/'finite_ground_contract.source.json',{'source_plan':ref(SOURCE),'coverage_plan':ref(HERE/'coverage_plan.json'),'compounds':contracts,'ground_policy':'Native court and all building foundations are sampled as one common solid. Actual top-face masks supersede source masks after compile. Exterior grades remain separate.'})
if __name__=='__main__':main()
