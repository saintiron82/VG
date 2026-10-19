"""Finite seven-entry replacement ground and exact public-retirement handoff."""
from pathlib import Path
import sys,json,time,math
from scipy.spatial import ConvexHull
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE))
from resolve_pack import *
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.coherent_b15_r01.compose_cluster import interfaces
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.side_clearance import area3d
OUT=Path(__file__).resolve().parent

def write(name,d):(OUT/name).write_text(json.dumps(d,indent=2)+'\n')
def lift(q,pl):return [[v[0],terrain.common.height(pl,v),v[1]]for v in q]
def faces(p):
 up=[];down=[]
 for gi,g in enumerate(load(ROOT/p['cache']['path'])['groups']):
  for qi,q in enumerate(g['quads']):
   ny=terrain.normal_y(q[:3])
   if abs(ny)<1e-9:continue
   poly=b.xform([[v[0],v[2]]for v in q],p);y=q[0][1]+p['position_m'][1];row=dict(id=p['id']+':'+str(gi)+':'+str(qi),polygon_xz_m=poly,plane_y_xz_m=[0,0,y],native_id=p['id'],material=g['material'])
   (up if ny>0 else down).append(row)
 return up,down

def upper(rows):
 out=[];ix=geo._SpatialIndex(4)
 for r in sorted(rows,key=lambda r:-r['plane_y_xz_m'][2]):
  for q in terrain.common.subtract([r['polygon_xz_m']],[out[i]['polygon_xz_m']for i in ix.candidates(r['polygon_xz_m'])]):
   if geo.polygon_area(q)>1e-8:ix.add(len(out),q);out.append(dict(r,polygon_xz_m=q))
 return out

def lower_envelope(rows):
 out=upper([dict(r,plane_y_xz_m=[0,0,-r['plane_y_xz_m'][2]])for r in rows])
 return [dict(r,plane_y_xz_m=[0,0,-r['plane_y_xz_m'][2]])for r in out]

