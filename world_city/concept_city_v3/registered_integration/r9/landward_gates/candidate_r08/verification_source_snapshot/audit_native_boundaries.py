"""Candidate-bound farm, training edge, and separator source audit."""
import json,sys
from pathlib import Path
from .build_corridors import H,ref,Ground
sys.path.insert(0,str(H/'native_pack'))
import inspect_farm_roads as f
from world_city.runtime_city.checks import placement as geo
C=H/sys.argv[1];farm=json.load(open(C/'farm_pack.json'));ownership=json.load(open(C/'ground_ownership.json'));assets={**f.a.S['common_assets'],**farm['common_assets']};roads=[]
for owner in ownership['owners']:
 if 'GATE_PUBLIC_CORRIDOR'not in owner['id']:continue
 for j,p in enumerate(owner['core_polygons_xz_m']):p=f.ccw(p);roads.append((owner['id'],j,p,f.bb(p)))
additions=[]
for i in farm['add_instances']:
 b=assets[i['asset_key']].get('bounds',f.a.B.get(i['asset_key']));poly=f.poly_for(i,b);hits=f.overlaps(poly,roads)
 if hits:additions.append(dict(id=i['id'],overlaps=hits))
training=[]
for id in ['TRAIN:r09:coarse','TRAIN:r09:fine']:
 i=f.a.I[id];asset=assets[i['asset_key']];path=f.a.ROOT/asset['render_path'];assert f.a.sha(path)==asset['render_sha256'];render=json.load(open(path));hits=[]
 for gn,g in enumerate(render['groups']):
  for qn,q in enumerate(g['quads']):
   u=[q[1][k]-q[0][k]for k in range(3)];v=[q[2][k]-q[0][k]for k in range(3)]
   if u[2]*v[0]-u[0]*v[2]<1e-9:continue
   world=[f.a.world(v,i)for v in q];poly=f.ccw([f.xz(v)for v in world]);h=f.overlaps(poly,roads)
   if h:hits.append(dict(group=gn,quad=qn,overlaps=h))
 training.append(dict(id=id,source=ref(path),overlaps=hits))
patch=json.load(open(C/'surface_patch.json'));edits={(e['material'],e['triangle_index']):e for e in patch['surface_edits']};rows=[]
for r in json.load(open(H/'local_source_faces.json')):
 for t in edits.get((r['material'],r['triangle_index']),{}).get('replacement_triangles_xyz_m',[r['triangle']]):rows.append(dict(r,triangle=t))
rows.extend(dict(material=m,triangle_index=i//3,triangle=vs[i:i+3])for m,vs in patch['appended_surfaces'].items()for i in range(0,len(vs),3));ground=Ground(rows);support=[]
for i in farm['add_instances']:
 if not i['id'].startswith('R9_WEST_PUBLIC_SEPARATOR'):continue
 b=assets[i['asset_key']]['bounds'];points=[f.xz(i['position_m'])]+f.poly_for(i,b);deltas=[i['position_m'][1]+b['min'][1]-ground.at(q)for q in points];support.append(dict(id=i['id'],max_delta_m=max(map(abs,deltas)),deltas_m=deltas))
report=dict(inputs={n:ref(C/n)for n in ['surface_patch.json','ground_ownership.json','farm_pack.json']},scope='Exact native farm/separator footprint and actual retained training-top polygons versus authored public road cores; separator support at center and four footprint corners on resolved ground.',added_instance_road_overlaps=additions,retained_training=training,separator_support=support,status='PASS'if not additions and all(not r['overlaps']for r in training)and all(r['max_delta_m']<=.01 for r in support)else 'FAIL');(C/'native_boundary_audit.json').write_text(json.dumps(report,separators=(',',':'))+'\n');print(json.dumps(dict(status=report['status'],added_overlaps=len(additions),training_overlaps=sum(len(r['overlaps'])for r in training),maximum_separator_support_delta_m=max(r['max_delta_m']for r in support))))
