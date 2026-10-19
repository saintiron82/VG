"""Source-frozen candidate for north approach and civic water regression."""
import json
from .build_scene import a,HERE

def run():
 b=a.load(HERE/'precinct_proxy_binding_r01.json')
 def rr(p):return dict(path=a.rel(p),sha256=a.sha(p))
 north=a.CITY/'assemblies/waterworks/registered_bridge/north_approach_r03'
 assert a.load(north/'full_cell_audit.json')['status']=='PASS'
 for folder,name in[(north,'north_approach_r03'),(a.CITY/'assemblies/waterworks/registered_services_r01','water_services_r01'),(a.CITY/'assemblies/waterworks/registered_mill_r01','canal_mill_r01')]:
  b['packs'].append(dict(rr(folder/'resolved_placements.json'),name=name));b['patches'].append(rr(folder/'surface_patch.json'))
  for f in['freeze_manifest.json','full_cell_audit.json','ownership_review.json']:
   if(folder/f).exists():b['evidence'].append(rr(folder/f))
 b['collision_contracts'].append(rr(north/'collision_contract.json'));b['water_extensions']=[rr(a.CITY/'assemblies/waterworks/registered_services_r01/water_extension.json')]
 b['limits']=['Candidate for exact north bridge-to-main-gate continuity, static cisterns/mill and accepted stair proxy; final replay/visual QA pending.','Existing whole-city public network failures and coherent district grading remain open.','No fluid simulation, whole-city completion or functional interiors claim.']
 (HERE/'north_water_binding_r01.json').write_text(json.dumps(b,indent=2)+'\n');print(a.sha(HERE/'north_water_binding_r01.json'))
if __name__=='__main__':run()
