"""Stage the source-sealed district packs before public-terminal composition."""
import json,time
from .build_scene import a,HERE,build
def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def main():
 b=a.load(HERE/'district_bound_r04.json');b['finite_physical_side_retirement_union']=True
 root=a.CITY/'registered_topography/revisions/r17_district_batches'
 for name,folder in [('private23','contour_bulk_r01'),('private18','coherent_batch18_r01')]:
  cpath=root/folder/'ready_subset_contract_r01.json';c=a.load(cpath)
  b['packs'].append(dict(c['native_pack'],name=name));b['patches'].append(c['top_patch']);b['evidence'].append(ref(cpath))
 back=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/backland_completion_r01'
 b['packs'].append(dict(ref(back/'activation_subset_r01/resolved_placements.json'),name='functional_backlands_842'))
 b['patches'].append(ref(HERE/'backland_activation_r03/surface_patch.json'));b['evidence'].append(ref(back/'activation_patch_review_r03/acceptance.json'))
 b['limits'].append('Producer preflight only: public-road emission, joint retaining closure and seven noble terminal replacements are not yet attached; do not render or claim traversal acceptance from this binding.')
 p=HERE/'joint_producer_preflight_r01.json';assert not p.exists();p.write_text(json.dumps(b,indent=2)+'\n');start=time.monotonic();out,patch,guard=build(b)
 record=dict(status='PASS_PRODUCER_COMPOSITION_ONLY',binding=ref(p),seconds=time.monotonic()-start,counts=out['counts'],shared_source_face_compositions=len(patch.get('finite_shared_triangle_composition',[])),surface_guard=dict(status=guard['status'],triangles=guard['triangles'],downward=guard['downward']),actual_scene_rendered=False,public_and_joint_boundary_pending=True)
 (HERE/'joint_producer_preflight_result_r01.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2),flush=True)
if __name__=='__main__':main()
