from pathlib import Path
import sys,json
OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(OUT.parent))
from build_ground_patch import *
from world_city.concept_city_v3.registered_integration.r8 import compose_finite_patches as compose
OUT=Path(__file__).resolve().parent
reviewpath=CITY/'registered_topography/revisions/public_corridors_r18/noble_existing_riser_coverage_final_r01.json';d=load(reviewpath);binding=load(OUT.parent/'activation_binding.json');banks=[];idx=geo._SpatialIndex(4)
for pr in binding['patches']:
 p=load(ROOT/pr['path']);vs=p['appended_surfaces'].get('bank',[])
 for i in range(len(vs)//3):
  t=vs[3*i:3*i+3];q=[[v[0],v[2]]for v in t];idx.add(len(banks),q);banks.append((pr,i,t))
rows=[]
for s in d['segments']:
 for k,t in enumerate(s['triangles_xyz_m']):
  n,L,z,project,unproject=compose.project_frame(t);poly=[project(v)for v in t];masks=[];sources=[]
  for i in idx.candidates(s['edge_xz_m']):
   pr,j,tr=banks[i]
   if max(abs(compose.dot(n,v)-z)/L for v in tr)>1e-7:continue
   q=[project(v)for v in tr]
   if fg.area(fg.clip(poly,q))>1e-14:masks.append(q);sources.append(dict(patch=pr,triangle_index=j))
  missing=fg.subtract([poly],masks);area=sum(fg.area(q)for q in missing);rows.append(dict(segment_id=s['id'],triangle_index=k,missing_source_frame_area=area,missing_polygons_xyz_m=[[unproject(v)for v in q]for q in missing],coverage=sources))
report=dict(status='PASS'if max(r['missing_source_frame_area']for r in rows)<1e-9 else'HELD',source=ref(reviewpath),binding=ref(OUT.parent/'activation_binding.json'),rows=rows,maximum_missing_source_frame_area=max(r['missing_source_frame_area']for r in rows));(OUT/'public_riser_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],report['maximum_missing_source_frame_area']);print([(r['segment_id'],r['triangle_index'],r['missing_source_frame_area'])for r in rows if r['missing_source_frame_area']>1e-9])
