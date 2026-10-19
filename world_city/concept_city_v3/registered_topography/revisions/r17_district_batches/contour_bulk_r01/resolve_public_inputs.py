"""Bind released R18 faces and unchanged actual faces on retained frontages."""
import json,math,time,collections
from .screen import HERE,write
from .. import author as a
from ..audit_retired_boundaries import interval
SOURCE=a.HERE.parent/'public_corridors_r18/frontage_profiles_r01.json'
SHA='bbadfd072c9142b1fcefbdc854b53f5b0e5cb6577fe4cfd58c99c77b5d82bdd9'

def seam_check(regions):
 idx=a.geo._SpatialIndex(2)
 for i,r in enumerate(regions):idx.add(i,r['polygon_xz_m'])
 errors=[];seen=set()
 for i,r in enumerate(regions):
  poly=r['polygon_xz_m']
  for p,q in zip(poly,poly[1:]+poly[:1]):
   if math.dist(p,q)<1e-8:continue
   for j in idx.candidates([p,q]):
    if j<=i:continue
    s=regions[j];sp=interval(p,q,s['polygon_xz_m'])
    if not sp or(sp[1]-sp[0])*math.dist(p,q)<1e-7:continue
    edge=[[p[k]+t*(q[k]-p[k])for k in(0,1)]for t in sp];delta=max(abs(a.common.height(r['plane_y_xz_m'],x)-a.common.height(s['plane_y_xz_m'],x))for x in edge)
    if delta>1e-6:
     key=(i,j,tuple(tuple(round(v,8)for v in x)for x in edge))
     if key not in seen:seen.add(key);errors.append(dict(left_region_id=r['id'],right_region_id=s['id'],edge_xz_m=edge,maximum_height_error_m=delta))
 return errors

def run():
 start=time.monotonic();assert a.sha(SOURCE)==SHA;src=json.loads(SOURCE.read_bytes());scene=a.load_scene();windows=[p for r in src['entries']for p in r['outside_r18_polygons_xz_m']];index=a.TriangleIndex(scene,windows);result=[]
 for r in src['entries']:
  regions=[dict(x,source_kind='released_r18_profile')for x in r['profile_regions']];gaps=[];steep=[];area=0.
  for j,p in enumerate(r['outside_r18_polygons_xz_m']):
   ps=list(index.covering(p));uncovered=a.common.subtract([p],[x['intersection_polygon_xz_m']for x in ps]);gaps.extend(uncovered)
   for k,x in enumerate(ps):
    q=x['intersection_polygon_xz_m'];g=math.hypot(*x['plane_y_xz_m'][:2]);entry=dict(id=r['holding_id']+':RETAINED:'+str(j)+':'+str(k),source_kind='actual_retained_r7_top',source_material=x['material'],source_triangle_index=x['triangle_index'],source_triangle_sha256=x['source_triangle_sha256'],polygon_xz_m=q,plane_y_xz_m=x['plane_y_xz_m'],triangles_xyz_m=list(a.fan_upward([[v[0],a.common.height(x['plane_y_xz_m'],v),v[1]]for v in q])),gradient=g);regions.append(entry);area+=a.geo.polygon_area(q)
    if g>.12+1e-7:steep.append(entry)
  gap=sum(a.geo.polygon_area(p)for p in gaps);seams=seam_check(regions);reasons=[]
  if r['uncovered_r18_area_m2']>1e-7:reasons.append('R18_LOCAL_COVERAGE_HOLD')
  if r['held_source_triangle_ids']:reasons.append('R18_LOCAL_GRADE_HOLD')
  if gap>1e-7:reasons.append('RETAINED_PUBLIC_TOP_GAP')
  if steep:reasons.append('RETAINED_PUBLIC_TRIANGLE_GRADE')
  if seams:reasons.append('ACTUAL_PUBLIC_HEIGHT_SEAM')
  if r['accepted_other_owner_area_m2']>1e-7:reasons.append('ACCEPTED_OTHER_OWNER_PROFILE_REQUIRED')
  result.append(dict(holding_id=r['holding_id'],public_road_id=r['public_road_id'],status='READY_SHARED_PUBLIC_PLANES'if not reasons else'HELD_PUBLIC_PORTIONS',hold_reasons=reasons,profile_regions=regions,retained_uncovered_polygons_xz_m=gaps,retained_uncovered_area_m2=gap,retained_steep_regions=steep,shared_height_failures=seams,accepted_other_owner_polygons_xz_m=r['accepted_other_owner_polygons_xz_m'],uncovered_r18_polygons_xz_m=r['uncovered_r18_polygons_xz_m'],activation=False))
  print(r['holding_id'],result[-1]['status'],reasons,flush=True)
 summary=dict(entries=len(result),ready=sum(r['status']=='READY_SHARED_PUBLIC_PLANES'for r in result),holds=sum(r['status']!='READY_SHARED_PUBLIC_PLANES'for r in result),reasons=dict(collections.Counter(k for r in result for k in r['hold_reasons'])),elapsed_s=time.monotonic()-start)
 write('resolved_public_inputs_r01.json',dict(source_public_profiles=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=SHA),base_scene_sha256=a.SCENE_SHA256,entries=result,summary=summary,scope='Exact finite public overlap planes only. Private-route solve, cut/fill support and actual emitted-side proof remain required.',activation=False));print(summary,flush=True)
if __name__=='__main__':run()
