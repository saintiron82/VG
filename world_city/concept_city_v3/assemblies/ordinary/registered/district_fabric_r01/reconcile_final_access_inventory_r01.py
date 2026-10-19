"""Read-only source inventory reconciliation. Does not execute traversal or change sources."""
import collections, datetime, hashlib, json, pathlib, time
ROOT=pathlib.Path(__file__).resolve().parents[6]
C=ROOT/'world_city/concept_city_v3'
D=C/'assemblies/ordinary/registered/district_fabric_r01'
R=C/'registered_topography/revisions/r17_district_batches'
T=C/'traversal_r5/revisions/r06_r8_precinct'
OUT=D/'final_access_inventory_reconciliation_r01'
assert not (OUT/'manifest.json').exists(), 'Immutable output already sealed'
OUT.mkdir(exist_ok=True)
def sha(b): return hashlib.sha256(b).hexdigest()
def rel(p): return str(p.relative_to(ROOT))
def ref(p): return {'path':rel(p),'sha256':sha(p.read_bytes())}
def read(p): return json.loads(p.read_bytes())
def write(name,x):
 p=OUT/name;p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n');return ref(p)
P={
 'actual_ledger':D/'city_activation_ledger_r02/completion_ledger.json',
 'actual_activation_acceptance':D/'city_activation_ledger_r02/manifest.json',
 'prior_r04_ledger':D/'city_completion_ledger_r04/completion_ledger.json',
 'catalog':T/'public_network_final_catalog_r01/route_catalog_481_r01.json',
 'vector_accounting':T/'public_network_final_catalog_r01/vector_accounting.json',
 'b15_routes':R/'coherent_b15_r02/route_handoff.json',
 'b15_contract':R/'coherent_b15_r02/contract.json',
 'b15_geometry_acceptance':R/'coherent_b15_r02/acceptance_report.json',
 'final23_release':R/'coherent_final24_r02/integration_handoff.json',
 'final23_routes':R/'coherent_final24_r02/route_handoff_ready_r05.json',
 'hall_withdrawal':D/'b08_market_hall_withdrawal_r01/handoff.json',
 'actual_scene':C/'evidence/r8_final110_runtime_r01/scene.json',
 'actual_manifest':C/'evidence/r8_final110_runtime_r01/activation_manifest.json',
 'activation_binding':C/'registered_integration/r8/final_exterior_candidate_r01/whole_city_activation_r03/activation_binding.json',
 'prepared_runtime':T/'public_network_final_runtime_r01/prepared_runtime.json',
 'runtime_input_seal':T/'final_replay_input_seal_r01/freeze_manifest.json',
}
sources={k:ref(p) for k,p in P.items()}
assert sources['actual_scene']['sha256']=='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
assert sources['catalog']['sha256']=='d2883a4b6e86eceabae3e9a1e85ab7f53279a66652b0d05480b7bf54701d7e45'
actual,old,cat,b15=map(read,[P['actual_ledger'],P['prior_r04_ledger'],P['catalog'],P['b15_routes']])
H={h['id']:h for b in actual['blocks'] for h in b['holdings']}
ordinary=[x for x in cat['routes'] if x['case_class']=='ordinary_entry']
ind={x['holding_id']:x for x in ordinary if x.get('holding_id')}
roots={x['entry_id']:x for x in ordinary if x['id'].startswith('B15_PUBLIC_ENTRY_')}
chains={x['holding_id']:x for x in b15['court_route_chains']}
nodes={x['id']:x for x in b15['nodes']}; doors={x['id']:x for x in b15['door_routes']}
edges={frozenset([x['a'],x['b']]):x for x in b15['edges']}
root_owners=collections.defaultdict(list)
rows=[];errors=[]
for hid,h in sorted(H.items()):
 row={'holding_id':hid,'block_id':hid.split(':')[0],'adopted':True,'implementation_tier':h['implementation_tier'],'source_release':h['source_release'],'source_record_locator':h['source_record_locator']}
 if hid in ind:
  r=ind[hid];row.update(access_disposition='INDIVIDUAL_CATALOG_ENTRY',catalog_route_id=r['id'],entry_id=r['entry_id'],catalog_selector=f"routes[id={r['id']}]",source_route_provenance=r.get('provenance',[]))
 elif hid in chains:
  ch=chains[hid];root=ch['public_root'].get('effective_node_id',ch['public_root']['node_id']);r=roots[root];root_owners[root].append(hid)
  chain=ch['route_ids_to_public']; missing_nodes=[n for n in chain if n not in nodes];missing_doors=[n for n in ch['door_link_ids'] if n not in doors]; missing_edges=[list(pair) for pair in zip(chain,chain[1:]) if frozenset(pair) not in edges]
  if missing_nodes or missing_doors or missing_edges:errors.append({'holding_id':hid,'nodes':missing_nodes,'doors':missing_doors,'edges':missing_edges})
  row.update(access_disposition='DIRECT_GATE_IS_CATALOG_ROOT' if len(chain)==1 else 'AUTHORED_INTERNAL_BRANCH_TO_CATALOG_ROOT',catalog_route_id=r['id'],entry_id=root,gate_route_id=ch['external_gate_route_id'],route_ids_to_public=chain,door_link_ids=ch['door_link_ids'],door_link_count=len(ch['door_link_ids']),chain_selector=f"court_route_chains[holding_id={hid}]",chain_reference_validation={'all_nodes_present':not missing_nodes,'all_door_routes_present':not missing_doors,'all_adjacent_chain_edges_present':not missing_edges},internal_branch_runtime_claim='No separate controller replay claimed for gate/internal door branches outside the root vector.')
 else:errors.append({'holding_id':hid,'error':'NO_AUTHORED_ACCESS_DISPOSITION'})
 rows.append(row)
