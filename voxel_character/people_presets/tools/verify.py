#!/usr/bin/env python3
"""Exhaustive small source matrix and optional six in-memory common compilations."""
import argparse,json,sys,time
from pathlib import Path
from presets import HERE,LILY,read,digest,file_sha,appearance_module,geometry_combinations
from compatibility import validate_derived
from build_render import make_animated_render

def verify(collection,output,compile_review=False):
    collection=collection.resolve();output=output.resolve()
    if output.exists():raise FileExistsError('New evidence path required')
    manifest=read(collection/'manifest.json')
    for name,sha in manifest['sources'].items():
        if file_sha(HERE.parent/name)!=sha:raise ValueError('Source drift: '+name)
    for name,sha in manifest['files'].items():
        if file_sha(collection/name)!=sha:raise ValueError('Artifact drift: '+name)
    start=time.perf_counter();shared=appearance_module();base=shared.load_sources();before=digest(base)
    results=[]
    for preset in geometry_combinations():
        sources=shared.derive_sources(preset,base)
        results.append(validate_derived(preset,sources,base))
    compiled=[]
    if compile_review:
        for id in manifest['review_presets']:
            preset=read(collection/(id+'.json'));sources=shared.derive_sources(preset,base)
            r=make_animated_render(sources['master.json'],sources['bind.json'],.02,max_candidates=1000000)
            rig=sources['rig.json'];ids={p['selector']['part'] for p in r['rigid_parts']}
            assert ids=={p['id'] for p in rig['parts']}
            assert all(p['cell_count']>0 for p in r['rigid_parts'])
            assert r['cell_count']<=rig['limits']['reference_max_cells']
            assert r['quad_count']<=rig['limits']['reference_max_quads']
            assert abs(r['bounds']['min'][1])<1e-9
            head=next(p for p in r['rigid_parts'] if p['selector']['part']=='head')
            assert {'iris','iris_light','eye_white','pupil'}<={g['material'] for g in head['groups']}
            assert r['materials']==sources['master.json']['materials']
            compiled.append({'preset_id':id,'status':'pass','source_master_sha256':digest(sources['master.json']),
              'parts':len(ids),'cells':r['cell_count'],'quads':r['quad_count'],'material_part_groups':sum(len(p['groups']) for p in r['rigid_parts']),
              'bounds_m':r['bounds'],'payload_sha256':r['payload_hash'],'parts_summary':[{k:p[k] for k in ['selector','pivot_world','bounds','cell_count','payload_hash']} for p in r['rigid_parts']],
              'mesh_file_retained':False,'actual_visual_review':False})
    assert digest(base)==before
    result={'schema':'riverstone.people.appearance_verification.v1','status':'pass','source_matrix_passed':len(results),'source_matrix_total':216,
      'all_supported_clip_bindings_passed':True,'review_common_compilations':compiled,'source_matrix':results,
      'collection_manifest_sha256':file_sha(collection/'manifest.json'),'collection_manifest':str(collection.relative_to(HERE)) if collection.is_relative_to(HERE) else str(collection),
      'sources':manifest['sources'],'validation_implementation':{str(p.relative_to(HERE)):file_sha(p) for p in [Path(__file__),HERE/'tools/compatibility.py',HERE/'tests/test_presets.py']},
      'seconds':round(time.perf_counter()-start,3),'limits':['No city actors instantiated.','No behavior, dialogue, schedules or economy enabled.',
      '216 source variants checked; only listed review variants voxel-compiled.','No appearance screenshot or city-scale rendering performance acceptance in this report.']}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','source_matrix_passed','source_matrix_total','seconds']}))
    print(json.dumps({'review_compiled':len(compiled),'cells':[r['cells'] for r in compiled],'quads':[r['quads'] for r in compiled]}))
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--collection',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--compile-review',action='store_true')
    a=p.parse_args();verify(a.collection,a.output,a.compile_review)
