"""Independent original-core replay of four preserved partial chunk records.
Read-only checkpoints; global constraints remain pending until full-domain finish.
"""
import argparse,json,resource,signal,time
from pathlib import Path
import adapter as a
import checkpoint_store
import layered_qa as qa
import replay_certificate_qa as replay

def verify(directory,samples=4):
    begin=time.perf_counter();before=a.sha(directory/'manifest.json');identity=a.load(directory/'manifest.json')['identity'];header=identity['header']
    if a.sha(a.core.__file__)!=header['compiler_source_sha256']:raise ValueError('Reference compiler changed')
    for name,key in [('master','authored_master_sha256'),('source','source_master_sha256'),('catalog','input_catalog_sha256'),('rules','layer_rules_sha256')]:
        if a.sha(a.ROOT/identity['source_paths'][name])!=header[key]:raise ValueError('Pinned source changed '+name)
    store=checkpoint_store.Store(directory,identity);records=list(store.load_records());state=store.load_state()
    with qa._text_file(a.ROOT/identity['source_paths']['master']) as stream:master=json.load(stream)
    if a.core.digest(master)!=header['master_hash']:raise ValueError('Canonical master changed')
    edge=header['chunk_edge_fine_cells'];halo=header['halo_fine_cells'];origin=header['grid_origin'];summaries=[r['chunk_stats'] for r in records]
    chosen=replay.choose_chunks(summaries,samples);reports=[]
    for number in chosen:
        tick=time.perf_counter();record=records[number];summary=record['chunk_stats'];key=summary['chunk'];lo=[v*edge for v in key];hi=[v+edge for v in lo]
        bounds={'min':[v-halo for v in lo],'max':[v+halo for v in hi]};result=a.core.compile_master(master,{'pitch':.05},cell_bounds=bounds,max_candidate_cells=5000000,max_output_cells=600000)
        cells={tuple(r[:3]):r for r in result['cells']};occupancy=qa.Fingerprint();faces=qa.Fingerprint();mesh=qa.Fingerprint()
        for row in result['cells']:
            if not replay.owned(row,lo,hi):continue
            occupancy.add(row)
            for axis in range(3):
                for sign in (-1,1):
                    p=list(row[:3]);p[axis]+=sign
                    if tuple(p) not in cells:faces.add([axis,sign,row[axis]+(sign>0),row[(axis+1)%3],row[(axis+2)%3],row[5]])
        for material,quad in record['quads']:
            rect=qa._quad_rectangle(quad,origin,.05)
            if replay.quad_owner(rect,edge)!=tuple(key):raise ValueError('Stored quad crossed ownership')
            axis,sign,plane,u0,u1,v0,v1=rect
            for u in range(u0,u1):
                for v in range(v0,v1):mesh.add([axis,sign,plane,u,v,material])
        checks={'occupancy_semantics':occupancy.as_dict()==qa._fingerprint(summary['full_fine_fingerprint']),'directed_material_faces':faces.as_dict()==mesh.as_dict(),'exterior_count':faces.count==summary['visible_unit_faces'],'quad_count':len(record['quads'])==summary['quads'],'bounded_not_global':result['global_constraints_evaluated'] is False}
        reports.append({'index':number,'chunk':key,'checks':checks,'pass':all(checks.values()),'candidate_cells':result['candidate_cells'],'seconds':time.perf_counter()-tick});del result,cells
    if a.sha(directory/'manifest.json')!=before:raise ValueError('Checkpoint changed during read-only replay')
    return {'schema':'riverstone.partial_house_checkpoint.reference_replay.v1','pass':bool(reports) and all(r['pass'] for r in reports),'compiled_chunks':len(records),'sampled_chunks':len(reports),'complete_asset':False,'global_constraints_pass':False,'all_chunks_replayed':len(records)==len(reports),'checkpoint_path':str(directory.relative_to(a.ROOT)),'manifest_sha256':before,'checkpoint_identity_sha256':store.identity_digest,'source_sha256':header['source_master_sha256'],'authored_master_sha256':header['authored_master_sha256'],'reference_core_sha256':a.sha(a.core.__file__),'producer_engine_sha256':header['layer_engine_sha256'],'verifier_sha256':a.sha(__file__),'reports':reports,'wall_seconds':time.perf_counter()-begin,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True);x=p.parse_args()
    if x.output.exists():raise ValueError('Prior QA preserved')
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
    def timeout(*_):raise TimeoutError('Replay 120 second cap')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(120)
    result=verify(x.checkpoint.resolve());a.write(x.output,result);print(json.dumps({k:v for k,v in result.items() if k!='reports'}));raise SystemExit(0 if result['pass'] else 1)
