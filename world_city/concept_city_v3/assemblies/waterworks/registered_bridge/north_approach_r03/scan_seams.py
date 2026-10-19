import json,math
from .profile import a,HERE,write
s=a.load_scene();f=s['bridge_mechanism']['bridge_to_world'];b,t=f['basis'],f['translation'];w=lambda p:[t[i]+sum(b[i][j]*p[j]for j in range(3))for i in range(3)];l=lambda p:[sum(b[j][i]*(p[j]-t[j])for j in range(3))for i in range(3)]
vs=[w([x,0,z])for x in[-140,-98]for z in[-4,4]];xmin,zmin=min(v[0]for v in vs),min(v[2]for v in vs);xmax,zmax=max(v[0]for v in vs),max(v[2]for v in vs);ix=a.TriangleIndex(s,[[[xmin,zmin],[xmax,zmin],[xmax,zmax],[xmin,zmax]]]);records=[]
for x in range(-135,-98):
 parts=[]
 for r in ix.rows:
  tri=[l(v)for v in r['vertices_xyz_m']]; zs=[]
  for u,v in zip(tri,tri[1:]+tri[:1]):
   if(u[0]-x)*(v[0]-x)<=0 and abs(v[0]-u[0])>1e-12:
    f=(x-u[0])/(v[0]-u[0]);zs.append(u[2]+f*(v[2]-u[2]))
  if len(zs)<2:continue
  lo,hi=max(-3,min(zs)),min(3,max(zs))
  if hi<lo+1e-8:continue
  ys=[]
  for z in[lo,hi]:
   p=w([x,0,z]);ys.append(a.common.height(r['plane_y_xz_m'],[p[0],p[2]]))
  parts.append(dict(lo=lo,hi=hi,ys=ys,grade=abs(ys[1]-ys[0])/(hi-lo),material=r['material'],sourcegrade=math.hypot(*r['plane_y_xz_m'][:2])))
 parts.sort(key=lambda r:r['lo']);gap=sum(max(0,v['lo']-u['hi'])for u,v in zip(parts,parts[1:])); full=bool(parts)and abs(parts[0]['lo']+3)<1e-6 and abs(parts[-1]['hi']-3)<1e-6 and gap<1e-7
 records.append(dict(x=x,full=full,gap=gap,grade=max([r['grade']for r in parts],default=999),sourcegrade=max([r['sourcegrade']for r in parts],default=999),material=list(set(r['material']for r in parts)),yrange=[min([v for r in parts for v in r['ys']],default=999),max([v for r in parts for v in r['ys']],default=999)]))
write('seam_scan.json',records);print(json.dumps(records,indent=1))
