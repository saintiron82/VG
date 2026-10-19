"""Read-only audit of the frozen r5 delivery and r03 preset/cache mapping.

This verifies existing evidence/provenance. It does not rerun or replace the
separate Python, Godot physics, or actual GUI inspection tests.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
CHARACTERS = ROOT.parent
REPO = CHARACTERS.parent
sys.path.insert(0, str(CHARACTERS / 'common'))
from core import digest
from appearance import derive_sources, load_sources


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def audit():
    sources = load_sources()
    canonical_hash = digest(sources['master.json'])
    source_files = {p.name: sha(p) for p in sorted((ROOT / 'data').glob('*.json'))}
    entries = []
    for index in [None, *range(6)]:
        relative = 'generated/r5' if index is None else f'generated/people_review_r3/review_{index:02d}'
        cache = ROOT / relative
        manifest = read(cache / 'manifest.json')
        assert manifest['source_hashes'] == source_files, f'Stale canonical source: {relative}'
        for name, expected_hash in manifest['files'].items():
            assert sha(cache / name) == expected_hash, f'Changed cache file: {relative}/{name}'
        for name, entry in manifest['source_modules'].items():
            assert sha(REPO / entry['source']) == entry['sha256'] == sha(cache / 'common' / name), f'Common vendor changed: {name}'
        master = read(cache / 'derived.master.json')
        master_hash = digest(master)
        assert master_hash == manifest['source_master_hash'], f'Derived hash mismatch: {relative}'
        for name in ('rig.json', 'bind.json', 'idle.json', 'walk.json', 'blink.json',
                     'expression_neutral.json', 'expression_happy.json', 'expression_focused.json', 'lily.render.json'):
            value = read(cache / name)
            assert value['master_hash'] == master_hash, f'Binding mismatch: {relative}/{name}'
            assert value['source_id'] == master['id'], f'Source ID mismatch: {relative}/{name}'
        entry = {'cache': relative, 'manifest_sha256': sha(cache / 'manifest.json'),
                 'derived_master_hash': master_hash, 'render_sha256': sha(cache / 'lily.render.json'),
                 'cells': manifest['cells'], 'quads': manifest['quads'],
                 'parts': manifest['parts'], 'mesh_groups': manifest['mesh_groups']}
        if index is None:
            assert master == sources['master.json'], 'Canonical Lily cache differs from current source'
        else:
            name = f'review_{index:02d}.json'
            old = CHARACTERS / 'people_presets/generated/r02' / name
            current = CHARACTERS / 'people_presets/generated/r03' / name
            assert old.read_bytes() == current.read_bytes(), f'Preset bytes changed: {name}'
            assert sha(current) == manifest['preset_sha256'], f'Preset/cache mismatch: {name}'
            derived = derive_sources(read(current))
            assert derived['master.json'] == master, f'Current derivation mismatch: {name}'
            assert master['extensions']['appearance']['base_master_hash'] == canonical_hash
            entry.update({'captured_preset_file': manifest['preset_file'],
                          'active_preset': str(current.relative_to(CHARACTERS)),
                          'preset_sha256': sha(current), 'preset_bytes_equal_r02_r03': True})
        entries.append(entry)
    collection = CHARACTERS / 'people_presets/generated/r03/manifest.json'
    collection_manifest = read(collection)
    for name, expected_hash in collection_manifest['sources'].items():
        assert sha(CHARACTERS / name) == expected_hash, f'Stale active people source: {name}'
    for name, expected_hash in collection_manifest['files'].items():
        assert sha(collection.parent / name) == expected_hash, f'Changed active preset: {name}'
    capture = read(ROOT / 'evidence/visual_r03/capture_manifest.json')
    assert capture['capture_complete'] and len(capture['captures']) == 6
    assert capture['candidate_change']['master_hash'] == canonical_hash
    images = {c['file']: sha(ROOT / 'evidence/visual_r03' / c['file']) for c in capture['captures']}
    return {'schema': 'riverstone.people.delivery_binding.v1', 'passed': True,
            'canonical_master_hash': canonical_hash, 'source_files_sha256': source_files,
            'active_collection': 'people_presets/generated/r03',
            'active_collection_manifest_sha256': sha(collection), 'caches': entries,
            'actual_visual_captures_sha256': images,
            'audit_scope': 'Hash integrity, current derivation, immutable common copies, and explicit equal-byte r02 to r03 preset rebinding. No new test execution or art acceptance inferred.',
            'capture_preset_history': 'Actual r03 screenshots used these r5-derived caches built from r02 preset paths. r03 preset bytes are identical; their new manifest binds the latest sources. Historical cache manifests and captures are preserved unchanged.',
            'unverified': ['Actual city controller integration', '100 actor runtime performance',
                           'Full animation/footplant visual acceptance', 'Final art acceptance']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        raise FileExistsError('Refusing to overwrite evidence: ' + str(args.output))
    result = audit()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'caches': len(result['caches']),
                      'actual_images': len(result['actual_visual_captures_sha256']),
                      'canonical_master_hash': result['canonical_master_hash'],
                      'report': str(args.output) if args.output else None}))
