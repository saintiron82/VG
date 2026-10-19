"""Independent unpruned reference replay of deterministic prepared-v3 ROI samples.

Existing stored chunks are read-only. No render or cell cache is regenerated.
Only the small payload comparison report is written under the same reservation.
"""
import argparse,gc,json,math,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent
sys.path[:0]=[str(B.parent),str(B/'sampler_v2'),str(B/'native_pitch_v1')]
import author as a
import reserved_io_r04 as reserved_io
from native_grid import Grids

def run(path):
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));start=time.monotonic();cpu0=resource.getrusage(resource.RUSAGE_SELF);cat=a.load(path);assert cat['complete'] and cat['sampler_provenance']['sampler_id']=='common.prepared_sampling_v3';w=reserved_io.writer_for_catalog(cat,a.ROOT,B,a.HERE.parent/'house_rules');assert a.sha(a.core.__file__)==cat['sampler_provenance']['reference_core_sha256']
    sources={}
    for label,pk,sk in [('coarse','source_master_path','source_sha256'),('roof','roof_master_path','roof_master_sha256'),('fine','canonical_master_path','canonical_master_sha256')]:
        p=a.ROOT/cat[pk];assert a.sha(p)==cat[sk];sources[label]=a.load(p)
    allrefs=[]
    for output in cat['outputs']:
        p=a.ROOT/output['path'];assert a.sha(p)==output['sha256'];allrefs+=a.load(p)['chunks']
    indices=sorted({0,len(allrefs)//3,(2*len(allrefs))//3,len(allrefs)-1});reports=[]
    for index in indices:
        ref=allrefs[index];p=a.ROOT/ref['path'];assert a.sha(p)==ref['sha256'];stored=a.load(p);cb=stored['sample_cell_bounds'];coarsecb=Grids(cat['source_native_pitch_m'],.05,tuple(cat['source_grid_origin_m']),tuple(cat['source_grid_origin_m'])).native_bounds(cb);row={'index':index,'stored_chunk':ref,'region':stored['region'],'chunk':stored['chunk'],'payloads':{}}
        for label,pitch,bounds,field in [('coarse',cat['source_native_pitch_m'],coarsecb,'coarse_payload_sha256'),('roof',.05,cb,'roof_only_payload_sha256'),('fine',.05,cb,'common_payload_sha256')]:
            assert time.monotonic()-start<590;w.check();result=a.core.compile_master(sources[label],{'pitch':pitch},max_candidate_cells=140000,max_output_cells=140000,cell_bounds=bounds);match=result['payload_hash']==stored[field];row['payloads'][label]={'exact_payload_match':match,'reference_payload_sha256':result['payload_hash'],'stored_payload_sha256':stored[field],'candidate_cells':result['candidate_cells'],'occupied_cells':len(result['cells']),'scope':result['evaluation_scope']};assert match,(index,label)
            if label=='fine':assert result['candidate_cells']==stored['fine_candidates'] and len(result['cells'])==stored['fine_cells']
            del result;gc.collect()
        reports.append(row);print(json.dumps({'replayed_chunk':index,'of':len(allrefs),'all_three_payloads_match':True,'seconds':time.monotonic()-start}),flush=True)
    cpu=resource.getrusage(resource.RUSAGE_SELF);report={'schema':'riverstone.facility.roi_independent_reference_replay.v1','asset_key':cat['asset_key'],'all_pass':True,'total_stored_chunks':len(allrefs),'replayed_chunks':len(indices),'reference_common_calls':3*len(indices),'selection':'First, one-third, two-thirds, last catalog chunk in fixed source order.','results':reports,'source_catalog_path':str(path.relative_to(a.ROOT)),'source_catalog_sha256':a.sha(path),'reference_core_sha256':a.sha(a.core.__file__),'sampler_provenance':cat['sampler_provenance'],'replay_implementation_sha256':a.sha(__file__),'source_shapes_cropped':False,'stored_chunks_modified':False,'global_constraints_claimed':False,'scope':'Full unpruned original/canonical/selected-roof source evaluated at four original integer cell_bounds. Exact cell-label payload comparisons, not whole-asset replay or visual acceptance.','wall_seconds':time.monotonic()-start,'user_cpu_seconds':cpu.ru_utime-cpu0.ru_utime,'system_cpu_seconds':cpu.ru_stime-cpu0.ru_stime,'peak_rss_kib':cpu.ru_maxrss};assert cpu.ru_maxrss<256*1024;w.write(path.parent/'reference_replay.json',report);print(json.dumps({k:report[k] for k in ['asset_key','all_pass','replayed_chunks','wall_seconds','peak_rss_kib']}),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('catalog',type=Path);q=p.parse_args();run(q.catalog.resolve())
