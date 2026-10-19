"""Exact finite approach unions; frozen native crossing edges remain fixed."""
import json,math
from scipy.spatial import ConvexHull
from . import select_profiles as s,finite
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a,regeneration
from world_city.runtime_city.checks import placement as g
HERE=s.HERE

def hull(points):
 pts=list(dict.fromkeys(tuple(p)for p in points));return[ list(pts[i])for i in ConvexHull(pts).vertices]
def union(polys):
 out=[]
 for p in polys:out.extend(finite.subtract([p],out))
 return out

def tail(bridge,road):
 start=[[v[0],v[2]]for v in bridge['approach_seams'][1]['xyz_m']];center=[sum(v[k]for v in start)/2 for k in(0,1)];st=s.station_at(road,center);i,_,_,_=s.section(road,st);pts=[center]+road['polyline_xz_m'][i+1:];polys=[];prev=start
 for j,(u,v)in enumerate(zip(pts,pts[1:])):
  if math.dist(u,v)<1e-8:continue
  L=math.dist(u,v);n=[-(v[1]-u[1])/L,(v[0]-u[0])/L];near=[[u[k]+sg*n[k]*road['width_m']/2 for k in(0,1)]for sg in(-1,1)];far=[[v[k]+sg*n[k]*road['width_m']/2 for k in(0,1)]for sg in(-1,1)]
  if j==0:
   sv=[start[1][k]-start[0][k]for k in(0,1)];sl=math.hypot(*sv);fv=[far[1][k]-far[0][k]for k in(0,1)];fl=math.hypot(*fv);uv=[sv[k]/sl+fv[k]/fl for k in(0,1)];ul=math.hypot(*uv);uv=[x/ul for x in uv];cosine=min(sum(uv[k]*sv[k]/sl for k in(0,1)),sum(uv[k]*fv[k]/fl for k in(0,1)));mid=[[sum((u[k],v[k]))/2+sg*uv[k]*road['width_m']/2/cosine for k in(0,1)]for sg in(-1,1)];polys.extend([hull(start+mid),hull(mid+far)])
  else:polys.extend([hull(prev+near),hull(near+far)])
  prev=far
 return polys

def full_width_profile(old):
 p=dict(old);start=[[v[0],v[2]]for v in p['deck_edge_xyz_m']];end=p['public_edge_xz_m'];W=p['road_width_m'];levels=p['longitudinal_levels'];knots=p['transverse_parameters'];units=[];centers=[]
 for t in levels:
  edge=[[(1-t)*start[j][k]+t*end[j][k]for k in(0,1)]for j in(0,1)];v=[edge[1][k]-edge[0][k]for k in(0,1)];L=math.hypot(*v);units.append([x/L for x in v]);centers.append([sum(q[k]for q in edge)/2 for k in(0,1)])
 widths=[W if j in(0,len(levels)-1)else W/min(sum(units[j][k]*units[n][k]for k in(0,1))for n in(j-1,j+1)) for j in range(len(levels))];edges=[[[centers[j][k]+sg*units[j][k]*widths[j]/2 for k in(0,1)]for sg in(-1,1)]for j in range(len(levels))];edges[0]=start;edges[-1]=end
 points=[];target=[];fixed={};Y=p['deck_edge_xyz_m'][0][1];terminal=[v[1]for v in p['public_seam_knots_xyz_m']]
 for j,t in enumerate(levels):
  for k,u in enumerate(knots):
   points.append([edges[j][0][c]+u*(edges[j][1][c]-edges[j][0][c])for c in(0,1)]);target.append(Y+t*(terminal[k]-Y))
   if j==0:fixed[len(points)-1]=Y
   if j==len(levels)-1:fixed[len(points)-1]=terminal[k]
 n=len(knots);tris=[]
 for j in range(len(levels)-1):
  for k in range(n-1):
   i=j*n+k;tris.extend([[i,i+1,i+n+1],[i,i+n+1,i+n]])
 result=regeneration.solve_field(points,tris,fixed,target)
 if result['status']!='PASSED_FINITE_TRIANGLE_GRADE':raise ValueError('Full width grade failed '+p['id'])
 proof=[]
 for j,(e,f)in enumerate(zip(edges,edges[1:])):
  u=[e[1][k]-e[0][k]for k in(0,1)];v=[f[1][k]-f[0][k]-u[k]for k in(0,1)];vv=sum(x*x for x in v);t=max(0,min(1,-sum(u[k]*v[k]for k in(0,1))/vv))if vv>1e-20 else 0.;minimum=math.hypot(*[u[k]+t*v[k]for k in(0,1)]);proof.append(dict(segment=j,minimum_full_transverse_width_m=minimum,at_parameter=t))
  if minimum<W-1e-8:raise ValueError('Width shrink '+p['id'])
 p.update(result);p['polygons_xz_m']=[finite.clean([e[0],f[0],f[1],e[1]])for e,f in zip(edges,edges[1:])];p['width_proof']=proof;p['cross_sections_xz_m']=edges;p.pop('polygon_xz_m');p.pop('old_ground');return p

