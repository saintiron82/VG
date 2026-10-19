"""Preserve sealed phase02 source, verify its closure, rebind exact R6 triangles."""
import json,time
from .promotion import rebind_unchanged_triangles
from .build_scene import a,HERE,BASE_SHA
from ..r7 import surface_guard

def run():
 start=time.monotonic();folder=a.CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase02';freeze_path=folder/'freeze_manifest.json';freeze=a.load(freeze_path,'3c54b69f6852c1adbb1cc0ebabf449e66048e8386bef5e2a88ec0c888939bdb1')
 for row in freeze['files']+freeze['external_input_and_import_closure']:
  assert a.sha(a.source_file(row['path']))==row['sha256'],row['path']
 old=a.load(a.source_file(freeze['base_scene']['path']),freeze['base_scene']['sha256']);new_path=a.CITY/'evidence/visual_registered_common_r7_palette_r01/scene.json';new=a.load(new_path,BASE_SHA)
 patch=a.load(a.source_file(freeze['ground_patch']['path']),freeze['ground_patch']['sha256']);rebound=rebind_unchanged_triangles(patch,old,new,freeze['base_scene']['sha256'],BASE_SHA);guard=surface_guard.audit_patch(rebound)
 r16=a.load(a.CITY/'registered_topography/revisions/r16_working_ranges/scene_patch.json')
 assert not {(r['material'],r['triangle_index']) for r in patch['surface_edits']}&{(r['material'],r['triangle_index']) for r in r16['surface_edits']}
 out=HERE/'precinct_phase02_rebound_patch.json';assert not out.exists();out.write_text(json.dumps(rebound,separators=(',',':'))+'\n')
 record=dict(source_freeze_sha256=a.sha(freeze_path),verified_refs=len(freeze['files'])+len(freeze['external_input_and_import_closure']),old_base_sha256=freeze['base_scene']['sha256'],new_base_sha256=BASE_SHA,source_triangle_count=len(patch['surface_edits']),ordered_xyz_and_all_replacement_geometry_unchanged=True,no_R16_source_edit_overlap=True,spatial_scope='Separated estate/abbey domains; ground producer excludes retained native owners. Actual scene and stair controller pending.',rebound_patch_sha256=a.sha(out),seconds=time.monotonic()-start)
 (HERE/'precinct_phase02_rebind_review.json').write_text(json.dumps(record,indent=2)+'\n')
 binding=dict(schema='riverstone.r8.binding.v1',base_scene=dict(path=a.rel(new_path),sha256=BASE_SHA),evidence=[dict(path=a.rel(freeze_path),sha256=a.sha(freeze_path)),dict(path=a.rel(HERE/'precinct_phase02_rebind_review.json'),sha256=a.sha(HERE/'precinct_phase02_rebind_review.json'))],patches=[dict(path=a.rel(out),sha256=a.sha(out))],packs=[dict(freeze['resolved_pack'],name='precinct_phase02')],limits=['Candidate precinct extension over R7; city district coverage remains incomplete.','26 x 0.15 m stair risers have static geometry proof only; character test pending.','Registered camera and bridge/water unchanged.'])
 (HERE/'precinct_preflight_binding.json').write_text(json.dumps(binding,indent=2)+'\n');print(json.dumps(record,indent=2))
if __name__=='__main__':run()
