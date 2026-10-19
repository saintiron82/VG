"""Bounded exact top replacement for the matched ready subset.

Only original R7 top indices are edited here. Joint public/private retained
sides are a separate composed step. Compact masks control cuts; disjoint
accepted planes control emitted geometry, so material subdivision is not
repeated as thousands of redundant Boolean subtractions.
"""
import json,time,collections,math
from .prepare import HERE,write
from .. import author as a
from ...r01_ownership import author as ownership
from ...public_corridors_r18 import public_domain

def run():
 start=time.monotonic();hand=json.loads((HERE/'physical_owner_handoff_r02.json').read_bytes());selected=set(hand['accepted_holding_ids']);masks=json.loads((HERE/'compact_cut_domains_r01.json').read_bytes())['polygons_xz_m'];mi=a.geo._SpatialIndex(16)
 for i,p in enumerate(masks):mi.add(i,p)
 scene=a.load_scene();index=a.TriangleIndex(scene,masks);edits=[];partitions=[]
 for r in index.rows:
  p=r['polygon_xz_m'];remaining=a.common.subtract([p],[masks[i]for i in sorted(mi.candidates(p))]);before=a.geo.polygon_area(p);after=sum(a.geo.polygon_area(q)for q in remaining)
  if before-after<1e-10:continue
  tris=[tr for q in remaining for tr in a.fan_upward([[v[0],a.common.height(r['plane_y_xz_m'],v),v[1]]for v in q])];edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],replacement_triangles_xyz_m=tris));partitions.append(dict(material=r['material'],triangle_index=r['triangle_index'],original_area_m2=before,retained_area_m2=after,removed_area_m2=before-after))
 print('Original top edits',len(edits),flush=True);holes=[r['old_body_polygon_xz_m']for r in hand['retirement_records']];hi=a.geo._SpatialIndex(16)
 restoration_path=None
 for i,p in enumerate(holes):hi.add(i,p)
 appended=collections.defaultdict(list);coverage=[];fail=[];down=0
 for i,r in enumerate(hand['rendered_plane_owners']):
  p=r['polygon_xz_m'];covers=[x['intersection_polygon_xz_m']for x in index.covering(p)]+[holes[j]for j in hi.candidates(p)];missing=a.common.subtract([p],covers);gap=sum(a.geo.polygon_area(q)for q in missing);outside=a.common.subtract([p],[masks[j]for j in mi.candidates(p)]);extra=sum(a.geo.polygon_area(q)for q in outside)
  if gap>1e-7 or extra>1e-7:fail.append(dict(id=r['id'],holding_id=r.get('holding_id'),missing_source_area_m2=gap,outside_cut_domain_m2=extra,missing_source_polygons_xz_m=missing,outside_cut_polygons_xz_m=outside))
  tris=list(a.fan_upward([[v[0],a.common.height(r['plane_y_xz_m'],v),v[1]]for v in p]));down+=sum(a.normal_y(t)<=0 for t in tris);appended[r['material']].extend(v for t in tris for v in t);coverage.append(dict(id=r['id'],area_m2=a.geo.polygon_area(p),missing_source_area_m2=gap,outside_cut_domain_m2=extra))
  if i and i%10000==0:print('Owner coverage',i,'holds',len(fail),flush=True)
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R17_COMPLETE_FINAL24_TOPS',status='TOP_CANDIDATE_PENDING_JOINT_SIDE_AND_FULL_COVERAGE_ACCEPTANCE',base_scene_sha256=a.SCENE_SHA256,source_surface_hashes={m:a.canonical_sha(scene['surfaces'][m])for m in sorted({r['material']for r in edits})},surface_edits=edits,appended_surfaces=dict(appended),removed_foundation_proxy_ids=[r['removed_foundation_proxy_id']for r in hand['retirement_records']],source_references=[dict(path=str((HERE/'physical_owner_handoff_r02.json').relative_to(a.ROOT)),sha256=a.sha(HERE/'physical_owner_handoff_r02.json'))]);report=dict(status='PASSED_TOP_SOURCE_COVERAGE'if not fail and not down else'HELD_TOP_SOURCE_COVERAGE',failures=fail,downward_top_count=down,source_partitions=partitions,owner_coverage=coverage,summary=dict(accepted_holdings=len(selected),source_top_edits=len(edits),appended_triangles=sum(len(v)//3 for v in appended.values()),missing_owner_count=len(fail),downward_top_count=down,elapsed_s=time.monotonic()-start),activation=False)
 write('top_scene_patch_r01.json',patch);write('top_coverage_report_r01.json',report);print(report['summary'],flush=True)
if __name__=='__main__':run()
