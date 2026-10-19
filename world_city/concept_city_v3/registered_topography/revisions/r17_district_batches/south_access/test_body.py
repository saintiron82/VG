exec(open('world_city/concept_city_v3/registered_topography/revisions/r17_district_batches/south_access/test_routes.py').read().split('for x in [184')[0])
r=next(x for x in json.loads((H.parent/'retirement_candidates.json').read_text())['rows']if x['source_id']=='B_REG_0478');p=r['old_terrain_body_hole_polygon_xz_m']
for i in oi.candidates(p):
 id,k,q=obs[i];t=a.clip(p,q)
 if id!='B_REG_0478' and t and a.geo.polygon_area(t)>1e-8:print('conflict',id,k,a.geo.polygon_area(t))
print('body',a.geo.polygon_area(p),a.audit_polygon(ix,p,1)['covered_area_m2']); print('sides',json.dumps(side.audit([dict(id='body',polygon_xz_m=p,floor_y_m=1)])));
print('belowgrade',json.dumps(side.audit([dict(id='body_below_grade',polygon_xz_m=p,floor_y_m=.44,headroom_m=2.76)])))
