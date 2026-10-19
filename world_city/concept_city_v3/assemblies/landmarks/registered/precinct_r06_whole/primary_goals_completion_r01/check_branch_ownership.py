from find_branches import *
profile=load(CITY/'validation/landmark_recovery_r1/recovered_rendered_profiles_r2.json');old=load(O/'main_opening_direct_diagnostics.json');rows=[]
for r in old['splices']:
 if not r['id'].startswith('HELD:'):continue
 group=r['id'][5:];sources=[x for k in ['approaches','landings']for x in profile[k]['triangles']if x['group_id']in (group,group+'_public_landing')];ix=geo._SpatialIndex(8)
 for i,s in enumerate(sources):ix.add(i,s['polygon_xz_m'])
 checks=[]
 for p,c in zip(r['polys'],r['support_checks']):
  src=[sources[i]for i in ix.candidates(p)if geo.intersection_area(p,sources[i]['polygon_xz_m'])>1e-10];native=[s['polygon_xz_m']for s in c['source_pieces']if s['material'].startswith('native:')];remaining=terrain.common.subtract([p],[s['polygon_xz_m']for s in src]+native);checks.append(dict(missing_source_owned_area_m2=sum(geo.polygon_area(q)for q in remaining),missing_polygons_xz_m=remaining,recovered_owner_ids=[s['owner_id']for s in src],native_parts_xz_m=native))
 row=dict(group=group,checks=checks,missing_source_owned_area_m2=sum(c['missing_source_owned_area_m2']for c in checks),actual_static_pass=r['passed']);rows.append(row);print(group,row['missing_source_owned_area_m2'],r['passed'])
write('direct_branch_ownership_review.json',dict(profile=ref(CITY/'validation/landmark_recovery_r1/recovered_rendered_profiles_r2.json'),scene=ref(SC),rows=rows,scope='Finite declared approach ownership plus actual native threshold floor, no road-color-only ownership.'))
