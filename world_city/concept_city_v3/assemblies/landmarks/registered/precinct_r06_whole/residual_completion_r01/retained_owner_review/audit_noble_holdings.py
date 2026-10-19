"""Read-only native noble use and exact owned-route audit; no labels imply completion."""
from pathlib import Path
import sys,json,time,math,collections
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE))
from resolve_pack import *
OUT=Path(__file__).resolve().parent
class NativeFirst:
 def __init__(self,scene,windows,vs):self.native=terrain.TriangleIndex({'surfaces':{'actual_noble_native_floor':vs}},windows);self.ground=terrain.TriangleIndex(scene,windows)
 def covering(self,p):
  used=[]
  for ix in(self.native,self.ground):
   for r in sorted(ix.covering(p),key=lambda r:max(terrain.common.height(r['plane_y_xz_m'],q)for q in r['intersection_polygon_xz_m']),reverse=True):
    if geo.polygon_area(r['polygon_xz_m'])<=1e-8:continue
    for q in terrain.common.subtract([r['intersection_polygon_xz_m']],used):
     if geo.polygon_area(q)>1e-8:yield dict(r,intersection_polygon_xz_m=q);used.append(q)
def main():
 t=time.monotonic();src=CITY/'assemblies/property/registered/r1/resolved_placements.json';pack=load(src);scene=terrain.load_scene();sides=SideIndex(scene);rows=[];cache={}
 for own in pack['ownership_masks']:
  eid=own['property_id'];floor=own['floor_y_m'];placements=[p for p in pack['placements']if p['property_id']==eid];routes=[r for r in pack['internal_routes']if r['id'].startswith(eid+':')];external=next(r for r in pack['external_access_surfaces']if r['property_id']==eid);vs=[];bodies=[];refs=[];flatparts=[]
  for p in placements:
   cp=Path(p['compiled_asset_ref']);cp=cp if cp.is_absolute()else ROOT/cp
   if cp not in cache:cache[cp]=load(cp)
   mesh=cache[cp];refs.append(dict(id=p['id'],cache=ref(cp),render_hash_matches=sha(cp)==p['render_sha256'],role=p['role']))
   # Exact local floor plus lower graded access tops. Wall/roof tops excluded.
   for g in mesh['groups']:
    for q in g['quads']:
     if not all(abs(v[1]-q[0][1])<1e-8 for v in q)or terrain.normal_y(q[:3])<=0:continue
     wy=q[0][1]+p['position_m'][1]
     if not floor-4<=wy<=floor+1e-5:continue
     poly=b.xform([[v[0],v[2]]for v in q],p)
     for tri in terrain.fan_upward([[x,wy,z]for x,z in poly]):vs.extend(tri)
     if abs(wy-floor)<1e-7:flatparts.append(poly)
   bodies.extend(dict(id=p['id'],polygon_xz_m=b.xform(q,p))for q in slab_rectangles(mesh,floor-p['position_m'][1]+.01,floor-p['position_m'][1]+2.2))
  windows=[q for r in routes for q in r['ribbon_polygons_xz_m']]+external['polygon_regions_xz_m'];idx=NativeFirst(scene,windows,vs);bi=geo._SpatialIndex(8)
  for i,p in enumerate(bodies):bi.add(i,p['polygon_xz_m'])
  rr=[]
  for r in routes:
   checks=[terrain.audit_polygon(idx,q,floor)for q in r['ribbon_polygons_xz_m']];hits=[]
   for q in r['ribbon_polygons_xz_m']:
    for i in bi.candidates(q):
     ar=geo.intersection_area(q,bodies[i]['polygon_xz_m'])
     if ar>1e-7:hits.append(dict(id=bodies[i]['id'],area_m2=ar))
   sc=sides.audit([dict(id=r['id'],polygon_xz_m=q,floor_y_m=floor)for q in r['ribbon_polygons_xz_m']]);rr.append(dict(id=r['id'],passes=all(c['passes_existing_surface']for c in checks)and not hits and not sc['contacts'],missing_m2=sum(c['missing_area_m2']for c in checks),max_floor_delta_m=max(c['max_floor_delta_m']for c in checks),native_contacts=hits,bank_contacts=sc['contacts']))
  er=[]
  for q in external['polygon_regions_xz_m']:
   c=terrain.audit_polygon(idx,q,None);pieces=c['source_pieces'];jumps=[]
   for a in pieces:
    for p in a['polygon_xz_m']:
     ys=[terrain.common.height(v['plane_y_xz_m'],p)for v in pieces if geo.point_in_convex_polygon(p,v['polygon_xz_m'],1e-7)]
     if ys and max(ys)-min(ys)>.15+1e-7:jumps.append(dict(point_xz_m=p,jump_m=max(ys)-min(ys)))
   er.append(dict(missing_m2=c['missing_area_m2'],excess_m2=c['excess_area_m2'],max_actual_grade=c['max_actual_triangle_grade'],jump_failures=jumps,source_pieces=pieces))
  row=dict(owner_id=eid,exclusive_source_polygon_xz_m=own['polygon_xz_m'],floor_y_m=floor,actual_native_placements=len(placements),actual_facilities_by_role=dict(collections.Counter(p['role']for p in placements)),actual_native_refs=refs,internal_routes=rr,external_actual_profile=er,internal_routes_pass=sum(r['passes']for r in rr),public_entry_status='Actual sampled gate/road interface and named onward continuation require R18/controller closure; original analytic ramp is not acceptance.',complete=False);rows.append(row);print(eid,'internal',row['internal_routes_pass'],'/',len(rr),'external missing',sum(r['missing_m2']for r in er),'jumps',sum(len(r['jump_failures'])for r in er),flush=True)
 report=dict(source=ref(src),scene=ref(terrain.SCENE_PATH),owners=rows,summary=dict(owners=len(rows),actual_native_placements=sum(r['actual_native_placements']for r in rows),internal_routes=sum(len(r['internal_routes'])for r in rows),internal_routes_pass=sum(r['internal_routes_pass']for r in rows),seconds=time.monotonic()-t),scope='Read-only exact retained native use, paths and actual entrance profiles. No whole-owner completion from source labels or source analytical ramps.');(OUT/'noble_native_use_and_access.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
