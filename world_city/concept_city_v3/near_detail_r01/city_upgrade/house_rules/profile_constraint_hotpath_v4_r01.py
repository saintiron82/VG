"""Read-only one-chunk selector-cache experiment; production engine is unchanged."""
import argparse, collections, gzip, hashlib, json, resource, statistics, time
from pathlib import Path
import layered_compile_frontier_v4_r01 as layer

def run(stats_path, output):
    if output.exists(): raise ValueError('Preserve diagnostic evidence')
    limit=192*1024*1024;resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
    a=layer.a;s=a.load(stats_path);header=s['compiled_header'];assert a.sha(layer.__file__)==header['layer_engine_sha256']
    for r in s['replay_contract']['inputs'].values():assert a.sha(a.ROOT/r['path'])==r['sha256']
    index=min(range(len(s['chunks'])),key=lambda i:abs(s['chunks'][i]['reference_owned_fine_cells']-25000))
    summary=s['chunks'][index];low,high=summary['owned_bounds_fine'];halo=header['halo_fine_cells']
    master=layer.load_master(a.ROOT/s['replay_contract']['inputs']['authored_master']['path'])
    start=time.perf_counter();plan=layer.prepared_sampling_v3.prepare_master(master,{'pitch':.05},max_plan_bytes=96*1024*1024);prep=time.perf_counter()-start
    assert plan.plan_key==s['prepared_plans']['fine']['plan_key']
    start=time.perf_counter();result=layer.prepared_sampling_v3.compile_prepared(plan,cell_bounds={'min':[x-halo for x in low],'max':[x+halo for x in high]},max_candidate_cells=1500000,max_output_cells=500000);sample=time.perf_counter()-start
    own=[r for r in result['cells'] if layer.owned(r,low,high)];fp=layer.Fingerprint()
    for r in own:fp.add(r)
    assert fp.value()==summary['full_fine_fingerprint'];mapping={i['id']:i['component'] for i in master['instances']}
    def select(cached):
        counts=collections.Counter();selected={c['id']:[] for c in master['constraints'] if c['kind']=='connected'};cache={};calls=0
        for row in own:
            key=(row[3],mapping[row[3]],row[4],row[5],row[6])
            if not cached or key not in cache:
                cell=dict(zip(('instance','component','part','material','feature'),key));matches=[]
                for c in master['constraints']:
                    calls+=1
                    if a.core.selector_matches(c.get('selector',{}),cell):matches.append((c['id'],c['kind']))
                if cached:cache[key]=matches
            else:matches=cache[key]
            for cid,kind in matches:
                counts[cid]+=1
                if kind=='connected':selected[cid].append(tuple(row[:3]))
        return dict(counts),selected,calls,len(cache)
    times={False:[],True:[]};reference=None;calls={}
    for trial in range(5):
        for cached in ([False,True] if trial%2==0 else [True,False]):
            begin=time.perf_counter();value=select(cached);times[cached].append(time.perf_counter()-begin)
            if reference is None:reference=value[:2]
            assert value[:2]==reference;calls[str(cached)]={'predicate_calls':value[2],'cached_semantic_keys':value[3]}
    report={'schema':'riverstone.constraint_selection.exact_cache_probe.v1','pass':True,'source_and_production_unchanged':True,'production_engine_modified':False,'stats':{'path':str(stats_path.relative_to(a.ROOT)),'sha256':a.sha(stats_path)},'asset_key':s['asset_key'],'chunk_index':index,'chunk':summary['chunk'],'owned_semantic_cells':len(own),'fine_occupancy_fingerprint_exact':True,'counts_and_ordered_connected_point_lists_exact':True,'prepare_seconds':prep,'sample_seconds':sample,'reference_selection_seconds':times[False],'cached_selection_seconds':times[True],'median_speedup':statistics.median(times[False])/statistics.median(times[True]),'calls':calls,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'memory_limit_bytes':limit,'diagnostic_sha256':a.sha(__file__),'cache_contract':'Memoize only pure selector_matches over all five exact semantic cell fields in the fixed full master. No coordinate, sampling, predicate, constraint, count, or point order changes.'}
    a.write(output,report);print(json.dumps(report));return 0
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stats',type=Path,required=True);p.add_argument('--output',type=Path,required=True);x=p.parse_args();raise SystemExit(run(x.stats.resolve(),x.output.resolve()))