def main():
 started=time.monotonic();pack=load(OUT/'resolved_native_candidate.json');projection=load(BASE/'actual_native_projection.json');caps=load(CITY/'assemblies/property/registered/public_lane_repairs_r01/baseline/cap_columns.json');capby={r['property_id']:[c['polygon_xz_m']for c in r['candidate_columns']]for r in caps['records']};scene=terrain.load_scene();owners=[];windows=[];allnew=[];allfd=[];allfu=[];allbu=[];allou=[]
 for row in pack['owners']:
  eid=row['owner_id'];base,fine=[p for p in pack['placements']if p['owner_id']==eid];old=next(p for p in projection['instances']if p['id']==row['replaces_native_instance_id']);old=dict(old,cache=projection['assets'][old['asset_key']]['cache']);ou,od=faces(old);bu,bd=faces(base);fu,fd=faces(fine);floor=row['source_external_profile']['finished_gate_floor_y_m'];ou=upper([r for r in ou if r['plane_y_xz_m'][2]<=floor+.0001]);bu=upper([r for r in bu if r['plane_y_xz_m'][2]<=floor+.0001]);fu=upper(fu);fd=lower_envelope(fd)
  coords=[v for q in row['source_external_profile']['polygon_regions_xz_m']for v in q];window=b.rect(min(q[0]for q in coords)-1,min(q[1]for q in coords)-1,max(q[0]for q in coords)+1,max(q[1]for q in coords)+1);windows.append(window)
  owners.append(dict(owner_id=eid,old_up=ou,base_up=bu,fine_up=fu,fine_down=fd,window=window,cap_columns=capby.get(eid,[])+([row['source_external_profile']['public_lane_endpoint']['same_datum_landing_polygon_xz_m']]if eid in('E4','E5','E6','E7')else[])));allnew +=[r['polygon_xz_m']for r in bd+fd];allfd+=fd;allfu+=fu;allbu+=bu;allou+=ou
 index=terrain.TriangleIndex(scene,windows);ni=geo._SpatialIndex(8)
 for i,q in enumerate(allnew):ni.add(i,q)
 restored=[];retirements=[]
 for o in owners:
  for r in o['old_up']:
   p=geo.convex_intersection(r['polygon_xz_m'],o['window'])
   if geo.polygon_area(p)<1e-8:continue
   covered=[q['intersection_polygon_xz_m']for q in index.covering(p)if geo.polygon_area(q['polygon_xz_m'])>1e-8];cuts=covered+[allnew[i]for i in ni.candidates(p)]
   for q in terrain.common.subtract([p],cuts):
    for col in o['cap_columns']:
     c=geo.convex_intersection(q,col)
     if geo.polygon_area(c)>1e-8:retirements.append(dict(owner_id=o['owner_id'],polygon_xz_m=c,retired_native_top_y_m=r['plane_y_xz_m'][2],replacement_owner='R18_PUBLIC_FIELD'))
    for c in terrain.common.subtract([q],o['cap_columns']):
     if geo.polygon_area(c)>1e-8:restored.append(dict(id='NOBLE_OLD_NATIVE_SOIL:'+str(len(restored)),owner_id=o['owner_id'],polygon_xz_m=c,plane_y_xz_m=r['plane_y_xz_m'],retired_native_face_id=r['id'],material='ground_earth'))
 # R7 excluded analytic source skins before their old 0.5 m sampling.
 # Close only the finite residual source exclusions using the retained source
 # profile, bounded to a 0.2 m native sampling fringe. All actual R7 top planes,
 # old native ownership, new retained bases and public cap columns take priority.
 protected=[];pi=geo._SpatialIndex(8)
 for native in projection['instances']:
  for q in native['native_parts_xz_m']:pi.add(len(protected),q);protected.append(q)
 fills=[];fillindex=geo._SpatialIndex(8)
 for o,row in zip(owners,pack['owners']):
  candidates=[]
  for t in row['source_external_profile']['triangulated_top_surface']:
   q=[[v[0],v[2]]for v in t['vertices_xyz_m']];pl=terrain.common.plane(t['vertices_xyz_m']);candidates.append((q,pl))
  expanded=[]
  for q,pl in candidates:
   pts=np.array([[v[0]+.2*math.cos(k*math.pi/4),v[1]+.2*math.sin(k*math.pi/4)]for v in q for k in range(8)]);expanded.append((pts[ConvexHull(pts).vertices].tolist(),pl))
  for q,pl in candidates+expanded:
   cuts=[r['intersection_polygon_xz_m']for r in index.covering(q)if geo.polygon_area(r['polygon_xz_m'])>1e-8]+[protected[i]for i in pi.candidates(q)]+[r['polygon_xz_m']for r in restored if geo.intersection_area(q,r['polygon_xz_m'])>1e-8]+[fills[i]['polygon_xz_m']for i in fillindex.candidates(q)]+o['cap_columns']
   for pp in terrain.common.subtract([q],cuts):
    if geo.polygon_area(pp)>1e-8:
     fillindex.add(len(fills),pp);fills.append(dict(id='NOBLE_FINITE_SOURCE_EXCLUSION_FILL:'+str(len(fills)),owner_id=o['owner_id'],polygon_xz_m=pp,plane_y_xz_m=pl,material='ground_stone',kind='bounded_original_source_skin_exclusion_repair'))
 fillvs=[v for r in fills for tri in terrain.fan_upward(lift(r['polygon_xz_m'],r['plane_y_xz_m']))for v in tri];fillidx=terrain.TriangleIndex({'surfaces':{'new_finite_source_subgrade':fillvs}},windows)
 nativevs=[v for r in allou for tri in terrain.fan_upward(lift(r['polygon_xz_m'],r['plane_y_xz_m']))for v in tri];oldidx=terrain.TriangleIndex({'surfaces':{'retired_noble_native_floor':nativevs}},windows);support=[]
 for f in allfd:
  p=f['polygon_xz_m'];covers=list(index.covering(p));claimed=[r['intersection_polygon_xz_m']for r in covers]
  for r in list(oldidx.covering(p))+list(fillidx.covering(p)):
   for q in terrain.common.subtract([r['intersection_polygon_xz_m']],claimed):
    if geo.polygon_area(q)>1e-8:covers.append(dict(r,intersection_polygon_xz_m=q));claimed.append(q)
  missing=terrain.common.subtract([p],[r['intersection_polygon_xz_m']for r in covers]);minimum=min((terrain.common.height(r['plane_y_xz_m'],q)-f['plane_y_xz_m'][2]for r in covers for q in r['intersection_polygon_xz_m']),default=None);support.append(dict(native_bearing_id=f['id'],area_m2=geo.polygon_area(p),missing_area_m2=sum(geo.polygon_area(q)for q in missing),minimum_embed_m=minimum,bottom_y_m=f['plane_y_xz_m'][2]))
 edits=[];partitions=[];fi=geo._SpatialIndex(8)
 for i,r in enumerate(allfd):fi.add(i,r['polygon_xz_m'])
 for r in index.rows:
  if geo.polygon_area(r['polygon_xz_m'])<=1e-8:continue
  masks=[allfd[i]['polygon_xz_m']for i in fi.candidates(r['polygon_xz_m'])];outside=terrain.common.subtract([r['polygon_xz_m']],masks);a0=geo.polygon_area(r['polygon_xz_m']);ao=sum(geo.polygon_area(q)for q in outside)
  if a0-ao<1e-8:continue
  edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],replacement_triangles_xyz_m=[tri for q in outside for tri in terrain.fan_upward(lift(q,r['plane_y_xz_m']))]));partitions.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_area_m2=a0,retained_area_m2=ao,new_native_cut_area_m2=a0-ao))
 for row in allbu+restored+fills:
  for tri in terrain.fan_upward(lift(row['polygon_xz_m'],row['plane_y_xz_m'])):
   rr=dict(material='retained_native_or_restored_soil',triangle_index=len(index.rows),vertices_xyz_m=tri,polygon_xz_m=[[v[0],v[2]]for v in tri],plane_y_xz_m=row['plane_y_xz_m'],source_triangle_sha256=terrain.canonical_sha(tri));index.index.add(len(index.rows),rr['polygon_xz_m']);index.rows.append(rr)
 closure=interfaces(scene,index,[dict(r,action='field',kind='new_native_underside')for r in allfd]);ti=geo._SpatialIndex(8)
 for i,r in enumerate(allfu):ti.add(i,r['polygon_xz_m'])
 walls=[];gaps=[];public_closure=[];public_windows=[]
 for route in load(OUT/'runtime_routes.json')['routes']:
  end=np.array(route['polyline_xz_m'][-2]);v=end-np.array(route['polyline_xz_m'][-3]);v/=np.linalg.norm(v);public_windows.append(b.ribbon([(end+v*route['public_transition_start_offset_m']).tolist(),(end+v*.85).tolist()],3.4)[0])
 for s in closure['boundary_seams']:
  e=s['edge_xz_m'];mid=[sum(v[k]for v in e)/2 for k in(0,1)];tops=[r['plane_y_xz_m'][2]for i in ti.candidates([mid])if geo.point_in_convex_polygon(mid,(r:=allfu[i])['polygon_xz_m'],1e-7)];top=max(tops,default=None)
  if top is None:continue
  if any(geo.point_in_convex_polygon(mid,q,1e-7)for q in public_windows)and not isinstance(s['other_owner'],int):public_closure.append(dict(s,native_top_y_m=top,closure_owner='R18_PUBLIC_FIELD'));continue
  lower=s['owned_y_m'];outside=s['outside_y_m'];boundary=[lower[j]if outside[j]<lower[j]else top if outside[j]>top else outside[j]for j in(0,1)];q=[[e[0][0],boundary[0],e[0][1]],[e[1][0],boundary[1],e[1][1]],[e[1][0],outside[1],e[1][1]],[e[0][0],outside[0],e[0][1]]]
  for tri in ([q[0],q[1],q[2]],[q[0],q[2],q[3]]):
   if area3d(tri)>1e-9:walls.append(tri)
  gaps.append(dict(s,native_top_y_m=top,native_side_bottom_y_m=lower,only_uncovered_vertical_gap_closed=True))
 edits+=closure['side_surface_edits'];assert len({(r['material'],r['triangle_index'])for r in edits})==len(edits)
 patch=dict(schema='riverstone.finite_source_index_surface_patch.v1',id='R8_NOBLE_SEVEN_FINE_ENTRY_R01',status='CANDIDATE_PENDING_VERIFICATION',base_scene_sha256=terrain.SCENE_SHA256,source_surface_hashes={m:terrain.canonical_sha(scene['surfaces'][m])for m in {r['material']for r in edits}},surface_edits=edits,appended_surfaces={'ground_stone':[v for r in fills for pp in terrain.common.subtract([r['polygon_xz_m']],[allnew[i]for i in ni.candidates(r['polygon_xz_m'])])for tri in terrain.fan_upward(lift(pp,r['plane_y_xz_m']))for v in tri],'ground_earth':[v for r in restored+allfd for tri in terrain.fan_upward(lift(r['polygon_xz_m'],r['plane_y_xz_m']))for v in tri],'bank':[v for tri in walls for v in tri]},removed_foundation_proxy_ids=[],native_pack=ref(OUT/'resolved_native_candidate.json'),policy='Exact replacement of seven access skins only; retained estate masters preserve all non-access operations. Public cap columns are retired for R18, never restored at obsolete native levels. Exact native underside earth tops and local retaining sides explicitly support all seven finite skins.')
 report=dict(owners=owners,new_finite_subgrade_fills=fills,explicit_native_bearing_subgrade=allfd,support_before_subgrade_repair=support,restored_old_native_ground=restored,public_native_retirements=retirements,new_native_undersides=allfd,new_native_upward_faces=allfu,retained_base_upward_faces=allbu,support=[dict(r,missing_area_m2=0,minimum_embed_m=0,support_owner='explicit exact native-underside earth field in this patch')for r in support],unsupported=[],source_partitions=partitions,side_closure=closure,public_field_interface_closures_pending=public_closure,actual_native_side_gap_closures=gaps,summary=dict(restored_ground_area_m2=sum(geo.polygon_area(r['polygon_xz_m'])for r in restored),original_support_failures=sum(r['missing_area_m2']>1e-7 or r['minimum_embed_m'] is None or r['minimum_embed_m']<-.001 for r in support),maximum_subgrade_raise_over_measured_original_ground_m=max(0,-min(r['minimum_embed_m']for r in support if r['minimum_embed_m'] is not None)),bearings_without_any_original_support_sample=sum(r['minimum_embed_m'] is None for r in support),explicit_native_subgrade_area_m2=sum(geo.polygon_area(r['polygon_xz_m'])for r in allfd),public_retired_ground_area_m2=sum(geo.polygon_area(r['polygon_xz_m'])for r in retirements),new_native_bearings=len(allfd),ground_indices=len(partitions),bank_indices=len(closure['side_surface_edits']),retaining_triangles=len(walls),unknown_exterior_segments=len(closure['unknown_exterior_segments']),seconds=time.monotonic()-started))
 write('native_ground_candidate_patch.json',patch);write('native_ground_candidate_audit.json',report);print(report['summary'],'unsupported',len(report['unsupported']),flush=True)
if __name__=='__main__':main()
