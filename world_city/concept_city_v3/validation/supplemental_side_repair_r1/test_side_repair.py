import sys,pathlib,json,hashlib,math,time
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r09_training_access.recovery_support import author as source,approaches as a
from world_city.concept_city_v3.validation.supplemental_side_repair_r1.side_repair import side_records,DATA_SHA256
D=json.loads((H/'finite_road_corner_restoration.json').read_text());patch=D['restorations'][0]
def owner(x,z):return patch if a.geo.point_in_convex_polygon([x,z],patch['polygon_xz_m'],1e-10) else source.owner_at(x,z)
def height(r,x,z):
 if r['owner_id']==patch['owner_id']:
  assert a.geo.point_in_convex_polygon([x,z],patch['polygon_xz_m'],1e-9),'outside finite patch'
  return a.point_y(patch['triangle_xyz_m'],x,z)
 return source.source_surface_height_at(r,x,z)
before={str(pathlib.Path(m.__file__).relative_to(ROOT)):hashlib.sha256(pathlib.Path(m.__file__).read_bytes()).hexdigest() for m in [source,a]}
# Reproduce the original failure on its minimal actual triangle fixture without
# scanning the full city or changing original globals.
import types
failure=json.loads((H/'targeted_original_endpoint_failures.json').read_text())['failures'][0]
g=dict(a.side_records.__globals__);g['supplemental_surface_domains']=lambda bounds:[failure['source']]
original_fixture=types.FunctionType(a.side_records.__code__,g,a.side_records.__name__,a.side_records.__defaults__,a.side_records.__closure__)
try:original_fixture([-530,-530,530,656],source.owner_at,source.source_surface_height_at)
except ValueError as e:original_error=str(e)
else:raise AssertionError('Original failure did not reproduce')
assert original_error=='Point outside finite public landing'
try:side_records([-530,-530,530,656],source.owner_at,source.source_surface_height_at)
except ValueError as e:inactive_error=str(e)
else:raise AssertionError('Repair accepted inactive restoration')
assert inactive_error=='Explicit finite restored road owner is not active'
# Compare every unaffected output against the earlier full-city original ledger.
ledger=json.loads((H/'original_endpoint_failures.json').read_text());expected=[]
for r in ledger['preceding_unaffected_edges']:
 av,bv=r['edge_xyz_m'];ys=r['bottom_ys_m'];p=[av[0],av[2]];q=[bv[0],bv[2]]
 if max(abs(av[1]-ys[0]),abs(bv[1]-ys[1]))<1e-6:continue
 key=tuple(sorted(tuple(round(v,7) for v in t) for t in (p,q)))
 expected.append(dict(id='RECOVERED_APPROACH_SIDE_'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:18],material_hint='stone',vertices_xyz_m=[av,bv,[q[0],ys[1],q[1]],[p[0],ys[0],p[1]]],outside_owner_id=r['outside_owner']['owner_id'],status='reconstructed finite support side; collision not approved'))
audit={};start=time.perf_counter();actual=side_records([-530,-530,530,656],owner,height,audit)
expected_by_id={r['id']:r for r in expected};actual_by_id={r['id']:r for r in actual}
missing=[k for k in expected_by_id if k not in actual_by_id];changed=[k for k in expected_by_id if k in actual_by_id and expected_by_id[k]!=actual_by_id[k]];added=[v for k,v in actual_by_id.items() if k not in expected_by_id]
report=dict(status='pass' if not missing and not changed else 'failed',original_minimal_error=original_error,inactive_restoration_rejected=True,original_boundary_edges=ledger['checked_boundary_edges'],original_undefined_edges=len(ledger['failures']),unaffected_emitted_sides=len(expected),repaired_emitted_sides=len(actual),missing_unaffected=missing,changed_unaffected=changed,added_records=added,audit=audit,wall_seconds=time.perf_counter()-start,restoration_sha256=DATA_SHA256,wrapper_sha256=hashlib.sha256((H/'side_repair.py').read_bytes()).hexdigest(),checker_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),inputs=before,geometry_scope='Side algorithm parity and explicit finite road restoration fixture; terrain adapter/native/controller integration separate.')
for name,h in before.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h
(H/'side_repair_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('audit','inputs','added_records')},indent=2));assert report['status']=='pass';assert len(audit['subdivisions'])==1
