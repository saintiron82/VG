"""Promotion gate for actual source -> Godot render -> independent critique.

This does not automate artistic judgment. It prevents replacing that judgment
with a concept image, an old render, raw quad counts or an unreviewed revision.
"""
from pathlib import Path
import argparse, hashlib, json

VIEWS = {'front', 'side', 'pedestrian', 'city_context'}
TOPICS = {'massing', 'material_direction', 'opening_proportion', 'balcony_access',
          'supports', 'street_clearance', 'reference_fidelity', 'lod_transition'}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate(report, root):
    root = Path(root).resolve()
    errors = []
    def check(condition, message):
        if not condition: errors.append(message)
    def ref(value, label):
        if not isinstance(value, dict):
            errors.append(label + ': missing file reference'); return
        path = Path(str(value.get('path', '')))
        if path.is_absolute() or '..' in path.parts:
            errors.append(label + ': non-repository path'); return
        target = (root / path).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            errors.append(label + ': unavailable file'); return
        check(sha(target) == value.get('sha256'), label + ': hash changed')
    check(report.get('schema') == 'riverstone.actual_visual_promotion.v1', 'invalid schema')
    check(bool(report.get('candidate_id')), 'candidate ID missing')
    for field in ('source_master', 'design_contract', 'source_render', 'reference_guide'):
        ref(report.get(field), field)
    check(bool(report.get('reference_photos')), 'original photo references missing')
    for i, photo in enumerate(report.get('reference_photos', [])): ref(photo, 'photo' + str(i))
    renders = report.get('actual_renders', [])
    check(VIEWS <= {r.get('view') for r in renders}, 'required actual views missing')
    for i, render in enumerate(renders):
        label = 'render' + str(i)
        ref(render.get('image'), label)
        ref(render.get('capture_report'), label + '.capture_report')
        check(render.get('engine') == 'Godot', label + ': actual engine required')
        check(render.get('kind') == 'actual_voxel_scene', label + ': concept is not actual scene')
        check(render.get('source_render_sha256') == report.get('source_render', {}).get('sha256'), label + ': stale source')
        check(isinstance(render.get('camera'), dict) and all(k in render['camera'] for k in ('position', 'target', 'fov')), label + ': camera missing')
    critique = report.get('independent_critique', {})
    check(bool(critique.get('reviewer')) and critique.get('reviewer') != report.get('author'), 'independent reviewer required')
    check(critique.get('actual_images_opened') is True, 'actual images not reviewed')
    observations = critique.get('observations', [])
    check(TOPICS <= {row.get('topic') for row in observations}, 'critique topics incomplete')
    for row in observations:
        check(row.get('status') in ('pass', 'not_applicable'), 'unresolved issue: ' + str(row.get('topic')))
        check(bool(row.get('reason')), 'critique reason missing')
        if row.get('status') == 'not_applicable': check(bool(row.get('design_basis')), 'not-applicable requires design basis')
    check(report.get('unresolved_issues') == [], 'unresolved issues remain')
    tests = report.get('functional_tests', {})
    for name in ('source_dimensions', 'entrance_to_public_road', 'balcony_door_to_deck',
                 'clearance_and_plot', 'lod_and_cache', 'collision_scope'):
        value = tests.get(name, {})
        ref(value.get('evidence'), 'functional.' + name)
        check(value.get('pass') is True, 'functional test pending: ' + name)
    check(report.get('status') == 'approved_representative', 'representative not approved')
    return {'all_pass': not errors, 'errors': errors,
            'scope': 'Evidence closure and recorded independent decision only; no automated art judgment.'}

def main():
    p = argparse.ArgumentParser(); p.add_argument('report', type=Path); p.add_argument('--root', type=Path, default=Path.cwd())
    args = p.parse_args(); result = validate(json.loads(args.report.read_text()), args.root)
    print(json.dumps(result, indent=2)); return 0 if result['all_pass'] else 2

if __name__ == '__main__': raise SystemExit(main())
