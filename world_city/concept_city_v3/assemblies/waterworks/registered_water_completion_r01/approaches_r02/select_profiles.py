"""Bounded full-width approach fields from actual R7 road cross-sections."""
import json,math,collections
from pathlib import Path
from . import finite
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a,regeneration
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.audit_retired_boundaries import interval
from world_city.concept_city_v3.assemblies.waterworks.registered_services_r01.select_drawhouses import rect
from world_city.concept_city_v3.assemblies.waterworks.registered_water_completion_r01.audit import ref
from world_city.runtime_city.checks import placement as g
HERE=Path(__file__).resolve().parent;CITY=a.CITY;ROOT=a.ROOT

def write(name,data):(HERE/name).write_text(json.dumps(data,separators=(',',':'),allow_nan=False)+'\n')
def section(road,station):
 dist=0
 for j,(u,v)in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
  L=math.dist(u,v)
  if dist+L>=station and L>1e-8:
   t=(station-dist)/L;c=[u[k]+t*(v[k]-u[k])for k in(0,1)];tan=[(v[k]-u[k])/L for k in(0,1)];normal=[-tan[1],tan[0]];return j,c,tan,[[c[k]+sign*normal[k]*road['width_m']/2 for k in(0,1)]for sign in(-1,1)]
  dist+=L
 raise ValueError('Outside road')
def station_at(road,point):
 best=None;dist=0
 for j,(u,v)in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
  L=math.dist(u,v)
  if L<1e-8:continue
  t=max(0,min(1,sum((point[k]-u[k])*(v[k]-u[k])for k in(0,1))/L**2));q=[u[k]+t*(v[k]-u[k])for k in(0,1)];r=(math.dist(q,point),dist+t*L,j)
  if best is None or r<best:best=r
  dist+=L
 return best[1]
def seam_profile(ix,edge,outward):
 spans=[]
 for i in ix.index.candidates(edge):
  r=ix.rows[i]
  if r['material']!='road':continue
  span=interval(*edge,r['polygon_xz_m'])
  if not span:continue
  t=sum(span)/2;p=[edge[0][k]+t*(edge[1][k]-edge[0][k])+outward[k]*1e-6 for k in(0,1)]
  if g.point_in_convex_polygon(p,r['polygon_xz_m'],1e-9):spans.append((span,r))
 raw=sorted({0.,1.}|{min(1,max(0,t))for span,_ in spans for t in span});knots=[]
 for t in raw:
  if not knots or t-knots[-1]>1e-7:knots.append(t)
  elif t==1:knots[-1]=1.
 votes=[];sources=[]
 for lo,hi in zip(knots,knots[1:]):
  mid=(lo+hi)/2;rs=[r for span,r in spans if span[0]-1e-9<=mid<=span[1]+1e-9]
  if not rs:return None,'missing_public_road_seam'
  vals=[[a.common.height(r['plane_y_xz_m'],[edge[0][k]+t*(edge[1][k]-edge[0][k])for k in(0,1)])for t in(lo,hi)]for r in rs]
  if any(max(v[k]for v in vals)-min(v[k]for v in vals)>1e-6 for k in(0,1)):return None,'overlapping_incompatible_public_planes'
  r=rs[0];sources.append(dict(interval=[lo,hi],material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],plane_y_xz_m=r['plane_y_xz_m']));votes.append(vals[0])
 heights=[votes[0][0]]
 for i,v in enumerate(votes):
  if abs(heights[-1]-v[0])>1e-6:return None,'discontinuous_public_seam'
  heights.append(v[1])
 if any(abs(heights[i+1]-heights[i])/(math.dist(*edge)*(knots[i+1]-knots[i]))>.12+1e-7 for i in range(len(knots)-1)):return None,'public_crossfall_above_limit'
 return dict(knots=knots,heights=heights,source_intervals=sources,xyz_m=[[edge[0][0]+t*(edge[1][0]-edge[0][0]),y,edge[0][1]+t*(edge[1][1]-edge[0][1])]for t,y in zip(knots,heights)]),'ok'
def solve(start,end,floor,profile):
 knots=profile['knots'];n=len(knots);length=math.dist([sum(p[k]for p in start)/2 for k in(0,1)],[sum(p[k]for p in end)/2 for k in(0,1)]);levels=[i/max(2,math.ceil(length/2))for i in range(max(2,math.ceil(length/2))+1)];points=[];target=[];fixed={}
 for j,t in enumerate(levels):
  for k,u in enumerate(knots):
   q=[(1-t)*(start[0][c]+u*(start[1][c]-start[0][c]))+t*(end[0][c]+u*(end[1][c]-end[0][c]))for c in(0,1)];points.append(q);target.append(floor+t*(profile['heights'][k]-floor))
   if j==0:fixed[len(points)-1]=floor
   if j==len(levels)-1:fixed[len(points)-1]=profile['heights'][k]
 tris=[]
 for j in range(len(levels)-1):
  for k in range(n-1):
   i=j*n+k;tris.extend([[i,i+1,i+n+1],[i,i+n+1,i+n]])
 result=regeneration.solve_field(points,tris,fixed,target)
 if result['status']=='PASSED_FINITE_TRIANGLE_GRADE':result.update(longitudinal_levels=levels,transverse_parameters=knots)
 return result

