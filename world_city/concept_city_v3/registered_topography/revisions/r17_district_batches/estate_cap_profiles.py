"""Actual R7 public top binding under proposed estate cap cuts."""
import json
from . import author as a

def run():
 source=a.CITY/'assemblies/property/registered/public_lane_repairs_r01/contact_polygons.json';d=json.loads(source.read_bytes());folder=a.HERE/'estate_public_caps_r01';folder.mkdir(exist_ok=True);out=folder/'actual_public_profiles.json'
 if out.exists():raise SystemExit('Preserve cap evidence')
 polys=[p for r in d['records']for c in r['contacts']for p in c['actual_traffic_contact_polygons_xz_m']];index=a.TriangleIndex(a.load_scene(),polys);rows=[]
 for r in d['records']:
  for c in r['contacts']:
   for j,p in enumerate(c['actual_traffic_contact_polygons_xz_m']):
    proof=a.audit_polygon(index,p);rows.append(dict(property_id=r['property_id'],canonical_public_road_id=r['canonical_public_road_id'],native_face_key=c['native_face_key'],polygon_xz_m=p,proof=proof))
 result=dict(schema='riverstone.r17.estate_cap_actual_public_profiles.v1',base_scene_sha256=a.SCENE_SHA256,contact_source=dict(path=str(source.relative_to(a.ROOT)),sha256=a.sha(source)),records=rows,summary=dict(regions=len(rows),missing_area_m2=sum(r['proof']['missing_area_m2']for r in rows),maximum_actual_triangle_grade=max(r['proof']['max_actual_triangle_grade']for r in rows)),status='ACTUAL_SOURCE_PLANE_BINDING_ONLY',activation=False);out.write_text(json.dumps(result,separators=(',',':'))+'\n');print(result['summary']);print(a.sha(out))
if __name__=='__main__':run()
