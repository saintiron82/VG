"""Retire only current R04 common earth tops already replaced by finite R18."""
import json, math, collections
from .height_field import HERE
from . import finite_geometry_r03 as g
from .revise_native_emission_r07 import fan, ref
from ..r17_district_batches import author as a

def main():
 sp=a.CITY/'evidence/r8_district_r04/scene.json';assert a.sha(sp)=='3c63a21f4490e1dada6be34428dc2d1ffacd326d8f34b2deee81e378ab6680d7';scene=json.loads(sp.read_bytes());hp=HERE/'top_hole_classification_r02.json';holes=json.loads(hp.read_bytes());pp=HERE/'finite_field_candidate_r07_native_bound.json';pub=json.loads(pp.read_bytes());ix=a.geo._SpatialIndex(4)
 for i,r in enumerate(pub['records']):ix.add(i,r['polygon_xz_m'])
 masks=collections.defaultdict(list);source_keys={};rows=[]
 for h in holes['rows']:
  if ':COMMON:'not in h['owner_id']:continue
  for r in h['current_rendered_top_pieces']:
   key=(r['material'],r['triangle_index']);source_keys[key]=r['source_triangle_sha256']
   for i in ix.candidates(r['polygon_xz_m']):
    owner=pub['records'][i];q=g.clip(r['polygon_xz_m'],owner['polygon_xz_m'])
    if q:masks[key].append(q)
 edits=[];evidence=[];total=0.;maxerr=0.
 for (material,index),parts in masks.items():
  tri=scene['surfaces'][material][index*3:index*3+3];assert a.canonical_sha(tri)==source_keys[(material,index)];poly=[[v[0],v[2]]for v in tri];plane=a.common.plane(tri);cuts=g.union(parts);retained=g.subtract([poly],cuts);ts=[t for p in retained for t in fan(p,plane)];before=g.area(poly);after=math.fsum(g.area([[v[0],v[2]]for v in t])for t in ts);ar=math.fsum(g.area(p)for p in cuts);error=abs(before-after-ar);assert error<1e-8,(material,index,error);maxerr=max(maxerr,error)
  if ar<=1e-14:continue
  edits.append(dict(material=material,triangle_index=index,source_triangle_sha256=a.canonical_sha(tri),replacement_triangles_xyz_m=ts));evidence.append(dict(material=material,triangle_index=index,source_triangle_xyz_m=tri,source_triangle_sha256=a.canonical_sha(tri),retired_polygons_xz_m=cuts,retired_area_m2=ar,source_plane_y_xz_m=plane,partition_error_m2=error,retained_plane_error_m=max((abs(v[1]-a.common.height(plane,[v[0],v[2]]))for t in ts for v in t),default=0.)));total+=ar
 refs=[ref(sp),ref(hp),ref(pp),ref(__import__('pathlib').Path(__file__)),ref(__import__('pathlib').Path(g.__file__))]
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R18_RETIRE_CURRENT_COMMON_DOUBLE_TOPS_R01',status='EXACT_CURRENT_SCENE_RETIREMENT_PENDING_COMPOSED_REPLAY',base_scene_sha256=a.sha(sp),source_surface_hashes={m:a.canonical_sha(scene['surfaces'][m])for m in sorted({r['material']for r in edits})},surface_edits=edits,appended_surfaces={},removed_foundation_proxy_ids=[],source_references=refs)
 p=HERE/'current_common_top_retirement_r01.json';p.write_text(json.dumps(patch,separators=(',',':'))+'\n');review=dict(status='PASS_EXACT_CURRENT_TOP_RETIREMENT',patch=ref(p),sources=refs,edited_current_triangles=len(edits),retired_area_m2=total,maximum_partition_error_m2=maxerr,records=evidence,scope='Only current R04 ground_earth intersections already owned by the canonical finite public field are retired. No native face, water, bank or replacement public plane is changed; no new top is appended by this patch.')
 rp=HERE/'current_common_top_retirement_review_r01.json';rp.write_text(json.dumps(review,separators=(',',':'))+'\n');print(json.dumps(dict(patch=ref(p),review=ref(rp),edited_triangles=len(edits),retired_area_m2=total,maximum_partition_error_m2=maxerr)))
if __name__=='__main__':main()
