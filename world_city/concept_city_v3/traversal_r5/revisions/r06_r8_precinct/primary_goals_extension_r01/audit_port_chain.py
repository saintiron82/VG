"""Check the new port turn against the exact selected fixed-span contract."""
import hashlib,json,pathlib,numpy as np
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());C=ROOT/'world_city/concept_city_v3'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def resolve(r):
 p=ROOT/r['path'];assert sha(p)==r['sha256'];return p
h=read(H/'port_route_handoff_r02.json');p=read(resolve(h['source_proof']));profile=read(resolve(p['fixed_profile']));audit=read(resolve(p['fixed_full_band_audit']));guard=read(resolve(p['selected_guard_compatibility']));contractp=C/'registered_integration/r8/final_exterior_candidate_r01/whole_city_activation_r03/contract_10.json';c=read(contractp);t=np.array(c['add_triangles_world_xyz_m']);xz=t[:,:,[0,2]];lo=xz.min(axis=1);hi=xz.max(axis=1);checks=dict(guard_compatibility_pass=guard['status']=='PASS'and guard['fixed_span_geometry_unchanged'],fixed_band_audit_pass=audit['status']=='PASS',all_source_slice_checks=all(p['checks'].values()),actual_selected_contract_id=c['id']=='FIXED_BRIDGE_STONE_SPANS_CONTINUOUS_WALK_R02');knots=[]
for v in p['new_native_join']['points_world_xyz_m']:
 q=np.array(v)[[0,2]];ids=np.where(np.all(q>=lo-1e-9,axis=1)&np.all(q<=hi+1e-9,axis=1))[0];hits=[]
 for i in ids:
  a,b,z=xz[i];m=np.column_stack((b-a,z-a));det=np.linalg.det(m)
  if abs(det)<1e-16:continue
  u,w=np.linalg.solve(m,q-a)
  if u>=-1e-9 and w>=-1e-9 and u+w<=1+1e-9:
   y=t[i,0,1]+u*(t[i,1,1]-t[i,0,1])+w*(t[i,2,1]-t[i,0,1]);hits.append(dict(contract_triangle_index=int(i),y_m=float(y),error_m=float(abs(y-v[1]))))
 assert hits and max(x['error_m']for x in hits)<1e-10
 knots.append(dict(point_world_xyz_m=v,actual_contract_hits=hits))
checks['all_join_knots_on_exact_selected_contract']=True;checks['profile_band_within_audited_headroom']=p['new_native_join']['native_butt_ended_join_bounds_local_xz_m'][1]>=-3.75 and p['new_native_join']['native_butt_ended_join_bounds_local_xz_m'][3]<=3.75
assert all(checks.values());out=dict(status='SOURCE_PASS_RUNTIME_PENDING',handoff=dict(path=str((H/'port_route_handoff_r02.json').relative_to(ROOT)),sha256=sha(H/'port_route_handoff_r02.json')),selected_contract=dict(path=str(contractp.relative_to(ROOT)),sha256=sha(contractp)),checks=checks,join_knot_plane_checks=knots,limits=['Only source continuity and the new bounded native turn are checked here; full-chain controller acceptance remains pending.'])
with(H/'port_source_audit.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
files=['build_port_chain_r02.py','audit_port_chain.py','port_chain_proof_r02.json','port_route_handoff_r02.json','port_source_audit.json']
with(H/'port_source_seal_r01.json').open('x')as f:json.dump(dict(status='QUIESCENT_PORT_SOURCE_FILES_ONLY',files={n:sha(H/n)for n in files}),f,indent=2);f.write('\n')
print(json.dumps(dict(checks=checks,seal_sha256=sha(H/'port_source_seal_r01.json'))))
