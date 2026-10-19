"""Production logistics route input, using the same owner-bound output as replay."""
import sys,pathlib,json,hashlib,math,copy,numpy as np
O=pathlib.Path(__file__).resolve().parent;N=O.parent;ROOT=O.parents[5];sys.path.insert(0,str(N))
from route_support_profile import OwnerSurface,RouteSupportSampler,generate_waypoint_profile,guard_cart_input_profile,ProfileError
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();P=O/'replay_r01';PREP=P/'prepared.json';CAP=N/'port_full_chain/replay_r01/evidence/runtime_r02/capsule.json';d=read(PREP);caps={r['id']:r for r in read(CAP)['routes']};surfaces={};sources={}
def surface(owner):
 if owner in surfaces:return surfaces[owner]
 pl=d['placements'][owner];a=d['assets'][pl['asset_key']];path=ROOT/a['render_path'];assert sha(path)==a['render_sha256'];mesh=read(path)
 if 'triangles'in mesh:t=np.array(mesh['triangles'],float)
 else:t=np.array([[q[k]for k in order]for g in mesh['groups']for q in g['quads']for order in [[0,2,1],[0,3,2]]],float)
 if pl.get('transform',{}).get('basis'):basis=np.array(pl['transform']['basis'])
 else:
  yaw=math.radians(pl.get('yaw_deg',0));c=math.cos(yaw);s=math.sin(yaw);basis=np.array([[c,0,s],[0,1,0],[-s,0,c]])
 t=t@basis.T+np.array(pl['position_m']);surfaces[owner]=OwnerSurface(owner,t,sha(path));sources[owner]={'path':str(path),'sha256':sha(path),'placement':pl};return surfaces[owner]
module_original=N/'route_support_profile.py';module_sha_at_start=sha(module_original);snapdir=O/'source_snapshots';snapdir.mkdir(exist_ok=True);module_snapshot=snapdir/(module_sha_at_start+'_route_support_profile.py');module_snapshot.write_bytes(module_original.read_bytes())
ledger=[];routes=[];errors=[]
for r in d['routes']:
 if r['id'].startswith('NEGATIVE_')or r['id'].endswith('_REVERSE'):continue
 obs=caps[r['id']]['position_samples'];owners={s['support_id']for s in obs};contracts=[x for x in r['placement_ids']if x.startswith('CONTRACT:')]
 for o in sorted(owners|set(contracts)):surface(o)
 sampler=RouteSupportSampler([surfaces[o]for o in sorted(owners|set(contracts))])
 try:points,proof=generate_waypoint_profile(r['points'],obs,sampler,contracts)
 except ProfileError as e:errors.append({'route':r['id'],'code':e.code,'details':e.details});continue
 guard=guard_cart_input_profile(points,obs,sampler,contracts)
 if guard['status']!='PASS':errors.append({'route':r['id'],'code':'SUPPORT_PROFILE_GUARD_FAILED','details':guard});continue
 new=copy.deepcopy(r);new['points']=points;new['length_m']=float(np.linalg.norm(np.diff(np.array(points),axis=0),axis=1).sum());new['production_profile_id']=r['id']+':OWNER_SURFACE_R01';routes.append(new)
 rev=copy.deepcopy(new);rev['id']+='_REVERSE';rev['points']=points[::-1];routes.append(rev);ledger.append({'id':r['id'],'original_xyz_hint':r['points'],'generated_points':points,'waypoints':proof,'reverse_uses_same_profile':True,'analytical_support_input_guard':guard})
out={'schema':'riverstone.production.owner_bound_logistics_routes.v1','status':'FAIL'if errors else'GENERATED_NOT_REPLAYED','sources':{'original_prepared':{'path':str(PREP),'sha256':sha(PREP)},'observed_ground':{'path':str(CAP),'sha256':sha(CAP)},'producer':{'path':str(pathlib.Path(__file__)),'sha256':sha(pathlib.Path(__file__))},'module':{'path':str(module_snapshot),'sha256':module_sha_at_start}},'surface_sources':sources,'routes':routes,'errors':errors,'limits':['No operational NPC/cart system exists in inspected current world_city runtime; this is its explicit reusable logistics route input artifact.','Runtime collision owner/contract sources remain unchanged.','Authored XZ unchanged, Y generated from nominated exact owner surface using original observed floor stratum; floor layer ambiguity rejects.','Sampling by the consuming unchanged cart fixture remains at0.1m translation and1degree orientation.','No automatic future regeneration across a changed source hash.']}
assert sha(module_original)==module_sha_at_start,'Shared source-support module changed during generation'
(O/'production_routes_r01.json').write_text(json.dumps(out,indent=2)+'\n');(O/'production_profile_ledger_r01.json').write_text(json.dumps({'routes':ledger,'errors':errors},indent=2)+'\n');print(json.dumps({'routes':len(routes),'errors':errors,'changes':[sum(abs(x['delta_y_m'])>1e-8 for x in l['waypoints'])for l in ledger]},indent=2))
if not errors:
 new=copy.deepcopy(d);rr={r['id']:r for r in routes};new['routes']=[rr.get(r['id'],r)for r in d['routes']]
 for k,p in [('production_routes',O/'production_routes_r01.json'),('production_profile_ledger',O/'production_profile_ledger_r01.json'),('route_support_module',module_snapshot),('route_support_producer',pathlib.Path(__file__))]:new['sources'][k]={'path':str(p),'sha256':sha(p)}
 new['assumptions']=[x for x in new['assumptions']if not x.startswith('Full chains have not')];new['production_routes_consumer']='Exact route arrays copied from source-hashed production_routes_r01.json; no test-only Y overrides.'
 (P/'prepared_production_r01.json').write_text(json.dumps(new,indent=2)+'\n')
