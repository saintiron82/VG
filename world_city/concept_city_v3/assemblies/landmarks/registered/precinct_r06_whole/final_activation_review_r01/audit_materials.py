"""Read-only current surface coverage of the five protected residual-use margins."""
from audit_activation import *
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as fg
import time

def main():
    start=time.monotonic();sp=CITY/'evidence/r8_final110_runtime_r01/scene.json';scene=load(sp)
    assert ref(sp)['sha256']=='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
    bp=CITY/'registered_integration/r8/final_exterior_candidate_r01/whole_city_activation_r03/activation_binding.json';binding=load(bp)
    pr=binding['residual_land_use_plans'][0];plan=load(ROOT/pr['path']);exclusions=[]
    for er in pr['exact_exclusions']:exclusions+=load(ROOT/er['path'])['polygons_xz_m']
    ex=geo._SpatialIndex(8)
    for i,q in enumerate(exclusions):ex.add(i,q)
    chosen=[r for r in plan['regions']if r['named_function_owner']in('SITE_CASTLE','SITE_CASTLE:TRAIN','E4','E7','SITE_MONASTERY')]
    rows=[];ix=geo._SpatialIndex(8);materials=set()
    for region in chosen:
        for j,s in enumerate(region['same_plane_functional_ground']):
            for q in fg.subtract([s['polygon_xz_m']],[exclusions[k]for k in ex.candidates(s['polygon_xz_m'])]):
                if fg.area(q)<=0:continue
                row=dict(s,region_id=region['id'],source_piece_index=j,polygon_xz_m=q,coverage=[])
                ix.add(len(rows),q);rows.append(row);materials.update((s['material'],s['proposed_material']))
    print('finite pieces',len(rows),flush=True)
    for material in sorted(materials):
        flat=scene['surfaces'].get(material,[])
        for i in range(len(flat)//3):
            t=flat[3*i:3*i+3]
            if terrain.normal_y(t)<=0:continue
            poly=[[v[0],v[2]]for v in t]
            for k in ix.candidates(poly):
                row=rows[k]
                if material not in(row['material'],row['proposed_material']):continue
                p=row['plane_y_xz_m'];error=max(abs(v[1]-terrain.common.height(p,[v[0],v[2]]))for v in t)
                if error>1e-7:continue
                origin=poly[0];local=lambda q:[[v[0]-origin[0],v[1]-origin[1]]for v in q]
                q=fg.clip(local(poly),local(row['polygon_xz_m']))
                if fg.area(q)<=1e-12:continue
                world=[[v[0]+origin[0],v[1]+origin[1]]for v in q]
                row['coverage'].append(dict(material=material,scene_triangle_index=i,triangle_sha256=canonical(t),plane_error_m=error,polygon_xz_m=world))
        print('checked',material,len(flat)//3,flush=True)
    summaries=[];details=[];fail=[]
    for region in chosen:
        rr=[r for r in rows if r['region_id']==region['id']];target=old=missing=area=0.;holes=[]
        for r in rr:
            q=r['polygon_xz_m'];origin=q[0];local=lambda p:[[v[0]-origin[0],v[1]-origin[1]]for v in p]
            covered=[local(x['polygon_xz_m'])for x in r['coverage']]
            rem=fg.subtract([local(q)],covered);miss=sum(fg.area(p)for p in rem);missing+=miss;area+=fg.area(q)
            if miss>1e-7:holes.append(dict(source_piece_index=r['source_piece_index'],missing_area_m2=miss,local_origin_xz_m=origin,remaining_local_polygons=rem))
            target+=sum(fg.area(x['polygon_xz_m'])for x in r['coverage']if x['material']==r['proposed_material'])
            old+=sum(fg.area(x['polygon_xz_m'])for x in r['coverage']if x['material']!=r['proposed_material'])
        summary=dict(region_id=region['id'],owner=region['named_function_owner'],function=region['planned_function'],effective_functional_area_m2=area,actual_target_material_area_m2=target,retained_original_material_area_m2=old,unmatched_projection_area_m2=missing,unmatched_pieces_over_1e_7_m2=holes)
        summaries.append(summary)
        details.extend(dict(region_id=r['region_id'],source_piece_index=r['source_piece_index'],polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'],current_same_plane_coverage=r['coverage'])for r in rr)
    budget=pr['unpainted_color_budget_m2'];unmatched=sum(r['unmatched_projection_area_m2']for r in summaries)
    if unmatched>budget:fail.append(dict(total_unmatched_area_m2=unmatched,declared_color_boundary_budget_m2=budget))
    report=dict(status='PASS_CURRENT_SAME_PLANE_FUNCTIONAL_MARGINS'if not fail else'FAIL',scene=ref(sp),binding=ref(bp),source_plan=pr,source_plan_summary=plan['summary'],current_activation_summary=[{k:v for k,v in r.items()if k not in('source_partitions','retained_complete_boundary_triangles','unpainted_color_boundaries')}for r in scene['r8_residual_land_use']],protected_region_summaries=summaries,actual_same_plane_rows=details,failures=fail,seconds=time.monotonic()-start,limits=['Material/functional ownership evidence only; no new surface, route or runtime traversal claim.','Nonwalking slopes, native reservations and existing missing-top areas keep their explicit source dispositions and are not promoted to functional walking ground.','Target-color completion is not asserted for conservatively retained original-material boundary triangles.'])
    (OUT/'functional_material_review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],regions=len(summaries),effective_area_m2=sum(r['effective_functional_area_m2']for r in summaries),unmatched_area_m2=unmatched,seconds=report['seconds']),indent=2));assert not fail


if __name__=='__main__':main()
