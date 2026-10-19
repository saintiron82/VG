"""Independent final-composite source/production/engine outcome audit."""
import json,pathlib,hashlib,mmap,re,math,numpy as np
O=pathlib.Path(__file__).resolve().parent;N=O.parent;ROOT=N.parents[4];P=O/'replay_r01';read=lambda p:json.loads(p.read_text())
def sha(p):
 with pathlib.Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def resolve(r):
 p=pathlib.Path(r['path']);p=p if p.is_absolute()else ROOT/p;assert sha(p)==r['sha256'];return p


d=read(P/'prepared_production_r01.json');base=read(P/'prepared.json');req=read(O/'request.json');prod=read(O/'production_routes_r01.json');run=read(P/'evidence/runtime_r01/run_manifest.json');checks={}
for k,v in d['sources'].items():checks['source:'+k]=sha(pathlib.Path(v['path']))==v['sha256']
for k,v in d['implementation_hashes'].items():checks['implementation:'+k]=sha(ROOT/k)==v
for key in ['assets','placements','buildings','cart_fixture','implementation_hashes']:checks['generator_preserves_'+key]=d[key]==base[key]
checks['original_controller']=sha(P/'Traversal.gd')==sha(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd');checks['common_loader']=sha(P/'RenderData.gd')==sha(ROOT/'voxel_character/common/preview/RenderData.gd');checks['original_cart_fixture']=sha(P/'CartClearance.gd')==sha(N/'CartClearance.gd');checks['no_runtime_source_drift']=all(x['changed_sources']==[]for x in run['runs'])
pr={r['id']:r for r in prod['routes']};rr={r['id']:r for r in d['routes']}
for id,r in pr.items():checks['production_route_exact:'+id]=r==rr[id]
patch=read(resolve(req['finite_patch']));edits={(x['material'],x['triangle_index']):x for x in patch['surface_edits']};oldreq=read(N/'port_full_chain/request.json');g=read(ROOT/oldreq['source_goal_collision']['asset']['render_path']);origin=np.array(oldreq['source_goal_collision']['placement']['position_m']);original={tuple(k):np.array(t)+origin for k,t in zip(g['source_face_indices'],g['triangles'])};floor_count=0
for name in ['PORT_SHED_0','PORT_SHED_5']:
 old=read(N/'port_replay_r01/geometry'/f'{name}.json');org=np.array(old['local_origin_proof']['applied_origin_xyz_m']);expected=dict(original)
 for f,t in zip(old['source_face_indices'],old['triangles']):expected[f['material'],f['base_triangle_index']]=np.array(t)+org
 geo=read(P/'geometry'/f'{name}.json')
 for f,t in zip(geo['source_face_indices'],geo['triangles']):
  mat=f['material']
  if 'appended_triangle_index'in f:
   i=f['appended_triangle_index'];a=patch['appended_surfaces'][mat][i*3:i*3+3];want=np.array([a[0],a[2],a[1]])
  elif f.get('replacement_index') is not None:
   row=edits[mat,f['base_triangle_index']];a=row['source_triangle_xyz_m'];assert np.array_equal(expected[mat,f['base_triangle_index']],np.array([a[0],a[2],a[1]]));a=row['replacement_triangles_xyz_m'][f['replacement_index']];want=np.array([a[0],a[2],a[1]])
  else:want=expected[mat,f['base_triangle_index']]
  assert np.array_equal(np.array(t),want),('Final source face mismatch',name,f);floor_count+=1
 checks['exact_resolved_floor:'+name]=True
# Independently reconstruct exact native composition using formal JSON top-level fields.
# The prior field-name regex failed on nested duplicate keys; its script and log are preserved.
scene=resolve(d['sources']['base_scene']);source_scene=read(scene);instances={x['id']:x for x in source_scene['common_instances']};assets=source_scene['common_assets'];contracts=source_scene['collision_contracts'];del source_scene;index=read(resolve(req['visual_index']));native_sources={}
for entry in index['packs']:
 pp=resolve(entry);pack=read(pp)
 assets.update(pack.get('common_assets',{}))
 for id in pack.get('remove_instance_ids',[]):assert id in instances;instances.pop(id)
 for change in pack.get('replace_instances',[]):
  id=change['id'];old=instances[id];assert old['asset_key']==change['expected_asset_key']and old['position_m']==change['expected_position_m'];instances[id]=dict(old,asset_key=change['asset_key'],palette_id=change['palette_id'],palette_override=change.get('palette_override',{}))
 for ins in pack.get('add_instances',[]):assert ins['id']not in instances;instances[ins['id']]=ins
 native_sources[str(pp.relative_to(ROOT))]=sha(pp)
disabled={id for c in contracts for id in c.get('disable_native_mesh_collider_ids',[])};render_cache={}
def get_render(k):
 if k not in render_cache:
  a=assets[k];p=ROOT/a['render_path'];assert sha(p)==a['render_sha256'];render_cache[k]=read(p)
 return render_cache[k]
def overlaps(a,b):return a[0]<=b[2]and a[2]>=b[0]and a[1]<=b[3]and a[3]>=b[1]
def bounds(ins):
 a=assets[ins['asset_key']];b=a.get('bounds')or get_render(ins['asset_key'])['bounds'];v=np.array([[x,0,z]for x in[b['min'][0],b['max'][0]]for z in[b['min'][2],b['max'][2]]]);yaw=ins.get('yaw_rad',0);c=math.cos(yaw);s=math.sin(yaw);q=v@np.array([[c,0,-s],[0,1,0],[s,0,c]])+ins['position_m'];return[q[:,0].min(),q[:,2].min(),q[:,0].max(),q[:,2].max()]
for r in d['routes']:
 if r['id'].startswith('NEGATIVE')or r['id'].endswith('_REVERSE'):continue
 geo=read(P/'geometry'/f"{r['group']}.json");boxes=geo['corridor_boxes_xz_m'];expected={id for id,ins in instances.items()if id not in disabled and any(overlaps(bounds(ins),bb)for bb in boxes)};actual={id for id in r['placement_ids']if d['placements'][id]['category']=='actual_native_common_mesh'}
 checks['all_final_native_intersections:'+r['id']]=actual==expected
 assert actual==expected,{'missing':sorted(expected-actual),'extra':sorted(actual-expected)}
 for id in actual:
  src=instances[id];p=d['placements'][id];assert p['asset_key']==src['asset_key']and p['position_m']==src['position_m']and p.get('yaw_rad',0)==src.get('yaw_rad',0)
 checks['exact_native_poses:'+r['id']]=True
results={}
for kind in ['capsule','cart']:
 p=P/'evidence/runtime_r01'/f'{kind}.json';report=read(p);pos=[r for r in report['routes']if not r['id'].startswith('NEGATIVE')];neg=[r for r in report['routes']if r['id'].startswith('NEGATIVE')];results[kind]={'status':report['status'],'positive_passed':sum(r['pass']for r in pos),'positive_cases':len(pos),'negative_passed':sum(r['pass']for r in neg),'negative_cases':len(neg),'summary':report['summary'],'failed_cases':[r for r in pos if not r['pass']],'report':{'path':str(p.relative_to(ROOT)),'sha256':sha(p)}}
assert all(checks.values());out={'schema':'riverstone.r10.final_composite_production_logistics_audit.v1','status':'PASS'if all(x['status']=='pass'for x in results.values())else'RUNTIME_FAILURES_RETAINED','checks':checks,'exact_floor_triangles_reconstructed':floor_count,'final_native_pack_sources':native_sources,'results':results,'production_routes':{'path':str((O/'production_routes_r01.json').relative_to(ROOT)),'sha256':sha(O/'production_routes_r01.json')},'limitations':prod['limits']+['Market delivery circuit and exact operational joining probes have separate certificates; these long routes still end at the historical named market goal.']};(O/'evidence_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'exact_floor_triangles_reconstructed':floor_count,'results':{k:[v['positive_passed'],v['negative_passed']]for k,v in results.items()}},indent=2))
