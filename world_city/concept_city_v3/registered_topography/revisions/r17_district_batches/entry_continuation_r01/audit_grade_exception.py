"""Independent finite face/coverage check for the approved B010 local option."""
import json,math
from pathlib import Path
from .. import author as a
HERE=Path(__file__).resolve().parent;SOURCE=HERE.parent/'contour_bulk_r01'
def run():
 f=HERE/'local_grade_options/PRIVATE_GROUP_BLOCK_010_R8_C006_15.json';assert a.sha(f)=='2454e6b49050a8c14b889ff8d4faaff63652d957cf1ff3a1415704b696a47c0e';d=json.loads(f.read_bytes());source=json.loads((a.ROOT/d['source_profile']['path']).read_bytes());g=next(r for r in json.loads((SOURCE/'shared_private_groups_r03.json').read_bytes())['groups']if r['id']==d['id']);datum=d['result']['datum_changes'][0];regions=source['public_fixed_regions']+[dict(r,plane_y_xz_m=[0,0,datum['candidate_floor_y_m']])for r in g['gate_fixed_regions']];idx=a.geo._SpatialIndex(4)
 for i,r in enumerate(regions):idx.add(i,r['polygon_xz_m'])
 maxerr=0.;checks=0;area=0.;grades=[];down=0
 for t in d['result']['triangles']:
  tr=t['vertices_xyz_m'];plane=a.common.plane(tr);grades.append(math.hypot(*plane[:2]));area+=a.geo.polygon_area(t['polygon_xz_m']);down+=a.normal_y(tr)<=0
  for v in tr:
   p=[v[0],v[2]]
   for j in idx.candidates([p]):
    r=regions[j]
    if a.geo.point_in_convex_polygon(p,r['polygon_xz_m'],1e-9):maxerr=max(maxerr,abs(v[1]-a.common.height(r['plane_y_xz_m'],p)));checks+=1
 expected=sum(a.geo.polygon_area(p)for p in source['private_domain_polygons_xz_m']);report=dict(status='PASS_FINITE_15_PERCENT_EXCEPTION_SOURCE',source_profile=dict(path=str(f.relative_to(a.ROOT)),sha256=a.sha(f)),holding_id=d['holding_ids'][0],upward_triangles=len(grades),downward_triangles=down,maximum_actual_gradient=max(grades),fixed_public_and_court_vertex_checks=checks,maximum_fixed_error_m=maxerr,expected_domain_area_m2=expected,actual_triangle_area_m2=area,coverage_area_error_m2=area-expected,datum_change=datum,policy='Explicit bounded service-ramp design exception authorized by parent. Full public profiles remain exact. Cart suitability and actual unchanged-controller passage remain separate pending acceptance.',activation=False)
 assert not down and max(grades)<=.15000001 and maxerr<1e-7 and abs(area-expected)<1e-7
 out=HERE/'b010_c006_exception_audit_r01.json';assert not out.exists();out.write_text(json.dumps(report,separators=(',',':'))+'\n');print(report)
if __name__=='__main__':run()
