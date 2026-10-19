"""Append the independently sealed residual precinct service domains."""
import json
from .build_scene import a,HERE

def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def main():
 dest=HERE/'district_bound_r03.json';assert not dest.exists()
 b=a.load(HERE/'district_bound_r02.json');folder=a.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/residual_extensions_r02';seal=a.load(folder/'READY_SEAL.json');rule=seal['integration']
 old=[p for p in b['patches']if p['path'].endswith('/combined_ready21_residual_surface_patch.json')];assert len(old)==1
 b['patches']=[p for p in b['patches']if p not in old]+[rule['replacement_combined_ground_patch']]
 b['packs'].append(dict(rule['native_pack'],name='precinct_residual_extensions_r02'));b['evidence'].append(ref(folder/'READY_SEAL.json'))
 b['limits'].append('Eight additional retained-ground institutional service domains are source-accepted; actual boundary walks remain separately tracked.')
 dest.write_text(json.dumps(b,indent=2)+'\n');print(ref(dest))
if __name__=='__main__':main()
