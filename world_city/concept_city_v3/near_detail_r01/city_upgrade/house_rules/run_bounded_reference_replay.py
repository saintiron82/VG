"""Preserved-reference verifier with a cap that never raises an inherited hard limit."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import replay_certificate_qa as replay


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stats',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',type=int,default=4);p.add_argument('--memory-limit',type=int,default=738197504);x=p.parse_args()
    if not 1<=x.samples<=16 or not 0<x.memory_limit<=1073741824:raise ValueError('Bounded replay requires 1..16 samples and at most 1GiB')
    if x.output.exists():raise ValueError('Existing replay evidence must not be overwritten')
    soft,hard=resource.getrlimit(resource.RLIMIT_AS);limit=x.memory_limit if hard==resource.RLIM_INFINITY else min(x.memory_limit,hard)
    resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
    try:report=replay.verify(x.stats,x.samples)
    except (replay.qa.QAError,OSError,ValueError,TypeError,KeyError) as error:report={'schema':'riverstone.house_detail.independent_native_replay.v1','pass':False,'error':str(error),'error_type':type(error).__name__}
    report['entrypoint']={'path':str(Path(__file__).resolve().relative_to(replay.qa.ROOT)),
        'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'reference_verifier_sha256':hashlib.sha256(Path(replay.__file__).read_bytes()).hexdigest(),
        'memory_limit_bytes':limit,'inherited_hard_limit_never_raised':True}
    x.output.parent.mkdir(parents=True,exist_ok=True);x.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report.get(k) for k in ('pass','sampled_chunks','elapsed_seconds','max_rss_kib','error')}),flush=True)
    return 0 if report['pass'] else 1

if __name__=='__main__':raise SystemExit(main())
