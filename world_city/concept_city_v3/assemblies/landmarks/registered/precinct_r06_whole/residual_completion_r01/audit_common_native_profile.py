"""Correct the Y0-only audit with every actual native common tread top."""
from pathlib import Path
import sys,json,math
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from resolve_pack import *
OUT=Path(__file__).resolve().parent

def main():
 src=load(OUT/'common_entry_surface_audit.json');ext=src['row']['external_surface'];projection=load(BASE/'actual_native_projection.json');p=next(p for p in projection['instances']if p['id']=='REGISTERED_LANDSCAPE:SITE_COMMON');asset=projection['assets'][p['asset_key']];mesh=load(ROOT/asset['cache']['path']);vs=[];toprows=[]
 for group in mesh['groups']:
  for q in group['quads']:
   if terrain.normal_y(q[:3])<=1e-9 or max(v[1]for v in q)>1e-8:continue
   poly=b.xform([[v[0],v[2]]for v in q],p);y=q[0][1]+p['position_m'][1];toprows.append({'material':group['material'],'polygon_xz_m':poly,'floor_y_m':y})
   for tri in terrain.fan_upward([[v[0],y,v[1]]for v in poly]):vs.extend(tri)
 class Support:
  def __init__(self):self.ground=terrain.TriangleIndex(terrain.load_scene(),ext['polygon_regions_xz_m']);self.native=terrain.TriangleIndex({'surfaces':{'actual_common_native_tread':vs}},ext['polygon_regions_xz_m'])
  def covering(self,q):
   rows=list(self.ground.covering(q));claimed=[r['intersection_polygon_xz_m']for r in rows];yield from rows
   for r in self.native.covering(q):
    for qq in terrain.common.subtract([r['intersection_polygon_xz_m']],claimed):
     if geo.polygon_area(qq)>1e-8:yield dict(r,intersection_polygon_xz_m=qq);claimed.append(qq)
 support=Support();checks=[terrain.audit_polygon(support,q,None)for q in ext['polygon_regions_xz_m']];steps=[]
 for check in checks:
  for r in check['source_pieces']:
   for q in r['polygon_xz_m']:
    ys=[terrain.common.height(s['plane_y_xz_m'],q)for s in check['source_pieces']if geo.point_in_convex_polygon(q,s['polygon_xz_m'],1e-7)]
    if ys and max(ys)-min(ys)>1e-7:steps.append({'point_xz_m':q,'step_m':max(ys)-min(ys)})
 side=SideIndex(terrain.load_scene(),ext['polygon_regions_xz_m']).audit([{'id':f'COMMON_ACTUAL_NATIVE:{i}:{j}','polygon_xz_m':r['polygon_xz_m'],'plane_y_xz_m':r['plane_y_xz_m']}for i,c in enumerate(checks)for j,r in enumerate(c['source_pieces'])]);report={'source':ref(OUT/'common_entry_surface_audit.json'),'native_instance_id':p['id'],'native_asset':asset,'native_pitch_m':mesh['pitch'],'actual_native_tops':toprows,'checks':checks,'actual_surface_jumps':steps,'maximum_actual_surface_jump_m':max((s['step_m']for s in steps),default=0),'bank_checks':side,'corrected_missing_area_m2':sum(c['missing_area_m2']for c in checks),'source_skin_primitive_prefix':'r1_access_skin_','source_external_surface':ext,'status':'NEEDS_NATIVE_TREAD_AND_TERRAIN_INTERFACE_REPAIR','correction':'The prior 112.872 m² missing screen omitted negative-local-Y native floor pieces. These are actual native tread ownership, not free empty soil. Preserve original audit as limited-index failed evidence.','runtime_replay':'pending'};(OUT/'common_actual_native_profile.json').write_text(json.dumps(report,indent=2)+'\n');print('missing',report['corrected_missing_area_m2'],'maxjump',report['maximum_actual_surface_jump_m'],'banks',len(side['contacts']),'levels',sorted({r['floor_y_m']for r in toprows}))
if __name__=='__main__':main()
