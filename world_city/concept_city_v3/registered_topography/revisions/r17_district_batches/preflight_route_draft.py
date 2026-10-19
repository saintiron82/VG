"""Early route-first batch screen; no source proposal is activated."""
import json,time
from pathlib import Path
from . import author as a
SOURCE=a.CITY/'assemblies/ordinary/registered/district_fabric_r01'

def main():
 folder=a.HERE/'route_draft_r01'
 if folder.exists():raise SystemExit('Preserve existing draft evidence')
 folder.mkdir();inputs={}
 for name in('backland_routes.json','selected_layout.json'):
  raw=(SOURCE/name).read_bytes();(folder/name).write_bytes(raw);inputs[name]=json.loads(raw)
 routes=inputs['backland_routes.json']['routes'];selected=inputs['selected_layout.json'];retired=set(selected['retired_source_ids']);ledger=json.loads((a.HERE/'retirement_candidates.json').read_text());eligible={r['source_id']for r in json.loads((a.HERE/'retired_body_boundary_audit.json').read_text())['rows']if r['status']=='COMPLETE_LEVEL_BODY_BOUNDARY'};restores=[r for r in ledger['rows']if r['source_id']in retired&eligible]
 windows=[p for r in routes for p in r['polygons_xz_m']]+[r['old_terrain_body_hole_polygon_xz_m']for r in restores];t=time.monotonic();index=a.TriangleIndex(a.load_scene(),windows);native_count=len(index.rows)
 hypothetical=[]
 for r in restores:
  p=r['old_terrain_body_hole_polygon_xz_m'];parts=list(index.covering(p));missing=a.common.subtract([p],[x['intersection_polygon_xz_m']for x in parts])
  for q in missing:
   for tri in a.fan_upward([[x,r['matching_level_band_y_m'],z]for x,z in q]):
    p=[[v[0],v[2]]for v in tri];row=dict(material='hypothetical_retired_body_restore',triangle_index=-len(hypothetical)-1,source_triangle_sha256=None,source_id=r['source_id'],vertices_xyz_m=tri,polygon_xz_m=p,plane_y_xz_m=[0.,0.,r['matching_level_band_y_m']]);index.index.add(len(index.rows),p);index.rows.append(row);hypothetical.append(row)
 results=[]
 for r in routes:
  checks=[a.audit_polygon(index,p,r['floor_y_m'])for p in a.common.disjoint_union(r['polygons_xz_m'])];status='LEVEL_FULL_WIDTH_SOURCE_CANDIDATE'if all(c['passes_existing_surface']for c in checks)else'REQUIRES_ROUTE_REPLAN_OR_EXACT_NATIVE_INTERFACE'
  results.append(dict(route_id=r['id'],floor_y_m=r['floor_y_m'],width_m=r['width_m'],polyline_xz_m=r['polyline_xz_m'],status=status,missing_area_m2=sum(c['missing_area_m2']for c in checks),max_floor_delta_m=max(c['max_floor_delta_m']or 0 for c in checks),max_actual_triangle_grade=max(c['max_actual_triangle_grade']for c in checks),checks=checks))
 report=dict(schema='riverstone.r17.route_draft_preflight.v1',base_scene_sha256=a.SCENE_SHA256,input_refs={n:dict(path=str((folder/n).relative_to(a.ROOT)),sha256=a.sha(folder/n))for n in inputs},hypothetical_retired_body_restorations=hypothetical,held_retirement_ids=sorted(retired-eligible),routes=results,summary=dict(route_count=len(results),complete_level=sum(r['status']=='LEVEL_FULL_WIDTH_SOURCE_CANDIDATE'for r in results),actual_indexed_triangles=native_count,hypothetical_restore_triangles=len(hypothetical),seconds=time.monotonic()-t),activation=False,limits=['This is a route draft; no holding layout existed in the sampled proposal.','Body restorations are hypothetical, pending final retirement/private-door/protected-owner composition.','A geometrically level route still needs connected public/private graph and native obstacle clearance.'])
 (folder/'report.json').write_text(json.dumps(report,separators=(',',':'))+'\n');print(report['summary']);print([(r['route_id'],r['status'],round(r['missing_area_m2'],5),round(r['max_floor_delta_m'],4))for r in results]);print(a.sha(folder/'report.json'))
if __name__=='__main__':main()
