"""Atomic, crash-persistent per-asset reservations within a fixed retained-byte cap.

The ledger never expires a reservation implicitly and never deletes payloads.
All participating writers must check before writes. Legacy observer reservations
are explicitly labelled and require their separate existing hard-limit guards.
"""
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import json
import os
import shutil
import stat
from pathlib import Path


class ReservationError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


class ReservationBook:
    def __init__(self, path, root, retained_roots, limit_bytes=350_000_000, headroom_bytes=262144, min_free_disk_bytes=1073741824):
        self.path=Path(path).resolve();self.root=Path(root).resolve()
        self.roots=sorted({str(Path(p).resolve()) for p in retained_roots})
        if not self.roots or any(not Path(p).is_relative_to(self.root) for p in self.roots):
            raise ReservationError('Retained roots must be inside the approved repository')
        if any(Path(a).is_relative_to(Path(b)) for a in self.roots for b in self.roots if a!=b):
            raise ReservationError('Nested retained roots would double-count output')
        if type(limit_bytes)is not int or limit_bytes<=0 or type(headroom_bytes)is not int or headroom_bytes<0:
            raise ReservationError('Invalid byte limit')
        if type(min_free_disk_bytes)is not int or min_free_disk_bytes<0:raise ReservationError('Invalid minimum free disk guard')
        self._writers={}
        self.contract={'min_free_disk_bytes':min_free_disk_bytes,'retained_roots':[str(Path(p).relative_to(self.root)) for p in self.roots],
                       'limit_bytes':limit_bytes,'headroom_bytes':headroom_bytes}

    def _path(self, value):
        p=(self.root/value).resolve()
        if not any(p.is_relative_to(Path(r)) for r in self.roots):
            raise ReservationError('Owned scope is outside retained roots')
        return p

    def _scopes(self, scopes):
        result=[]
        for value in scopes:
            if set(value)!={'directory','prefix'} or not isinstance(value['prefix'],str) or '/' in value['prefix']:
                raise ReservationError('Scope requires a directory and filename prefix')
            directory=self._path(value['directory'])
            result.append({'directory':str(directory.relative_to(self.root)),'prefix':value['prefix']})
        if not result:raise ReservationError('An asset must own a measurable output scope')
        return sorted(result,key=lambda x:(x['directory'],x['prefix']))

    def _files(self,scope):
        d=self._path(scope['directory']);prefix=scope['prefix']
        for p in d.rglob('*') if d.exists() else []:
            if p.is_symlink():raise ReservationError('Symlinks are not budget evidence')
            if p.is_file() and (not prefix or p.relative_to(d).parts[0].startswith(prefix)):
                yield p

    def owned_bytes(self,scopes):
        return sum(p.stat().st_size for p in {p for s in scopes for p in self._files(s)})

    def retained_bytes(self):
        total=0
        for r in self.roots:
            for p in Path(r).rglob('*'):
                if p.is_symlink():raise ReservationError('Symlinks are not budget evidence')
                if p.is_file():total+=p.stat().st_size
        return total

    @contextmanager
    def _locked(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.with_suffix(self.path.suffix+'.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            if self.path.exists():
                state=json.loads(self.path.read_text())
                if state['contract']!=self.contract:raise ReservationError('Shared budget contract changed')
            else:state={'schema':'riverstone.retained_output.reservations.v2','contract':self.contract,'assets':{}}
            yield state

    def _write(self,state):
        payload=(json.dumps(state,sort_keys=True,indent=2)+'\n').encode();tmp=self.path.with_name(self.path.name+'.tmp')
        with tmp.open('wb') as f:f.write(payload);f.flush();os.fsync(f.fileno())
        os.replace(tmp,self.path)
        fd=os.open(self.path.parent,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)

    @staticmethod
    def _overlap(a,b):
        da=Path(a['directory']);db=Path(b['directory'])
        if da==db:return a['prefix'].startswith(b['prefix']) or b['prefix'].startswith(a['prefix'])
        for outer,inner in ((a,b),(b,a)):
            od=Path(outer['directory']);id=Path(inner['directory'])
            if id.is_relative_to(od):
                return not outer['prefix'] or id.relative_to(od).parts[0].startswith(outer['prefix'])
        return False

    def _summary(self,state):
        # One inventory. Active mutable files are covered by their complete cap,
        # not by subtracting their later size from an earlier global size scan.
        active={key:r for key,r in state['assets'].items() if r['state']=='ACTIVE'}
        sizes={key:0 for key in state['assets']};retained=unowned=0
        def matches(p,scopes):
            for scope in scopes:
                directory=self.root/scope['directory']
                if p.is_relative_to(directory):
                    rel=p.relative_to(directory)
                    if rel.parts and (not scope['prefix'] or rel.parts[0].startswith(scope['prefix'])):return True
            return False
        for root in self.roots:
            for p in Path(root).rglob('*'):
                try:
                    info=p.lstat()
                    if stat.S_ISLNK(info.st_mode):raise ReservationError('Symlinks are not budget evidence')
                    if not stat.S_ISREG(info.st_mode):continue
                    size=info.st_size
                except FileNotFoundError:
                    # Active atomic renames cannot affect the cap-based envelope.
                    if any(matches(p,r['scopes']) for r in active.values()):continue
                    raise ReservationError('Unowned output changed during budget inventory; retry at a safe boundary')
                retained+=size;owner=None
                for key,r in state['assets'].items():
                    if matches(p,r['scopes']):
                        sizes[key]+=size
                        if r['state']=='ACTIVE':owner=key
                if owner is None:unowned+=size
        rows={};pending=0;active_caps=0
        for key,r in state['assets'].items():
            size=sizes[key];remaining=max(0,r['cap_bytes']-size) if r['state']=='ACTIVE' else 0
            rows[key]={'state':r['state'],'owned_bytes':size,'remaining_reserved_bytes':remaining,'cap_bytes':r['cap_bytes'],'enforcement':r['enforcement']}
            pending+=remaining
            if r['state']=='ACTIVE':active_caps+=max(r['cap_bytes'],size)
        projected=unowned+active_caps+self.contract['headroom_bytes']
        free=shutil.disk_usage(self.root).free
        return {'retained_bytes':retained,'remaining_reserved_bytes':pending,'unowned_retained_bytes':unowned,
                'active_caps_bytes':active_caps,'headroom_bytes':self.contract['headroom_bytes'],
                'reserved_total_bytes':projected,'limit_bytes':self.contract['limit_bytes'],
                'unreserved_bytes':self.contract['limit_bytes']-projected,'assets':rows,
                'disk_free_bytes':free,'minimum_free_disk_bytes':self.contract['min_free_disk_bytes'],
                'disk_free_after_reserved_growth_bytes':free-pending-self.contract['headroom_bytes'],
                'disk_free_after_active_caps_bytes':free-active_caps-self.contract['headroom_bytes']}

    def acquire_writer(self,key):
        if key in self._writers:raise ReservationError('Writer lease already acquired by this book')
        directory=self.path.parent/(self.path.name+'.writers');directory.mkdir(parents=True,exist_ok=True)
        f=(directory/(hashlib.sha256(key.encode()).hexdigest()+'.lock')).open('a')
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            f.close();raise ReservationError('Another writer owns this asset reservation')
        with self._locked() as state:
            if state['assets'].get(key,{}).get('state')!='ACTIVE':
                f.close();raise ReservationError('Writer requires an active reservation')
        self._writers[key]=(f,os.getpid())
        return f

    def release_writer(self,key):
        entry=self._writers.get(key)
        if entry is None:return
        f,pid=entry
        if pid!=os.getpid():raise ReservationError('Inherited writer lease cannot be released by another process')
        fcntl.flock(f,fcntl.LOCK_UN);f.close();del self._writers[key]

    @contextmanager
    def writer(self,key):
        self.acquire_writer(key)
        try:yield self
        finally:self.release_writer(key)

    def reserve(self,key,scopes,cap_bytes,identity,observational=False):
        if not isinstance(key,str) or not key or type(cap_bytes)is not int or cap_bytes<=0:
            raise ReservationError('Invalid reservation key/cap')
        record={'state':'ACTIVE','scopes':self._scopes(scopes),'cap_bytes':cap_bytes,'identity':copy.deepcopy(identity),
                'identity_sha256':digest(identity),'enforcement':'legacy_observer' if observational else 'prewrite_required'}
        with self._locked() as state:
            prior=state['assets'].get(key)
            if prior is not None and prior!=record:raise ReservationError('Reservation identity/cap changed or previously released')
            for other,r in state['assets'].items():
                if other!=key and r['state']=='ACTIVE' and any(self._overlap(a,b) for a in record['scopes'] for b in r['scopes']):
                    raise ReservationError('Asset scopes overlap another active reservation')
            state['assets'][key]=record;summary=self._summary(state)
            if (summary['assets'][key]['owned_bytes']>cap_bytes or summary['unreserved_bytes']<0 or
                summary['disk_free_after_active_caps_bytes']<self.contract['min_free_disk_bytes']):
                raise ReservationError('Atomic output reservation exceeds the shared retained cap')
            self._write(state);return summary

    def check(self,key,additional_bytes=0):
        if key not in self._writers or self._writers[key][1]!=os.getpid():
            raise ReservationError('Prewrite check requires the exclusive lifetime asset writer lease')
        if type(additional_bytes)is not int or additional_bytes<0:raise ReservationError('Invalid prewrite byte count')
        with self._locked() as state:
            r=state['assets'].get(key)
            if r is None or r['state']!='ACTIVE':raise ReservationError('No active per-asset output reservation')
            summary=self._summary(state)
            if summary['assets'][key]['owned_bytes']+additional_bytes>r['cap_bytes']:
                raise ReservationError('Per-asset prewrite cap exhausted')
            if summary['unreserved_bytes']<0:raise ReservationError('Shared retained reservation cap exhausted')
            if summary['disk_free_after_active_caps_bytes']<self.contract['min_free_disk_bytes']:
                raise ReservationError('Minimum free disk guard exhausted before output write')
            return summary

    def release(self,key,identity,reason):
        if key in self._writers and self._writers[key][1]!=os.getpid():
            raise ReservationError('Inherited writer lease cannot release another process reservation')
        temporary_lease=key not in self._writers
        if temporary_lease:self.acquire_writer(key)
        try:return self._release_with_writer(key,identity,reason)
        finally:
            if temporary_lease:self.release_writer(key)

    def _release_with_writer(self,key,identity,reason):
        with self._locked() as state:
            r=state['assets'].get(key)
            if r is None or r['identity_sha256']!=digest(identity):raise ReservationError('Release identity mismatch')
            r['state']='RELEASED';r['release_reason']=str(reason);r['retained_bytes_at_release']=self.owned_bytes(r['scopes'])
            self._write(state);return self._summary(state)

    def record(self,key):
        with self._locked() as state:return copy.deepcopy(state['assets'].get(key))

    def inspect(self):
        with self._locked() as state:return self._summary(state)
