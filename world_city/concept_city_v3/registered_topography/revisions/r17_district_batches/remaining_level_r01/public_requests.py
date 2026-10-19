"""Publish shared ordinary entry requests without fixing defective old road faces."""
import json,math,collections
from .screen import HERE,BULK
from .. import author as a,native_clearance

def run():
 screen=json.loads((HERE/'entry_screen.json').read_bytes());budget={r['id']:r for r in json.loads((HERE/'required_core_budget.json').read_bytes())['rows']};plan=json.loads(a.PLAN_PATH.read_bytes());roads={r['id']:r for r in plan['roads']};bulk=json.loads(BULK.read_bytes());holdings={}
 for d in bulk['districts']:
  p=native_clearance.require_ref(d['ground_proposal']);lay=native_clearance.require_ref(p['layout'])
  for h in lay['holdings']:holdings[h['id']]=h
 rows=[];classes=collections.Counter()
 for r in screen['entries']:
  h=holdings[r['id']];b=budget[r['id']];road=roads[r['public_road_id']];seg=r['public_segment_index'];pts=road['polyline_xz_m'];station=sum(math.dist(u,v)for u,v in zip(pts[:seg],pts[1:seg+1]))+math.dist(pts[seg],r['canonical_public_center_xz_m']);errs={e['kind']for e in r['source_errors']}
  why='DIRECT_FINITE_PROFILE_MATH_PASS'if r['status']=='FINITE_PROFILE_MATH_CANDIDATE'else'STEEP_OLD_PUBLIC_CROSS_SECTION'if r['source_crossfall_grade']>.12000001 else'INCONSISTENT_OLD_PUBLIC_HEIGHTS'if'discontinuous_public_top'in errs else'INCOMPLETE_OLD_PUBLIC_EDGE_COVERAGE'if errs else'FINITE_QUAD_OR_FIXED_PROFILE_HOLD'
  classes[why]+=1
  mid=[sum(p[k]for p in r['public_edge_xz_m'])/2 for k in(0,1)];run=math.dist(h['gate_position_xz_m'],mid)
  rows.append(dict(id=r['id']+':R18_ENTRY_REQUEST',holding_id=r['id'],block_id=r['block_id'],public_road_id=r['public_road_id'],canonical_segment_index=seg,canonical_station_m=station,canonical_center_xz_m=r['canonical_public_center_xz_m'],requested_public_edge_xz_m=r['public_edge_xz_m'],width_m=r['width_m'],private_gate_xz_m=h['gate_position_xz_m'],private_gate_edge_xz_m=r['private_start_edge_xz_m'],current_court_floor_y_m=r['floor_y_m'],court_design_datum_interval_y_m=[r['floor_y_m']+b['maximum_required_core_cut_m']-2.5,r['floor_y_m']-b['maximum_required_core_fill_m']+2.5],private_approach_length_m=run,necessary_endpoint_height_interval_y_m=[r['floor_y_m']-.12*run,r['floor_y_m']+.12*run],source_reserved_route_polygons_xz_m=h['external_route_polygons_xz_m'],source_holding_polygon_xz_m=h['holding_polygon_xz_m'],proposed_finite_profile_polygon_xz_m=r['polygon_xz_m'],old_face_screen=why,old_face_errors=r['source_errors'],old_source_crossfall_grade=r['source_crossfall_grade'],old_source_faces=r['source_public_faces'],binding_policy='Request only: regenerated R18 transverse profile must be returned by source hash. Existing accepted B15/native/precinct/water seams have priority. Old inconsistent or absent corner heights are evidence, not fixed constraints. Any court datum change requires atomic native-origin/door rebinding. Endpoint interval is necessary only; actual triangles still require full gradient, native/water/owner and seam checks.',activation=False))
 out=dict(schema='riverstone.r17.contour_public_requests.v1',base_scene=dict(path=str(a.SCENE_PATH.relative_to(a.ROOT)),sha256=a.SCENE_SHA256),canonical_plan=dict(path=str(a.PLAN_PATH.relative_to(a.ROOT)),sha256=a.sha(a.PLAN_PATH)),source_bulk=dict(path=str(BULK.relative_to(a.ROOT)),sha256=a.sha(BULK)),entries=rows,summary=dict(entries=len(rows),classification=dict(classes),required_core_design_holds=0),required_response=['holding_id','public_road_id','profile_regions: finite polygons and exact XYZ triangles','shared_edge_xyz_m: all finite knots','source/contract sha256','accepted or held reason'],scope='Shared frontage requests for one continuous public field. Mathematical profile candidates are not scene or route acceptance.',activation=False)
 p=HERE/'public_interface_requests.json';assert not p.exists();p.write_text(json.dumps(out,separators=(',',':'))+'\n');print(out['summary']);print(a.sha(p))
if __name__=='__main__':run()