def run():
 scene=a.load_scene();handoff=json.loads((HERE.parent/'crossing_interfaces.json').read_text());contract=json.loads((CITY/'registered_topography/revisions/r14_precinct_merchant/contract.json').read_text());roads={r['id']:r for r in contract['roads']};windows=[rect(r['position_m'][0],r['position_m'][2],65)for r in handoff['crossings']];ix=a.TriangleIndex(scene,windows);print('indexed',len(ix.rows),flush=True);np=json.loads((CITY/'registered_integration/r8/coverage_plan/native_projection.json').read_text());native=[];ni=g._SpatialIndex(12)
 for r in np['instances']:
  for p in r['native_owner_parts_xz_m']:ni.add(len(native),p);native.append((r['id'],p))
 for r in handoff['crossings']:ni.add(len(native),r['native_ownership_polygon_xz_m']);native.append((r['placement_id'],r['native_ownership_polygon_xz_m']))
 wet=[[[v[0],v[2]]for v in scene['surfaces']['water'][j:j+3]]for j in range(0,len(scene['surfaces']['water']),3)];selected=[];rejected=[];options=[]
 for bridge in handoff['crossings']:
  road=roads[bridge['id']];center=[bridge['position_m'][0],bridge['position_m'][2]];center_station=station_at(road,center)
  for endi,sign in enumerate([-1,1]):
   start=[[v[0],v[2]]for v in bridge['approach_seams'][endi]['xyz_m']];ends=bridge['local_x_limits_m'][endi];candidates=[]
   for extension in[3,4,5,6,8,10,12,14,16,20,24,28]:
    station=center_station+ends+sign*extension
    try:j,terminal,tangent,end=section(road,station)
    except ValueError:continue
    poly=a.common.clean([start[0],end[0],end[1],start[1]]);reason=None
    if not poly or not g.is_convex_polygon(poly):reason='nonconvex_approach'
    elif any(g.polygon_area(g.convex_intersection(poly,p))>1e-7 for p in wet):reason='water_contact'
    else:
     hits=sorted(set(native[i][0]for i in ni.candidates(poly)if g.polygon_area(g.convex_intersection(poly,native[i][1]))>1e-7))
     if hits:reason='native_contact:'+','.join(hits)
    if reason:rejected.append(dict(id=bridge['id'],side=sign,extension=extension,reason=reason));continue
    ground=finite.audit(ix,poly)
    if ground['missing_area_m2']>1e-7 or ground['excess_area_m2']>1e-6:rejected.append(dict(id=bridge['id'],side=sign,extension=extension,reason='actual_ground_coverage',missing=ground['missing_area_m2'],excess=ground['excess_area_m2']));continue
    seam,reason=seam_profile(ix,end,[sign*v for v in tangent])
    if not seam:rejected.append(dict(id=bridge['id'],side=sign,extension=extension,reason=reason));continue
    solution=solve(start,end,bridge['deck_top_y_m'],seam)
    if solution['status']!='PASSED_FINITE_TRIANGLE_GRADE':rejected.append(dict(id=bridge['id'],side=sign,extension=extension,reason='grade_infeasible'));continue
    overlaps=[]
    for prior in selected:
     q=g.convex_intersection(poly,prior['polygon_xz_m'])
     if g.polygon_area(q)>1e-7:
      # Flat co-level public junctions can be composed once with explicit ownership.
      flat=all(abs(t['plane_y_xz_m'][0])+abs(t['plane_y_xz_m'][1])<1e-8 for t in solution['triangles']+prior['triangles']);same=abs(solution['heights_m'][0]-prior['heights_m'][0])<1e-7
      if not(flat and same):reason='nonflat_prior_approach_overlap';break
      overlaps.append(dict(other_id=prior['id'],area_m2=g.polygon_area(q)))
    if reason=='nonflat_prior_approach_overlap':rejected.append(dict(id=bridge['id'],side=sign,extension=extension,reason=reason));continue
    solution.update(id=bridge['id']+(':START_APPROACH'if sign<0 else':END_APPROACH'),bridge_id=bridge['id'],bridge_placement_id=bridge['placement_id'],side=sign,road_id=road['id'],road_width_m=road['width_m'],terminal_road_segment=j,terminal_station_m=station,terminal_center_xz_m=terminal,polygon_xz_m=poly,deck_edge_xyz_m=bridge['approach_seams'][endi]['xyz_m'],public_edge_xz_m=end,public_seam_knots_xyz_m=seam['xyz_m'],public_seam_source_intervals=seam['source_intervals'],old_ground=ground,flat_same_height_overlap=overlaps,extension_beyond_native_edge_m=extension)
    candidates.append(solution)
   if not candidates:print('NO FIT',bridge['id'],sign,flush=True)
   else:
    chosen=candidates[0];selected.append(chosen);print('SELECT',chosen['id'],chosen['extension_beyond_native_edge_m'],chosen['maximum_gradient'],len(chosen['public_seam_knots_xyz_m']),flush=True)
   options.append(dict(id=bridge['id'],side=sign,passing_candidates=len(candidates)))
 write('profiles.json',dict(schema='riverstone.water_crossing_approaches.r02',base_scene=ref(a.SCENE_PATH),frozen_crossing_interfaces=ref(HERE.parent/'crossing_interfaces.json'),profiles=selected,options=options,rejected=rejected,status='ALL_EIGHT_PROFILES_SOLVED'if len(selected)==8 else'PARTIAL_PROFILE_SELECTION',activation=False));print('selected',len(selected),flush=True)
if __name__=='__main__':run()
