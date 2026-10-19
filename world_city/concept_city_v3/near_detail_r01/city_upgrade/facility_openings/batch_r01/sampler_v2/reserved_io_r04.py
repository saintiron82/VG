"""Explicit60MB batch suballocation writer; same approved350MB shared ledger.

The completed v1 ROI catalog remains immutable. Its exact mirrored reservation
identity is required in the new ledger; this changes accounting, never geometry.
"""
import atexit,hashlib,sys
from pathlib import Path
import reserved_io_r02 as previous

CONFIG_SHA='77b2a42b3694fdb35f9cd923869fec707f22c22fc31e77806e6397dbc6a325d4'
HELPER_SHA='4585bb869ec736e30e524ec6d408db9ed3adceda7d82b336225b8f0079bd9b55'
ALLOCATION_PATH=Path(__file__).with_name('batch_allocation.v2.json')
ALLOCATION_SHA='6efcefb300d70099e13d8e53e155a8423e3fe8c0b8eab6bbd76b3cfdc6b8e1fe'
_ACTIVE=[]

def close_all_writers():
    for writer in list(_ACTIVE):writer.close()
atexit.register(close_all_writers)

class ReservedWriter(previous.ReservedWriter):
    def close(self):
        self.book.release_writer(self.key)
        if self in _ACTIVE:_ACTIVE.remove(self)

    def check(self,additional_bytes=0):
        # Checks use one actual inventory. Unbuffered stream writes are visible
        # to the next check; exclusive asset ownership prevents a second writer.
        if hashlib.sha256(ALLOCATION_PATH.read_bytes()).hexdigest()!=ALLOCATION_SHA:raise ValueError('Allocation SHA changed')
        allocation=previous.json.loads(ALLOCATION_PATH.read_text())
        assert allocation['limit_bytes']==60000000
        self.book.check(self.key,additional_bytes)
        total=sum(p.stat().st_size for p in self.batch_root.rglob('*') if p.is_file())
        if total+additional_bytes>allocation['limit_bytes']:raise ValueError('Approved60MB facility batch allocation exhausted')

def writer_for_catalog(catalog,repo_root,batch_root,house_root):
    root=Path(repo_root).resolve();house=Path(house_root).resolve();r=catalog['output_reservation']
    assert catalog['signature']==r['identity']['signature'] and catalog['source_sha256']==r['identity']['source_sha256']
    p=house/'shared_output_budget.v2.json';helper=house/'output_reservations_v3.py'
    assert hashlib.sha256(p.read_bytes()).hexdigest()==CONFIG_SHA
    assert hashlib.sha256(helper.read_bytes()).hexdigest()==HELPER_SHA
    sys.path.insert(0,str(house));from output_reservations_v3 import ReservationBook
    cfg=previous.json.loads(p.read_text());book=ReservationBook(root/cfg['book_path'],root,[root/p for p in cfg['retained_roots']],cfg['limit_bytes'],min_free_disk_bytes=cfg['min_free_disk_bytes']);record=book.record(r['key'])
    if record is None or record['state']!='ACTIVE' or record['identity']!=r['identity'] or record['cap_bytes']!=r['cap_bytes'] or record['scopes']!=sorted(r['scopes'],key=lambda x:(x['directory'],x['prefix'])):
        raise ValueError('No exact active mirrored output reservation for this frozen ROI catalog')
    book.acquire_writer(r['key'])
    writer=ReservedWriter(book,r['key'],batch_root,r['scopes'],root);_ACTIVE.append(writer)
    try:writer.check()
    except BaseException:writer.close();raise
    writer.provenance={'batch_allocation_path':str(ALLOCATION_PATH.relative_to(root)),'batch_allocation_sha256':ALLOCATION_SHA,'batch_limit_bytes':60000000,'schema':'riverstone.facility.composition_budget.v1','key':r['key'],'cap_bytes':r['cap_bytes'],'original_roi_accounting_unchanged':True,'shared_limit_bytes':cfg['limit_bytes'],'minimum_free_disk_bytes':cfg['min_free_disk_bytes'],'dependencies':[{'path':str(ALLOCATION_PATH.relative_to(root)),'sha256':ALLOCATION_SHA,'role':'explicit60MB suballocation within unchanged shared350MB cap'},{'path':str(p.relative_to(root)),'sha256':CONFIG_SHA,'role':'approved composition shared output budget'},{'path':str(helper.relative_to(root)),'sha256':HELPER_SHA,'role':'exclusive writer and prewrite reservation matcher'},{'path':str(Path(previous.__file__).relative_to(root)),'sha256':hashlib.sha256(Path(previous.__file__).read_bytes()).hexdigest(),'role':'unbuffered atomic serialization implementation'}]}
    return writer
