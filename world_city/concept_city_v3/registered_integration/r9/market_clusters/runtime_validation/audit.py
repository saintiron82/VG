"""Verify actual source faces, authentic composition and immutable capsule evidence."""
import hashlib,json,math
from pathlib import Path
import numpy as np
H=Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());P=H/'replay_r01'
def load(p):return json.loads(Path(p).read_bytes())
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
d=load(P/'prepared.json');req=load(H/'request.json');result=load(P/'evidence/capsule_replay.json');assert result['prepared_sha256']==sha(P/'prepared.json')
for r in d['sources'].values():assert sha(r['path'])==r['sha256']
for p,digest in d['implementation_hashes'].items():assert sha(ROOT/p)==digest
for key,a in d['assets'].items():assert sha(ROOT/a['render_path'])==a['render_sha256']
assert sha(P/'Traversal.gd')==sha(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd')
assert sha(P/'RenderData.gd')==sha(ROOT/'voxel_character/common/preview/RenderData.gd')
headless=load(d['sources']['producer_root_headless']['path']);assert headless['visual_index_sha256']==d['sources']['visual_index']['sha256'];assert headless['common_instances']==d['coverage']['native_composition']['resolved_instances']==5683
source=load(d['sources']['base_scene']['path']);patch=load(d['sources']['finite_patch']['path']);assert not patch['surface_edits'] and not patch['removed_foundation_proxy_ids']
all_points={}
for r in d['routes']:
 if r['group']!='ISOLATED_CONTROL':all_points.setdefault(r['group'],[]).extend(r['points'])
counts=[]
for row in d['coverage']['collision_audit']:
 g=row['group'];key='SCENE:R9:MARKET:'+g;geo=load(ROOT/d['assets'][key]['render_path']);origin=d['placements'][key]['position_m'];bb=row['bounds_xz_m']
 assert row['all_route_points_and_full_width_within_crop']
 for p in all_points[g]:assert bb[0]<=p[0]-1.5 and p[0]+1.5<=bb[2] and bb[1]<=p[2]-1.5 and p[2]+1.5<=bb[3]
 actual=[]
 for face,local in zip(geo['source_face_indices'],geo['triangles']):
  mat=face['material'];idx=face.get('base_triangle_index')
  if idx is None:idx=face['appended_triangle_index'];tri=patch['appended_surfaces'][mat][idx*3:idx*3+3];which='append'
  else:tri=source['surfaces'][mat][idx*3:idx*3+3];which='base'
  assert mat!='water';world=[[v[k]+origin[k]for k in range(3)]for v in local];assert world==[tri[0],tri[2],tri[1]],(g,mat,idx)
  actual.append((which,mat,idx))
 expected=[]
 for which,surfaces in [('base',source['surfaces']),('append',patch['appended_surfaces'])]:
  for mat,v in surfaces.items():
   if mat=='water':continue
   arr=np.asarray(v,dtype=np.float64).reshape(-1,3,3);mask=(arr[:,:,0].min(1)<=bb[2])&(arr[:,:,0].max(1)>=bb[0])&(arr[:,:,2].min(1)<=bb[3])&(arr[:,:,2].max(1)>=bb[1])
   expected.extend((which,mat,int(i))for i in np.nonzero(mask)[0])
 assert set(actual)==set(expected) and len(actual)==len(expected),(g,len(actual),len(expected));assert geo['local_origin_proof']['applied_world_roundtrip_error_m']==0
 assert not any(p.startswith('MARKET_stall') for p in row['native_ids'])
 counts.append(dict(group=g,authentic_whole_source_triangles=len(actual),source_faces_removed_within_crop=0,source_faces_added_within_crop=0,full_service_width_contained=True,native_instances=len(row['native_ids'])))
# Exact requested14 source paths and their reverses; no failure-driven steering edit.
source_routes={r['id']:r for r in load(d['sources']['producer_runtime_routes']['path'])['routes']};positives=[r for r in d['routes'] if 'expected_failure'not in r];assert len(positives)==28
for r in positives:
 reverse=r['id'].endswith('_REVERSE');ident=r['id'][:-8]if reverse else r['id'];pts=source_routes[ident]['points'];assert r['points']==(list(reversed(pts))if reverse else pts)
assert {r['id']for r in result['routes']}=={r['id']for r in d['routes']}
positive_results=[r for r in result['routes']if 'expected_failure'not in r];negative_results=[r for r in result['routes']if 'expected_failure'in r]
counter=next(r for r in negative_results if r['id']=='NEGATIVE_ACTUAL_CLUSTER_STALL_COUNTER')
assert len(positive_results)==28 and len(negative_results)==3
report=dict(schema='riverstone.r9.market_physics_evidence_audit.v1',status='PASS' if result['status']=='pass' else 'RUNTIME_FAILURE_RETAINED',source_identity_checks='PASS',full_source_face_parity='PASS',exact_authored_route_parity='PASS',unchanged_controller_and_loader=True,exact_integration_index=ref(ROOT/req['visual_index']['path']),prepared=ref(P/'prepared.json'),runtime_result=ref(P/'evidence/capsule_replay.json'),positive_case_count=28,positive_passed=sum(r['pass']for r in positive_results),customer_directional_cases=14,service_directional_cases=14,negative_controls=[dict(id=r['id'],expected=r['expected_failure'],actual=r['status'],passed=r['pass'],contact_ids=r['obstacle_contact_ids'])for r in negative_results],summary=result.get('summary'),source_bound_crops=counts,old_public493_runtime_rerun=False,limits=['This new replay tests14 selected market paths in both directions only, not all132 market links.','The old493 certification is retained separately and was not rerun here.','A3m service link is tested with the unchanged0.6m diameter pedestrian capsule; no cart physics or full-width lateral sweep is claimed.','Actual source floors and all overlapping native/box colliders are composed. Water display triangles are excluded; no synthetic floor, snapping or controller corrections were added.'])
with (H/'audit_report.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(status=report['status'],positive_passed=report['positive_passed'],positive_cases=28,negative_passed=sum(r['pass']for r in negative_results),crops=len(counts),source_triangles=sum(r['authentic_whole_source_triangles']for r in counts)),indent=2))
