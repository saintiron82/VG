from pathlib import Path
import sys,json,hashlib,numpy as np
OUT=Path(__file__).resolve().parent; N=OUT.parent;ROOT=N.parents[6]
# Anchor to the repository rather than any caller's working directory.
ROOT=next(p for p in OUT.parents if (p/'world_city/concept_city_v3').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as fg

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def digest(x):return hashlib.sha256(json.dumps(x,separators=(',',':'),allow_nan=False).encode()).hexdigest()
Q=[dict(material='land_D_NOBLE',triangle_index=14907,polygon_xz_m=[[-156.374459,-136.50149654309254],[-156.374459,-136.439306],[-159.75490788192386,-136.439306]]),dict(material='land_D_NOBLE',triangle_index=15379,polygon_xz_m=[[-149.00077885362657,-128.4387567771745],[-149.,-128.43885016498024],[-149.,-128.437389318108]]),dict(material='land_D_NOBLE',triangle_index=16054,polygon_xz_m=[[-148.000341250546,-123.98246769060515],[-148.,-123.98252406872356],[-148.,-123.98155710277138]])]
collarpath=N/'private_collars.json'; patchpath=N/'normalization_final_r02/noble_surface_patch.json'
collars=json.loads(collarpath.read_text())['owners'];patch=json.loads(patchpath.read_text());vs=patch['appended_surfaces']['ground_stone'];tris=[vs[i:i+3]for i in range(0,len(vs),3)];rows=[]
for query in Q:
 q=query['polygon_xz_m'];hits=[]
 for i,r in enumerate(collars):
  clip=fg.clip(q,r['polygon_xz_m'])
  if fg.area(clip)<=1e-14:continue
  emitted=[]
  for ti,t in enumerate(tris):
   x=fg.clip(clip,[[v[0],v[2]]for v in t]);a=fg.area(x)
   if a<=1e-14:continue
   p=r['plane_y_xz_m'];maxerr=max(abs(v[1]-(p[0]*v[0]+p[1]*v[2]+p[2]))for v in t)
   if maxerr>1e-7:continue
   emitted.append(dict(material='ground_stone',appended_triangle_index=ti,triangle_sha256=digest(t),vertices_xyz_m=t,intersection_polygon_xz_m=x,area_m2=a,maximum_plane_error_m=maxerr))
  uncovered=fg.subtract([clip],[e['intersection_polygon_xz_m']for e in emitted]);err=sum(fg.area(x)for x in uncovered)
  assert err<1e-10,(r['id'],err)
  hits.append(dict(source_owner_array_index=i,owner=r,intersection_polygon_xz_m=clip,area_m2=fg.area(clip),emitted_source_triangles=emitted,uncovered_by_emitted_floor_area_m2=err))
 missing=fg.subtract([q],[h['intersection_polygon_xz_m']for h in hits]);missingarea=sum(fg.area(x)for x in missing)
 rows.append(dict(query,query_area_m2=fg.area(q),owners=hits,remaining_area_m2=missingarea,remaining_polygons_xz_m=missing,status='EXACT_EMITTED_NOBLE_PRIVATE_COLLAR_PRIORITY'if hits and missingarea<1e-10 else 'NO_NOBLE_COLLAR_COVERAGE_DO_NOT_EXCLUDE_AS_NOBLE'))
report=dict(id='R8_NOBLE_R02_RESIDUAL_LANDUSE_PRECEDENCE_REVIEW_R01',source_log=ref(ROOT/'world_city/concept_city_v3/registered_integration/r8/landuse_noble_trial_1205.log'),collar_source=ref(collarpath),emitted_patch=ref(patchpath),rows=rows,excluded_color_reassignment_owner_polygons=[h['owner']for h in rows[0]['owners']],policy='Read-only exact ownership classification. Exclude these actual emitted collars from obsolete same-plane material reassignment; retain every current plane. The two tiny queries without noble ownership remain separately unresolved; no area tolerance is enlarged.',runtime_acceptance_claim=False)
(OUT/'ownership_report.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'SOURCE_SEAL.json').write_text(json.dumps(dict(sources=[ref(Path(__file__)),ref(OUT/'ownership_report.json'),ref(collarpath),ref(patchpath)],tests=dict(first_query_fully_owned=rows[0]['remaining_area_m2']<1e-10,all_ten_owner_pieces_actually_emitted=len(rows[0]['owners'])==10,other_queries_not_misclassified=not rows[1]['owners']and not rows[2]['owners'])),indent=2)+'\n')
print(ref(OUT/'ownership_report.json'));print([(r['triangle_index'],r['query_area_m2'],len(r['owners']),r['remaining_area_m2'])for r in rows])
