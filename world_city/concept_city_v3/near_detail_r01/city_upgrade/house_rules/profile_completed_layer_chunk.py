"""Profile one completed owned chunk; verify exact committed occupancy and quads.

No production engine edit, full-asset recompile, render replacement, or global
constraint claim. Requires a finished checkpoint-backed v2 asset.
"""
import argparse,cProfile,gzip,io,itertools,json,pstats,resource,time
from pathlib import Path
import layered_compile_v2_r02 as layer


def run(stats_path,output):
    if output.exists():raise ValueError('Existing profiling evidence preserved')
    _,hard=resource.getrlimit(resource.RLIMIT_AS);limit=268435456 if hard==resource.RLIM_INFINITY else min(hard,268435456)
    resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
    stats=layer.a.load(stats_path);header=stats['compiled_header'];contract=stats['replay_contract']
    for key in ('authored_master','source_master','layer_rules'):
        r=contract['inputs'][key]
        if layer.a.sha(layer.a.ROOT/r['path'])!=r['sha256']:raise ValueError('Profile input hash mismatch')
    if layer.a.sha(layer.__file__)!=header['layer_engine_sha256']:raise ValueError('Profile must use the exact recorded engine')
    master=layer.load_master(layer.a.ROOT/contract['inputs']['authored_master']['path']);rules=layer.a.load(layer.a.ROOT/contract['inputs']['layer_rules']['path'])
    index=max(range(len(stats['chunks'])),key=lambda i:stats['chunks'][i]['reference_owned_fine_cells']);summary=stats['chunks'][index]
    ck=layer.a.ROOT/stats['checkpoint']['directory']/f'chunk-{index:08d}.json.gz'
    with gzip.open(ck,'rt') as f:saved=json.load(f)
    # Checkpoint format wraps payload under 'record' in current helper.
    expected_record=saved.get('record',saved);expected_quads=expected_record['quads']
    phases={};prof=cProfile.Profile();prof.enable();start=time.perf_counter();cpu_start=time.process_time()
    def timed(name,fn):
        wall=time.perf_counter();cpu=time.process_time();result=fn();phases[name]={'wall_seconds':time.perf_counter()-wall,'cpu_seconds':time.process_time()-cpu};return result
    sources=timed('prepare_spatial_sources_once',lambda:(layer.SpatialSource(master,.05,range_only=True),layer.SpatialSource(master,.1,range_only=True)))
    low,high=summary['owned_bounds_fine'];halo=header['halo_fine_cells'];origin=header['grid_origin']
    clo=[origin[j]+(low[j]-halo)*.05 for j in range(3)];chi=[origin[j]+(high[j]+halo)*.05 for j in range(3)]
    bounds={'min':[v-halo for v in low],'max':[v+halo for v in high]};cb={k:[v//2 for v in vs] for k,vs in bounds.items()}
    bounded=timed('bbox_disjoint_prune_and_copy',lambda:(sources[0].bounded_master(clo,chi),sources[1].bounded_master(clo,chi)))
    budget={'max_candidate_cells':rules['max_chunk_candidate_cells'],'max_output_cells':rules['max_chunk_output_cells']}
    fine=timed('common_v2_fine_sample',lambda:layer.exact_sampling_v2.compile_master_v2(bounded[0],{'pitch':.05},cell_bounds=bounds,**budget))
    coarse=timed('common_v2_core_sample',lambda:layer.exact_sampling_v2.compile_master_v2(bounded[1],{'pitch':.1},cell_bounds=cb,**budget))
    own,near,core,cells=timed('lossless_layer_split',lambda:layer.split_cells(fine,coarse,low,high,rules))
    def fingerprint(rows):
        result=layer.Fingerprint()
        for row in rows:result.add(row)
        return result.value()
    fp=timed('owned_occupancy_hash',lambda:fingerprint(own))
    expected=timed('expected_exterior_face_extraction',lambda:layer.expected_faces(own,cells))
    quads,actual=timed('common_mesh_and_owned_face_extraction',lambda:layer.owned_quads(layer.make_render_data(fine),low,high,rules)) if fine['cells'] else ([],set())
    face=timed('exposed_face_hash',lambda:fingerprint([list(f) for f in actual]))
    def expanded():
        yield from near
        for row in core:
            for delta in itertools.product((0,1),repeat=3):yield [*(2*row[j]+delta[j] for j in range(3)),*row[3:]]
    expansion=timed('reconstruction_hash',lambda:fingerprint(expanded()))
    wall=time.perf_counter()-start;cpu=time.process_time()-cpu_start;prof.disable()
    checks={'owned_occupancy_semantics_exact':fp==summary['full_fine_fingerprint'],
        'lossless_reconstruction_exact':expansion==fp,'exterior_set_exact':expected==actual,
        'exterior_count_exact':len(actual)==summary['visible_unit_faces'],'stored_counts_exact':len(near)==summary['stored_fine_cells'] and len(core)==summary['stored_core_cells'],
        'committed_quad_payload_exact':[[material,quad] for material,quad in quads]==expected_quads,
        'candidate_counts_exact':fine['candidate_cells']==summary['near_candidate_cells'] and coarse['candidate_cells']==summary['core_candidate_cells']}
    text=io.StringIO();pstats.Stats(prof,stream=text).sort_stats('cumulative').print_stats(30)
    report={'schema':'riverstone.layered_detail.one_chunk_profile.v1','pass':all(checks.values()),'checks':checks,'asset_key':stats['asset_key'],'chunk_index':index,'chunk':summary['chunk'],
        'source_master_sha256':stats['source_master_sha256'],'authored_master_sha256':stats['authored_master_sha256'],'layer_engine_sha256':header['layer_engine_sha256'],
        'sampling_backend':header['sampling_backend'],'phases':phases,'profiled_wall_seconds':wall,'profiled_cpu_seconds':cpu,
        'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'memory_limit_bytes':limit,'stats_path':str(stats_path.relative_to(layer.a.ROOT)),
        'checkpoint_path':str(ck.relative_to(layer.a.ROOT)),'checkpoint_sha256':layer.a.sha(ck),'cprofile':text.getvalue(),
        'scope':'One completed owned chunk; source preparation is shown separately from per-chunk work. cProfile adds instrumentation overhead. Reservation I/O/serialization and global constraint aggregation are excluded. No output geometry replaced.'}
    layer.a.write(output,report);print(json.dumps({k:report[k] for k in ('pass','asset_key','chunk_index','profiled_wall_seconds','profiled_cpu_seconds','max_rss_kib','phases')}),flush=True)
    return 0 if report['pass'] else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stats',type=Path,required=True);p.add_argument('--output',type=Path,required=True);x=p.parse_args();raise SystemExit(run(x.stats.resolve(),x.output.resolve()))
