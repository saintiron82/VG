"""Material-only terrain promotion; r4 native placements remain byte-equivalent."""
import json,hashlib,copy
from pathlib import Path
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];ROOT=CITY.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=HERE/'candidate.json';out=copy.deepcopy(json.loads(src.read_bytes()));contract=CITY/'registered_topography/revisions/r11_ground_materials/contract.json';mod='world_city.concept_city_v3.registered_topography.revisions.r11_ground_materials.author';binding=json.loads((HERE/'terrain_binding.json').read_bytes());binding.update(contract_path=str(contract.relative_to(ROOT)),contract_sha256=sha(contract),module=mod)
 (HERE/'material_binding.json').write_text(json.dumps(binding,indent=2)+'\n');out['terrain_module']=mod;out['provenance']['input_packs'].append(dict(name='owned_ground_materials',path=str(contract.relative_to(ROOT)),sha256=sha(contract)));out['provenance']['material_promotion']=dict(parent_sha256=sha(src),same_building_geometry=True,same_height_functions=True,additional_floor_planes=False)
 dest=HERE/'material_candidate.json';assert not dest.exists();dest.write_text(json.dumps(out,separators=(',',':'))+'\n');print(sha(dest))
if __name__=='__main__':main()
