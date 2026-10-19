"""Absorb finite original named-road side wedges into the same traffic field."""
import math
from . import finite,select_profiles as s
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a,regeneration
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.public_tails import circle
from world_city.runtime_city.checks import placement as g

def inside(p,poly,tol=1e-8):
 sign=1 if g.signed_polygon_area(poly)>0 else-1
 return all(sign*g._cross(u,v,p)/math.dist(u,v)>=-tol for u,v in zip(poly,poly[1:]+poly[:1])if math.dist(u,v)>1e-10)
def mask(road,bridge,side,outer=None):
 line=road['polyline_xz_m'];edge=[[v[0],v[2]]for v in bridge['approach_seams'][0 if side<0 else 1]['xyz_m']];center=[sum(v[k]for v in edge)/2 for k in(0,1)];st=s.station_at(road,center);j,_,tan,_=s.section(road,st);out=[]
 lo=0 if side<0 else j;hi=j+1 if side<0 else len(line)-1
 if outer is not None:
  oi,_,_,_=s.section(road,outer);lo=min(j,oi);hi=max(j,oi)+1
 polys=[g.road_ribbon(line[i],line[i+1],road['width_m'])for i in range(lo,hi)if math.dist(line[i],line[i+1])>1e-8]+[circle(line[i],road['width_m']/2)for i in range(max(1,lo),min(len(line)-1,hi+1))]
 # Exact native seam halfplane points away from the deck; the outer terminal
 # halfplane retains only the local interval and excludes all continuing road.
 normal=[side*math.cos(bridge['yaw_rad']),-side*math.sin(bridge['yaw_rad'])]
 if outer is not None:_,oc,ot,oe=s.section(road,outer)
 for p in polys:
  p=finite.half(p,lambda v:sum((v[k]-center[k])*normal[k]for k in(0,1)))
  if p and outer is not None:p=finite.half(p,lambda v:-side*sum((v[k]-oc[k])*ot[k]for k in(0,1)))
  if p:out.append(p)
 return out

def expand(profiles,bridges,roads,scene):
 bs={b['id']:b for b in bridges};holes=[b['native_ownership_polygon_xz_m']for b in bridges];allpoly=[q for p in profiles for q in p['polygons_xz_m']];windows=[s.rect(b['position_m'][0],b['position_m'][2],65)for b in bridges];ix=a.TriangleIndex(scene,windows)
 for p in profiles:
  if p['id']=='NORTH_SHARED_JUNCTION':sem=[q for rid in p['road_ids']for q in mask(roads[rid],bs[rid],1)]
  elif p['id'].endswith(':START_APPROACH'):sem=mask(roads[p['road_id']],bs[p['road_id']],-1,p['terminal_station_m'])
  else:continue
  wedges=[]
  for q in sem:wedges.extend(finite.subtract([q],holes+allpoly+wedges))
  wedges=[q for q in wedges if g.polygon_area(q)>1e-8];p['named_road_semantic_parts_xz_m']=sem;p['named_road_added_wedge_area_m2']=sum(g.polygon_area(q)for q in wedges)
  if not wedges:continue
  if p['id']=='NORTH_SHARED_JUNCTION':
   tris=[dict(vertices_xyz_m=t,polygon_xz_m=[[v[0],v[2]]for v in t],plane_y_xz_m=[0,0,15.6],gradient=0.)for q in wedges for t in a.fan_upward([[x,15.6,z]for x,z in q])]
  else:
   base=p['triangles'];global_knots=[v for q in wedges for v in q]
   for q in wedges:
    for u,v in zip(q,q[1:]+q[:1]):
     for t in base:
      span=finite.interval(u,v,t['polygon_xz_m'])
      if span:global_knots.extend([[u[k]+w*(v[k]-u[k])for k in(0,1)]for w in span])
   vertices=[];ids={};fixed={};target=[];triangles=[]
   terminal=p['public_edge_xz_m'];tl=math.dist(*terminal)
   def add(v):
    key=tuple(round(x,9)for x in v)
    if key in ids:return ids[key]
    i=len(vertices);ids[key]=i;vertices.append(v);values=[a.common.height(t['plane_y_xz_m'],v)for t in base if inside(v,t['polygon_xz_m'])]
    if values:
     if max(values)-min(values)>1e-6:raise ValueError('Fixed wedge join mismatch')
     fixed[i]=values[0];y=values[0]
    else:
     nearest=min(base,key=lambda t:min(g.point_segment_distance(v,u,w)for u,w in zip(t['polygon_xz_m'],t['polygon_xz_m'][1:]+t['polygon_xz_m'][:1])));y=a.common.height(nearest['plane_y_xz_m'],v)
    if abs(g._cross(*terminal,v)/tl)<1e-7:
     rows=[ix.rows[j]for j in ix.index.candidates([v])if inside(v,ix.rows[j]['polygon_xz_m'],1e-8)];ys=[a.common.height(r['plane_y_xz_m'],v)for r in rows]
     if not ys or max(ys)-min(ys)>1e-6:raise ValueError('Expanded terminal source incompatible')
     if i in fixed and abs(fixed[i]-ys[0])>1e-6:raise ValueError('Expanded terminal mismatch')
     fixed[i]=ys[0];y=ys[0]
    target.append(y);return i
   for q in wedges:
    boundary=[]
    for u,v in zip(q,q[1:]+q[:1]):
     L=math.dist(u,v);knots=[(0,u)]
     for w in global_knots:
      if g.point_segment_distance(w,u,v)<1e-8:
       t=sum((w[k]-u[k])*(v[k]-u[k])for k in(0,1))/L**2
       if 1e-8<t<1-1e-8:knots.append((t,w))
     for j in range(1,math.ceil(L)):
      t=j/math.ceil(L);knots.append((t,[u[k]+t*(v[k]-u[k])for k in(0,1)]))
     for _,w in sorted(knots,key=lambda x:x[0]):
      ident=add(w)
      if not boundary or boundary[-1]!=ident:boundary.append(ident)
    center=add([sum(v[k]for v in q)/len(q)for k in(0,1)])
    for u,v in zip(boundary,boundary[1:]+boundary[:1]):
     if g.polygon_area([vertices[center],vertices[u],vertices[v]])>1e-10:triangles.append([center,u,v])
   result=regeneration.solve_field(vertices,triangles,fixed,target)
   if result['status']!='PASSED_FINITE_TRIANGLE_GRADE':raise ValueError('Named wedge solve failed '+p['id']+' '+result['status'])
   tris=result['triangles'];p['named_road_wedge_solver']=dict(status=result['status'],maximum_gradient=result['maximum_gradient'],maximum_fixed_error_m=result['maximum_fixed_error_m'],vertices=len(vertices),fixed_vertices=len(fixed))
  p['polygons_xz_m'].extend(wedges);p['triangles'].extend(tris);p['maximum_gradient']=max(t['gradient']for t in p['triangles']);allpoly.extend(wedges)
  print('NAMED WEDGES',p['id'],len(wedges),p['named_road_added_wedge_area_m2'],len(tris),flush=True)
