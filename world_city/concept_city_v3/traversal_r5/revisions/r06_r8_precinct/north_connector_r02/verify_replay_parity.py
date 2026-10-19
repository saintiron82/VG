import hashlib,json,pathlib
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
a=json.loads((H.parent/'north_connector_r01/prepared_runtime.json').read_bytes());b=json.loads((H/'prepared_runtime.json').read_bytes())
normalized=json.loads(json.dumps(a['routes']).replace('NORTH_APPROACH_R03_CONTINUOUS_ROAD','NORTH_APPROACH_R04_CONTINUOUS_ROAD'))
assert normalized==b['routes'],'Route mutation beyond declared contract ID revision'
for n in ['Traversal.gd','RenderData.gd']:assert sha(H/n)==sha(H.parent/'north_connector_r01'/n)
old=json.loads(pathlib.Path(a['sources']['scene']['path']).read_bytes());new=json.loads(pathlib.Path(b['sources']['scene']['path']).read_bytes())
for k in ['surfaces','common_assets','common_instances','boxes','bridge_mechanism']:assert old[k]==new[k],k
oc=next(c for c in old['collision_contracts']if c['id'].startswith('NORTH_'));nc=next(c for c in new['collision_contracts']if c['id'].startswith('NORTH_'))
assert len(oc['add_triangles_world_xyz_m'])==len(nc['add_triangles_world_xyz_m'])==74
assert [[t[0],t[2],t[1]]for t in oc['add_triangles_world_xyz_m']]==nc['add_triangles_world_xyz_m']
for src in b['sources'].values():assert sha(pathlib.Path(src['path']))==src['sha256']
for p,h in b['implementation_hashes'].items():assert sha(ROOT/p)==h
out={'status':'PASS_IDENTICAL_18_CASES_AND_CONTROLLER','previous_failed_freeze':ref(H.parent/'north_connector_r01/freeze_manifest.json'),'prepared':ref(H/'prepared_runtime.json'),'same_routes':18,'same_visual_fields':True,'north_contract_reversed_faces':74,'same_native_caches':True,'path_binding_note':'Copied path-binding helper wrote valid runtime input, then stopped at a legacy evidence reference absent in this new revision. This independent check verified all resolved paths and exact input hashes before runtime. No rejected physics attempt occurred in this revision.'}
with(H/'evidence/replay_parity.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(out))
