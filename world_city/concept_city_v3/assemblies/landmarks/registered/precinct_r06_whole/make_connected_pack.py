"""Promote only exact geometry + retained named-entry proven holdings."""
from build_ledger import *
import copy

def main():
 pack=load(HERE/'resolved_placements.json');routes=load(HERE/'supported_external_routes_r05.json');geometry=load(HERE/'connected_route_geometry_tests.json');continuation=load(HERE/'connected_public_continuation.json');assert continuation['external_routes']['sha256']==sha(HERE/'supported_external_routes_r05.json');assert geometry['sources']['external_routes']['sha256']==sha(HERE/'supported_external_routes_r05.json')
 good={r['holding_id']for r in routes['routes']if r['pass']}&{r['holding_id']for r in geometry['routes']if r['pass']}&{r['holding_id']for r in continuation['route_continuations']if r['status']=='PASS'}
 d=copy.deepcopy(pack);d['sources'].update(candidate_pack=ref(HERE/'resolved_placements.json'),external_routes=ref(HERE/'supported_external_routes_r05.json'),route_geometry_tests=ref(HERE/'connected_route_geometry_tests.json'),public_continuation=ref(HERE/'connected_public_continuation.json'))
 for k in ('placements','actual_bearing_footprints','internal_routes'):d[k]=[r for r in d[k]if r['holding_id']in good]
 d['holdings']=[r for r in d['holdings']if r['id']in good];assetkeys={r['asset_key']for r in d['placements']};d['assets']=[r for r in d['assets']if r['id']in assetkeys];d['external_routes']=[r for r in routes['routes']if r['holding_id']in good]
 d['excluded_holdings']+= [dict(id=r['id'],reason='Not promoted: exact two metre corridor and named public-entry graph do not both pass; retained in candidate source only.')for r in pack['holdings']if r['id']not in good]
 d['summary']={'holdings':len(d['holdings']),'meaningful_domain_area_m2':sum(r['area_m2']for r in d['holdings']),'placements':len(d['placements']),'asset_types':len(d['assets']),'native_bearing_pieces':len(d['actual_bearing_footprints']),'public_connected_holdings':len(good)}
 d['status']='SOURCE_GEOMETRY_AND_NAMED_PUBLIC_ENTRY_PROVEN_NOT_APPLIED';d['activation_requirements']=['Apply connected_surface_patch.json and this native pack atomically to the exact R7 baseline, with source-index conflict resolution against other candidate packs.','Independent combined scene art, full-width route clearance, and player/NPC replay remain integration acceptance gates.'];d['activation']=False
 for r in d['holdings']:r['status']='FINITE_NATIVE_AND_EXTERNAL_ENTRY_PROVEN_NOT_APPLIED';r['public_entry_proof']=next(x for x in continuation['route_continuations']if x['holding_id']==r['id'])
 write('resolved_connected_placements.json',d)
 ledger=load(HERE/'owner_completion_ledger.json')
 for o in ledger['owners']:
  active=[r for r in d['holdings']if r['owner_id']==o['owner_id']];o['integration_ready_holding_ids']=[r['id']for r in active];o['integration_ready_domain_area_m2']=sum(r['area_m2']for r in active);o['whole_owner_complete']=False
 ledger['sources']['connected_native_pack']=ref(HERE/'resolved_connected_placements.json');ledger['summary']['integration_ready_holdings']=len(good);ledger['summary']['integration_ready_domain_area_m2']=d['summary']['meaningful_domain_area_m2'];write('owner_completion_ledger.json',ledger);print(d['summary'])
if __name__=='__main__':main()
