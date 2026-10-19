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
from pathlib import Path


class ReservationError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


class ReservationBook:
    def __init__(self, path, root, retained_roots, limit_bytes=180_000_000, headroom_bytes=262144):
        self.path=Path(path).resolve();self.root=Path(root).resolve()
        self.roots=sorted({str(Path(p).resolve()) for p in retained_roots})
        if not self.roots or any(not Path(p).is_relative_to(self.root) for p in self.roots):
            raise ReservationError('Retained roots must be inside the approved repository')
        if any(Path(a).is_relative_to(Path(b)) for a in self.roots for b in self.roots if a!=b):
            raise ReservationError('Nested retained roots would double-count output')
        if type(limit_bytes)is not int or limit_bytes<=0 or type(headroom_bytes)is not int or headroom_bytes<0:
            raise ReservationError('Invalid byte limit')
        self.contract={'retained_roots':[str(Path(p).relative_to(self.root)) for p in self.roots],
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
            else:state={'schema':'riverstone.retained_output.reservations.v1','contract':self.contract,'assets':{}}
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
        retained=self.retained_bytes();rows={};pending=0
        for key,r in state['assets'].items():
            size=self.owned_bytes(r['scopes']);remaining=max(0,r['cap_bytes']-size) if r['state']=='ACTIVE' else 0
            rows[key]={'state':r['state'],'owned_bytes':size,'remaining_reserved_bytes':remaining,'cap_bytes':r['cap_bytes'],'enforcement':r['enforcement']}
            pending+=remaining
        projected=retained+pending+self.contract['headroom_bytes']
        return {'retained_bytes':retained,'remaining_reserved_bytes':pending,'headroom_bytes':self.contract['headroom_bytes'],
                'reserved_total_bytes':projected,'limit_bytes':self.contract['limit_bytes'],
                'unreserved_bytes':self.contract['limit_bytes']-projected,'assets':rows}

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
            if summary['assets'][key]['owned_bytes']>cap_bytes or summary['unreserved_bytes']<0:
                raise ReservationError('Atomic output reservation exceeds the shared retained cap')
            self._write(state);return summary

    def check(self,key,additional_bytes=0):
        if type(additional_bytes)is not int or additional_bytes<0:raise ReservationError('Invalid prewrite byte count')
        with self._locked() as state:
            r=state['assets'].get(key)
            if r is None or r['state']!='ACTIVE':raise ReservationError('No active per-asset output reservation')
            summary=self._summary(state)
            if summary['assets'][key]['owned_bytes']+additional_bytes>r['cap_bytes']:
                raise ReservationError('Per-asset prewrite cap exhausted')
            if summary['unreserved_bytes']<0:raise ReservationError('Shared retained reservation cap exhausted')
            return summary

    def release(self,key,identity,reason):
        with self._locked() as state:
            r=state['assets'].get(key)
            if r is None or r['identity_sha256']!=digest(identity):raise ReservationError('Release identity mismatch')
            r['state']='RELEASED';r['release_reason']=str(reason);r['retained_bytes_at_release']=self.owned_bytes(r['scopes'])
            self._write(state);return self._summary(state)

    def record(self,key):
        with self._locked() as state:return copy.deepcopy(state['assets'].get(key))

    def inspect(self):
        with self._locked() as state:return self._summary(state)
