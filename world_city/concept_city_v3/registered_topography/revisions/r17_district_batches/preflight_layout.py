"""One snapshot, one source index, all proposed holdings. No activation."""
import argparse,json,time
from . import author as a
from . import side_clearance
SOURCE=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/selected_layout.json'

def virtual_restorations(index,selected):
 ledger=json.loads((a.HERE/'retirement_candidates.json').read_text());eligible={r['source_id']for r in json.loads((a.HERE/'retired_body_boundary_audit.json').read_text())['rows']if r['status']=='COMPLETE_LEVEL_BODY_BOUNDARY'};wanted=set(selected['retired_source_ids']);new=[]
 for r in ledger['rows']:
  if r['source_id']not in wanted&eligible:continue
  poly=r['old_terrain_body_hole_polygon_xz_m'];missing=a.common.subtract([poly],[q['intersection_polygon_xz_m']for q in index.covering(poly)])
  for p in missing:
   for tri in a.fan_upward([[x,r['matching_level_band_y_m'],z]for x,z in p]):
    q=[[v[0],v[2]]for v in tri];row=dict(material='hypothetical_retired_body_restore',triangle_index=-len(new)-1,source_triangle_sha256=None,source_id=r['source_id'],vertices_xyz_m=tri,polygon_xz_m=q,plane_y_xz_m=[0,0,r['matching_level_band_y_m']]);index.index.add(len(index.rows),q);index.rows.append(row);new.append(row)
 return new,sorted(wanted-eligible)

def run(name):
 folder=a.HERE/name
 if folder.exists():raise SystemExit('Preserve prior batch evidence')
 folder.mkdir();raw=SOURCE.read_bytes();(folder/'selected_layout.json').write_bytes(raw);d=json.loads(raw);scene=a.load_scene();start=time.monotonic();owners=[]
 for p in d['placements']:
  for j,q in enumerate(p['native_foundation_polygons_xz_m']):owners.append(dict(id=p['id']+':FOOTING:'+str(j),holding_id=p['holding_id'],kind='native_footing',floor_y_m=p['finished_floor_y_m'],polygon_xz_m=q))
 for h in d['holdings']:
  for key,kind in [('core_court_polygons_xz_m','court'),('external_route_polygons_xz_m','external_route')]:
   for j,q in enumerate(a.common.disjoint_union(h[key])):owners.append(dict(id=h['id']+':'+kind+':'+str(j),holding_id=h['id'],kind=kind,floor_y_m=h['floor_y_m'],polygon_xz_m=q))
 for h in d['shared_private_routes']:
  for j,q in enumerate(a.common.disjoint_union(h['polygons_xz_m'])):owners.append(dict(id=h['id']+':'+str(j),holding_id=h['id'],kind='shared_route',floor_y_m=h['floor_y_m'],polygon_xz_m=q))
 windows=[r['polygon_xz_m']for r in owners];candidates=json.loads((a.HERE/'retirement_candidates.json').read_text())['rows'];windows +=[r['old_terrain_body_hole_polygon_xz_m']for r in candidates if r['source_id']in d['retired_source_ids']]
 index=a.TriangleIndex(scene,windows);actual_count=len(index.rows);restores,held=virtual_restorations(index,d);checks=[]
 for owner in owners:
  r=a.audit_polygon(index,owner['polygon_xz_m'],owner['floor_y_m']);r.update(owner);checks.append(r)
 side=side_clearance.SideIndex(scene,windows).audit(owners)
 report=dict(schema='riverstone.r17.layout_snapshot_preflight.v1',base_scene_sha256=a.SCENE_SHA256,source_layout=dict(path=str((folder/'selected_layout.json').relative_to(a.ROOT)),sha256=a.sha(folder/'selected_layout.json')),proposed_retired_ids=d['retired_source_ids'],held_retirement_ids=held,hypothetical_body_restoration_triangles=restores,top_checks=checks,retained_side_clearance=side,summary=dict(holdings=len(d['holdings']),actual_doors=len(d['actual_doors']),finite_regions=len(owners),top_regions_pass=sum(c['passes_existing_surface']for c in checks),top_regions_held=sum(not c['passes_existing_surface']for c in checks),retained_side_contacts=len(side['contacts']),actual_source_triangles=actual_count,seconds=time.monotonic()-start),activation=False,remaining=['Final complete internal door routes and public/private graph.','Exact new native/cache mask proof and cross-pack body clearance.','Old private door/landing retirement and finite source-index composition.','Actual scene/controller validation.'])
 (folder/'report.json').write_text(json.dumps(report,separators=(',',':'))+'\n');print(report['summary']);print('held retirement',held);print('held owners',[(c['id'],round(c['missing_area_m2'],5),round(c['max_floor_delta_m']or 0,5))for c in checks if not c['passes_existing_surface']][:35]);print(a.sha(folder/'report.json'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--name',default='layout_draft_r01');run(p.parse_args().name)
