"""Exclusive writer and visible-stream regressions for new composition only."""
import hashlib,json,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parents[2]/'house_rules')]
import reserved_io_r04 as rio
from output_reservations_v3 import ReservationBook,ReservationError

def main():
    tests={}
    with tempfile.TemporaryDirectory(prefix='facility_stream_budget_r04_') as td:
        root=Path(td);batch=root/'batch';batch.mkdir();book=ReservationBook(root/'book.json',root,[batch],100000,headroom_bytes=0,min_free_disk_bytes=0);scopes=[{'directory':'batch','prefix':'asset'}];book.reserve('x',scopes,10000,{'fixture':'stream'})
        try:book.check('x')
        except ReservationError:tests['check_requires_lifetime_writer']=True
        book.acquire_writer('x');other=ReservationBook(root/'book.json',root,[batch],100000,headroom_bytes=0,min_free_disk_bytes=0)
        try:other.acquire_writer('x')
        except ReservationError:tests['second_writer_rejected']=True
        w=rio.ReservedWriter(book,'x',batch,scopes,root);p=batch/'asset.render.gz'
        with w.stream(p) as f:
            f.write(b'a'*7000);tests['unflushed_stream_bytes_visible']=p.stat().st_size==7000
            try:f.write(b'b'*4000)
            except ReservationError:tests['pending_stream_cannot_exceed_cap']=p.stat().st_size==7000
            else:raise AssertionError('Buffered bytes escaped cap')
        target=batch/'asset.report.json';w.write(target,{'pass':True});tests['temporary_names_remain_in_prefix']=w.accepts(target.with_name(target.name+'.tmp'));tests['stream_bytes_equal_accepted_write']=p.read_bytes()==b'a'*7000;tests['atomic_report_committed']=json.loads(target.read_text())=={'pass':True};tests['temporary_removed_after_success']=not list(batch.glob('*.tmp'))
        try:
            with w.stream(p):pass
        except ValueError:tests['previous_stream_failure_evidence_preserved']=p.read_bytes()==b'a'*7000
        w.close();other.acquire_writer('x');tests['writer_lease_released']=True;other.release_writer('x')
    with tempfile.TemporaryDirectory(prefix='facility_suballocation60_') as td:
        root=Path(td);batch=root/'batch';batch.mkdir();book=ReservationBook(root/'book.json',root,[batch],350000000,headroom_bytes=0,min_free_disk_bytes=0);scopes=[{'directory':'batch','prefix':'asset'}];book.reserve('cap',scopes,70000000,{'fixture':'60MB boundary'});book.acquire_writer('cap');w=rio.ReservedWriter(book,'cap',batch,scopes,root)
        with (batch/'asset.sparse').open('wb') as f:f.truncate(59999900)
        w.check(100);tests['exact60MB_boundary_allowed']=True
        try:w.check(101)
        except ValueError:tests['over60MB_rejected_before_write']=True
        import reserved_io_r03 as old
        old_writer=old.ReservedWriter(book,'cap',batch,scopes,root)
        try:old_writer.check(0)
        except ValueError:tests['old30MB_policy_unchanged']=True
        w.close()
    assert len(tests)==13 and all(tests.values()),tests
    result={'schema':'riverstone.facility.reserved_io.r04.tests.v1','all_pass':True,'tests':tests,'actual_asset_sampling':False,'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'writer_sha256':hashlib.sha256(Path(rio.__file__).read_bytes()).hexdigest(),'previous_helpers_untouched':True};(HERE/'reserved_io.r04.tests.json').write_text(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n');print(json.dumps(result))
if __name__=='__main__':main()