root_rows=[]
for rid,r in sorted(roots.items(),key=lambda x:x[1]['id']):
 owners=sorted(root_owners[rid]);root_rows.append({'catalog_route_id':r['id'],'entry_id':rid,'holding_ids':owners,'holding_count':len(owners),'disposition':'SHARED_HOLDING_ROOT' if len(owners)>1 else ('SINGLE_HOLDING_ROOT' if owners else 'CATALOGUED_BACKBONE_ROOT_WITH_NO_ASSIGNED_HOLDING_CHAIN'),'catalog_selector':f"routes[id={r['id']}]"})
old17=[h for b in old['blocks'] for h in b['remaining_private17_holdings']]
b07=[h for b in old['blocks'] for h in b['separate_B07_refit_holdings']]
coverage={x.get('holding_id'):x for x in cat['coverage']['ordinary_entries'] if x.get('holding_id')}
old_rows=[]
for h in old17:
 hid=h['id'];cv=coverage[hid];old_rows.append({'holding_id':hid,'former_failure_class':h['failure_class'],'current_catalog_status':cv['status'],'adopted_in_actual_scene':hid in H,'current_disposition':'ADOPTED_FINAL23' if hid in H else 'WITHDRAWN_UNBUILT_PROPOSAL_RETAINED_NORTH_MARKET_HALL_SERVICE_GROUND','catalog_route_ids':cv['route_ids'],'evidence_source':'final23_release' if hid in H else 'hall_withdrawal'})
# Snapshot only already-produced results. The runtime producer is concurrently writing its file.
live=T/'public_network_final_runtime_r01/evidence/public_network_replay.json'
for _ in range(25):
 try: raw=live.read_bytes(); replay=json.loads(raw);break
 except json.JSONDecodeError:time.sleep(.15)
else:raise RuntimeError('Could not snapshot an intact replay file')
observed=datetime.datetime.now(datetime.timezone.utc).isoformat()
selected=[x for x in replay['routes'] if x['id'].startswith('B15_PUBLIC_ENTRY_')]
assert replay['prepared_sha256']==sources['prepared_runtime']['sha256']
snapshot={'schema':'riverstone.ordinary_b15_root_replay_excerpt.v1','observed_at_utc':observed,'source_observation':{'path':rel(live),'sha256_at_observation':sha(raw),'live_file_may_later_change':True},'prepared_runtime':sources['prepared_runtime'],'observed_replay_status':replay['status'],'observed_total_result_rows':len(replay['routes']),'scope':'Exact existing B15 root result rows only; not a new run or a claim of full481 completion.','routes':selected}
snapref=write('b15_root_replay_excerpt.json',snapshot)
rr={x['id']:x for x in selected}
for root in root_rows:
 ids=[root['catalog_route_id'],root['catalog_route_id']+'_REVERSE'];root['existing_actual_replay']=[{'id':rid,'pass':rr.get(rid,{}).get('pass'),'status':rr.get(rid,{}).get('status')} for rid in ids]
