"""Read-only protected exterior accounting, without treating source plans as runtime passes."""
from pathlib import Path
import sys,json,hashlib,collections
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from resolve_pack import *
OUT=Path(__file__).resolve().parent;RES=OUT.parent/'residual_completion_r01'

def write(name,data):
    p=OUT/name;p.write_text(json.dumps(data,indent=2)+'\n');return ref(p)

def main():
    scene_path=CITY/'evidence/r8_district_61_noble_r02_contracts_runtime/scene.json';scene=load(scene_path)
    actual={p['id']:p for p in scene['common_instances']};assets=scene['common_assets']
    source_owners_path=CITY/'registered_integration/r8/coverage_plan/protected_source_owner_ledger.json'
    sources=load(source_owners_path)['owners'];baseline_path=BASE/'actual_owner_use_ledger.json'
    baseline={r['owner_id']:r for r in load(baseline_path)['owners']}
    packs=[BASE/'resolved_connected_placements.json',RES/'resolved_residual_placements.json',RES/'residual_extensions_r02/resolved_extension_placements.json']
    graph_path=BASE/'connected_public_continuation.json';graph={r['route_id']:r for r in load(graph_path)['route_continuations']}
    holdings=[];routes=[];reconcile=[];pack_rows=[]
    for path in packs:
        pack=load(path);holdings +=[dict(h,source_pack=ref(path))for h in pack['holdings']]
        for p in pack['placements']:
            s=actual[p['id']];a=assets[s['asset_key']]
            assert all(s.get(k)==p.get(k)for k in('asset_key','position_m','yaw_rad','scale')),(p['id'],'pose')
            assert a['render_sha256']==p['cache']['sha256'],p['id']
            assert a['master_sha256']==p['source']['sha256'],p['id']
            reconcile.append(dict(native_id=p['id'],owner_id=p['owner_id'],source_pack=ref(path),actual_asset_key=s['asset_key'],actual_render_sha256=a['render_sha256'],actual_master_sha256=a['master_sha256'],pose_exact=True))
        for r in pack['external_routes']:
            parent=r.get('joins_verified_route_id');g=graph.get(r['id'])or graph.get(parent)
            named=g['named_public_road_ids']if g else['CASTLE_APPROACH']if r['id']=='RETAINED_TRAINING_ENTRY_R01'or parent=='RETAINED_TRAINING_ENTRY_R01'else[]
            assert named,r['id']
            routes.append(dict(id=r['id'],holding_id=r['holding_id'],source_pack=ref(path),source_width_m=r['width_m'],polyline_xz_m=r['polyline_xz_m'],joins_local_route_id=parent,parent_public_entry_ids=['ROAD:'+x for x in named],source_graph_proof=ref(graph_path)if g else ref(RES/'training_walk_tests.json'),access_scope='required_training_precinct_entrance'if r['id']=='RETAINED_TRAINING_ENTRY_R01'else'local_garden_court_or_maintenance_access',source_status='FINITE_SOURCE_SUPPORTED',actual_capsule_status='NOT_IN_PRIOR_412_CATALOG',runtime_pass=False))
        pack_rows.append(dict(source=ref(path),holdings=len(pack['holdings']),exact_functional_domain_area_m2=sum(h.get('exact_area_m2',h['area_m2'])for h in pack['holdings']),actual_native_instances=len(pack['placements']),actual_scene_reconciliation='PASS'))
    assert len(holdings)==47 and len(routes)==47 and len(reconcile)==189
    write('actual_ground_activation.json',dict(scene=ref(scene_path),status='PASS_ACTUAL_NATIVE_CACHE_AND_POSE_RECONCILIATION',packs=pack_rows,placements=reconcile,limits=['This proves the listed native activations. Source-owned functional domains are not a fresh whole-owner area census.']))
    write('local_access_routes.json',dict(routes=routes,summary=dict(total_source_access_chains=47,local_garden_court_maintenance_chains=46,required_training_entry_chains=1),training_full_continuation=ref(OUT/'training_entry_runtime_handoff.json'),policy='Local garden/court maintenance access is not a new required city-road entrance. Parent public entry IDs are explicit; controller replay remains separate.'))
    traversal=CITY/'traversal_r5/revisions/r06_r8_precinct';rp=traversal/'public_network_r18_runtime_r01/evidence/public_network_replay.json';runtime=load(rp);runtime_by={r['id']:r for r in runtime['routes']}
    pending=[]
    for eid in('E1','E2'):
        for suffix in('','_REVERSE'):
            rid=f'NOBLE:{eid}:registered_r1:service_gate'+suffix;assert not runtime_by[rid]['pass']
            pending.append(dict(id=rid,owner_id=eid,kind='required_noble_entrance',prior_status='FAILED_ON_014313DB',selected_repair=ref(RES/'noble_cap_route_repair_r01/integration_handoff.json'),final_scene_replay='PENDING'))
    for name,owner in [('abbey_gate_extension_r01.json','SITE_MONASTERY'),('cloister_extension_r01.json','SITE_CLOISTER')]:
        ep=traversal/'pending_extensions_r01'/name
        for r in load(ep)['routes']:
            for suffix in('','_REVERSE'):pending.append(dict(id=r['id']+suffix,owner_id=owner,kind='retained_gate_or_cloister_continuation',source=ref(ep),final_scene_replay='PENDING'))
    for suffix in('','_REVERSE'):pending.append(dict(id='TRAIN_RETAINED_ENTRY_R01'+suffix,source_alias='RETAINED_TRAINING_ENTRY_R01',owner_id='SITE_TRAIN',kind='required_training_entrance',source=ref(OUT/'training_entry_runtime_handoff.json'),final_scene_replay='PENDING'))
    write('pending_required_routes.json',dict(status='AWAITING_FINAL_COMPOSED_SCENE_REPLAY',prior_scene=ref(scene_path),prior_replay=ref(rp),required_pending_direction_count=len(pending),routes=pending,local_access_catalog=ref(OUT/'local_access_routes.json'),scope='This list identifies the newly repaired or not-yet-tested protected entrances. All previously passing entries still require the parent final-scene regression; this is not a citywide route inventory.'))
    uses={r['owner_id']:r['intended_use']for r in load(RES/'whole_owner_use_plan.json')['owner_uses']}
    static_sources={
        'SITE_CEMETERY':[RES/'cemetery_public_caps_r03/integration_handoff.json'],
        'SITE_CLOISTER':[RES/'retained_cloister_handoff_r01/integration_handoff.json'],
        'SITE_BASIN':[CITY/'assemblies/waterworks/registered_water_completion_r01/reservoir_native_audit.json'],
        'SITE_COMMON':[RES/'common_entry_repair_r03/source_contract_tests.json'],
        'SITE_MARKET':[CITY/'assemblies/landmarks/r8_current_coverage_r01/facility_coverage.json'],
        'SITE_TRAIN':[RES/'training_walk_tests.json',OUT/'training_entry_runtime_handoff.json'],
        'SITE_CASTLE':[BASE/'connected_public_continuation.json'],
        'SITE_PORT':[CITY/'assemblies/waterworks/registered_water_completion_r01/harbor_interfaces.json'],
        'SITE_CLERGY':[BASE/'connected_public_continuation.json'],
        'SITE_MONASTERY':[RES/'retained_garden_access_r03/gate_native_r03/integration_handoff.json']}
    public={'SITE_CEMETERY':['CATHEDRAL_APPROACH'],'SITE_CLOISTER':['CATHEDRAL_APPROACH','CLERGY_EAST_GATE'],'SITE_BASIN':['RESERVOIR_SERVICE'],'SITE_COMMON':['WEST_MONASTERY_EDGE'],'SITE_MARKET':['MARKET_CONTOUR'],'SITE_TRAIN':['CASTLE_APPROACH'],'SITE_CASTLE':['CASTLE_APPROACH'],'SITE_PORT':['PORT_BRIDGE_TIE'],'SITE_CLERGY':['CATHEDRAL_APPROACH','CLERGY_EAST_GATE'],'SITE_MONASTERY':['MARKET_CONTOUR']}
    retained={'SITE_CEMETERY':'Retained burial rows and native cemetery boundary; obsolete road-encroaching connection branch replaced with finite off-public soil restoration.','SITE_CLOISTER':'Retained cloister quadrangle and actual west-cloister walking geometry; one new 510 m² quiet garden.','SITE_BASIN':'Hydraulic reserve remains excluded from ordinary building ownership; its zero exclusive block-grid area is not a missing parcel or completion proof.','SITE_COMMON':'Retained common/terrace-park grounds, fine visible entry and continuous collision envelope with the fixed +8 m public terminal.','SITE_MARKET':'Retained native trading court and market facilities; use the actual facility registry and canonical public network rather than new filler props.','SITE_TRAIN':'Retained drill ground, barracks, stable, practice facilities and fine native entry; added tack/service holding and exercise verge.','SITE_CASTLE':'Retained castle envelope and fortification footprint; bounded outer-bailey service/exercise courts and clear inspection verges.','SITE_PORT':'Retained seven-node native quay/pier deck graph and loading/water-edge open ground; city-road continuation is a separate public-network test.','SITE_CLERGY':'Retained cathedral/canon exterior fabric; finite kitchen-growing, orchard, alms/service and processional grounds.','SITE_MONASTERY':'Retained abbey envelope and productive grounds; added kitchen beds, orchard/nursery, herb/processional courts and clear inspection verges; bounded old-wall gate openings.'}
    noble_internal=CITY/'assemblies/ordinary/registered/district_fabric_r01/noble_internal_route_review_r01/internal_route_acceptance.json'
    owners=[]
    for s in sources:
        oid=s['source_owner_id'];hs=[h for h in holdings if h['owner_id']==oid];rr=[r for r in routes if any(h['id']==r['holding_id']for h in hs)]
        if oid.startswith('E'):
            refs=[noble_internal,RES/'noble_entry_batch_r02/integration_handoff.json'];description='Retained household buildings, garden/orchard and service courts; active corrected R7 internal source routes accepted statically; seven fine exterior entries use explicit physical profiles and contracts.'
            if oid in('E1','E2'):refs.append(RES/'noble_cap_route_repair_r01/integration_handoff.json')
            entryids=[f'NOBLE:{oid}:registered_r1:service_gate'];prior=[dict(id=rid+suffix,passed=runtime_by[rid+suffix]['pass'])for rid in entryids for suffix in('','_REVERSE')]
        else:
            refs=static_sources[oid];description=retained[oid];entryids=['ROAD:'+x for x in public[oid]]+([f'COMMON_FINE_ENTRY_LANE_{i}'for i in range(3)]if oid=='SITE_COMMON'else[]);prior=[dict(id=rid+suffix,passed=runtime_by[rid+suffix]['pass'])for rid in entryids for suffix in('','_REVERSE')if rid+suffix in runtime_by]
        owners.append(dict(owner_id=oid,exclusive_within_block_source_grid_m2=s['exclusive_ordinary_exclusion_grid_m2'],source_polygon_xz_m=s['polygon_xz_m'],intended_exterior_use=uses[oid],retained_and_repaired_exterior=description,source_evidence=[ref(p)for p in refs],actual_new_ground_holdings=[dict(id=h['id'],function=h['function'],exact_domain_area_m2=h.get('exact_area_m2',h['area_m2']),source_pack=h['source_pack'])for h in hs],new_ground_exact_domain_area_m2=sum(h.get('exact_area_m2',h['area_m2'])for h in hs),new_native_instances=sum(p['owner_id']==oid for p in reconcile),source_local_access_ids=[r['id']for r in rr],parent_public_entry_ids=sorted(set(entryids+[x for r in rr for x in r['parent_public_entry_ids']])),prior_exact_scene_entry_results=prior,pending_required_route_ids=[r['id']for r in pending if r['owner_id']==oid],acceptance='BOUNDED_LISTED_EXTERIOR_SOURCE_AND_ACTIVATION_EVIDENCE; FINAL_RUNTIME_PENDING',whole_owner_area_complete_certified=False,unresolved_scope=['No fresh 100% geometric-use census is asserted for the entire protected polygon.','Building interiors and wallwalk traversal are outside this exterior acceptance.','Local garden/service maintenance routes remain source-supported unless individually replayed.']))
    phase02=CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase02/resolved_placements.json';ph=load(phase02)
    ledger=dict(schema='riverstone.protected_exterior_acceptance.v1',status='SOURCE_AND_PRIOR_ACTUAL_ACTIVATION_ACCEPTED_FINAL_SCENE_PENDING',actual_prior_scene=ref(scene_path),final_candidate_binding=ref(CITY/'registered_integration/r8/final_exterior_candidate_r01/noble_cap_bridge_binding.json'),source_owner_ledger=ref(source_owners_path),actual_ground_activation=ref(OUT/'actual_ground_activation.json'),pending_required_routes=ref(OUT/'pending_required_routes.json'),local_access_routes=ref(OUT/'local_access_routes.json'),owners=owners,summary=dict(owner_count=17,exclusive_source_block_grid_area_m2=210334,new_functional_holdings=47,new_functional_domain_area_m2=sum(h.get('exact_area_m2',h['area_m2'])for h in holdings),new_native_instances_verified_actual=189,whole_owner_area_completion_certifications=0,pending_required_protected_directions=len(pending)),separate_prior_phase02=dict(source=ref(phase02),holdings=[dict(id=h['id'],function=h['function'],exact_domain_area_m2=h['area_m2'])for h in ph['holdings']],source_domain_area_m2=5379.25,reason_separate='Cross-pack source ownership is sealed; these holdings are not relabelled as new R06 acreage or added to an exclusive-owner percentage.'),deferred_scope=['Interior room layouts, interior access and interior furnishing.','Castle/fortification wallwalk traversal and elevated patrol routes.','Microtextures and fine decorative props.'],measurement_limits=['210334 m² is exclusive source-owner area inside registered block faces, not whole polygon area.','New functional-domain area is finite source ownership with actual native activation; it is not fully paved footprint or guaranteed total-owner coverage.','Prior runtime passes are bound to 014313db and do not certify the final candidate scene.','Original zero-new-activation entries in the early R7 ledgers are historical and superseded by this actual activation check.'])
    write('protected_exterior_acceptance.json',ledger)
    lines=['# Protected precinct exterior acceptance','',f"47 finite grounds holdings ({ledger['summary']['new_functional_domain_area_m2']:.2f}m²) and 189 native placements are verified in actual scene 014313db. Phase02 adds a separately owned 5379.25 m². Final candidate activation and replay are pending.",'','## Owner ledger']
    for o in owners:lines.append(f"- {o['owner_id']}: {o['retained_and_repaired_exterior']} New grounds: {len(o['actual_new_ground_holdings'])} / {o['new_ground_exact_domain_area_m2']:.2f}m². Pending required directions: {len(o['pending_required_route_ids'])}.")
    lines +=['','## Exact remaining acceptance','- E1/E2 fine entrances: four directions after the bounded cap repair.','- Abbey orchard and herb gates plus retained cloister continuation: six directions.','- Main training entry: two directions; visible 0.125 m native treads have only static acceptance so far.','- 46 local garden/court/maintenance chains retain finite source support and explicit parent public entries; they are separate from required precinct entrances.','- The prior 387/412 city test is preserved; final combined regression is still required.','','## Scope boundary','Interiors, elevated wallwalk traversal and microtexture/detail are deferred. This ledger accepts the listed finite exterior components and source evidence; it does not assert 100% whole-owner land-use coverage.']
    (OUT/'ACCEPTANCE.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(ledger['summary'],indent=2))


if __name__=='__main__':main()