def run():
 scene=a.load_scene();bridges=json.loads((HERE.parent/'crossing_interfaces.json').read_text())['crossings'];b={r['id']:r for r in bridges};roads={r['id']:r for r in json.loads((a.CITY/'registered_topography/revisions/r14_precinct_merchant/contract.json').read_text())['roads']};selected=json.loads((HERE/'profiles.json').read_text())['profiles'];profiles=[]
 keep=['MARKET_NORTH:START_APPROACH','NORTH_BACK_LANE:START_APPROACH','EAST_RADIAL:START_APPROACH','EAST_WALL_SERVICE:START_APPROACH']
 for p in selected:
  if p['id']in keep:profiles.append(full_width_profile(p))
 nraw=tail(b['MARKET_NORTH'],roads['MARKET_NORTH'])+tail(b['NORTH_BACK_LANE'],roads['NORTH_BACK_LANE']);npolys=union(nraw)
 east_end=next(p for p in selected if p['id']=='EAST_WALL_SERVICE:END_APPROACH');eredge=[[v[0],v[2]]for v in b['EAST_RADIAL']['approach_seams'][1]['xyz_m']];ewedge=[[v[0],v[2]]for v in b['EAST_WALL_SERVICE']['approach_seams'][1]['xyz_m']];eraw=[hull(eredge+ewedge+east_end['public_edge_xz_m'])]
 # Native deck rectangles retain their sole floor ownership. Any overlap of the
 # eastern turning fan with the solid bank-edge rectangle is removed exactly.
 epolys=finite.subtract(eraw,[x['native_ownership_polygon_xz_m']for x in bridges])
 for ident,polys,y,ids in [('NORTH_SHARED_JUNCTION',npolys,15.6,['MARKET_NORTH','NORTH_BACK_LANE']),('EAST_SHARED_JUNCTION',epolys,2.5,['EAST_RADIAL','EAST_WALL_SERVICE'])]:
  tris=[]
  for poly in polys:
   for t in a.fan_upward([[x,y,z]for x,z in poly]):tris.append(dict(id=ident+':T'+str(len(tris)),vertices_xyz_m=t,polygon_xz_m=[[v[0],v[2]]for v in t],plane_y_xz_m=[0,0,y],gradient=0.))
  p=dict(id=ident,bridge_ids=ids,road_ids=ids,polygons_xz_m=polys,triangles=tris,maximum_gradient=0.,fixed_deck_seams=[dict(bridge_id=rid,side=1,xyz_m=b[rid]['approach_seams'][1]['xyz_m'])for rid in ids],ownership_kind='single shared finite road junction')
  if ident=='EAST_SHARED_JUNCTION':p.update(public_seam_knots_xyz_m=east_end['public_seam_knots_xyz_m'],public_seam_source_intervals=east_end['public_seam_source_intervals'],road_id='EAST_WALL_SERVICE',public_edge_xz_m=east_end['public_edge_xz_m'],terminal_station_m=east_end['terminal_station_m'],terminal_road_segment=east_end['terminal_road_segment'])
  profiles.append(p)
 from .extend_named import expand
 expand(profiles,bridges,roads,scene)
 windows=[t['polygon_xz_m']for p in profiles for t in p['triangles']];ix=a.TriangleIndex(scene,windows);native=json.loads((a.CITY/'registered_integration/r8/coverage_plan/native_projection.json').read_text())['instances'];nativeparts=[(r['id'],p)for r in native for p in r['native_owner_parts_xz_m']]+[(r['placement_id'],r['native_ownership_polygon_xz_m'])for r in bridges];ni=g._SpatialIndex(12)
 for i,(_,p)in enumerate(nativeparts):ni.add(i,p)
 wet=[[[v[0],v[2]]for v in scene['surfaces']['water'][j:j+3]]for j in range(0,len(scene['surfaces']['water']),3)];allpolys=[];fail=[]
 for p in profiles:
  polys=p.get('polygons_xz_m',[p.get('polygon_xz_m')]);p['polygons_xz_m']=polys;p['area_m2']=sum(g.polygon_area(q)for q in polys);p['preflight']=[]
  for j,poly in enumerate(polys):
   ground=finite.audit(ix,poly);nativehits=[nativeparts[i][0]for i in ni.candidates(poly)if g.polygon_area(finite.intersect(poly,nativeparts[i][1]))>1e-7];wetarea=sum(g.polygon_area(finite.intersect(poly,q))for q in wet);overlap=sum(g.polygon_area(finite.intersect(poly,q))for q in allpolys);r=dict(piece=j,ground=ground,native_hits=nativehits,water_overlap_m2=wetarea,prior_field_overlap_m2=overlap);p['preflight'].append(r);allpolys.append(poly)
   if ground['missing_area_m2']>1e-7 or ground['excess_area_m2']>1e-6 or nativehits or wetarea>1e-7 or overlap>1e-7:fail.append(dict(id=p['id'],piece=j,missing=ground['missing_area_m2'],excess=ground['excess_area_m2'],native=nativehits,wet=wetarea,overlap=overlap))
 print('FIELD',[(p['id'],p['area_m2'],len(p['triangles']))for p in profiles],flush=True);print('FAIL',fail,flush=True)
 result=dict(schema='riverstone.water_crossing_shared_fields.r02',base_scene_sha256=a.SCENE_SHA256,source_interfaces_sha256=a.sha(HERE.parent/'crossing_interfaces.json'),source_profiles_sha256=a.sha(HERE/'profiles.json'),profiles=profiles,failures=fail,status='PREFLIGHT_PASS'if not fail else'HELD',activation=False)
 s.write('fields.json',result)
 terminals=[dict(id=p['id'],road_id=p['road_id'],road_width_m=roads[p['road_id']]['width_m'],terminal_road_segment=p['terminal_road_segment'],terminal_station_m=p['terminal_station_m'],xyz_m=p['public_seam_knots_xyz_m'],source_intervals=p['public_seam_source_intervals'])for p in profiles if 'public_seam_knots_xyz_m'in p]
 s.write('public_handoff.json',dict(schema='riverstone.water_approach_public_handoff.r02',base_scene_sha256=a.SCENE_SHA256,frozen_crossing_interfaces_sha256=a.sha(HERE.parent/'crossing_interfaces.json'),field_source_sha256=a.sha(HERE/'fields.json'),status=result['status'],exact_public_terminals=terminals,finite_field_owners=[dict(id=p['id'],polygons_xz_m=p['polygons_xz_m'])for p in profiles],native_deck_holes=[dict(id=r['placement_id'],polygon_xz_m=r['native_ownership_polygon_xz_m'],deck_top_y_m=r['deck_top_y_m'],deck_underside_y_m=r['deck_underside_y_m'])for r in bridges],policy='R18 must exclude these exact finite field/native ownership masks and fix the complete transverse terminal profiles. Only nonwalking lateral edges may receive retaining closure. Northern road tails meet only each other; their shared terminal has no third public-road continuation.',activation=False))
if __name__=='__main__':run()
