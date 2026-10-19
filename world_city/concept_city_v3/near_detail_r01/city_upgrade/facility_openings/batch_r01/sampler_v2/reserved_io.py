"""Prewrite accounting for the explicit-v2 facility pipeline.

Geometry is supplied by frozen common and composition code. This adapter only
serializes, measures and atomically writes within a shared per-asset reservation.
"""
import gzip,io,json,os
from contextlib import contextmanager
from pathlib import Path

WINDOW_COMPOSITION_LIMIT_BYTES=30_000_000

def encoded(path,value):
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()
    if Path(path).suffix!='.gz':return raw
    b=io.BytesIO()
    with gzip.GzipFile(filename='',mode='wb',fileobj=b,mtime=0) as z:z.write(raw)
    return b.getvalue()

class ReservedWriter:
    def __init__(self,book,key,batch_root,scopes,repo_root):
        self.book=book;self.key=key;self.batch_root=Path(batch_root).resolve();self.scopes=scopes;self.root=Path(repo_root).resolve()
    def check(self,additional_bytes=0):
        self.book.check(self.key,additional_bytes)
        total=sum(p.stat().st_size for p in self.batch_root.rglob('*') if p.is_file())
        if total+additional_bytes>WINDOW_COMPOSITION_LIMIT_BYTES:
            raise ValueError('Existing30MB facility opening/composition allocation exhausted')
    def accepts(self,path):
        p=Path(path).resolve()
        for s in self.scopes:
            d=(self.root/s['directory']).resolve()
            if p.is_relative_to(d) and (not s['prefix'] or p.relative_to(d).parts[0].startswith(s['prefix'])):return True
        return False
    @contextmanager
    def stream(self,path):
        path=Path(path).resolve()
        if not self.accepts(path):raise ValueError('Stream outside this asset reservation scope')
        if path.exists():raise ValueError('Refuse to overwrite prior candidate or failure evidence')
        self.check();path.parent.mkdir(parents=True,exist_ok=True)
        budget=self
        with path.open('xb') as raw:
            class CheckedStream:
                def write(self,data):budget.check(len(data));return raw.write(data)
                def flush(self):return raw.flush()
                def tell(self):return raw.tell()
            yield CheckedStream()
    def write(self,path,value):
        path=Path(path).resolve()
        if not self.accepts(path):raise ValueError('Write outside this asset reservation scope')
        payload=encoded(path,value)
        # The original destination remains present during the temporary write.
        # Check the full additional temporary payload, not only the net increase.
        self.check(len(payload));path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_name('.tmp.'+path.name)
        with tmp.open('wb') as f:f.write(payload);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)

def writer_for_catalog(catalog,repo_root,batch_root,house_root):
    """Reopen the same active reservation for composition, replay and sealing."""
    import hashlib,sys
    sys.path.insert(0,str(house_root))
    from output_reservations_v1 import ReservationBook
    root=Path(repo_root).resolve();r=catalog['output_reservation'];assert catalog['signature']==r['identity']['signature'] and catalog['source_sha256']==r['identity']['source_sha256'];p=root/r['shared_config_path']
    if hashlib.sha256(p.read_bytes()).hexdigest()!=r['shared_config_sha256']:raise ValueError('Shared immutable budget configuration SHA changed')
    cfg=json.loads(p.read_text());book=ReservationBook(root/cfg['book_path'],root,[root/p for p in cfg['retained_roots']],cfg['limit_bytes']);record=book.record(r['key'])
    if record is None or record['state']!='ACTIVE' or record['identity']!=r['identity'] or record['cap_bytes']!=r['cap_bytes'] or record['scopes']!=sorted(r['scopes'],key=lambda x:(x['directory'],x['prefix'])):raise ValueError('No exact active output reservation for this catalog')
    writer=ReservedWriter(book,r['key'],batch_root,r['scopes'],root);writer.check();return writer
