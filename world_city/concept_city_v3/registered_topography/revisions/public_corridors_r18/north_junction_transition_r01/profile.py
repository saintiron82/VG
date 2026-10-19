"""Exact planar outward envelope anchored to the existing15.6m shared junction."""
import json,math,hashlib,time
from pathlib import Path
from .. import finite_geometry_r03 as g
HERE=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[6]
CITY=ROOT/'world_city/concept_city_v3'

def cross(o,a,b):return(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
def hull(pts):
 pts=sorted(set(tuple(p)for p in pts));lo=[];up=[]
 for p in pts:
  while len(lo)>1 and cross(lo[-2],lo[-1],p)<=0:lo.pop()
  lo.append(p)
 for p in reversed(pts):
  while len(up)>1 and cross(up[-2],up[-1],p)<=0:up.pop()
  up.append(p)
 return [list(p)for p in lo[:-1]+up[:-1]]
def val(pl,p):return pl[0]*p[0]+pl[1]*p[1]+pl[2]
def minus(a,b):return[a[i]-b[i]for i in range(3)]
def half(p,pl):
 if not p:return[]
 o=[];A=p[-1];da=val(pl,A);ina=da>=0
 for B in p:
  db=val(pl,B);inb=db>=0
  if ina!=inb:
   t=da/(da-db);o.append([A[k]+t*(B[k]-A[k])for k in(0,1)])
  if inb:o.append(B)
  A,da,ina=B,db,inb
 return g.clean(o)
def planes():
 f=CITY/'assemblies/waterworks/registered_water_completion_r01/approaches_r02/fields.json'
 assert hashlib.sha256(f.read_bytes()).hexdigest()=='ded6209b586bb5c97874bbe1552b5d20b0965a0f9458324158ad91761d487ff1'
 d=json.loads(f.read_bytes());src=next(r for r in d['profiles']if r['id']=='NORTH_SHARED_JUNCTION');h=hull([p for t in src['triangles']for p in t['polygon_xz_m']]);ps=[[0.,0.,15.6]]
 for a,b in zip(h,h[1:]+h[:1]):
  dx,dz=b[0]-a[0],b[1]-a[1];n=math.hypot(dx,dz);nx,nz=dz/n,-dx/n;ps.append([.10*nx,.10*nz,15.6-.10*(nx*a[0]+nz*a[1])])
 return h,ps
HULL,PLANES=planes()
def new_height(oldplane,p):return min(val(oldplane,p),max(val(pl,p)for pl in PLANES))
def changed_parts(poly,oldplane):
 out=[]
 for i,pl in enumerate(PLANES):
  p=half(poly,minus(oldplane,pl))
  if not p:continue
  for j,q in enumerate(PLANES):
   if i==j:continue
   p=half(p,minus(pl,q))
   if not p:break
  if p:
   # Strict positive lowering; boundaries alone never retire source faces.
   lowering=[val(oldplane,v)-val(pl,v)for v in p]
   if max(lowering)>1e-10:out.append(dict(envelope_plane_index=i,polygon_xz_m=p,plane_y_xz_m=pl,maximum_lowering_m=max(lowering)))
 return out

def main():
 start=time.monotonic();p=HERE.parent/'finite_field_candidate_r07_native_bound.json';d=json.loads(p.read_bytes());rows=[]
 for r in d['records']:
  poly=r['polygon_xz_m'];bb=[min(v[0]for v in poly),min(v[1]for v in poly),max(v[0]for v in poly),max(v[1]for v in poly)]
  if bb[0]>125 or bb[2]<20 or bb[1]>-250 or bb[3]<-350:continue
  parts=changed_parts(poly,r['plane_y_xz_m'])
  if parts:rows.append(dict(source_owner_id=r['id'],source_polygon_xz_m=poly,source_plane_y_xz_m=r['plane_y_xz_m'],changed_parts=parts))
 pts=[p for r in rows for q in r['changed_parts']for p in q['polygon_xz_m']];out=dict(status='UNACTIVATED_FINITE_PROFILE_SCREEN',source_public_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),junction_hull_xz_m=HULL,envelope_planes_y_xz_m=PLANES,rows=rows,changed_area_m2=sum(g.area(q['polygon_xz_m'])for r in rows for q in r['changed_parts']),changed_owner_count=len(rows),bounds_xz_m=[min(p[0]for p in pts),min(p[1]for p in pts),max(p[0]for p in pts),max(p[1]for p in pts)],max_lowering_m=max(q['maximum_lowering_m']for r in rows for q in r['changed_parts']),max_new_grade=max(math.hypot(*pl[:2])for pl in PLANES),seconds=time.monotonic()-start);f=HERE/'profile_screen.json';f.write_text(json.dumps(out,separators=(',',':'))+'\n');print({k:v for k,v in out.items()if k not in ['rows','junction_hull_xz_m','envelope_planes_y_xz_m']})
if __name__=='__main__':main()
