"""Retire only old common access ownership, restore its exact old native planes,
cut new native bearings, and close finite retaining gaps below/above native sides.
"""
from pathlib import Path
import sys,json,math,collections,time
OUT=Path(__file__).resolve().parent;RES=OUT.parent;BASE=RES.parent;sys.path.insert(0,str(BASE))
from resolve_pack import *
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.coherent_b15_r01.compose_cluster import interfaces
OUT=Path(__file__).resolve().parent;RES=OUT.parent

def write(name,d):(OUT/name).write_text(json.dumps(d,indent=2)+'\n')
def lift(p,plane):return [[v[0],terrain.common.height(plane,v),v[1]]for v in p]
def native_faces(p):
 mesh=load(ROOT/p['cache']['path']);up=[];down=[]
 for g in mesh['groups']:
  for q in g['quads']:
   ny=terrain.normal_y(q[:3]);poly=b.xform([[v[0],v[2]]for v in q],p)
   if abs(ny)<1e-9:continue
   y=q[0][1]+p['position_m'][1];row={'id':p['id']+':face:'+str(len(up)+len(down)),'polygon_xz_m':poly,'plane_y_xz_m':[0,0,y],'native_id':p['id'],'material':g['material']}
   (up if ny>0 else down).append(row)
 return up,down

