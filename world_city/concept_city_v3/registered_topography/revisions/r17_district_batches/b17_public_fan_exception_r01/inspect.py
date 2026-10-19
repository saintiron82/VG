import json,math
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write
HERE=Path(__file__).resolve().parent
SCENE=a.CITY/'evidence/r8_district_r04/scene.json';SHA='3c63a21f4490e1dada6be34428dc2d1ffacd326d8f34b2deee81e378ab6680d7';assert a.sha(SCENE)==SHA;s=json.loads(SCENE.read_bytes());rows=[]
for i in range(53682,53689):
 t=s['surfaces']['road'][i*3:i*3+3];p=[[v[0],v[2]]for v in t];plane=a.common.plane(t);rows.append(dict(material='road',triangle_index=i,source_triangle_sha256=a.canonical_sha(t),vertices_xyz_m=t,polygon_xz_m=p,area_m2=a.geo.polygon_area(p),plane_y_xz_m=plane,gradient=math.hypot(*plane[:2])))
entry=next(r for r in json.loads((a.HERE/'public_dependency_review_r01/actual_public_inputs_r01.json').read_bytes())['entries']if r['holding_id']=='BLOCK_017:R8_I004');bad=[r for r in rows if r['gradient']>.12];d=dict(base_scene=dict(path=str(SCENE.relative_to(a.ROOT)),sha256=SHA),holding_id='BLOCK_017:R8_I004',road_id='BLOCK_017:ALLEY',defect_rows=bad,adjacent_source_rows=rows,exact_entry_overlap_regions=[r for r in entry['profile_regions']if r['source_triangle_index']in{t['triangle_index']for t in bad}],policy='Candidate local canonical public repair. Preserve neighboring genuine public coordinates and all retained native/water owners. The bad triangle alone cannot retain all three old vertices and change its gradient; include finite adjacent road ownership if necessary.',activation=False)
write(HERE/'source_exception.json',d)
for r in rows:print(r)
print('SHA',a.sha(HERE/'source_exception.json'))
