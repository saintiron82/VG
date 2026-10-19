"""Before-use regression for visible streamed byte accounting and temp prefixes."""
import json,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parents[2]/'house_rules'))
import reserved_io_r02 as rio
from output_reservations_v1 import ReservationBook,ReservationError

def main():
    tests={}
    with tempfile.TemporaryDirectory(prefix='facility_stream_budget_') as td:
        root=Path(td);batch=root/'batch';batch.mkdir();book=ReservationBook(root/'book.json',root,[batch],100000,headroom_bytes=0);scopes=[{'directory':'batch','prefix':'asset'}];book.reserve('x',scopes,10000,{'fixture':'stream'});w=rio.ReservedWriter(book,'x',batch,scopes,root);p=batch/'asset.render.gz'
        with w.stream(p) as f:
            f.write(b'a'*7000);tests['unflushed_stream_bytes_visible']=p.stat().st_size==7000
            try:f.write(b'b'*4000)
            except ReservationError:tests['pending_stream_cannot_exceed_cap']=p.stat().st_size==7000
            else:raise AssertionError('Buffered bytes escaped cap')
        target=batch/'asset.report.json';w.write(target,{'pass':True});tests['temporary_names_remain_in_prefix']=w.accepts(target.with_name(target.name+'.tmp'));tests['stream_bytes_equal_accepted_write']=p.read_bytes()==b'a'*7000;tests['atomic_report_committed']=json.loads(target.read_text())=={'pass':True};tests['temporary_removed_after_success']=not list(batch.glob('*.tmp'))
        try:
            with w.stream(p):pass
        except ValueError:tests['previous_stream_failure_evidence_preserved']=p.read_bytes()==b'a'*7000
    assert len(tests)==7 and all(tests.values()),tests
    result={'schema':'riverstone.facility.reserved_io.r02.tests.v1','all_pass':True,'tests':tests,'actual_asset_sampling':False,'previous_helper_untouched':True};(HERE/'reserved_io.r02.tests.json').write_text(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n');print(json.dumps(result))
if __name__=='__main__':main()
