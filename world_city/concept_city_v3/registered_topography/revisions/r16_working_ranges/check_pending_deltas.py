"""Read-only comparison with the three known R6 finite terrain inputs."""
import json
from . import author as a
PATCHES=[
 a.CITY/'registered_topography/revisions/r15_merchant_local_patch/subset_07/scene_patch.json',
 a.CITY/'traversal_r5/revisions/r02/scene_patch.json',
 a.CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase01/combined_clergy_ground_patch.json']

def run():
 f=a.FrozenLocal();regions=a.native_holes()+a.court_regions()+a.terminal_domains();index=a.geo._SpatialIndex(8)
 for i,r in enumerate(regions):index.add(i,r['polygon_xz_m'])
 touched=set()
 for r in regions:
  for q in f.cover(r['polygon_xz_m']):touched.add((q['material'],q['source_triangle_index']))
 reports=[]
 for p in PATCHES:
  data=json.loads(p.read_bytes());changed={(r['material'],r['triangle_index']) for r in data['surface_edits']};hits=touched & changed;overlaps=[]
  for material,vertices in data['appended_surfaces'].items():
   for start in range(0,len(vertices),3):
    poly=[[v[0],v[2]] for v in vertices[start:start+3]]
    if not a.clean(poly):continue
    for i in index.candidates(poly):
     q=a.clean(a.geo.convex_intersection(poly,regions[i]['polygon_xz_m']))
     if q:overlaps.append(dict(material=material,triangle_index=start//3,owner_id=regions[i]['id'],area_m2=a.geo.polygon_area(q)))
  reports.append(dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p),base_scene_sha256=data['base_scene_sha256'],intersecting_original_triangle_edits=sorted(hits),appended_surface_overlaps=overlaps))
 return dict(schema='riverstone.r16_known_delta_review.v1',status='READ_ONLY_PROVISIONAL_R6_INPUT_COMPARISON',r6_scene_binding=None,source_snapshot=a.read('evidence/frozen_r5_local_triangles.json')['scene'],source_triangle_keys_checked=len(touched),reports=reports,limits=['Source snapshot refers to R5 scene.json; future R6 binding must verify actual XYZ, not rely on old triangle indices alone.','Only the three listed terrain patches were checked. Native instance additions need their own final pack conflict audit.'])
if __name__=='__main__':
 p=a.HERE/'known_r6_delta_audit.json'
 if p.exists():raise SystemExit('Evidence already exists')
 d=run();p.write_text(json.dumps(d,separators=(',',':'))+'\n');print(a.sha(p));print([(r['path'],len(r['intersecting_original_triangle_edits']),len(r['appended_surface_overlaps'])) for r in d['reports']])
