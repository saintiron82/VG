"""Activate a sealed twelve-cell guard revision without changing bridge motion."""
import json,pathlib,sys
from world_city.concept_city_v3.registered_integration.r6 import apply_packs as a
D=pathlib.Path(__file__).resolve().parent
ref=lambda p:dict(path=a.rel(p),sha256=a.sha(p))
def main(source):
 bp=a.source_file(source);b=a.load(bp);hp=a.CITY/'assemblies/waterworks/registered_bridge/port_guard_opening_r01/integration_handoff.json';h=a.load(hp);pr=h['native_pack'];p=a.load(a.ROOT/pr['path'],pr['sha256'])
 assert p['replaced_placement_ids']==['BRIDGE_MAIN_RIVER:DRAWBRIDGE_FIXED']
 assert h['activation']['top_patch_changes']==h['activation']['collision_contract_changes']==h['activation']['water_changes']==0
 for item in p['assets'].values()if isinstance(p['assets'],dict)else p['assets']:a.asset_record(item)
 b['packs'].append(dict(pr,name='port_guard_continuous_cart_opening'));b['evidence'] += [ref(hp),h['source_cell_ledger'],h['compatibility_audit'],h['static_clearance'],h['runtime_seal'],h['runtime_summary']]
 b['source_stage']='Whole-city110-holding exterior candidate; compiled port apron, continuous3m guard opening, finite shared-source correction, and source retriangulations. Actual view and final481-vector replay pending.'
 out=D/'whole_city_activation_r01';assert not out.exists();out.mkdir();q=out/'activation_binding.json';q.write_text(json.dumps(b,indent=2)+'\n');print(ref(q),len(b['patches']),len(b['packs']),len(b['collision_contracts']),flush=True)
if __name__=='__main__':main(sys.argv[1])
