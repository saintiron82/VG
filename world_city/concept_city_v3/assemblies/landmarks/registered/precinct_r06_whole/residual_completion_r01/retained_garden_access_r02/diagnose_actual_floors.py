"""Clip retained actual native floors first, exposing only genuine surface gaps."""
from pathlib import Path
import sys,json,time
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE));sys.path.insert(0,str(OUT.parent))
from resolve_pack import *
from audit_retained_garden_access import GardenSupportIndex
OUT=Path(__file__).resolve().parent
class ActualGardenIndex:
 def __init__(self,scene,windows):
  self.terrain=terrain.TriangleIndex(scene,windows);projection=load(BASE/'actual_native_projection.json');vs=[];self.sources=[]
  for p in projection['instances']:
   if not p['asset_key'].startswith(('registered_institutional_site_cemetery_','registered_institutional_site_clergy_','registered_institutional_site_monastery_')):continue
   a=projection['assets'][p['asset_key']];mesh=load(ROOT/a['cache']['path']);self.sources.append(dict(id=p['id'],source=a['source'],cache=a['cache']))
   for q in horizontal(mesh,0,True):
    for tri in terrain.fan_upward([[v[0],p['position_m'][1],v[1]]for v in b.xform(q,p)]):vs.extend(tri)
  self.native=terrain.TriangleIndex({'surfaces':{'actual_retained_native_floor':vs}},windows)
 def covering(self,p):
  claimed=[]
  for index in (self.native,self.terrain):
   for r in index.covering(p):
    if geo.polygon_area(r['polygon_xz_m'])<=1e-8:continue
    for q in terrain.common.subtract([r['intersection_polygon_xz_m']],claimed):
     if geo.polygon_area(q)>1e-8:yield dict(r,intersection_polygon_xz_m=q);claimed.append(q)

def main():
 t=time.monotonic();old=load(OUT.parent/'retained_garden_access_audit.json');routes=[r for r in old['routes']if not r['support_native_bank_pass']];scene=terrain.load_scene();idx=ActualGardenIndex(scene,[q for r in routes for q in r['source_route']['ribbon_polygons_xz_m']]);rows=[]
 for r in routes:
  checks=[terrain.audit_polygon(idx,q,r['floor_y_m'])for q in r['source_route']['ribbon_polygons_xz_m']];bad=[]
  for c in checks:
   for s in c['source_pieces']:
    if max(abs(terrain.common.height(s['plane_y_xz_m'],q)-r['floor_y_m'])for q in s['polygon_xz_m'])>1e-5:bad.append(s)
  row=dict(id=r['id'],floor_y_m=r['floor_y_m'],surface_checks=checks,wrong_floor_pieces=bad,unresolved_native_contacts=r['native_contacts'],unresolved_bank_contacts=r['bank_contacts'],named_public_binding=r['public_binding'],surface_pass=all(c['passes_existing_surface']for c in checks));rows.append(row);print(r['id'],row['surface_pass'],'missing',sum(c['missing_area_m2']for c in checks),'badpieces',len(bad),flush=True)
 report=dict(source=ref(OUT.parent/'retained_garden_access_audit.json'),scene=ref(terrain.SCENE_PATH),actual_native_sources=idx.sources,routes=rows,seconds=time.monotonic()-t,method='Actual retained native local Y0 floor dominates its own exact footprint. Remaining original actual terrain is disjointly clipped. Degenerate source triangles are not extrapolated.')
 (OUT/'actual_floor_diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
