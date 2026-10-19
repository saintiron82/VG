"""Bounded data authoring and exact rectangular composition, not a voxel engine."""
import gzip, hashlib, json, os, resource, sys
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(110,)*2)
import numpy as np
from PIL import Image
O=Path(__file__).resolve().parent; A=O.parent
R=next(p for p in O.parents if (p/'voxel_character/common/core.py').exists())
sys.path.insert(0,str(R));sys.path.insert(0,str(A/'railing_measurement_r01'))
import measure_panel as measured
from voxel_character.common import core,render_data
P=1/32
EDIT_LO=(-104,204,156);EDIT_HI=(-40,242,160)
OWN_LO=(-105,203,155);OWN_HI=(-39,243,161)
HALO_LO=(-106,202,154);HALO_HI=(-38,244,162)
BASE=A/'roof_repair_r05/roof_repaired.render.json.gz'
BASE_SHA='22baa95f2afc2bf9f1753eaf256bd172aed9fa9c161a21a0b96626b7c2ab9925'
IMAGE=R/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png'
IMAGE_SHA='552b0bd61eba3c3f5bee98a6b3a5fac085362dc8804e049e325db55fb902ec93'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(65536),b''):h.update(b)
 return h.hexdigest()
def ref(p):return {'path':str(Path(p).relative_to(R)),'sha256':sha(p)}
def read(p):
 with gzip.open(p,'rt') if str(p).endswith('.gz') else open(p) as f:return json.load(f)
def save(name,obj):
 p=O/name;assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True)
 b=json.dumps(obj,separators=(',',':'),allow_nan=False).encode()
 p.write_bytes(gzip.compress(b,mtime=0) if str(p).endswith('.gz') else b)
 assert sum(x.stat().st_size for x in O.rglob('*') if x.is_file())<10_000_000
 return ref(p)
def bounds_contains(pt,lo=OWN_LO,hi=OWN_HI):return all(lo[i]<=pt[i]<hi[i] for i in range(3))
def baseline():
 a=np.load(A/'foundation_repair_r01/foundation_arrays.npz')
 return np.where(a['occupancy'],a['materials'],-1).astype(np.int16)
def value(a,p):
 x,y,z=p;ix=x//4+48;iy=y//4;iz=z//4+40
 return int(a[iy,ix,iz]) if 0<=ix<96 and 0<=iy<112 and 0<=iz<80 else -1
def inherited_cells(a,lo=HALO_LO,hi=HALO_HI):
 return {(x,y,z):value(a,(x,y,z)) for y in range(lo[1],hi[1]) for x in range(lo[0],hi[0]) for z in range(lo[2],hi[2]) if value(a,(x,y,z))>=0}
def coords(y,x):return 152+x-256,496-(250+y)-1
def mask_owner(labels):return {(coords(int(y),int(x))[0],coords(int(y),int(x))[1],z) for y,x in np.argwhere((labels==1)|(labels==2)) for z in range(156,160)}
def face_geometry(q):
 g=[[round(v/P) for v in p] for p in q];lo=[min(p[a] for p in g) for a in range(3)];hi=[max(p[a] for p in g) for a in range(3)]
 a=next(a for a in range(3) if lo[a]==hi[a]);u,v=[i for i in range(3) if i!=a]
 e=[g[1][i]-g[0][i] for i in range(3)];f=[g[2][i]-g[0][i] for i in range(3)]
 n=[e[1]*f[2]-e[2]*f[1],e[2]*f[0]-e[0]*f[2],e[0]*f[1]-e[1]*f[0]];s=1 if n[a]>0 else -1
 return g,lo,hi,a,u,v,s
def rect(q,u,v,ul,vl,uh,vh):
 out=[list(p) for p in q]
 for p in out:p[u]=max(ul*P,min(uh*P,p[u]));p[v]=max(vl*P,min(vh*P,p[v]))
 return out
