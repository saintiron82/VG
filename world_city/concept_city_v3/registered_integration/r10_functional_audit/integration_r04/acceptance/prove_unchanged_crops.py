"""Transfer only exact unchanged bounded collision domains, never claim a new replay."""
from pathlib import Path
import collections,hashlib,json
H=Path(__file__).resolve().parents[2];R=next(p for p in H.parents if(p/'voxel_character').is_dir())
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(R)),'sha256':sha(p)}
a=H/'integration_r03/surface_patch.json';b=H/'integration_r04/surface_patch.json';old,new=read(a),read(b)
assert old['surface_edits']==new['surface_edits']
assert old.get('removed_foundation_proxy_ids',[])==new.get('removed_foundation_proxy_ids',[])
assert sha(H/'integration_r03/index.json')==sha(H/'integration_r04/index.json')
def faces(d):
 return collections.Counter((m,tuple(tuple(x)for x in v[i:i+3]))for m,v in d['appended_surfaces'].items()for i in range(0,len(v),3))
o,n=faces(old),faces(new);removed=o-n;added=n-o
changed=[(m,t) for pool in (removed,added)for (m,t),count in pool.items()for _ in range(count)]
def overlaps(t,bb):
 return min(p[0]for p in t)<=bb[2]and max(p[0]for p in t)>=bb[0]and min(p[2]for p in t)<=bb[3]and max(p[2]for p in t)>=bb[1]
paths=[H/'interface_runtime'/x/'prepared.json'for x in ['final_interfaces_replay_r01','final_clergy_replay_r01','final_market_join_replay_r01','graph_block011_replay_r01']]
paths.append(H/'network/port_final_composite/replay_r01/prepared_production_r01.json')
records=[]
for p in paths:
 d=read(p);patch_ref=d['sources'].get('finite_patch',d['sources'].get('final_finite_patch'));assert patch_ref['sha256']==sha(a)
 tests=[]
 for row in d['coverage']['collision_audit']:
  if 'bounds_xz_m' in row: boxes=[row['bounds_xz_m']]
  else:
   key='SCENE:R10:PORT_FULL:'+row['group'];asset=d['assets'][key];geo_path=R/asset['render_path'];assert sha(geo_path)==asset['render_sha256'];geo=read(geo_path);boxes=geo['corridor_boxes_xz_m']
  hits=[{'material':m,'triangle_xyz_m':t}for m,t in changed if any(overlaps(t,bb)for bb in boxes)]
  tests.append({'group':row['group'],'bounds_xz_m':boxes,'changed_triangles_intersecting_crop':len(hits),'first_hits':hits[:3],'status':'EXACT_UNCHANGED_COLLISION_DOMAIN'if not hits else'NEW_REPLAY_REQUIRED'})
 records.append({'prepared':ref(p),'domains':tests,'status':'EXACT_UNCHANGED_COLLISION_DOMAINS'if all(not x['changed_triangles_intersecting_crop']for x in tests)else'REPLAY_REQUIRED'})
out={'schema':'riverstone.exact_collision_domain_transfer.v1','status':'PASS_UNCHANGED_DOMAINS_ONLY'if all(x['status']=='EXACT_UNCHANGED_COLLISION_DOMAINS'for x in records)else'PARTIAL_REPLAY_NEEDED','prior_patch':ref(a),'current_patch':ref(b),'same_source_edit_arrays':True,'same_removed_foundation_proxy_ids':True,'native_visual_index_byte_identical':True,'removed_appended_triangles':sum(removed.values()),'new_appended_triangles':sum(added.values()),'records':records,'limits':['This is a structural equality proof for already tested bounded collision crops, not a fresh engine replay.','Native instances, source faces, replacement faces and every unchanged appended face remain exact. Changed faces are proven outside each full selected collision AABB.','Gate candidate is changed and has its own fresh 26 capsule/26 cart replay; historical old493 is not globally promoted by this proof.']}
p=Path(__file__).with_name('unchanged_crop_transfer.json');assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'records':[{ 'prepared':x['prepared']['path'],'status':x['status']}for x in records]},indent=2))
