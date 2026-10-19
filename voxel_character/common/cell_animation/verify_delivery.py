"""Read-only reproducibility, frozen-source, and actual capture lineage gate."""
import argparse
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
COMMON=HERE.parent
REPO=COMMON.parents[1]

def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def verify():
    render_path=HERE/'generated/flow_pitch_0.1_r4.json'
    render=read(render_path);clip=read(HERE/'data/flow_clip.json');master=read(COMMON/'assets/fountain/master.json')
    assert render_path.read_bytes()==(HERE/'generated/flow_repeat_r4.json').read_bytes()
    assert render['master_hash']==clip['master_hash']==digest(master)
    assert render['cell_animation']['clip_hash']==digest(clip)
    assert render['provenance']['builder_sha256']==sha(HERE/'build_render.py')
    assert render['provenance']['compiler_source_hash']==sha(COMMON/'core.py')
    assert render['provenance']['coordinate_plane_preprocessor_sha256']==sha(COMMON/'coordinate_planes.py')
    assert render['cell_count']==10720
    assert render['provenance']['static_cells_occluded_by_fixed_pools']==40
    assert [len(p['positions']) for p in render['cell_animation']['pools']]==[256,36,48]
    assert 'states' not in render['cell_animation'] and 'states' not in clip
    frozen=read(HERE/'evidence/frozen_sources_before.json')
    for path,expected in frozen.items():assert sha(REPO/path)==expected,path
    prior=read(COMMON/'assets/fountain/source_integrity.json')
    for row in prior['fountain_source_files']:assert sha(REPO/row['path'])==row['sha256'],row['path']
    for row in prior['physics_manifest_source_files']:assert sha(COMMON.parent/'physics'/row['path'])==row['sha256'],row['path']
    for row in clip['source_lineage']['files']:assert sha(REPO/row['path'])==row['sha256'],row['path']
    assert (HERE/'RenderData.gd').read_bytes()==(COMMON/'preview/RenderData.gd').read_bytes()
    checks={}
    for name,count in [('python_tests',26),('common_regression',82),('physics_regression',26)]:
        log=(HERE/f'evidence/{name}.log').read_text()
        assert f'Ran {count} tests' in log and '\nOK\n' in log,name
        checks[name]=count
    headless=read(HERE/'evidence/headless_flow_r4.json')
    assert headless['passed'] and len(headless['checks'])==73 and all(c['pass'] for c in headless['checks'])
    assert headless['clip_hash']==digest(clip)
    checks['godot_full']=73
    cap=HERE/'evidence/render_r5';reports={}
    for name,time in [('start',0),('peak',.6),('alternate',1.2),('detail',.6),('movie',0)]:
        report=read(cap/f'{name}.json');reports[name]=report
        assert report['render_file_sha256']==sha(render_path)
        assert report['master_hash']==digest(master) and report['clip_hash']==digest(clip)
        assert report['mode']=='graphical_preview' and report['static_mesh_resources_and_arrays_unchanged']
        state=report['state'];assert state['capacity']==340 and state['pool_node_count']==3 and state['pool_resource_count']==9
        if name!='movie':
            assert report['screenshot_saved'] and not state['playing']
            assert abs(state['evaluation_time']-time)<1e-8
        else:
            assert report['movie_mode'] and report['movie_fps']==30 and report['frames']==145
            assert report['movie_clock_source']=='explicit_capture_fps'
            assert abs(report['movie_time']-4.8)<1e-8
    for a,b in zip(reports['start']['state']['pools'],reports['movie']['state']['pools']):
        for key in ['positions','member_indices','color_indices','visible_count']:assert a[key]==b[key],key
    assert (cap/'render_exit.txt').read_text().strip()=='0'
    assert (cap/'decode_validation.log').read_text()==''
    frame_hashes=[row.split(',')[-1].strip() for row in (cap/'frames.md5').read_text().splitlines() if not row.startswith('#')]
    assert len(frame_hashes)==145 and all(frame_hashes[i]==frame_hashes[i+72] for i in range(72))
    assert frame_hashes[0]==frame_hashes[144]
    probe=read(cap/'video_probe.json')['streams'][0]
    assert probe['nb_read_frames']=='145' and probe['r_frame_rate']=='30/1'
    sources=list(HERE.glob('*.py'))+list(HERE.glob('*.gd'))+list(HERE.glob('*.md'))+list(HERE.glob('*.sh'))+list((HERE/'tests').glob('*.py'))+list((HERE/'tests').glob('*.gd'))+[HERE/'project.godot',HERE/'Preview.tscn',HERE/'data/flow_clip.json']
    artifacts=[render_path,HERE/'generated/flow_repeat_r4.json',HERE/'generated/flow_oracle_r4.json']
    artifacts+=list(cap.iterdir())
    artifacts += [HERE/'evidence'/name for name in ['headless_flow_r4.json','headless_flow_r4.log','python_tests.log','common_regression.log','physics_regression.log','visual_review.md','frozen_sources_before.json']]
    return {'schema':'riverstone.voxel.cell_animation.verification.v1','passed':True,
      'master_hash':digest(master),'clip_hash':digest(clip),'payload_hash':render['payload_hash'],
      'repeated_build_byte_identical':True,'checks':checks,
      'fixed_pool':{'capacity':340,'nodes':3,'owned_resources':9,'members':[256,36,48]},
      'static_cells':10720,'explicit_static_occlusion_removed_cells':40,
      'capture':{'file':'evidence/render_r5/pools.mp4','frames':145,'fps':30,'width':probe['width'],'height':probe['height'],'duration':float(probe['duration']),'two_loop_return_matches_start':True,'decoded_loop_frame_pairs_exact':72,'movie_clock':'integer_active_frame_index / 30' ,'offline_fixed_step_not_realtime_benchmark':True},
      'unsupported':['pitch0.2 structural failure','pitch0.05 not evaluated','legacy alternative shader clip','fluid/physics simulation','game integration'],
      'source_sha256':{str(p.relative_to(HERE)):sha(p) for p in sorted(sources)},
      'frozen_source_sha256':frozen,
      'artifact_sha256':{str(p.relative_to(HERE)):sha(p) for p in sorted(artifacts)}}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--write',action='store_true');args=parser.parse_args();result=verify();path=HERE/'evidence/verification.json'
    if args.write:
        with path.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    else:assert read(path)==result,'saved verification drift'
    print('PASS: repeated pure-data build, 3 analytic functions, frozen sources, tests, actual two-loop capture and decode')