counts={'adopted_holdings':len(H),'non_b15_holdings':len(ind),'b15_holdings':len(chains),'catalog_ordinary_root_routes':len(ordinary),'b15_catalog_roots':len(roots),'b15_used_roots':sum(bool(x['holding_ids']) for x in root_rows),'b15_unassigned_catalog_roots':sum(not x['holding_ids'] for x in root_rows),'b15_direct_gate_roots':sum(len(x['route_ids_to_public'])==1 for x in chains.values()),'b15_holdings_using_backbone_branches':sum(len(x['route_ids_to_public'])>1 for x in chains.values()),'b15_shared_root_groups':sum(len(x['holding_ids'])>1 for x in root_rows),'extra_memberships_in_shared_root_groups':sum(max(0,len(x['holding_ids'])-1) for x in root_rows),'old17_now_adopted':sum(x['adopted_in_actual_scene'] for x in old_rows),'old17_now_withdrawn':sum(not x['adopted_in_actual_scene'] for x in old_rows),'separate_b07_now_adopted':sum(x in H for x in b07),'genuine_missing_required_access_in_inventory':len(errors),'adopted_intentionally_inaccessible_holdings':0,'obsolete_proposal_count_outside_adopted110':1,'existing_b15_root_directions_observed':len(selected),'existing_b15_root_directions_passed':sum(x.get('pass') is True for x in selected)}
checks={
 '110_unique_adopted_holdings':len(H)==110,
 '84_independent_non_b15_entries_exact':set(ind)=={h for h in H if not h.startswith('BLOCK_015:')},
 '26_b15_authored_chains_exact':set(chains)=={h for h in H if h.startswith('BLOCK_015:')},
 '106_catalog_entries_equal_84_plus22':len(ordinary)==106 and len(ind)==84 and len(roots)==22,
 'all_b15_source_chain_references_exist':not errors,
 'net_four_is_six_shared_memberships_minus_two_unassigned_roots':counts['extra_memberships_in_shared_root_groups']==6 and counts['b15_unassigned_catalog_roots']==2 and len(H)-len(ordinary)==4,
 'old17_resolved_as16_adopted_plus_hall_withdrawal':len(old_rows)==17 and counts['old17_now_adopted']==16 and [x['holding_id'] for x in old_rows if not x['adopted_in_actual_scene']]==['BLOCK_008:R8_C003'],
 'all_seven_b07_adopted_with_individual_entries':len(b07)==7 and set(b07)<=set(ind),
 'final_ordinary_coverage_has_no_held_rows':not [x for x in cat['coverage']['ordinary_entries'] if x['status']=='held'],
 '44_existing_b15_root_directions_pass':len(selected)==44 and all(x.get('pass') is True for x in selected),
}
ledger={'schema':'riverstone.final_ordinary_access_inventory_reconciliation.v1','status':'PASS_READ_ONLY_INVENTORY_RECONCILIATION' if all(checks.values()) else 'HOLD','observed_at_utc':observed,'sources':sources,'runtime_excerpt':snapref,'counts':counts,'answer':'There is no canonical set of four missing holding entries. All84 non-B15 holdings have individual entries;26 B15 holding chains use20 of22 catalogued roots. Six additional memberships in five shared-root groups, offset by two unassigned backbone roots, explain110-106=4.','holdings':rows,'b15_catalog_root_ownership':root_rows,'former17_candidate_dispositions':old_rows,'separate_b07_adopted_ids':b07,'stale_metadata':{'source':'catalog','locations':['limits[2]','source_candidate_accounting.private_holding_batches.private_holdings','source_candidate_accounting.private_holding_batches.accepted_entry_roots','source_candidate_accounting.private_holding_batches.held_candidates'],'literal_limit':next(s for s in cat['limits'] if '17 ordinary candidates remain held' in s),'inherited_counts':{k:cat['source_candidate_accounting']['private_holding_batches'][k] for k in ['private_holdings','fixed_b15_entry_roots','accepted_entry_roots','held_candidates']},'current_reconciliation':'61 earlier non-B15 +16 former held +7 separate B07 =84 non-B15; plus26 B15=110. Former17 includes one unbuilt hall proposal withdrawn, not an adopted inaccessible holding. Final23 release, exact current routes and coverage supersede these inherited counts; original catalog remains untouched.'},'limits':['Read-only identity and authored-connectivity reconciliation; no new route tests or geometry.','All44 B15 root direction results are already passing against the bound actual runtime. The full481 replay remains separate and may still be running.','Gate links, internal door branches and untested court movement are not promoted to controller acceptance by a passing public root. Their exact authored chains and sealed finite terrain proofs remain the evidence.','The exterior_only tier limits interiors and simulation; it is not used as an excuse for a missing required exterior entry. No adopted holding is classified as intentionally inaccessible.','No global zero-unassigned land-area or complete enclosure claim is added.'], 'checks':checks,'errors':errors,'passed':all(checks.values())}
ledgerref=write('ledger.json',ledger)
lines=['# Final ordinary access inventory reconciliation','',ledger['status'],'',f"Bound actual scene: `{sources['actual_scene']['sha256']}`.",f"Catalog: `{sources['catalog']['sha256']}`.",'','## Result','','There are no four identifiable missing holding entries. The counts use different units:','', '- 84 non-B15 adopted holdings each have an individual catalogued entry.', '- 26 B15 holdings have authored court-to-public chains using 20 of the 22 catalogued B15 public roots.', '- Five shared-root groups account for six additional holding memberships. Two catalogued B15 backbone roots have no assigned holding chain.', '- Therefore 110 holdings minus 106 catalogued entry roots equals 6 shared memberships minus 2 unassigned roots.','', 'All 44 B15 public-root directions pass in the existing actual-scene replay snapshot. Internal gate and door branches are source-proven and are not individually claimed as replayed. The complete 481-case replay is a separate gate.','', '## Shared B15 roots','', '| Catalog root | Exact root node | Adopted holdings |','|---|---|---|']
for x in root_rows:
 if x['holding_count']>1:lines.append(f"| {x['catalog_route_id']} | {x['entry_id']} | {', '.join(x['holding_ids'])} |")
