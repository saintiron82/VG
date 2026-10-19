import pathlib,json,hashlib
O=pathlib.Path(__file__).resolve().parent;P=O/'replay_r01';ROOT=O.parents[5];read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=read(P/'prepared_bound_r02.json');b=read(P/'prepared_height_corrected_r03.json');run=read(P/'evidence/runtime_r03/run_manifest.json');checks={}
for k in ['assets','placements','buildings','cart_fixture','implementation_hashes']:checks['unchanged_'+k]=a[k]==b[k]
for k,v in b['sources'].items():checks['source:'+k]=sha(pathlib.Path(v['path']))==v['sha256']
for k,v in b['implementation_hashes'].items():checks['implementation:'+k]=sha(ROOT/k)==v
checks['no_drift']=all(x['changed_sources']==[]for x in run['runs'])
for x,y in zip(a['routes'],b['routes']):
 diff=[(i,p,q)for i,(p,q)in enumerate(zip(x['points'],y['points']))if p!=q]
 checks['only_one_exact_hint_change:'+x['id']]=not diff if x['id'].startswith('NEGATIVE_')else len(diff)==1 and diff[0][1]==[119.59834894318314,1.0,419.36416610734005] and diff[0][2]==[119.59834894318314,1.75,419.36416610734005]
results={}
for kind in ['capsule','cart']:
 p=P/'evidence/runtime_r03'/f'{kind}.json';d=read(p);rr=d['routes'];pos=[r for r in rr if not r['id'].startswith('NEGATIVE_')];neg=[r for r in rr if r['id'].startswith('NEGATIVE_')];results[kind]={'status':d['status'],'positive_passed':sum(r['pass']for r in pos),'positive_cases':len(pos),'negative_passed':sum(r['pass']for r in neg),'negative_cases':len(neg),'summary':d['summary'],'report':{'path':str(p.relative_to(ROOT)),'sha256':sha(p)}}
assert all(checks.values());out={'schema':'riverstone.r10.port_height_corrected_evidence_audit.v1','status':'PASS'if all(r['status']=='pass'for r in results.values())else'FAIL','checks':checks,'results':results,'original_failure_preserved':'port_full_chain/evidence_audit.json and replay_r01/evidence/runtime_r02','correction':'Same XZ at one north-contract waypoint Y1.0 to existing floorY1.75; no geometry/contract/controller/ray or clearance change.','limits':['Endpoint is old named market goal, not new market delivery circuit.','Kinematic rigid cart fixture, no vehicle dynamics, traction, load or NPC operations.','Production owner-bound profile module integration remains a distinct deliverable.']};(O/'height_corrected_evidence_audit.json').write_text(json.dumps(out,indent=2)+'\n');print({k:(v['positive_passed'],v['negative_passed'])for k,v in results.items()})
