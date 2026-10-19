"""Upgrade read-only ancestral guards without repeating certified voxel sampling."""
import argparse,json,resource,time
from pathlib import Path
import adapter as a
import imported_checkpoint_chain_v2 as chain

def verify(contract_path,prior_path,output):
    if output.exists():raise ValueError('Preserve prior evidence')
    resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));start=time.perf_counter()
    spec=a.load(contract_path);prior=a.load(prior_path)
    if not prior['pass'] or prior['import_contract_sha256']!=a.sha(contract_path) or prior['imported_chunks']!=spec['original_count']:
        raise ValueError('Earlier exact replay/source certificate mismatch')
    old_guard=Path(__file__).resolve().parent/'replay_code/import_prefix_adapter_2b6e41e7c617cbf8.py'
    if a.sha(old_guard)!='2b6e41e7c617cbf82cd5bbeff25e83cb7a8ecde6f008106988aaad644b9c00f9':raise ValueError('Earlier guard snapshot changed')
    reader=chain._ReadOnlyStore(a.ROOT/spec['original_directory'],spec['original_identity'],spec['original_files'],repository_root=a.ROOT)
    if reader.reader.completed_count!=spec['original_count'] or chain.producer_segments(reader.reader)!=spec['producer_segments']:
        raise ValueError('Producer chain or prefix changed')
    reader.check_pins()
    report={**prior,'schema':'riverstone.imported_prefix.reference_replay_plus_ancestral_guard.v2','independent_sampling_evidence':{'path':str(prior_path.relative_to(a.ROOT)),'sha256':a.sha(prior_path),'reader_snapshot':{'path':str(old_guard.relative_to(a.ROOT)),'sha256':a.sha(old_guard)}},'new_verification_sampling_calls':0,'earlier_sampling_seconds':prior['elapsed_seconds'],'elapsed_seconds':time.perf_counter()-start,'all_ancestor_source_hashes_and_geometry_rules_verified':True,'all_ancestor_aggregate_states_reverified':True,'reader_sha256':a.sha(chain.__file__),'guard_verifier_sha256':a.sha(__file__),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    a.write(output,report);print(json.dumps({k:report[k] for k in ('pass','imported_chunks','elapsed_seconds','max_rss_kib','new_verification_sampling_calls')}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--contract',required=True,type=Path);p.add_argument('--prior-proof',required=True,type=Path);p.add_argument('--output',required=True,type=Path);x=p.parse_args();verify(x.contract.resolve(),x.prior_proof.resolve(),x.output.resolve())
