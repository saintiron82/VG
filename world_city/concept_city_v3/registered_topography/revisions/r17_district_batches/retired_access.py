"""Atomic ordinary body, proxy and private-access retirement for bulk patches."""
import json
from . import author as a

def build(layout, scene):
 candidates=json.loads((a.HERE/'retirement_candidates.json').read_bytes())
 proof=json.loads((a.HERE/'retired_body_boundary_audit.json').read_bytes())
 if candidates['base_scene_sha256']!=a.SCENE_SHA256 or proof['base_scene_sha256']!=a.SCENE_SHA256:raise ValueError('Stale retirement evidence')
 by_id={r['source_id']:r for r in candidates['rows']};passed={r['source_id']for r in proof['rows']if r['status']=='COMPLETE_LEVEL_BODY_BOUNDARY'}
 wanted=list(layout['retired_source_ids'])
 if len(wanted)!=len(set(wanted)):raise ValueError('Duplicate retired source ID')
 active={p['id']:p for p in scene['common_instances']};boxes={p['id']:p for p in scene['boxes']};records=[];restorations=[]
 for sid in wanted:
  if sid not in passed or sid not in active:raise ValueError('Unproved or absent retirement '+sid)
  r=by_id[sid]
  if a.canonical_sha(active[sid])!=a.canonical_sha(r['source_instance']):raise ValueError('Changed native instance '+sid)
  bid=sid+':owned_foundation'
  if bid not in boxes or boxes[bid].get('source_mass_id')!=sid:raise ValueError('Missing old foundation proxy '+sid)
  records.append(dict(source_id=sid,old_source_path_ids=[p['id']for p in r['old_source_paths']],old_actual_door_ids=[p['id']for p in r['actual_old_access_records']],removed_foundation_proxy_id=bid,former_access_domains=[dict(id=p['id'],polygons_xz_m=p.get('reserved_connection_polygons_xz_m',[]),actual_door_xyz_m=p['actual_door_xyz_m'])for p in r['actual_old_access_records']],former_access_policy='Retire private entrance semantics. Preserve original rendered planes outside explicit new owners; remaining old paving is ordinary ground without an active door.',new_active_entrance=False))
  restorations.append(dict(id=sid+':EXPOSED_BODY_RESTORATION',source_id=sid,polygon_xz_m=r['old_terrain_body_hole_polygon_xz_m'],floor_y_m=r['existing_finished_floor_y_m'],material='ground_earth',boundary_status='COMPLETE_LEVEL_BODY_BOUNDARY',source_native_bottom_y_m=r['native_origin_y_m'],existing_foundation_bottom_y_m=r['foundation_proxy']['bottom_y_m']))
 paths=sorted({p for r in records for p in r['old_source_path_ids']});doors=sorted({p for r in records for p in r['old_actual_door_ids']})
 for route in layout.get('door_routes',[])+layout.get('shared_private_routes',[]):
  target=route.get('connects_source_path_or_road_id',route.get('connects_to_id'))
  if target in paths or target in doors:raise ValueError('New route references a retired entrance '+target)
 return dict(schema='riverstone.r17.atomic_retirement.v1',base_scene_sha256=a.SCENE_SHA256,source_references=[dict(path=str((a.HERE/f).relative_to(a.ROOT)),sha256=a.sha(a.HERE/f))for f in ('retirement_candidates.json','retired_body_boundary_audit.json')],retired_source_ids=wanted,removed_foundation_proxy_ids=[r['removed_foundation_proxy_id']for r in records],retired_source_path_ids=paths,retired_actual_door_ids=doors,records=records,body_restorations=restorations,old_private_access_no_longer_active=True,activation=False)
