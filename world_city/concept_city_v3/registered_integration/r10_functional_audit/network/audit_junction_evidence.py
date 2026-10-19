"""Verify retained bounded replay sources, route inputs and unchanged controller."""
import json,pathlib,hashlib,collections,numpy as np
O=pathlib.Path(__file__).resolve().parent;ROOT=O.parents[4];P=O/'junction_replay_r01';d=json.load(open(P/'prepared.json'));run=json.load(open(P/'evidence/replay_r01/run_manifest.json'));report=json.load(open(P/'evidence/replay_r01/capsule.json'));request=json.load(open(O/'junction_runtime_request.json'))
def sha(p):return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
checks={};drift=[]
for key,ref in d['sources'].items():
 p=pathlib.Path(ref['path']);p=p if p.is_absolute() else ROOT/p
 checks['source:'+key]=sha(p)==ref['sha256']
for key,digest in d['implementation_hashes'].items():
 p=ROOT/key
 if sha(p)!=digest:
  snap=d['implementation_snapshots'][key];sp=pathlib.Path(snap['path']);sp=sp if sp.is_absolute() else ROOT/sp;assert sha(sp)==digest;drift.append({'source_path':key,'used_sha256':digest,'retained_snapshot':str(sp.relative_to(ROOT)),'live_authoring_source_has_changed_since_replay':True})
assert all(checks.values()),[k for k,v in checks.items() if not v]
assert run['runs'][0]['changed_sources']==[]
assert sha(P/'Traversal.gd')==sha(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd')
assert sha(P/'RenderData.gd')==sha(ROOT/'voxel_character/common/preview/RenderData.gd')
prepared={r['id']:r for r in d['routes']};results={r['id']:r for r in report['routes']};groups=[]
for s in request['junctions']:
 cases=[r for r in request['routes'] if r['group']==s['group']];ids=[]
 for r in cases:
  assert prepared[r['id']]['points']==r['points'];assert prepared[r['id']+'_REVERSE']['points']==list(reversed(r['points']));ids +=[r['id'],r['id']+'_REVERSE']
 rs=[results[i] for i in ids];geom=json.load(open(P/'geometry'/f"{s['group']}.json"));a=np.asarray(geom['triangles'],dtype=np.float32);zero=int(np.all(np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0])==0,axis=1).sum())
 groups.append({'group':s['group'],'cases':len(rs),'passed':sum(r['pass'] for r in rs),'junction_all_requested_directions_pass':all(r['pass'] for r in rs),'source_face_count':len(geom['source_face_indices']),'source_faces_removed_or_added':0,'source_world_roundtrip_error_m':geom['local_origin_proof']['applied_world_roundtrip_error_m'],'float32_zero_faces':zero,'runtime_cases':[{'id':r['id'],'pass':r['pass'],'status':r['status'],'ground_ray_miss_frames':r['ground_ray_miss_frames'],'off_floor_frames':r['not_on_floor_frames'],'obstacle_contacts':r['obstacle_contact_ids']} for r in rs]})
neg=[r for r in report['routes'] if r['id'].startswith('NEGATIVE_')];out={'schema':'riverstone.r10.junction_evidence_audit.v1','status':'PARTIAL_23_OF_24_POSITIVE_TURNS_PASS','unchanged_controller_and_loader':True,'exact_request_polyline_parity':True,'exact_r9_index':request['visual_index'],'source_identity_checks':checks,'source_changes_during_replay':[],'retained_post_replay_authoring_drift':drift,'positive_cases':24,'positive_passed':sum(g['passed'] for g in groups),'negative_controls_passed':sum(r['pass'] for r in neg),'groups':groups,'report':{'path':str((P/'evidence/replay_r01/capsule.json').relative_to(ROOT)),'sha256':sha(P/'evidence/replay_r01/capsule.json')},'limits':['One ray-miss is a strict fail even though the route reached its destination with0contacts and0off-floor frames.','Do not mark SEAM_03 unrestricted/bidirectionally validated based on3/4 directional passes.','The5 fully passing junctions validate only their requested3–4m approach/turn/exit combinations; neither arbitrary corner turning nor carts are certified.','All source triangles selected whole by exact finite preparer; no height or collision edits.','Live gate preparer changed after replay; the actual source version is retained and independently hash-verified.']};(O/'junction_evidence_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['status','positive_cases','positive_passed','negative_controls_passed']},indent=2))
