"""Repeat binder semantic gates via CLI parsing, with every write isolated here.

The production binder is imported without bytecode writes. H, C and R are replaced
with fixture roots. Only two catalog/index metadata records and four render inputs
are copied; no near meshes, masters, collision assets or production catalog writes.
"""
from pathlib import Path
import argparse
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import sys
import traceback

sys.dont_write_bytecode = True
V = Path(__file__).resolve().parent
R = next(p for p in V.parents if (p / 'voxel_character/common/core.py').is_file())
U = R / 'world_city/concept_city_v3/near_detail_r01/city_upgrade'
C = R / 'world_city/concept_city_v3'
B = U / 'bind_source_roof_far_visual.py'
M = U / 'far_roof_lod_r01/expansion_r01/integration_manifest.json'
CAT = C / 'playable_detail_r01/near_catalog.json'
IDX = C / 'playable_r01/generated/tile_r01/index.json'
TEMPLATE = U / 'far_roof_lod_r01/expansion_r01/validation/runtime_review_r01/revision_r03/binder_binding_edges.py'
FR = V / 'fixture_repository'
ALLOWED = {'far_visual_contract_path', 'far_visual_contract_sha256',
           'far_visual_render_path', 'far_visual_render_sha256'}
MODES = ['positive', 'input_unsupported', 'input_wrong_asset',
         'input_wrong_source', 'input_wrong_schema', 'input_wrong_baseline',
         'proof_wrong_asset', 'proof_failed', 'proof_wrong_source',
         'proof_wrong_baseline', 'proof_wrong_input', 'default_cli_positive',
         'outside_h_manifest', 'stale_near']
MAX_OUTPUT_BYTES = 3_000_000


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data, pretty=False):
    assert path.resolve().is_relative_to(V)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2 if pretty else None,
                               separators=None if pretty else (',', ':')) + '\n')
    return {'path': str(path.relative_to(FR)), 'sha256': sha(path)} if path.is_relative_to(FR) else None


def nonfar(cat):
    return dict(cat, assets={asset: {k: v for k, v in record.items() if k not in ALLOWED}
                             for asset, record in cat['assets'].items()})