lines+=['','Both `BLOCK_015:R8_D016` and `BLOCK_015:R8_D023` reach root12 through `B15:R8:LANE:2_5:08`, then `B15:R8:LANE:2_5:02`. All other shared-owner gate links connect directly to their listed backbone root. Exact door-link IDs and chain edge references are in ledger.json.','', 'The two roots without assigned holding chains are `B15_PUBLIC_ENTRY_19` (`B15:R8:LANE:1_0:01`) and `B15_PUBLIC_ENTRY_22` (`B15:R8:LANE:1_0:04`). They remain catalogued finite backbone connectors; they do not denote absent dwellings.','', '## Reconciliation of the inherited “17 remain held” line','','That line and private_holding_batches counts are inherited 61-holding metadata. Current route/coverage records and final23 release account for all former candidates:16 adopted plus the withdrawn960m² market-hall/service-ground proposal. The seven B07 holdings are a separate addition.','', '| Former candidate | Current disposition |','|---|---|']
for x in old_rows:lines.append(f"| {x['holding_id']} | {x['current_disposition']} |")
lines+=['','B07 separately adopted: '+', '.join(b07)+'.','','## Evidence','']
for k in ['actual_ledger','catalog','b15_routes','b15_contract','b15_geometry_acceptance','final23_release','final23_routes','hall_withdrawal']:
 p=P[k];lines.append(f"- {k}: [{p.name}]({pathlib.Path(__import__('os').path.relpath(p,OUT)).as_posix()}); SHA256 `{sources[k]['sha256']}`.")
lines+=['','The ledger contains all110 exact holding IDs, their entry disposition and source selectors. The existing44 B15 result rows are preserved in b15_root_replay_excerpt.json; its observation hash refers to a concurrently progressing source file. Original catalogs, R04 ledger and failed strict-palette diagnostic remain unchanged. No geometry or traversal run was added.','']
(OUT/'README.md').write_text('\n'.join(lines))
manifest={'schema':'riverstone.immutable_access_inventory_manifest.v1','status':ledger['status'],'passed':ledger['passed'],'files':[ledgerref,snapref,ref(OUT/'README.md')],'producer':ref(pathlib.Path(__file__)),'source_count':len(sources),'source_references':sources}
write('manifest.json',manifest)
print(json.dumps({'manifest':ref(OUT/'manifest.json'),'counts':counts,'checks':checks,'errors':errors},indent=2))
