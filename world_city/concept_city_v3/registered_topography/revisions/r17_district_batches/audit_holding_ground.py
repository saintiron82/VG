"""Whole proposed ground owners, on the retained 16-holding snapshot."""
import json,time
from . import author as a
from .preflight_layout import virtual_restorations
from .side_clearance import SideIndex
if __name__=='__main__':
 p=a.HERE/'layout_draft_r01/full_holding_ground_audit.json'
 if p.exists():raise SystemExit('Preserve ground evidence')
 source=a.HERE/'layout_draft_r01/selected_layout.json';d=json.loads(source.read_text());scene=a.load_scene();t=time.monotonic();windows=[h['holding_polygon_xz_m']for h in d['holdings']]
 candidates=json.loads((a.HERE/'retirement_candidates.json').read_text())['rows'];windows +=[r['old_terrain_body_hole_polygon_xz_m']for r in candidates if r['source_id']in d['retired_source_ids']]
 index=a.TriangleIndex(scene,windows);restores,held=virtual_restorations(index,d);rows=[];owners=[]
 for h in d['holdings']:
  r=a.audit_polygon(index,h['holding_polygon_xz_m'],h['floor_y_m']);r.update(id=h['id'],floor_y_m=h['floor_y_m']);rows.append(r);owners.append(dict(id=h['id'],polygon_xz_m=h['holding_polygon_xz_m'],floor_y_m=h['floor_y_m']))
 side=SideIndex(scene,windows).audit(owners)
 result=dict(base_scene_sha256=a.SCENE_SHA256,source_layout_sha256=a.sha(source),rows=rows,side_clearance=side,summary=dict(holding_count=len(rows),complete_level_count=sum(r['passes_existing_surface']for r in rows),held_count=sum(not r['passes_existing_surface']for r in rows),side_contacts=len(side['contacts']),seconds=time.monotonic()-t),activation=False)
 p.write_text(json.dumps(result,separators=(',',':'))+'\n');print(result['summary']);print([(r['id'],r['missing_area_m2'],r['max_floor_delta_m'])for r in rows if not r['passes_existing_surface']]);print(a.sha(p))
