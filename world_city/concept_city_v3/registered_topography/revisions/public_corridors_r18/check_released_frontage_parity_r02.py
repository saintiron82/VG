"""Plane parity for already released finite frontage regions against final owners."""
import json,math
from .height_field import HERE
from . import finite_geometry_r03 as g
from ..r17_district_batches import author as a

def main():
 f=HERE/'frontage_profiles_r01.json';p=HERE/'finite_field_candidate_r04_common.json';front=json.loads(f.read_bytes());data=json.loads(p.read_bytes());ix=a.geo._SpatialIndex(4)
 for i,r in enumerate(data['records']):ix.add(i,r['polygon_xz_m'])
 count=0;area=0;error=0;bad=[];source_ids=set()
 for e in front['entries']:
  for r in e['profile_regions']:
   source_ids.add(r['source_triangle_index'])
   for i in ix.candidates(r['polygon_xz_m']):
    s=data['records'][i];q=g.clip(r['polygon_xz_m'],s['polygon_xz_m'])
    if not q:continue
    err=max(abs(a.common.height(r['plane_y_xz_m'],v)-a.common.height(s['plane_y_xz_m'],v))for v in q);count+=1;area+=g.area(q);error=max(error,err)
    if err>1e-7:bad.append(dict(holding_id=e['holding_id'],released_profile_id=r['id'],owner_id=s['id'],polygon_xz_m=q,maximum_difference_m=err))
 out=dict(status='PASS_RELEASED_PROFILE_PLANE_PARITY'if not bad else'HELD_RELEASED_PROFILE_PARITY',candidate_sha256=a.sha(p),released_source_sha256=a.sha(f),code_sha256=a.sha(__file__),source_triangles=len(source_ids),intersections=count,intersected_area_m2=area,maximum_plane_difference_m=error,failures=bad,scope='Exact intersecting plane preservation only; changed exclusion coverage is separately audited. No controller acceptance.')
 (HERE/'released_frontage_parity_r02.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print(out)
if __name__=='__main__':main()
