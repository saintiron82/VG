from pathlib import Path
import sys,json,time,hashlib
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE));sys.path.insert(0,str(OUT.parent/'retained_garden_access_r02'))
from resolve_pack import *
from diagnose_actual_floors import ActualGardenIndex
OUT=Path(__file__).resolve().parent

def write(n,d):p=OUT/n;p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n');return ref(p)
class Support(ActualGardenIndex):
 def __init__(self,scene,windows,vs):self.terrain=terrain.TriangleIndex(scene,windows);self.native=terrain.TriangleIndex({'surfaces':{'actual_native_floor':vs}},windows)
def main():
 started=time.monotonic();scene_path=CITY/'evidence/r8_district_61_noble_r02_runtime/scene.json';scene=load(scene_path);sourcepath=OUT.parent/'retained_garden_access_r03/route_search.json';old=load(sourcepath)['routes'][0]['candidates'][0];assert old['group']=='cathedral'and old['passes'];polys=old['ribbon_polygons_xz_m'];pts=[p for q in polys for p in q];window=b.rect(min(p[0]for p in pts)-.1,min(p[1]for p in pts)-.1,max(p[0]for p in pts)+.1,max(p[1]for p in pts)+.1);floor=14;vs=[];bodies=[];native=[];cache={}
 for p in scene['common_instances']:
  a=scene['common_assets'][p['asset_key']];bb=a.get('bounds');py=p['position_m'][1]
  if bb is None:
   rp=ROOT/a['render_path']
   if str(rp)not in cache:cache[str(rp)]=load(rp)
   bb=cache[str(rp)]['bounds']
  if bb['min'][1]+py>floor+2.2 or bb['max'][1]+py<floor-1e-7:continue
  wp=b.xform(b.rect(bb['min'][0],bb['min'][2],bb['max'][0],bb['max'][2]),p)
  if geo.intersection_area(wp,window)<1e-8:continue
  rp=ROOT/a['render_path'];mp=ROOT/a['master_path'];assert sha(rp)==a['render_sha256']and sha(mp)==a['master_sha256'];mesh=cache.setdefault(str(rp),load(rp));native.append(dict(id=p['id'],asset_key=p['asset_key'],source=ref(mp),cache=ref(rp),position_m=p['position_m'],yaw_rad=p['yaw_rad'],scale=p.get('scale',[1,1,1])))
  for q in slab_rectangles(mesh,floor-py+.01,floor-py+2.2):
   q=b.xform(q,p)
   if geo.intersection_area(q,window)>1e-8:bodies.append(dict(id=p['id'],polygon_xz_m=q))
  for q in horizontal(mesh,floor-py,True):
   q=b.xform(q,p)
   if geo.intersection_area(q,window)>1e-8:
    for tri in terrain.fan_upward([[x,floor,z]for x,z in q]):vs.extend(tri)
 print('actual assets',len(native),'body polygons',len(bodies),flush=True)
 idx=Support(scene,[window],vs);sides=SideIndex(scene,[window]);checks=[terrain.audit_polygon(idx,q,floor)for q in polys];contacts=[]
 for qi,q in enumerate(polys):
  for r in bodies:
   hit=geo.convex_intersection(q,r['polygon_xz_m']);area=geo.polygon_area(hit)
   if area>1e-7:contacts.append(dict(route_piece_index=qi,native_id=r['id'],polygon_xz_m=hit,area_m2=area))
 bank=sides.audit([dict(id='RETAINED_CLOISTER_ROUTE:'+str(i),polygon_xz_m=q,floor_y_m=floor)for i,q in enumerate(polys)])
 passed=all(c['passes_existing_surface']for c in checks)and not contacts and not bank['contacts'];row=dict(id='CLERGY_CLOISTER_GARDEN:ACTUAL_PORTAL_CONTINUATION_R01',owner_id='SITE_CLOISTER',width_m=2,floor_y_m=14,polyline_xz_m=old['polyline_xz_m'],ribbon_polygons_xz_m=polys,native_portal_id='cathedral_registered:west_cloister_walk_0',named_public_road_id='CATHEDRAL_APPROACH',retained_source_continuation=old['public_binding'],runtime_ready=False)
 report=dict(status='PASS'if passed else'FAIL',scene=ref(scene_path),source_route=ref(sourcepath),route=row,actual_native_sources=native,surface_checks=checks,native_contacts=contacts,bank_contacts=bank['contacts'],summary=dict(full_width_m=2,missing_area_m2=sum(c['missing_area_m2']for c in checks),maximum_floor_delta_m=max(c['max_floor_delta_m']for c in checks),native_contacts=len(contacts),bank_contacts=len(bank['contacts']),seconds=time.monotonic()-started),scope='Read-only current-scene full-width local route proof through retained native cloister portal. Historical retained graph binds named CATHEDRAL_APPROACH semantics; current network and original-controller runtime replay remain separate acceptance gates.')
 rr=write('actual_scene_audit.json',report);print(report['status'],report['summary'],flush=True)
 if not passed:return
 routes=write('runtime_routes.json',dict(status='ACTUAL_SCENE_STATIC_PASS_RUNTIME_PENDING',routes=[row],scene=ref(scene_path),audit=rr,original_controller_unchanged=True))
 hand=write('integration_handoff.json',dict(id='R8_RETAINED_CLOISTER_ACTUAL_PORTAL_CONTINUATION_R01',status='ACTUAL_SCENE_STATIC_PASS_RUNTIME_PENDING',runtime_routes=routes,actual_scene_audit=rr,native_packs=[],terrain_patches=[],collision_contracts=[],geometry_changes=False,runtime_ready=False))
 write('READY_SEAL.json',dict(handoff=hand,files=[ref(Path(__file__)),rr,routes,hand],runtime_ready=False));print('HANDOFF',hand,flush=True)
if __name__=='__main__':main()
