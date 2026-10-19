"""Probe exact-domain subdivisions of only the thirteen precision inversions."""
import json,math,collections
from .audit import HERE,f32,ny

def cross(t):
 u=[t[1][k]-t[0][k]for k in range(3)];v=[t[2][k]-t[0][k]for k in range(3)];return[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
def state(t):
 f=[[f32(x)for x in v]for v in t];n=cross(f);return 'up'if n[1]>0 else'zero'if all(x==0 for x in n)else'bad'
def children(t,e):
 i,j=e;k=3-i-j;m=[(t[i][d]+t[j][d])/2 for d in range(3)];a=[t[i],m,t[k]];b=[m,t[j],t[k]]
 if ny(a)<0:a[1],a[2]=a[2],a[1]
 if ny(b)<0:b[1],b[2]=b[2],b[1]
 return[a,b]
def solve(t,depth=0):
 if state(t)!='bad':return[t],depth
 if depth>=16:return None,depth
 opts=[]
 for e in [(0,1),(1,2),(2,0)]:
  ts=children(t,e)
  if any(ny(q)<=0 for q in ts):continue
  bad=[q for q in ts if state(q)=='bad'];measure=sum(math.sqrt(sum(x*x for x in cross([[f32(v)for v in p]for p in q])))for q in bad)
  opts.append(((len(bad),measure,-math.dist(t[e[0]],t[e[1]])),ts))
 for _,ts in sorted(opts,key=lambda r:r[0])[:1]:
  out=[];maxd=depth
  for q in ts:
   v,d=solve(q,depth+1)
   if v is None:break
   out+=v;maxd=max(maxd,d)
  else:return out,maxd
 return None,depth

def run():
 report=json.loads((HERE/'report.json').read_bytes());records=[]
 for r in report['cases']:
  if r['float32_normal_y']>=0:continue
  ts,depth=solve(r['vertices_xyz_m']);counts=collections.Counter(state(t)for t in ts or[]);print(r.get('appended_triangle_index',r.get('source_triangle_index')),None if ts is None else len(ts),depth,dict(counts),flush=True);records.append(dict(source=r,replacement_triangles_xyz_m=ts,depth=depth,counts=dict(counts)))
 (HERE/'subdivision_probe.json').write_text(json.dumps(dict(records=records,passed=all(r['replacement_triangles_xyz_m']is not None for r in records)),separators=(',',':'))+'\n')
if __name__=='__main__':run()
