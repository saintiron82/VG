"""Bind sealed canal approaches and level common entry over the district view."""
import json
from .build_scene import a,HERE

def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def main():
 p=HERE/'district_bound_r02.json';assert not p.exists(),'Preserve bindings'
 b=a.load(HERE/'district_bound_r01.json')
 w=a.CITY/'assemblies/waterworks/registered_water_completion_r01';wc=a.load(w/'activation_contract.json');wa=a.load(w/'approaches_r02/activation_contract.json')
 c=a.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/common_entry_repair_r02';cs=a.load(c/'READY_SEAL.json')
 b['packs'] += [dict(wc['placement_pack'],name='water_crossings_r01'),dict(cs['native_pack'],name='common_entry_r02')]
 b['patches'] += [wa['surface_patch'],cs['surface_patch']]
 b['water_extensions']=b.get('water_extensions',[])+wc['water_extensions']
 b['evidence'] += [ref(w/'freeze_manifest.json'),ref(w/'approaches_r02/freeze_manifest.json'),ref(c/'READY_SEAL.json')]
 b['limits'] += ['Four canal crossings and common entry are source-accepted local geometry; their complete public-network continuation and controller replay remain pending.']
 p.write_text(json.dumps(b,indent=2)+'\n');print(ref(p))
if __name__=='__main__':main()