def partition_quad(q,lo=OWN_LO,hi=OWN_HI):
 """Return exact outside pieces and inside piece by the solid-side cell owner."""
 g,ql,qh,a,u,v,s=face_geometry(q);owner=ql[a]-(1 if s>0 else 0)
 if not lo[a]<=owner<hi[a]:return [q],None
 ul=max(ql[u],lo[u]);uh=min(qh[u],hi[u]);vl=max(ql[v],lo[v]);vh=min(qh[v],hi[v])
 if ul>=uh or vl>=vh:return [q],None
 outside=[]
 for bounds in [(ql[u],ql[v],ul,qh[v]),(uh,ql[v],qh[u],qh[v]),(ul,ql[v],uh,vl),(ul,vh,uh,qh[v])]:
  if bounds[0]<bounds[2] and bounds[1]<bounds[3]:outside.append(rect(q,u,v,*bounds))
 return outside,rect(q,u,v,ul,vl,uh,vh)
def faces(q,mat):
 g,lo,hi,a,u,v,s=face_geometry(q)
 for i in range(lo[u],hi[u]):
  for j in range(lo[v],hi[v]):
   p=[0,0,0];p[a]=lo[a]-(s>0);p[u]=i;p[v]=j
   yield (a,s,*p,mat)
def expected_faces(cells,lo=OWN_LO,hi=OWN_HI):
 out=set()
 for p,m in cells.items():
  if not bounds_contains(p,lo,hi):continue
  for a in range(3):
   for s in [-1,1]:
    n=list(p);n[a]+=s
    if tuple(n) not in cells:out.add((a,s,*p,m))
 return out
class JsonStream:
 def __init__(self,f):self.f=f;self.buf='';self.pos=0;self.eof=False;self.dec=json.JSONDecoder()
 def fill(self):
  self.buf=self.buf[self.pos:];self.pos=0;b=self.f.read(65536);self.eof=not bool(b);self.buf+=b
 def space(self):
  while True:
   while self.pos<len(self.buf) and self.buf[self.pos].isspace():self.pos+=1
   if self.pos<len(self.buf) or self.eof:return
   self.fill()
 def peek(self):self.space();return self.buf[self.pos] if self.pos<len(self.buf) else ''
 def eat(self,c):assert self.peek()==c,(c,self.peek());self.pos+=1
 def value(self):
  self.space()
  while True:
   try:
    v,n=self.dec.raw_decode(self.buf,self.pos)
    if n==len(self.buf) and not self.eof:self.fill();continue
    self.pos=n;return v
   except json.JSONDecodeError:
    if self.eof:raise
    self.fill()
def stream_render(path,meta):
 """Yield (original group index, material, quad index, quad), no full expansion."""
 with gzip.open(path,'rt') as f:
  p=JsonStream(f);p.eat('{');count=0;names=[]
  while p.peek()!='}':
   key=p.value();p.eat(':')
   if key=='groups':
    p.eat('[');gi=0
    while p.peek()!=']':
     p.eat('{');assert p.value()=='material';p.eat(':');mat=p.value();names.append(mat);p.eat(',');assert p.value()=='quads';p.eat(':');p.eat('[');qi=0
     while p.peek()!=']':
      q=p.value();yield gi,mat,qi,q;qi+=1;count+=1
      if p.peek()==',':p.eat(',')
      else:break
     p.eat(']');p.eat('}');gi+=1
     if p.peek()==',':p.eat(',')
     else:break
    p.eat(']')
   else:meta[key]=p.value()
   if p.peek()==',':p.eat(',')
   else:break
  p.eat('}');assert p.peek()=='' and count==meta['quad_count'];meta['group_names']=names
def hash_group_init(mat):
 h=hashlib.sha256();h.update(json.dumps({'material':mat},separators=(',',':')).encode());h.update(b'\n');return h
def hash_quad(h,q):h.update(json.dumps(q,separators=(',',':')).encode());h.update(b'\n')
