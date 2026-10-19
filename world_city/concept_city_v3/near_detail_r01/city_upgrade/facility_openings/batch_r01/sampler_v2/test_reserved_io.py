"""Tiny synthetic file accounting tests; no source compilation."""
import gzip,json,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[6]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parents[2]/'house_rules'))
import reserved_io
from output_reservations_v1 import ReservationBook,ReservationError

def main():
    checks={}
    with tempfile.TemporaryDirectory(prefix='facility_budget_test_') as temp:
        root=Path(temp);batch=root/'batch';batch.mkdir();book=ReservationBook(root/'ledger.json',root,[batch],20000,headroom_bytes=0);scope=[{'directory':'batch/asset','prefix':''}];book.reserve('test',scope,4000,{'fixture':1});w=reserved_io.ReservedWriter(book,'test',batch,scope,root);p=batch/'asset/data.json.gz';value={'groups':[{'material':'stone','quads':[[[0,0,0],[1,0,0],[1,1,0],[0,1,0]]]}]};w.write(p,value);checks['gzip_roundtrip']=json.loads(gzip.decompress(p.read_bytes()))==value;checks['deterministic_encoding']=p.read_bytes()==reserved_io.encoded(p,value);checks['temporary_renamed']=not p.with_name('.tmp.'+p.name).exists();old=p.read_bytes()
        w.write(p,value);checks['atomic_rewrite_identical']=p.read_bytes()==old
        try:w.write(batch/'foreign.json',value)
        except ValueError:checks['out_of_scope_rejected_before_write']=not (batch/'foreign.json').exists()
        try:w.write(batch/'asset/too_large.json',{'x':'x'*5000})
        except ReservationError:checks['per_asset_cap_rejected_before_write']=not (batch/'asset/too_large.json').exists()
        before=reserved_io.WINDOW_COMPOSITION_LIMIT_BYTES;reserved_io.WINDOW_COMPOSITION_LIMIT_BYTES=p.stat().st_size
        try:w.write(p,value)
        except ValueError:checks['existing_plus_temporary_peak_budgeted']=p.read_bytes()==old
        reserved_io.WINDOW_COMPOSITION_LIMIT_BYTES=before
        checks['no_temporary_failure_artifacts']=not list(batch.rglob('.tmp.*'))
    assert len(checks)==8 and all(checks.values()),checks
    out={'schema':'riverstone.facility.reserved_io.tests.v1','tests':checks,'all_pass':True,'actual_source_compile_executed':False};(HERE/'reserved_io.tests.json').write_text(json.dumps(out,sort_keys=True,separators=(',',':'))+'\n');print(json.dumps(out))
if __name__=='__main__':main()
