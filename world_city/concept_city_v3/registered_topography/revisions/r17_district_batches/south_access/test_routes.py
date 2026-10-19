import json,pathlib
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.side_clearance import SideIndex
H=pathlib.Path(__file__).resolve().parent;P=H.parents[3]
s=a.load_scene();W=[[100,310],[225,310],[225,380],[100,380]];ix=a.TriangleIndex(s,[W]);side=SideIndex(s,[W]);print('loaded',len(ix.rows),len(side.rows),flush=True)
np=json.loads((P/'registered_integration/r8/coverage_plan/native_projection.json').read_text());rp=json.loads((P/'registered_integration/r8/coverage_plan/block_015_route_parcels.json').read_text())
obs=[];oi=a.geo._SpatialIndex(16)
def add(id,kind,poly):
 if not a.intersects(a.bounds(poly),a.bounds(W)):return
 oi.add(len(obs),poly);obs.append((id,kind,poly))
for r in np['instances']:
 for kind in ('native_owner_parts_xz_m','roof_parts_xz_m'):
  for p in r[kind]:add(r['id'],kind,p)
for i,p in enumerate(rp['special_reserved_polygon_parts_xz_m']):add(str(i),'special_reserved',p)
vs=s['surfaces']['water']
for j in range(0,len(vs),3):add(str(j//3),'water',[[v[0],v[2]]for v in vs[j:j+3]])
for x in [184,185,186,187,188,189]:
 p=[[x-1.75,342],[x+1.75,342],[x+1.75,371],[x-1.75,371]];r=a.audit_polygon(ix,p,1)
 conflicts=[]
 for i in oi.candidates(p):
  id,k,q=obs[i];t=a.clip(p,q)
  if t and a.geo.polygon_area(t)>1e-8:conflicts.append((id,k,a.geo.polygon_area(t)))
 out={'x':x,**{k:v for k,v in r.items() if k not in ('source_pieces','uncovered_polygons_xz_m')},'conflicts':conflicts,'side':side.audit([dict(id='candidate',polygon_xz_m=p,floor_y_m=1)])}
 (H/f'test_{x}.json').write_text(json.dumps(out));print('x',x,'missing',r['missing_area_m2'],'delta',r['max_floor_delta_m'],'conflicts',conflicts,'side hits',len(out['side']['contacts']),flush=True)
