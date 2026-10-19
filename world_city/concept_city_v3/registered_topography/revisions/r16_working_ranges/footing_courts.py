"""Exact native footing exclusions and court recoloring on frozen R6 planes.

This bounded partial patch cannot activate the ranges before their public
terminal fields are accepted and composed. Native assembly stays parent-owned.
"""
import json,math
from collections import defaultdict
from . import author as a, frozen_r6 as f

def build(scene):
 owners=a.native_holes()+a.court_regions();idx=f.SurfaceIndex(scene,windows=[f.bounds(r['polygon_xz_m']) for r in owners],margin=0)
 holes=[r['polygon_xz_m'] for r in a.native_holes()];courts=a.court_regions();edits=[];append=[];removed=defaultdict(float);changed=[]
 owner_index=a.geo._SpatialIndex(8)
 for i,r in enumerate(owners):owner_index.add(i,r['polygon_xz_m'])
 for r in idx.records:
  candidates=[owners[i] for i in sorted(owner_index.candidates(r['polygon_xz_m']))]
  local=[o for o in candidates if a.clean(a.geo.convex_intersection(r['polygon_xz_m'],o['polygon_xz_m']))]
  if not local:continue
  parts=[r['polygon_xz_m']]
  for o in local:
   new=[]
   for p in parts:
    q=a.clean(a.geo.convex_intersection(p,o['polygon_xz_m']))
    if not q:new.append(p);continue
    removed[o['id']]+=a.geo.polygon_area(q)
    if o['kind']=='existing_plane_court_material':append.extend(v for t in f.fan_upward(f.lift(q,r['plane_y_xz_m'])) for v in t)
    new.extend(a.subtract([p],[o['polygon_xz_m']]))
   parts=new
  replacement=[t for p in parts for t in f.fan_upward(f.lift(p,r['plane_y_xz_m']))]
  edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],replacement_triangles_xyz_m=replacement))
  changed.append(r)
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R16_WORKING_NATIVE_FOOTINGS_COURT_MATERIAL',status='INACTIVE_PARTIAL_PATCH_PUBLIC_TERMINALS_PENDING',base_scene_sha256=f.SCENE_SHA256,source_surface_hashes={m:f.canonical_sha(scene['surfaces'][m]) for m in sorted({r['material'] for r in edits})},surface_edits=edits,appended_surfaces={'ground_stone':append},removed_foundation_proxy_ids=[])
 proof=[]
 for o in owners:
  p=o['polygon_xz_m'];cover=idx.cover(p);parts=[r['intersection_polygon_xz_m'] for r in cover];gap=sum(a.geo.polygon_area(q) for q in a.subtract([p],parts));ys=[a.height(r['plane_y_xz_m'],q) for r in cover for q in r['intersection_polygon_xz_m']]
  ar=a.geo.polygon_area(p);record=dict(owner_id=o['id'],area_m2=ar,covered_area_m2=sum(a.geo.polygon_area(q) for q in parts),uncovered_m2=gap,removed_source_top_m2=removed[o['id']],minimum_source_y_m=min(ys),maximum_source_y_m=max(ys))
  assert gap<1e-7 and abs(removed[o['id']]-ar)<1e-6 and max(abs(y-2.5) for y in ys)<1e-7,record
  proof.append(record)
 assert all(f.normal_y(t)>0 for e in edits for t in e['replacement_triangles_xyz_m'])
 assert all(f.normal_y(append[i:i+3])>0 for i in range(0,len(append),3))
 result=dict(status='PASS_BOUNDED_FOOTING_AND_COURT_SOURCE_GEOMETRY',base_scene_sha256=f.SCENE_SHA256,input_refs=a.build_contract()['input_refs'],native_footing_count=len(holes),native_footing_area_m2=sum(a.geo.polygon_area(p) for p in holes),court_count=len(courts),court_area_m2=sum(a.geo.polygon_area(o['polygon_xz_m']) for o in courts),source_triangle_edit_count=len(edits),court_triangle_count=len(append)//3,all_authored_tops_upward=True,owner_checks=proof,all26_candidate_ledger=a.all_candidate_ledger(),runtime_addition_count=4,retired_source_ids=[],retired_foundation_proxies=[],public_terminal_status='PENDING',new_native_compile_cells=0)
 return patch,result

def main():
 scene=f.load_scene();patch,report=build(scene)
 for name,data in [('footing_court_patch.json',patch),('footing_court_report.json',report)]:
  p=a.HERE/name
  if p.exists():raise ValueError('Refusing to overwrite '+name)
  p.write_text(json.dumps(data,separators=(',',':'))+'\n');print(name,a.sha(p),flush=True)
if __name__=='__main__':main()
