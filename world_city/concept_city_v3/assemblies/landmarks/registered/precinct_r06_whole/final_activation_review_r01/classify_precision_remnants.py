"""Classify the strict source-material projection difference against exact runtime retirements."""
from audit_materials import *
import numpy as np

def main():
    audit_path=OUT/'functional_material_review.json';audit=load(audit_path)
    precision_path=CITY/'evidence/r8_final110_precision_r01/runtime_precision_ledger.json';precision=load(precision_path)
    sourceplan=load(ROOT/audit['source_plan']['path']);plans={r['id']:r for r in sourceplan['regions']}
    removals=precision['removals'];ix=geo._SpatialIndex(4)
    for i,r in enumerate(removals):ix.add(i,[[v[0],v[2]]for v in r['source_triangle_xyz_m']])
    rows=[];unknown=0.;before=0.;zero_covered=0.;touched=set()
    for r in audit['actual_same_plane_rows']:
        polygon=r['polygon_xz_m'];origin=polygon[0];local=lambda p:[[v[0]-origin[0],v[1]-origin[1]]for v in p];world=lambda p:[[v[0]+origin[0],v[1]+origin[1]]for v in p]
        missing=fg.subtract([local(polygon)],[local(x['polygon_xz_m'])for x in r['current_same_plane_coverage']]);area=sum(fg.area(p)for p in missing)
        if not area:continue
        before+=area;source=plans[r['region_id']]['same_plane_functional_ground'][r['source_piece_index']];accepted=[];covered=[]
        for j in ix.candidates(polygon):
            z=removals[j];t=z['source_triangle_xyz_m']
            if z['material']not in(source['material'],source['proposed_material']):continue
            if max(abs(v[1]-terrain.common.height(r['plane_y_xz_m'],[v[0],v[2]]))for v in t)>1e-7:continue
            q=local([[v[0],v[2]]for v in t]);hits=[p for part in missing if (p:=fg.clip(part,q))]
            if not hits:continue
            f=np.asarray(t,dtype=np.float32);assert np.all(np.cross(f[1]-f[0],f[2]-f[0])==0)
            assert canonical(t)==z['source_triangle_sha256']
            accepted.append(q);covered.append(dict(material=z['material'],source_triangle_index=z['source_triangle_index'],source_triangle_sha256=z['source_triangle_sha256'],intersection_area_m2=sum(fg.area(p)for p in hits),exact_float32_cross_zero=True));touched.add(j)
        remaining=fg.subtract(missing,accepted);left=sum(fg.area(p)for p in remaining);unknown+=left;zero_covered+=area-left
        rows.append(dict(region_id=r['region_id'],source_piece_index=r['source_piece_index'],initial_projection_difference_m2=area,retired_exact_float32_zero_source_rows=covered,remaining_projection_difference_m2=left,remaining_world_polygons_xz_m=[world(p)for p in remaining]))
    budget=audit['source_plan']['unpainted_color_budget_m2']
    report=dict(status='PASS_DECLARED_PRECISION_RETIREMENTS_AND_EXISTING_COLOR_BOUNDARY_BUDGET'if unknown<=budget else'UNRESOLVED',scene=audit['scene'],strict_material_audit=ref(audit_path),runtime_precision_ledger=ref(precision_path),initial_unmatched_projection_m2=before,exact_zero_retirement_accounted_projection_m2=zero_covered,remaining_authored_color_boundary_projection_m2=unknown,declared_authored_color_boundary_budget_m2=budget,distinct_bound_zero_retirement_rows=len(touched),rows=rows,policy='The failed strict runtime-versus-authored color projection check is retained. Its differences are classified by exact source retirement, never by enlarging a zero predicate or geometric area threshold. No geometry is added or changed.',runtime_walkability='PENDING_ORIGINAL_CONTROLLER_REPLAY')
    (OUT/'precision_material_addendum.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in('rows','policy','strict_material_audit','runtime_precision_ledger','scene')},indent=2));assert unknown<=budget


if __name__=='__main__':main()
