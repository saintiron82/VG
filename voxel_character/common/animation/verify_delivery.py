"""Check source -> layer geometry -> actual capture lineage; no rendering."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMMON = HERE.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def verify():
    capture = HERE / 'evidence/render_v1'
    master = read(COMMON / 'assets/house/master.json')
    master_digest = hashlib.sha256(json.dumps(master, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    clip = read(HERE / 'data/house_door.json')
    assert clip['master_hash'] == master_digest
    assert (HERE / 'TransformTracks.gd').read_bytes() == (COMMON / 'preview/AnimationTracks.gd').read_bytes()
    geometry = []
    for pitch in ('0.1', '0.05'):
        final = HERE / f'generated/r2/house_{pitch}.render.json'
        repeat = HERE / f'generated/repeat_r2/house_{pitch}.render.json'
        captured = HERE / f'generated/house_{pitch}.render.json'
        a, b = read(final), read(captured)
        assert final.read_bytes() == repeat.read_bytes()
        assert captured.read_bytes() == (capture / captured.name).read_bytes()
        assert a['master_hash'] == b['master_hash'] == master_digest
        assert a['provenance']['builder_sha256'] == sha(HERE / 'build_render.py')
        assert b['provenance']['builder_sha256'] == sha(capture / 'build_render.py.snapshot')
        for layer in a['provenance']['layers']:
            assert layer['compiler_source_hash'] == sha(COMMON / 'core.py')
        a.pop('provenance'); b.pop('provenance')
        assert a == b, 'Rendered/final geometry or source binding differs'
        geometry.append({'pitch':float(pitch),'final':str(final.relative_to(HERE)),
                         'captured':str(captured.relative_to(HERE)),
                         'repeat_byte_identical':True,'all_nonprovenance_fields_identical':True,
                         'payload_hash':a['payload_hash'],'cell_count':a['cell_count'],
                         'quad_count':a['quad_count'],'pivot_world':a['rigid_parts'][0]['pivot_world']})
    for name, angle in [('closed',0), ('open',105), ('returned',0), ('whole_house',105), ('movie',0)]:
        report = read(capture / f'{name}.json')
        assert report['animation']['sidecar_sha256'] == sha(HERE / 'data/house_door.json')
        assert report['animation']['same_phase']
        assert report['animation']['mesh_resources_and_asset_roots_unchanged']
        assert report['same_camera_transform'] and report['same_camera_scale']
        for state in report['animation']['states']:
            assert state['tracks'][0]['rotation_degrees'] == angle
        for model in report['models']:
            assert sha(Path(model['path'])) == model['render_file_sha256']
        if name != 'movie':
            assert report['screenshot_saved']
    assert (capture / 'render_exit.txt').read_text().strip() == '0'
    assert (capture / 'decode_validation.log').read_text() == ''
    probe = read(capture / 'video_probe.json')['streams'][0]
    assert (probe['width'], probe['height'], probe['nb_read_frames']) == (1440,900,'181')
    headless = read(HERE / 'evidence/headless_house.json')
    assert headless['passed'] and len(headless['checks']) == 23
    assert all(check['pass'] for check in headless['checks'])
    for name,count in [('python_tests',17),('static_viewer_regression',6),('physics_readonly_regression',26)]:
        log = (HERE / f'evidence/{name}.log').read_text()
        assert f'Ran {count} tests' in log and '\nOK\n' in log
    sources = ['core.py','render_data.py','assets/house/master.json','preview/RenderData.gd',
               'preview/Comparison.gd','preview/AnimationTracks.gd','preview/project.godot']
    sources += ['animation/' + name for name in ['build_render.py','TransformTracks.gd','sync_runtime.py',
        'data/house_door.json','tests/test_pipeline.py','tests/CheckAnimation.gd','run_checks.sh',
        'record_preview.sh','verify_delivery.py','README.md']]
    artifacts = list((HERE / 'generated').rglob('*.json'))
    artifacts += [p for p in capture.iterdir() if p.is_file()]
    artifacts += [p for p in (HERE / 'evidence').iterdir() if p.is_file() and p.name != 'verification.json']
    return {'schema':'riverstone.voxel.animation.verification.v1',
        'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'passed':True,'master_hash':master_digest,
        'checks':{'python':17,'static_viewer_regression':6,'physics_readonly_regression':26,'godot_actual_house':23},
        'geometry':geometry,
        'capture':{'path':'evidence/render_v1/door.mp4','width':1440,'height':900,
                   'frames':181,'encoded_fps':30,'duration_seconds':6.033333,
                   'recording_wall_seconds_approx':38,'renderer':'Godot 4.6.3 compatibility / Mesa llvmpipe',
                   'interpretation':'Actual visual transform playback. Fixed-step offline recording, not a physics test or realtime FPS benchmark.',
                   'reuse_basis':'Final cut-selector repair changes provenance only for these house inputs; every other JSON field equals captured input. Original builder, inputs, movie and reports retained.',
                   'direct_visual_review':'evidence/visual_review.md'},
        'source_sha256':{p:sha(COMMON / p) for p in sources},
        'artifact_sha256':{str(p.relative_to(HERE)):sha(p) for p in sorted(set(artifacts))}}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true',help='Create the final manifest; refuse overwrite.')
    args=parser.parse_args()
    result=verify()
    target=HERE / 'evidence/verification.json'
    if args.write:
        with target.open('x') as stream: json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
    else:
        saved=read(target)
        for key in ('source_sha256','artifact_sha256'):
            assert saved[key] == result[key], key+' drift'
    print('PASS: sources, repeated geometry, capture lineage, video decode and regression reports')