def main():
 started=time.monotonic();pack=load(OUT/'resolved_native_candidate.json');base,fine=pack['placements'];projection=load(BASE/'actual_native_projection.json');old=next(p for p in projection['instances']if p['id']=='REGISTERED_LANDSCAPE:SITE_COMMON');old=dict(old,cache=projection['assets'][old['asset_key']]['cache']);ou,od=native_faces(old);bu,bd=native_faces(base);fu,fd=native_faces(fine);ou=[r for r in ou if r['plane_y_xz_m'][2]<=9+1e-8];bu=[r for r in bu if r['plane_y_xz_m'][2]<=9+1e-8];finepoly=[r['polygon_xz_m']for r in fd];allnew=[r['polygon_xz_m']for r in bd+fd];fi=geo._SpatialIndex(8)
 for i,q in enumerate(allnew):fi.add(i,q)
 scene=terrain.load_scene();window=b.rect(-304,-61,-241,-40);index=terrain.TriangleIndex(scene,[window]);restored=[]
 # Retire old source-native floor columns only where no original terrain and no
 # new actual native bearing exists. Their original top Y is the soil datum.
 for oldface in ou:
  if not geo.intersection_area(oldface['polygon_xz_m'],window)>1e-8:continue
  p=oldface['polygon_xz_m'];covered=[r['intersection_polygon_xz_m']for r in index.covering(p)if geo.polygon_area(r['polygon_xz_m'])>1e-8];cut=covered+[allnew[i]for i in fi.candidates(p)]
  for q in terrain.common.subtract([p],cut):
   if geo.polygon_area(q)>1e-8:restored.append({'id':'COMMON_OLD_NATIVE_SOIL:'+str(len(restored)),'polygon_xz_m':q,'plane_y_xz_m':oldface['plane_y_xz_m'],'retired_native_face_id':oldface['id'],'material':'ground_earth'})
 # Source footprint support uses actual old native top faces only in R7 holes.
 nativevs=[v for r in ou for tri in terrain.fan_upward(lift(r['polygon_xz_m'],r['plane_y_xz_m']))for v in tri];oldidx=terrain.TriangleIndex({'surfaces':{'retired_common_native_floor':nativevs}},[window]);support=[]
 for f in fd:
  p=f['polygon_xz_m'];covers=list(index.covering(p));claimed=[r['intersection_polygon_xz_m']for r in covers]
  for r in oldidx.covering(p):
   for q in terrain.common.subtract([r['intersection_polygon_xz_m']],claimed):
    if geo.polygon_area(q)>1e-8:covers.append(dict(r,intersection_polygon_xz_m=q));claimed.append(q)
  missing=terrain.common.subtract([p],[r['intersection_polygon_xz_m']for r in covers]);minimum=min((terrain.common.height(r['plane_y_xz_m'],q)-f['plane_y_xz_m'][2]for r in covers for q in r['intersection_polygon_xz_m']),default=-999);support.append({'native_bearing_id':f['id'],'area_m2':geo.polygon_area(p),'missing_area_m2':sum(geo.polygon_area(q)for q in missing),'minimum_embed_m':minimum,'bottom_y_m':f['plane_y_xz_m'][2]})
 edits=[];partitions=[];ni=geo._SpatialIndex(8)
 for i,p in enumerate(finepoly):ni.add(i,p)
 for r in index.rows:
  if geo.polygon_area(r['polygon_xz_m'])<=1e-8:continue
  masks=[finepoly[i]for i in ni.candidates(r['polygon_xz_m'])];outside=terrain.common.subtract([r['polygon_xz_m']],masks);a0=geo.polygon_area(r['polygon_xz_m']);ao=sum(geo.polygon_area(q)for q in outside)
  if a0-ao<1e-8:continue
  replacement=[tri for p in outside for tri in terrain.fan_upward(lift(p,r['plane_y_xz_m']))];edits.append({'material':r['material'],'triangle_index':r['triangle_index'],'source_triangle_sha256':r['source_triangle_sha256'],'replacement_triangles_xyz_m':replacement});partitions.append({'material':r['material'],'triangle_index':r['triangle_index'],'source_area_m2':a0,'retained_area_m2':ao,'new_native_cut_area_m2':a0-ao})
 # The closure context is the unchanged R7 exterior plus exact retained base
 # floor and the old-native soil pieces restored above.
 for row in bu+restored:
  for tri in terrain.fan_upward(lift(row['polygon_xz_m'],row['plane_y_xz_m'])):
   rr={'material':'retained_native_or_restored_soil','triangle_index':len(index.rows),'vertices_xyz_m':tri,'polygon_xz_m':[[v[0],v[2]]for v in tri],'plane_y_xz_m':row['plane_y_xz_m'],'source_triangle_sha256':terrain.canonical_sha(tri)};index.index.add(len(index.rows),rr['polygon_xz_m']);index.rows.append(rr)
 logical=[dict(r,action='field',kind='new_native_underside')for r in fd];closure=interfaces(scene,index,logical);ti=geo._SpatialIndex(8)
 for i,r in enumerate(fu):ti.add(i,r['polygon_xz_m'])
 walls=[];gaps=[]
 for s in closure['boundary_seams']:
  e=s['edge_xz_m'];mid=[sum(v[k]for v in e)/2 for k in(0,1)];tops=[r['plane_y_xz_m'][2]for i in ti.candidates([mid])if geo.point_in_convex_polygon(mid,(r:=fu[i])['polygon_xz_m'],1e-7)];top=max(tops,default=None)
  if top is None:continue
  lower=s['owned_y_m'];outside=s['outside_y_m'];boundary=[lower[j]if outside[j]<lower[j]else top if outside[j]>top else outside[j]for j in(0,1)]
  q=[[e[0][0],boundary[0],e[0][1]],[e[1][0],boundary[1],e[1][1]],[e[1][0],outside[1],e[1][1]],[e[0][0],outside[0],e[0][1]]]
  from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.side_clearance import area3d
  for tri in ([q[0],q[1],q[2]],[q[0],q[2],q[3]]):
   if area3d(tri)>1e-9:walls.append(tri)
  gaps.append(dict(s,native_top_y_m=top,native_side_bottom_y_m=lower,only_uncovered_vertical_gap_closed=True))
 # Native faces own their own .5 m thickness. No duplicate bank is emitted over
 # that native side span; only external soil gaps are closed.
 edits+=closure['side_surface_edits'];assert len({(r['material'],r['triangle_index'])for r in edits})==len(edits)
 append={'ground_earth':[v for r in restored for tri in terrain.fan_upward(lift(r['polygon_xz_m'],r['plane_y_xz_m']))for v in tri],'bank':[v for tri in walls for v in tri]};patch={'schema':'riverstone.finite_source_index_surface_patch.v1','id':'R8_COMMON_NATIVE_ENTRY_REPAIR_R02','status':'CANDIDATE_PENDING_WALK_AND_SOURCE_CHECKS','base_scene_sha256':terrain.SCENE_SHA256,'source_surface_hashes':{m:terrain.canonical_sha(scene['surfaces'][m])for m in {r['material']for r in edits}},'surface_edits':edits,'appended_surfaces':append,'removed_foundation_proxy_ids':[],'native_pack':ref(OUT/'resolved_native_candidate.json'),'policy':'Explicit native instance replacement; restore only retired old native top planes outside new bearings, then cut exact new native columns. Finite retained-bank fragments only; water unchanged.'};report={'native_source':ref(OUT/'resolved_native_candidate.json'),'restored_old_native_ground':restored,'new_native_undersides':fd,'new_native_upward_faces':fu,'retained_base_upward_faces':bu,'support':support,'unsupported':[r for r in support if r['missing_area_m2']>1e-7 or r['minimum_embed_m']<-.001],'source_partitions':partitions,'side_closure':closure,'actual_native_side_gap_closures':gaps,'summary':{'restored_old_native_ground_area_m2':sum(geo.polygon_area(r['polygon_xz_m'])for r in restored),'new_native_bearings':len(fd),'ground_indices':len(partitions),'bank_indices':len(closure['side_surface_edits']),'new_retaining_triangles':len(walls),'unknown_exterior_segments':len(closure['unknown_exterior_segments']),'seconds':time.monotonic()-started}}
 write('native_ground_candidate_patch.json',patch);write('native_ground_candidate_audit.json',report);print(report['summary'],'unsupported',len(report['unsupported']))
if __name__=='__main__':main()
