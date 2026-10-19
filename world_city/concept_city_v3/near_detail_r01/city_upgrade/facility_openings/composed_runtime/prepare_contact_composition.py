"""Measure a corrected composition and retain its finite ownership contracts.

This does not emit another whole-building render or claim final acceptance.
"""
import argparse,collections,resource,time
from pathlib import Path
import stream_compose_priority as sc
a=sc.a;sr=sc.sr

def main(catalog,interfaces,prefix):
    start=time.monotonic();comp=sc.Composition(catalog,interfaces)
    summary=comp.count();print({'stage':'count',**summary},flush=True)
    report={'schema':'riverstone.facility.composition_candidate_preflight.v2','all_pass':False,'review_status':'Measured corrected composition; independent gable retest and final review pending.','summary':summary,'source_inputs':comp.inputs,'interface_priority_selftests':sc.selftests(),'interface_priority_edits':comp.interface_priority_edits,'original_collider_reference_unchanged':True}
    out=Path(str(prefix)+'.preflight.json');a.write(out,report)
    faces=sr.plane_audit(comp.factory);report['faces']=faces
    print({'stage':'faces',**faces},flush=True)
    retained=collections.defaultdict(list)
    for material,quad in comp.retained:retained[material].append(quad)
    rp=Path(str(prefix)+'.outside_retained_sourcequads.json.gz')
    a.write(rp,{'schema':'riverstone.facility.outside_retained_sourcequads.v1','asset_key':comp.key,'source_render_sha256':comp.item['source_render_sha256'],'groups':[{'material':m,'quads':qs} for m,qs in sorted(retained.items())],'world_local_aabbs':comp.regions,'collision_input_unchanged':True,'surface_module_rule':'Use retained source face domains. Compile AABBs are not actual feature overlay exclusion envelopes.'})
    ep=Path(str(prefix)+'.source_face_exceptions.json.gz')
    a.write(ep,{'schema':'riverstone.finite_source_face_edits.v1','source_render_sha256':comp.item['source_render_sha256'],'edits':comp.source_edits,'internal_contact_exceptions':comp.contact_exceptions,'internal_contact_area_m2_each_side':comp.contact_area,'interface_priority_edits':comp.interface_priority_edits,'scope':'Original numeric quad/winding/material/order preserved outside finite ROI subtraction and exact opposed internal-contact exceptions.'})
    report.update(outside_retained_sourcequads={'path':str(rp.relative_to(a.ROOT)),'sha256':a.sha(rp)},source_face_exceptions={'path':str(ep.relative_to(a.ROOT)),'sha256':a.sha(ep)},untouched_original_quad_count=comp.untouched_count,untouched_quad_fingerprint=comp.untouched_sha,finite_edited_original_quad_count=comp.edited_count,elapsed_seconds=round(time.monotonic()-start,3),max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,whole_render_emitted=False,unpaired_edge_count_not_used_as_external_hole_certificate=True)
    a.write(out,report)
    assert summary['runtime_cap_96mib_pass'] and report['max_rss_kib']<256*1024
    assert not faces['same_normal_duplicate_unit_faces'] and not faces['opposed_coplanar_unit_faces']
    print({'prepared':True,'quad_count':summary['quad_count'],'mib':summary['runtime_mib'],'seconds':report['elapsed_seconds'],'rss_kib':report['max_rss_kib']},flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('catalog',type=Path);p.add_argument('interfaces',type=Path);p.add_argument('prefix',type=Path);args=p.parse_args();main(args.catalog.resolve(),args.interfaces.resolve(),args.prefix.resolve())
