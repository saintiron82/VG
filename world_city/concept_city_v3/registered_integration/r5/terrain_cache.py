"""Exact source-bound sequential terrain row products; no geometry approximation."""
import hashlib,json,math
from pathlib import Path

def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def file_sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class RowCache:
 def __init__(self,path,binding):
  self.binding=binding;self.key=digest(binding);self.path=Path(path)/self.key;self.path.mkdir(parents=True,exist_ok=True);self.hits=0;self.writes=0
  p=self.path/'binding.json'
  if p.exists():
   if json.loads(p.read_bytes())!=binding:raise ValueError('Terrain cache binding mismatch')
  else:p.write_text(json.dumps(binding,sort_keys=True,indent=2,allow_nan=False)+'\n')
 def filename(self,z):return self.path/('row_%+07d.json'%z)
 def load(self,z,groups,interfaces):
  p=self.filename(z)
  if not p.exists():return None
  envelope=json.loads(p.read_bytes());d=envelope['data']
  if envelope['sha256']!=digest(d) or d['binding']!=self.key or d['z']!=z:raise ValueError('Terrain row cache hash/binding mismatch')
  if d['prior_interfaces_sha256']!=digest(sorted(interfaces)):raise ValueError('Terrain row cache sequence mismatch')
  if not isinstance(d['domains'],int) or d['domains']<0:raise ValueError('Invalid cached domain count')
  for mat,verts in d['groups'].items():
   if len(verts)%3 or any(len(v)!=3 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in v) for v in verts):raise ValueError('Invalid cached terrain vertices')
  if set(d['new_interfaces'])&interfaces:raise ValueError('Repeated cached retaining ownership')
  for mat,verts in d['groups'].items():groups.setdefault(mat,[]).extend(verts)
  interfaces.update(d['new_interfaces']);self.hits+=1;return d['domains']
 def save(self,z,groups,starts,interfaces,prior_interfaces,domains):
  p=self.filename(z)
  if p.exists():raise ValueError('Refusing to overwrite a completed terrain row')
  d=dict(binding=self.key,z=z,prior_interfaces_sha256=digest(sorted(prior_interfaces)),domains=domains,groups={k:v[starts.get(k,0):] for k,v in groups.items() if len(v)>starts.get(k,0)},new_interfaces=sorted(interfaces-prior_interfaces))
  data=json.dumps(dict(data=d,sha256=digest(d)),separators=(',',':'),allow_nan=False)+'\n';tmp=p.with_suffix('.tmp');tmp.write_text(data);tmp.replace(p);self.writes+=1
 def report(self):return dict(binding_sha256=self.key,path=str(self.path),cache_hits=self.hits,new_rows=self.writes,source_bound=True,geometry_approximation=False)
