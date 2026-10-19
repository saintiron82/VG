exec(open('world_city/concept_city_v3/registered_topography/revisions/r17_district_batches/south_access/test_routes.py').read().split('for x in [184')[0])
ret=next(x for x in json.loads((H.parent/'retirement_candidates.json').read_text())['rows']if x['source_id']=='B_REG_0161');body=ret['old_terrain_body_hole_polygon_xz_m']
for z in [324,324.5,325,325.5,326,326.5,327,328,329]:
 p=[[106,z-1.75],[142,z-1.75],[142,z+1.75],[106,z+1.75]];r=a.audit_polygon(ix,p,1)
 conflicts=[]
 for i in oi.candidates(p):
  id,k,q=obs[i];t=a.clip(p,q)
  if t and a.geo.polygon_area(t)>1e-8:conflicts.append((id,k,a.geo.polygon_area(t)))
 left=a.common.subtract(r['uncovered_polygons_xz_m'],[body]);rem=sum(a.geo.polygon_area(q)for q in left)
 out={'z':z,**{k:v for k,v in r.items() if k not in ('source_pieces','uncovered_polygons_xz_m')},'conflicts':conflicts,'after_authorized_restoration_missing_m2':rem,'side':side.audit([dict(id='candidate',polygon_xz_m=p,floor_y_m=1)])}
 (H/f'test_west_{z}.json').write_text(json.dumps(out));print('z',z,'missing',r['missing_area_m2'],'delta',r['max_floor_delta_m'],'restore_remaining',rem,'conflicts',conflicts,'side hits',len(out['side']['contacts']),flush=True)
