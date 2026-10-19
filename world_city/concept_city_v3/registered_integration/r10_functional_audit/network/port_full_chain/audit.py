"""Audit complete port chain scope, source parity, original controls and failures."""
import pathlib,json,hashlib
O=pathlib.Path(__file__).resolve().parent;N=O.parent;ROOT=N.parents[4];P=O/'replay_r01';read=lambda p:json.loads(p.read_text())
def sha(p):
 with pathlib.Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
d=read(P/'prepared_bound_r02.json');req=read(O/'request.json');run=read(P/'evidence/runtime_r02/run_manifest.json');checks={}
for k,v in d['sources'].items():checks['source:'+k]=sha(pathlib.Path(v['path']))==v['sha256']
for k,v in d['implementation_hashes'].items():checks['implementation:'+k]=sha(ROOT/k)==v
checks['original_controller']=sha(P/'Traversal.gd')==sha(ROOT/'world_city/concept_city_v3/traversal_r5/Traversal.gd');checks['common_loader']=sha(P/'RenderData.gd')==sha(ROOT/'voxel_character/common/preview/RenderData.gd');checks['unchanged_cart_fixture']=sha(P/'CartClearance.gd')==sha(N/'CartClearance.gd');checks['no_source_drift']=all(x['changed_sources']==[] for x in run['runs']);pr={x['id']:x for x in d['routes']};positive=[]
for r in req['routes']:
 checks['forward_vector:'+r['id']]=pr[r['id']]['points']==r['points'];checks['reverse_vector:'+r['id']]=pr[r['id']+'_REVERSE']['points']==r['points'][::-1];positive +=[r['id'],r['id']+'_REVERSE']
results={}
for kind in ['capsule','cart']:
 report=read(P/'evidence/runtime_r02'/f'{kind}.json');rows={r['id']:r for r in report['routes']};rr=[rows[i] for i in positive];nn=[x for x in report['routes'] if x['id'].startswith('NEGATIVE_')];results[kind]={'status':report['status'],'positive_passed':sum(x['pass'] for x in rr),'positive_cases':len(rr),'negative_passed':sum(x['pass'] for x in nn),'negative_cases':len(nn),'failed_positive_cases':[x for x in rr if not x['pass']],'report':{'path':str((P/'evidence/runtime_r02'/f'{kind}.json').relative_to(ROOT)),'sha256':sha(P/'evidence/runtime_r02'/f'{kind}.json')},'summary':report['summary']}
assert all(checks.values());out={'schema':'riverstone.r10.complete_port_chain_evidence_audit.v1','status':'PASS' if all(x['positive_passed']==4 and x['negative_passed']==2 for x in results.values()) else 'FAILURES_RETAINED','source_checks':checks,'scope':[{'id':r['id'],'length_m':r['length_inside_bay_to_market_m'],'threshold_to_market_m':r['length_threshold_to_market_m'],'start_xyz_m':r['points'][0],'end_xyz_m':r['points'][-1],'directional_cases':2} for r in req['routes']],'results':results,'collision_coverage':d['coverage'],'limits':req['limits']};(O/'evidence_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'results':{k:{x:v[x] for x in ['status','positive_passed','positive_cases','negative_passed','negative_cases']} for k,v in results.items()}},indent=2))
