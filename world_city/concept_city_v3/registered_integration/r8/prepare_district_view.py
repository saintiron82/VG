"""Prepare the integrated B15/precinct view from producer-bound artifacts."""
import json,sys
from pathlib import Path
from .build_scene import a,HERE

def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def main(patch_path,acceptance_path,destination):
 patch_path=Path(patch_path).resolve();acceptance_path=Path(acceptance_path).resolve();destination=Path(destination).resolve()
 assert not destination.exists(),'Preserve earlier bindings'
 binding=a.load(HERE/'civic_bound_r02.json')
 precinct=a.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01'
 seal=a.load(precinct/'FIELD_BATCH_SEAL.json');source=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/coherent_regrade_r01/BLOCK_015'
 binding['patches']=[r for r in binding['patches']if not r['path'].endswith('precinct_connected21_normalized_patch.json')]
 binding['patches'] += [seal['surface_patch_to_use_with_ready21'],ref(patch_path)]
 binding['packs'] += [dict(seal['native_pack'],name='precinct_residual18'),dict(ref(source/'resolved_placements.json'),name='coherent_b15_26')]
 binding['evidence'] += [ref(precinct/'FIELD_BATCH_SEAL.json'),ref(source/'freeze_manifest.json'),ref(acceptance_path),ref(a.CITY/'traversal_r5/revisions/r06_r8_precinct/north_connector_r02/freeze_manifest.json')]
 binding['review_cameras']={
  'r8_b15_oblique':dict(position_m=[315,125,405],target_m=[205,3,225],purpose='Whole coherent 26-holding district with varied attached frontage, working courts and connected lanes.'),
  'r8_b15_court_eye':dict(position_m=[250.25,4.15,270.25],target_m=[236.1,4.15,284.4],eye_height_m=1.65,purpose='Native +2.5 m court gate; local producer geometry checked, actual movement is a separate replay gate.')}
 binding['limits']=['Integrated exterior candidate: coherent B15 plus connected precinct fields and bounded north bridge connection.','Other ordinary districts and remaining public corridor repairs are still being activated.','No whole-city completion, full interiors, fluid simulation or texture-polish claim.']
 destination.write_text(json.dumps(binding,indent=2)+'\n');print(ref(destination))
if __name__=='__main__':main(*sys.argv[1:])
