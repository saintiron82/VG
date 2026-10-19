"""Finite graded-earth bearing and bounded cut/fill obligations."""
import json,time,math
from .. import author as a,side_clearance
from .source_preflight import HERE,read,write

def run():
 t=time.monotonic();scene=a.load_scene();hand=read('terrain_handoff.json');owners=json.loads((HERE/'owners.json').read_bytes())['physical_owners'];oi=a.geo._SpatialIndex(16)
 for i,o in enumerate(owners):oi.add(i,o['polygon_xz_m'])
 old=a.TriangleIndex(scene,[o['polygon_xz_m']for o in owners]);native=[];fail=[]
 for parcel in hand['parcels']:
  for owner in parcel.get('native_footing_owners',[]):
   for j,p in enumerate(owner['polygons_xz_m']):
    floor=parcel['floor_y_m'];bottom=owner['native_bottom_y_m'];eligible=[o['polygon_xz_m']for i in oi.candidates(p)if(o:=owners[i])['plane_y_xz_m']==[0,0,floor]];gap=sum(a.geo.polygon_area(q)for q in a.common.subtract([p],eligible));pieces=list(old.covering(p));cut=max([max(a.common.height(r['plane_y_xz_m'],v)-floor for v in r['intersection_polygon_xz_m'])for r in pieces]+[0]);fill=max([max(floor-a.common.height(r['plane_y_xz_m'],v)for v in r['intersection_polygon_xz_m'])for r in pieces]+[0]);row=dict(id=owner['id']+':BEARING:'+str(j),polygon_xz_m=p,finished_earth_datum_m=floor,native_bottom_y_m=bottom,embedded_depth_m=floor-bottom,missing_earth_owner_m2=gap,maximum_cut_m=cut,maximum_fill_m=fill,source_ground_pieces=[dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],polygon_xz_m=r['intersection_polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'])for r in pieces]);native.append(row)
    if gap>1e-7 or floor-bottom<-1e-7:fail.append(row['id'])
 budget=[]
 for o in owners:
  if o.get('kind')=='retired_private_floor_restoration':continue
  cut=0.;fill=0.;over=[]
  for r in old.covering(o['polygon_xz_m']):
   ds=[a.common.height(r['plane_y_xz_m'],v)-a.common.height(o['plane_y_xz_m'],v)for v in r['intersection_polygon_xz_m']];cut=max(cut,*ds);fill=max(fill,*[-v for v in ds]);q=side_clearance.halfspace([[p[0],0,p[1]]for p in r['intersection_polygon_xz_m']],lambda v:a.common.height(r['plane_y_xz_m'],[v[0],v[2]])-a.common.height(o['plane_y_xz_m'],[v[0],v[2]])-2.5000001)
   if q and(a0:=a.geo.polygon_area([[v[0],v[2]]for v in q]))>1e-8:over.append(dict(area_m2=a0,polygon_xz_m=[[v[0],v[2]]for v in q],source_material=r['material'],source_triangle_index=r['triangle_index']))
  budget.append(dict(id=o['id'],maximum_cut_m=cut,maximum_fill_m=fill,cut_over_design_screen=over))
 result=dict(scene_patch_sha256=a.sha(HERE/'candidate_scene_patch.json'),native_bearings=native,failures=fail,physical_owner_budget=budget,max_native_cut_m=max(r['maximum_cut_m']for r in native),max_native_fill_m=max(r['maximum_fill_m']for r in native),maximum_field_cut_m=max(r['maximum_cut_m']for r in budget),maximum_field_fill_m=max(r['maximum_fill_m']for r in budget),support_semantics='These finite earth domains replace retired ordinary private grades and extend below the native bearing bottoms. Their exposed perimeter is closed by the exact retaining faces in interfaces.json. Terrain top faces are suppressed inside actual native footprints; no duplicate top, whole-plot hole, elevated-house origin, or new native support cache is used.',status='PASS_FINITE_EARTH_BEARING'if not fail else'FAILED',elapsed_s=time.monotonic()-t,activation=False);write('support_review_r01.json',result);print({k:v for k,v in result.items()if not isinstance(v,list)},flush=True)
if __name__=='__main__':run()
