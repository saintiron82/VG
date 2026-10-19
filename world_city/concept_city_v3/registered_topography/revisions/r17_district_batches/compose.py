"""Pure bounded R7 source-index compositor for district owners.

Call only after parcel, native, top, side and public-seam preflight. This helper
retains original source planes, except separately proved level retired holes.
"""
from collections import defaultdict
import json
from . import author as a

def lift(poly,plane):return[[x,a.common.height(plane,[x,z]),z]for x,z in poly]
def classify_parts(poly,owners):
 """Owner order is explicit precedence; interiors emitted once."""
 remaining=[poly];out=[]
 for owner in owners:
  rest=[]
  for p in remaining:
   q=a.clip(p,owner['polygon_xz_m'])
   if q:
    out.append((owner,q));rest.extend(a.common.subtract([p],[owner['polygon_xz_m']]))
   else:rest.append(p)
  remaining=rest
 return out,remaining

def verify_restorations(restorations):
 if not restorations:return
 candidates=json.loads((a.HERE/'retirement_candidates.json').read_text());proof=json.loads((a.HERE/'retired_body_boundary_audit.json').read_text())
 if candidates['base_scene_sha256']!=a.SCENE_SHA256 or proof['base_scene_sha256']!=a.SCENE_SHA256 or proof['retirement_candidates_sha256']!=a.sha(a.HERE/'retirement_candidates.json'):raise ValueError('Stale restoration evidence')
 rows={r['source_id']:r for r in candidates['rows']};passed={r['source_id']for r in proof['rows']if r['status']=='COMPLETE_LEVEL_BODY_BOUNDARY'}
 for r in restorations:
  old=rows.get(r['source_id'])
  if not old or r['source_id']not in passed:raise ValueError('Unproved current ordinary restoration')
  if a.canonical_sha(r['polygon_xz_m'])!=a.canonical_sha(old['old_terrain_body_hole_polygon_xz_m'])or abs(r['floor_y_m']-old['existing_finished_floor_y_m'])>a.BAND_TOLERANCE_M:raise ValueError('Restoration outside proved old body/floor')

def build(scene,owners,restorations=(),removed_foundation_proxy_ids=()):
 verify_restorations(restorations)
 if any(o['action']not in('hole','paint')for o in owners):raise ValueError('Unknown finite action')
 for o in owners:
  if not a.geo.is_convex_polygon(o['polygon_xz_m']):raise ValueError('Require normalized convex owner '+o['id'])
  if o['action']=='paint'and o['material']not in scene['materials']:raise ValueError('Unknown explicit material '+o['material'])
 windows=[o['polygon_xz_m']for o in owners]+[r['polygon_xz_m']for r in restorations];index=a.TriangleIndex(scene,windows);oi=a.geo._SpatialIndex(16)
 for i,o in enumerate(owners):oi.add(i,o['polygon_xz_m'])
 edits=[];appended=defaultdict(list);areas=defaultdict(float);source_parts=[]
 for r in index.rows:
  candidates=[owners[i]for i in oi.candidates(r['polygon_xz_m'])];assigned,remaining=classify_parts(r['polygon_xz_m'],candidates)
  if not assigned:continue
  for owner,p in assigned:
   areas[owner['id']]+=a.geo.polygon_area(p)
   if owner['action']=='paint':
    expected=owner.get('floor_y_m')
    if expected is not None and any(abs(a.common.height(r['plane_y_xz_m'],q)-expected)>a.BAND_TOLERANCE_M for q in p):raise ValueError('Material owner would change declared floor '+owner['id'])
    appended[owner['material']].extend(v for t in a.fan_upward(lift(p,r['plane_y_xz_m']))for v in t)
  replacement=[t for p in remaining for t in a.fan_upward(lift(p,r['plane_y_xz_m']))]
  before=a.geo.polygon_area(r['polygon_xz_m']);after=sum(a.normal_y(t)/2 for t in replacement);owned=sum(a.geo.polygon_area(p)for _,p in assigned)
  if abs(before-after-owned)>1e-7:raise ValueError('Source partition mismatch')
  edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],replacement_triangles_xyz_m=replacement));source_parts.append(dict(material=r['material'],triangle_index=r['triangle_index'],original_area_m2=before,retained_area_m2=after,reowned_area_m2=owned))
 restore_ledger=[];prior_restore=[]
 for r in restorations:
  if r.get('boundary_status')!='COMPLETE_LEVEL_BODY_BOUNDARY':raise ValueError('Unproved retired hole')
  poly=r['polygon_xz_m'];existing=[v['intersection_polygon_xz_m']for v in index.covering(poly)];missing=a.common.subtract([poly],existing+prior_restore);prior_restore.extend(missing);emitted=0.;native=0.
  for p in missing:
   active=[owners[i]for i in oi.candidates(p)];assigned,remaining=classify_parts(p,active)
   for owner,q in assigned:
    ar=a.geo.polygon_area(q)
    if owner['action']=='hole':native+=ar;continue
    if abs(owner.get('floor_y_m',r['floor_y_m'])-r['floor_y_m'])>a.BAND_TOLERANCE_M:raise ValueError('Retired hole/new floor mismatch')
    appended[owner['material']].extend(v for t in a.fan_upward(lift(q,[0,0,r['floor_y_m']]))for v in t);emitted+=ar
   for q in remaining:
    appended[r['material']].extend(v for t in a.fan_upward(lift(q,[0,0,r['floor_y_m']]))for v in t);emitted+=a.geo.polygon_area(q)
  missing_area=sum(a.geo.polygon_area(p)for p in missing)
  if abs(missing_area-emitted-native)>1e-7:raise ValueError('Restored hole area mismatch')
  restore_ledger.append(dict(id=r['id'],source_id=r['source_id'],old_missing_area_m2=missing_area,new_native_hole_area_m2=native,restored_top_area_m2=emitted))
 source_keys=[(r['material'],r['triangle_index'])for r in edits]
 if len(source_keys)!=len(set(source_keys)):raise ValueError('Duplicate original source index')
 if not all(a.normal_y(t)>0 for r in edits for t in r['replacement_triangles_xyz_m']):raise ValueError('Downward replacement top')
 if not all(a.normal_y(vs[i:i+3])>0 for vs in appended.values()for i in range(0,len(vs),3)):raise ValueError('Downward appended top')
 actual_boxes={r['id']for r in scene.get('boxes',[])}
 if not set(removed_foundation_proxy_ids)<=actual_boxes:raise ValueError('Missing original foundation proxy')
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R17_DISTRICT_FINITE_SOURCE_CANDIDATE',status='INACTIVE_PENDING_COMPLETE_BATCH_GATES',base_scene_sha256=a.SCENE_SHA256,source_surface_hashes={m:a.canonical_sha(scene['surfaces'][m])for m in sorted({r['material']for r in edits})},surface_edits=edits,appended_surfaces=dict(appended),removed_foundation_proxy_ids=list(removed_foundation_proxy_ids))
 report=dict(original_source_index_count=len(edits),appended_triangles=sum(len(v)//3 for v in appended.values()),source_partitions=source_parts,owner_area_m2=dict(areas),restored_holes=restore_ledger,all_emitted_top_normals_positive=True,unaffected_original_triangles_policy='Exact original value/order retained by hash-checked scene applier.',bank_side_policy='No automatic bank preservation approval: require separate clear-volume audit or exact finite owned cuts.',activation=False)
 return patch,report
