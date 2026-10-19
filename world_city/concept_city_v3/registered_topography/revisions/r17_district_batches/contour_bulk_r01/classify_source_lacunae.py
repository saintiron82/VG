"""Locate the three inherited top omissions before any finite restoration."""
import json,math
from .screen import HERE,write
from .. import author as a,native_clearance

def run():
 scene=a.load_scene();hand=json.loads((HERE/'physical_owner_handoff_r01.json').read_bytes());report=json.loads((HERE/'top_coverage_report_r01.json').read_bytes());byid={r['id']:r for r in hand['rendered_plane_owners']};bad=[r for r in report['failures']if r['missing_source_area_m2']>1e-7];projection=json.loads(native_clearance.PROJECTION.read_bytes());retired={r['source_id']for r in hand['retirement_records']};native=[];ni=a.geo._SpatialIndex(16)
 for inst in projection['instances']:
  if inst['id']in retired:continue
  for p in inst['native_owner_parts_xz_m']:ni.add(len(native),p);native.append(dict(id=inst['id'],polygon_xz_m=p))
 water=scene['terrain_contract']['water_domain_polygons'];wi=a.geo._SpatialIndex(16)
 for i,r in enumerate(water):wi.add(i,r['polygon_xz_m'])
 boxes=scene['terrain_contract']['ordinary_foundations'];bi=a.geo._SpatialIndex(16)
 for i,r in enumerate(boxes):bi.add(i,r['polygon_xz_m'])
 windows=[]
 for r in bad:
  for p in r['missing_source_polygons_xz_m']:
   x0,z0,x1,z1=a.bounds(p);windows.append([[x0-.25,z0-.25],[x1+.25,z0-.25],[x1+.25,z1+.25],[x0-.25,z1+.25]])
 old=a.TriangleIndex(scene,windows);rows=[]
 for item in bad:
  owner=byid[item['id']]
  for j,p in enumerate(item['missing_source_polygons_xz_m']):
   if a.geo.polygon_area(p)<=1e-10:continue
   hits=[]
   for source,index,kind in[(native,ni,'retained_native'),(water,wi,'water'),(boxes,bi,'ordinary_foundation')]:
    for k in index.candidates(p):
     r=source[k];q=a.clip(p,r['polygon_xz_m'])
     if q and(a0:=a.geo.polygon_area(q))>1e-10:hits.append(dict(kind=kind,owner_id=r.get('id',r.get('source_mass_id')),area_m2=a0,polygon_xz_m=q))
   x0,z0,x1,z1=a.bounds(p);window=[[x0-.25,z0-.25],[x1+.25,z0-.25],[x1+.25,z1+.25],[x0-.25,z1+.25]];near=[dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],polygon_xz_m=r['intersection_polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'])for r in old.covering(window)];ds=[a.common.height(r['plane_y_xz_m'],v)-a.common.height(owner['plane_y_xz_m'],v)for r in near for v in r['polygon_xz_m']]
   rows.append(dict(id=owner['id']+':LACUNA:'+str(j),proposed_owner_id=owner['id'],holding_id=owner.get('holding_id'),polygon_xz_m=p,area_m2=a.geo.polygon_area(p),proposed_plane_y_xz_m=owner['plane_y_xz_m'],existing_owner_hits=hits,adjacent_source_triangles=near,adjacent_cut_max_m=max(ds+[0]),adjacent_fill_max_m=max([-d for d in ds]+[0]),status='UNOWNED_INHERITED_TOP_OMISSION'if not hits else'EXISTING_OWNER_REQUIRES_REVIEW'))
 out=dict(base_scene_sha256=a.SCENE_SHA256,source_top_report_sha256=a.sha(HERE/'top_coverage_report_r01.json'),records=rows,summary=dict(records=len(rows),area_m2=sum(r['area_m2']for r in rows),existing_owner_hits=sum(len(r['existing_owner_hits'])for r in rows)),policy='No original floor is invented. Any adopted repair is explicitly new finite coherent earth at its approved owner plane, with measured adjacent-source cut/fill and no retained native/water overlap.',activation=False);write('source_lacuna_classification_r01.json',out);print(out['summary'],flush=True)
if __name__=='__main__':run()
