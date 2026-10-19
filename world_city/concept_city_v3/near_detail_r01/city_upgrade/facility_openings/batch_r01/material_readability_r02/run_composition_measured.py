"""Bounded subprocess resource evidence; geometry stays in frozen composition."""
import argparse,hashlib,json,resource,subprocess,sys,time
from pathlib import Path
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'sampler_v2'))
import reserved_io_r04 as reserved_io
HERE=Path(__file__).resolve().parent;B=HERE.parent
sys.path.insert(0,str(B.parent));import author as a

def main(catalog,handoff):
    start=time.monotonic();cmd=[sys.executable,'-u',str(HERE/'compose_reserved.py'),str(catalog),'--roof-handoff',str(handoff),'--edges','--emit'];status=None
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=600);status={'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'timed_out':False}
    except subprocess.TimeoutExpired as e:
        status={'returncode':None,'stdout':str(e.stdout or ''),'stderr':str(e.stderr or ''),'timed_out':True}
    usage=resource.getrusage(resource.RUSAGE_CHILDREN);cat=a.load(catalog);w=reserved_io.writer_for_catalog(cat,a.ROOT,B,a.HERE.parent/'house_rules');report={'schema':'riverstone.facility.composition_resource_usage.v1','asset_key':cat['asset_key'],'wall_seconds':time.monotonic()-start,'user_cpu_seconds':usage.ru_utime,'system_cpu_seconds':usage.ru_stime,'peak_rss_kib':usage.ru_maxrss,'memory_limit_bytes':256*1024*1024,'wall_limit_seconds':600,'command':cmd,'driver_reference':{'path':str(Path(__file__).relative_to(a.ROOT)),'sha256':a.sha(__file__)},'source_catalog_sha256':a.sha(catalog),**status};w.write(HERE/'composed'/cat['asset_key']/'composition_resource_usage.json',report);w.close();print(json.dumps(report),flush=True);assert status['returncode']==0 and not status['timed_out'];assert usage.ru_maxrss<256*1024
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('catalog',type=Path);p.add_argument('--roof-handoff',type=Path,required=True);q=p.parse_args();main(q.catalog.resolve(),q.roof_handoff.resolve())
