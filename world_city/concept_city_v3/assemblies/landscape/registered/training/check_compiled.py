"""Persisted native doors, walking slabs, floor datums and cached crown/prop bounds."""
import json,sys,math
from pathlib import Path
from . import author as t
from world_city.concept_city_v3.assemblies.property.registered import author as a
sys.path.insert(0,str(t.c.CITY/'validation'))
from check_landmark_access_candidate import slab_rectangles,transform
from check_registered_source import spatial
import geometry as g

def run():
 path=t.HERE/'resolved_placements.json';p=json.loads(path.read_text());renders={};obstacles=[];issues=[]
 for key,v in p['asset_manifest'].items():
  assert a.file_sha(v['compiled_asset_ref'])==v['render_sha256'];assert a.file_sha(v['master_path'])==v['master_file_sha256'];renders[key]=json.loads(Path(v['compiled_asset_ref']).read_text())
 for ins in p['placements']:
  dy=18-ins['position_m'][1];render=renders[ins['asset_key']]
  for j,poly in enumerate(slab_rectangles(render,dy+.05,dy+1.85)):obstacles.append(dict(id=ins['id']+':slab:'+str(j),owner_id=ins['id'],poly=transform(poly,ins)))
  if 'footprint_xz_m' in ins:
   b=render['bounds'];lo,hi=b['min'],b['max'];actual=transform([[lo[0],lo[2]],[hi[0],lo[2]],[hi[0],hi[2]],[lo[0],hi[2]]],ins)
   if not a.contained(actual,ins['footprint_xz_m']):issues.append(dict(kind='sampled_bounds_exceed_reserved_native_footprint',id=ins['id'],polygon_xz_m=actual))
 query=spatial(obstacles)
 for r in p['internal_routes']:
  for j,strip in enumerate(r['ribbon_polygons_xz_m']):
   for o in query(strip):
    ar=g.area(g.convex_intersection(strip,o['poly']))
    if ar>1e-5:issues.append(dict(kind='compiled_walking_slab_overlap',route_id=r['id'],segment=j,obstacle_id=o['id'],polygon_xz_m=o['poly'],area_m2=ar))
 for door in p['actual_doors']:
  assert door['actual_cached_threshold_evidence'];assert door['door_xyz_m'][1]==18
  route=next(r for r in p['internal_routes'] if r.get('door_id')==door['id']);assert route['full_polyline_xyz_m'][0]==door['door_xyz_m']
 # The explicit actual-cell road ledger must exactly match the persisted faces it names.
 ground=next(m for m in p['ownership_masks'] if m['kind']=='finite_common_drill_floor_and_access')
 for r in p['actual_public_surface_overrides']:
  face=ground['compiled_upward_faces'][r['compiled_face_index']];assert r['actual_compiled_top_y_m']==face['y_m'];assert a.contained(r['polygon_xz_m'],face['polygon_xz_m']);assert r['road_id']=='CASTLE_APPROACH'
 report=dict(schema='riverstone.registered_training.native_slab_check.v1',resolved_pack_sha256=a.file_sha(path),checker_sha256=a.file_sha(__file__),status='fail' if issues else 'pass_bounded_native_doors_and_ribbons',counts=dict(placements=len(p['placements']),actual_doors=len(p['actual_doors']),full_width_routes=len(p['internal_routes']),native_slab_rectangles=len(obstacles),issues=len(issues)),issues=issues,limits=['No actual capsule/horse-controller, closed-door interior or complete floor-support claim.','The exact source public profile is separate from sampled common top steps; terrain interface acceptance remains required.'])
 (t.HERE/'compiled_checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return report
if __name__=='__main__':raise SystemExit(2 if run()['issues'] else 0)
