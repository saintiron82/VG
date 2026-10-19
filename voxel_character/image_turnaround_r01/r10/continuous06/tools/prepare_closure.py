"""Freeze measured larger-lobe evidence without changing any prior asset."""
from surface_atlas import *

def run():
    report = read(BASE / 'evidence/verification.json')
    sheet = Image.new('RGB', (1536, 1220), 'white')
    d = ImageDraw.Draw(sheet)
    d.text((14, 10), 'APPROVED VIOLET r06 | larger lower-lobe chart prototype | depth/root/material correspondence uncertain', fill='black')
    for i, name in enumerate(['front', 'side', 'back']):
        box = A['views'][name]['crop_review']
        im = Image.fromarray(SOURCE).crop(box)
        im.thumbnail((490, 280))
        im = im.resize((im.width * 2, im.height * 2))
        im.thumbnail((490, 280))
        sheet.paste(im, (512 * i + 10, 42))
        d.text((512 * i + 10, 327), name + (' | counterpart UNKNOWN' if name == 'back' else ' | tentative same-lobe match' if name == 'side' else ' | observed visible patch'), fill='black')
    for filename, y in [('source_four_views.jpg', 360), ('common125_four_views.jpg', 760)]:
        im = Image.open(BASE / 'generated' / filename).convert('RGB')
        im.thumbnail((1536, 390))
        sheet.paste(im, (0, y))
    d.text((14, 1163), '12.5mm:580 cells /1 component. 25mm:68 cells /5 components. Same master,25mm thickness,origin fixed. No repair.', fill='black')
    d.text((14, 1182), 'Front IoU93.1%; side coverage72.0%; back candidate support81.0%. Prior upper-flap contact0. Full costume/rig/GPU not validated.', fill='black')
    d.text((14, 1201), 'Actual144 pixel changes ->144 mask pixels ->7 common25 cells; unrelated face25 pixels ->0 geometry. Geometry/art not approved.', fill='black')
    sheet.save(BASE / 'generated/approved_lobe_actual_3d_comparison.jpg', quality=92)
    p = BASE / 'generated/approved_lobe_actual_3d_comparison.jpg'
    write(BASE / 'evidence/comparison_provenance.json', {'path': str(p.relative_to(REPO)), 'sha256': sha(p), 'approved_source_sha256': A['source_sha256'], 'actual_surface_npz_sha256': sha(BASE / 'generated/continuous_surface.npz'), 'master_sha256': sha(BASE / 'generated/panel_master.json.gz'), 'common_mesh_sha256': sha(BASE / 'generated/common125.render.json.gz'), 'CPU_renderer_sha256': sha(CPU_SOURCE), 'script_sha256': sha(__file__), 'image_manipulation': 'Only assembly of literal reference crops and actual CPU geometry renders, labels. No repainting, generated illustration or texture projection.'})
    previous = read(ROOT / 'continuous05c/closure.json')
    paths = {x['path'] for x in previous['files']}
    paths.add(str((ROOT / 'continuous05c/closure.json').relative_to(REPO)))
    for p in BASE.rglob('*'):
        if p.is_file() and p.name != 'closure.json' and ('__pycache__' not in p.parts):
            paths.add(str(p.relative_to(REPO)))
    for p in ['voxel_character/lily_city/data/appearance_contract.json', 'voxel_character/three_head_reference_r01/violet_r06_independent_skin_ratio_validation.json']:
        paths.add(p)
    files = [{'path': p, 'sha256': sha(REPO / p), 'bytes': (REPO / p).stat().st_size} for p in sorted(paths)]
    out = {'schema': 'riverstone.frozen_measured_surface_closure.v1', 'status': 'continuous06 process evidence; whole-character/attachment/art incomplete', 'approved_source': {'path': A['source'], 'sha256': A['source_sha256'], 'Publication metadata omitted.': 'Publication metadata omitted.', 'approval_quote': '맞아 이걸로 해'}, 'preserved_failures': ['prior05/05b in frozen05c dependency closure', 'attempt01 missing15 side root correspondences before bounded explicit prior', '25mm result5 components; no islands removed', 'prior upper-flap contact0 even at12.5mm; no connector fabricated'], 'positive_checks': ['source pixel hash -> independent contour/chart/fold masks -> coupled curvature solution -> common prism master -> actual compiler/mesh -> exact projection overlays', 'same source/master and independent measurement replay exact; common payload/mesh repeat exact', '144 actual local pixels ->144 measured pixels ->7 common25 cell changes; unrelated face25pixel changes ->0 geometry', 'source topology1component,sharedfold154edges,nonmanifold0,adaptive true maximum depth error0.879mm', 'same immutable master12.5mm thin ROI1component580cells'], 'limits': ['side yaw and normalized fold-arc correspondence are priors, vertical residual RMS21.6mm/max39.9mm', 'back candidate identity unknown, not held as true panel target', '15 root vertices use explicit<=4pixel nearest-row depth prior; not observed attachment', 'no final two-sided albedo/material, full outfit/head/body/rig/socket/GPU or art approval', 'actual source is a front-domain graph with two visible charts; hidden multiple-depth returns remain unresolved'], 'representative_image': str((BASE / 'generated/approved_lobe_actual_3d_comparison.jpg').relative_to(REPO)), 'reproduce_in_separate_copy': ['tools/surface_atlas.py', 'tools/review_atlas.py', 'tools/verify_atlas.py', 'tools/prepare_closure.py'], 'predecessor_closure_sha256': sha(ROOT / 'continuous05c/closure.json'), 'changed_predecessor_files': report['changed_frozen05c_files'], 'files': files, 'file_count': len(files), 'total_bytes': sum((x['bytes'] for x in files)), 'excluded': ['__pycache__', 'active full_atlas_plan01 next-stage inventory', 'future whole-character geometry']}
    write(BASE / 'closure.json', out)
    print(json.dumps({'closure': str((BASE / 'closure.json').relative_to(REPO)), 'sha256': sha(BASE / 'closure.json'), 'files': len(files), 'image_sha256': sha(BASE / 'generated/approved_lobe_actual_3d_comparison.jpg'), 'r10_bytes': sum((p.stat().st_size for p in ROOT.rglob('*') if p.is_file()))}))
if __name__ == '__main__':
    run()
