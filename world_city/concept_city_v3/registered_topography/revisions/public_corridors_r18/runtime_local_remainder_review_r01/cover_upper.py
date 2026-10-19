import json,math,time
from fractions import Fraction as F
from pathlib import Path
from ..north_junction_transition_r01.author import ROOT,CITY,HERE as N,a,g,ref,dump
HERE=Path(__file__).resolve().parent

def frac(p):return[tuple(F(float(x))for x in v)for v in p]
def cross(a,b,p):return(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
def area(p):return abs(sum(cross(p[0],p[i],p[i+1])for i in range(1,len(p)-1)))/2 if len(p)>2 else F(0)
def sign(p):return 1 if sum(cross(p[0],p[i],p[i+1])for i in range(1,len(p)-1))>0 else-1
def half(p,a,b,s):
 if not p:return[]
 out=[];u=p[-1];du=s*cross(a,b,u)
 for v in p:
  dv=s*cross(a,b,v)
  if(du>=0)!=(dv>=0):
   t=du/(du-dv);out.append(tuple(u[k]+t*(v[k]-u[k])for k in(0,1)))
  if dv>=0:out.append(v)
  u,du=v,dv
 return out if area(out)>0 else[]
def diff(p,q):
 inside=p;out=[];s=sign(q)
 for u,v in zip(q,q[1:]+q[:1]):
  if u==v:continue
  part=half(inside,u,v,-s)
  if part:out.append(part)
  inside=half(inside,u,v,s)
  if not inside:break
 return out,inside

def main():
 start=time.monotonic();mp=HERE/'upper_contour_source_matches.json';matches=json.loads(mp.read_bytes());pp=N.parent/'finite_field_candidate_r07_native_bound.json';pub=json.loads(pp.read_bytes());idx=a.geo._SpatialIndex(4)
 for i,r in enumerate(pub['records']):idx.add(i,r['polygon_xz_m'])
 rows=[];cache={}
 for mi,m in enumerate(matches['matches']):
  poly=[[v[0],v[2]]for v in m['triangle_xyz_m']];P=frac(poly);parts=[P];covers=[];heights=[]
  for i in sorted(idx.candidates(poly)):
   r=pub['records'][i];Q=cache.setdefault(i,frac(r['polygon_xz_m']))
   if not area(Q):continue
   rem=[];ov=F(0)
   for part in parts:
    rest,inside=diff(part,Q);rem+=rest;ov+=area(inside)
   parts=rem
   if ov:
    covers.append(dict(owner_id=r['id'],polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'],overlap_area_m2=float(ov)))
    for v in m['triangle_xyz_m']:heights.append(v[1]-a.common.height(r['plane_y_xz_m'],[v[0],v[2]]))
   if not parts:break
  missing=sum(area(q)for q in parts);rows.append(dict(**m,source_projected_area_m2=float(area(P)),current_public_cover_records=covers,uncovered_area_m2=float(missing),uncovered_polygons_xz_m=[[[float(v)for v in x]for x in q]for q in parts],old_minus_current_height_range_m=[min(heights),max(heights)]if heights else None));print(mi,'missing',float(missing),'parts',len(parts),'sec',time.monotonic()-start,flush=True)
 out=dict(status='EXACT_RATIONAL_SOURCE_OWNERSHIP_CLASSIFICATION',sources=[ref(mp),ref(pp),ref(Path(__file__))],rows=rows,total_source_projected_area_m2=sum(r['source_projected_area_m2']for r in rows),total_uncovered_area_m2=sum(r['uncovered_area_m2']for r in rows));dump(HERE/'upper_contour_owner_coverage.json',out);print('sourcearea',out['total_source_projected_area_m2'],'missing',out['total_uncovered_area_m2']);print('maxmissing',max(r['uncovered_area_m2']for r in rows))
if __name__=='__main__':main()