def run():
    assert not sys.flags.optimize, 'Binder assertion gates must run without -O.'
    manifest = read(M)
    original_cat = read(CAT)
    original_idx = read(IDX)
    keys = [entry['asset_key'] for entry in manifest['entries']]
    assert len(keys) == 2 and len(set(keys)) == 2
    cat = {k: copy.deepcopy(v) for k, v in original_cat.items() if k != 'assets'}
    cat['assets'] = {key: copy.deepcopy(original_cat['assets'][key]) for key in keys}
    idx = {'schema': original_idx['schema']}
    idx['common_assets'] = {key: copy.deepcopy(original_idx['common_assets'][key]) for key in keys}
    watched = {B, M, CAT, IDX, TEMPLATE}
    for entry in manifest['entries']:
        watched.update({R / entry['render_path'],
                        R / entry['candidate_provenance']['path'],
                        R / entry['source_roof_input_contract']['path'],
                        R / idx['common_assets'][entry['asset_key']]['render_path']})
    before = {str(path.relative_to(R)): sha(path) for path in sorted(watched)}
    binder_source = B.read_bytes()
    (V / 'bind_source_roof_far_visual.snapshot.py').write_bytes(binder_source)
    spec = importlib.util.spec_from_file_location('binder_cli_under_test', B)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Byte-for-byte copies, shared by all cases. Binder only reads these inputs.
    copied_inputs = []
    for entry in manifest['entries']:
        for relative in [entry['render_path'], idx['common_assets'][entry['asset_key']]['render_path']]:
            src, dst = R / relative, FR / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
            copied_inputs.append({'path': relative, 'bytes': dst.stat().st_size, 'sha256': sha(dst)})

    rows = []
    for mode in MODES:
        root = FR / 'cases' / mode
        h, croot = root / 'U', root / 'C'
        m, case_cat = copy.deepcopy(manifest), copy.deepcopy(cat)
        default_mp = h / 'far_roof_lod_r01/expansion_r01/integration_manifest.json'
        custom_mp = h / 'far_roof_lod_r01/cli_revision_nondefault_r17/integration_manifest.json'
        mp = default_mp if mode == 'default_cli_positive' else custom_mp
        if mode == 'outside_h_manifest':
            # Existing valid manifest outside H, but still inside the fixture R.
            mp = root / 'outside_H/integration_manifest.json'
        for entry in m['entries']:
            key = entry['asset_key']
            inp = read(R / entry['source_roof_input_contract']['path'])
            proof = read(R / entry['candidate_provenance']['path'])
            if mode == 'input_unsupported': inp['status'] = 'UNSUPPORTED'
            if mode == 'input_wrong_asset': inp['asset_key'] = 'wrong'
            if mode == 'input_wrong_source': inp['source_master']['sha256'] = 'wrong'
            if mode == 'input_wrong_schema': inp['schema'] = 'wrong'
            if mode == 'input_wrong_baseline': inp['baseline_far_render']['sha256'] = 'wrong'
            entry['source_roof_input_contract'] = write(root / 'proofs' / (key + '.input.json'), inp)
            proof['input_contract'] = copy.deepcopy(entry['source_roof_input_contract'])
            if mode == 'proof_wrong_asset': proof['asset_key'] = 'wrong'
            if mode == 'proof_failed': proof['all_geometry_tests_pass'] = False
            if mode == 'proof_wrong_source': proof['source_master']['sha256'] = 'wrong'
            if mode == 'proof_wrong_baseline': proof['baseline_far_render']['sha256'] = 'wrong'
            if mode == 'proof_wrong_input': proof['input_contract'] = {'path': 'wrong', 'sha256': 'wrong'}
            entry['candidate_provenance'] = write(root / 'proofs' / (key + '.proof.json'), proof)
            (mp.parent / key).mkdir(parents=True, exist_ok=True)
            if mode == 'stale_near':
                case_cat['assets'][key]['sha256'] = 'stale-near-sha256'
        write(mp, m)
        cp = croot / 'playable_detail_r01/near_catalog.json'
        ip = croot / 'playable_r01/generated/tile_r01/index.json'
        write(cp, case_cat)
        write(ip, idx)
        pre_catalog_sha, pre_index_sha = sha(cp), sha(ip)
        mod.H, mod.C, mod.R = h, croot, FR
        argv = [str(B)] + ([] if mode == 'default_cli_positive' else ['--manifest', str(mp)])
        saved_argv, sys.argv = sys.argv, argv
        out, err = io.StringIO(), io.StringIO()
        accepted, error, error_line = False, '', None
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                mod.main()
            accepted = True
        except (AssertionError, KeyError, ValueError, SystemExit) as exc:
            error = type(exc).__name__ + ': ' + str(exc)
            frames = traceback.extract_tb(exc.__traceback__)
            binder_frames = [frame for frame in frames if Path(frame.filename) == B]
            if binder_frames:
                error_line = {'line': binder_frames[-1].lineno, 'source': binder_frames[-1].line}
        finally:
            sys.argv = saved_argv
        expected = mode in {'positive', 'default_cli_positive'}
        after_cat = read(cp)
        contracts = sorted(root.rglob('runtime.contract.json'))
        sibling_paths = sorted(mp.parent / key / 'runtime.contract.json' for key in keys)
        binding_checks = []
        if accepted:
            for entry in m['entries']:
                key = entry['asset_key']
                path = mp.parent / key / 'runtime.contract.json'
                contract = read(path)
                binding_checks.append(
                    contract['integration_manifest'] == {'path': str(mp.relative_to(FR)), 'sha256': sha(mp)}
                    and after_cat['assets'][key]['far_visual_contract_path'] == str(path.relative_to(FR))
                    and after_cat['assets'][key]['far_visual_contract_sha256'] == sha(path)
                    and after_cat['assets'][key]['far_visual_render_path'] == entry['render_path']
                    and after_cat['assets'][key]['far_visual_render_sha256'] == entry['render_sha256'])
        checks = {
            'acceptance_matches_expectation': accepted == expected,
            'all_non_far_catalog_fields_preserved': nonfar(case_cat) == nonfar(after_cat),
            'catalog_asset_keys_preserved': set(after_cat['assets']) == set(keys),
            'index_bytes_preserved': sha(ip) == pre_index_sha,
            'rejection_has_no_catalog_write': accepted or sha(cp) == pre_catalog_sha,
            'rejection_has_no_runtime_contract': accepted or not contracts,
            'contracts_beside_selected_manifest': contracts == sibling_paths if accepted else not contracts,
            'accepted_contract_and_catalog_bindings_match': all(binding_checks),
            'explicit_case_does_not_create_default_manifest': mode == 'default_cli_positive' or not default_mp.exists(),
        }
        rows.append({'case': mode, 'expected_accept': expected, 'accepted': accepted,
                     'pass': all(checks.values()), 'checks': checks,
                     'argv': [str(B.relative_to(R))] + ([] if len(argv) == 1 else ['--manifest', str(mp.relative_to(FR))]),
                     'error': error, 'rejected_at': error_line,
                     'stdout': out.getvalue().strip(), 'stderr': err.getvalue().strip(),
                     'catalog_before_sha256': pre_catalog_sha, 'catalog_after_sha256': sha(cp),
                     'runtime_contracts': [str(path.relative_to(FR)) for path in contracts]})
    after = {str(path.relative_to(R)): sha(path) for path in sorted(watched)}
    report = {
        'scope': 'Imported current production binder with patched H/C/R and real argparse sys.argv parsing. Every fixture and output is confined to this directory. No GUI, no production edits, and only two metadata records from each catalog/index are copied.',
        'binder_source_path': str(B.relative_to(R)),
        'binder_source_sha256': hashlib.sha256(binder_source).hexdigest(),
        'template_path': str(TEMPLATE.relative_to(R)),
        'python_version': sys.version,
        'fixture_root': str(FR.relative_to(R)),
        'nondefault_revision': 'cli_revision_nondefault_r17',
        'source_catalog_asset_count': len(original_cat['assets']),
        'isolated_catalog_asset_count': len(keys),
        'target_asset_keys': keys,
        'targets_had_preexisting_far_bindings': {key: bool(original_cat['assets'][key].get('far_visual_contract_path')) for key in keys},
        'copied_geometry_inputs': copied_inputs,
        'production_watched_file_sha256_before': before,
        'production_watched_file_sha256_after': after,
        'production_watched_files_unchanged': before == after,
        'all_non_far_catalog_fields_preserved': all(row['checks']['all_non_far_catalog_fields_preserved'] for row in rows),
        'case_count': len(rows), 'accepted_count': sum(row['accepted'] for row in rows),
        'rejected_count': sum(not row['accepted'] for row in rows),
        'all_pass': all(row['pass'] for row in rows) and before == after,
        'cases': rows,
        'failed': [row['case'] for row in rows if not row['pass']],
        'output_limit_bytes': MAX_OUTPUT_BYTES,
    }
    report_path = V / 'binder_cli_guards.json'
    write(report_path, report, pretty=True)
    # Fixed-width total ensures this includes the report's own final serialized size.
    report['output_total_bytes_decimal'] = '0000000000'
    write(report_path, report, pretty=True)
    total = sum(path.stat().st_size for path in V.rglob('*') if path.is_file())
    report['output_total_bytes_decimal'] = f'{total:010d}'
    report['output_within_limit'] = total <= MAX_OUTPUT_BYTES
    write(report_path, report, pretty=True)
    total = sum(path.stat().st_size for path in V.rglob('*') if path.is_file())
    report['output_total_bytes_decimal'] = f'{total:010d}'
    report['all_pass'] = report['all_pass'] and total <= MAX_OUTPUT_BYTES
    write(report_path, report, pretty=True)
    print(json.dumps({k: report[k] for k in ['binder_source_sha256', 'case_count', 'accepted_count', 'rejected_count', 'all_pass', 'failed', 'production_watched_files_unchanged', 'all_non_far_catalog_fields_preserved', 'output_total_bytes_decimal', 'output_within_limit']}))
    assert report['all_pass'], 'See binder_cli_guards.json for failed gates.'


if __name__ == '__main__':
    run()
