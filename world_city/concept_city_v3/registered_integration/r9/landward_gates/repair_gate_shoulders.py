"""Side-only source-bound repair of the r09 forecourt grass cracks.
Road tops, terrain source edits and all native instances are immutable inputs.
Shared shoulder sections replace per-segment distance interpolation; explicit
bank faces close the genuine height difference to unchanged outside surfaces.
"""
from __future__ import annotations
import json,math,hashlib,sys,collections,time
from pathlib import Path
import numpy as np
from .build_corridors import H,ROOT,Ground,xz,plane,ph,up,cut3,area3,ref
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import fan,clean
SHA='074ba4697256780f2dd083897b4ec1c798f1751388c2953dc39b437dccabd210'

def digest(x):return hashlib.sha256(json.dumps(x,separators=(',',':')).encode()).hexdigest()
def write(path,x):path.write_text(json.dumps(x,separators=(',',':'),allow_nan=False)+'\n')
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def f32(v):return np.asarray(v,dtype=np.float32).tolist()
def key(q):return tuple(float(v)for v in np.asarray(q,dtype=np.float32))
def valid(t):
 a=np.asarray(t,dtype=np.float32);n=np.cross(a[1]-a[0],a[2]-a[0]);return float(np.dot(n,n))>0 and float(n[1])>0

def main():
 start=time.monotonic();src=H/'candidate_r09';assert hashlib.sha256((src/'surface_patch.json').read_bytes()).hexdigest()==SHA
 p=json.load(open(src/'surface_patch.json'));old_grass=p['appended_surfaces']['ground_grass'];rows=json.load(open(H/'local_source_faces.json'));ground=Ground(rows)
 bands=[];bound_sections=[]
 for o in p['ownership'][:2]:
  ss=o['shared_cross_sections_xyz_m'];wide=[i for i,s in enumerate(ss)if math.dist(xz(s[1]),xz(s[2]))>6.001];lo=min(wide);hi=max(wide)
  for k,kk in [(0,1),(3,2)]:
   section=[]
   for i in range(lo,hi+1):
    outer,inner=ss[i][k],ss[i][kk];source=ground.at(xz(outer));# Continuous shared-section grass setback; vertical retaining faces absorb the genuine source-height differences.
    yy=inner[1];section.append([inner,[outer[0],yy,outer[2]]])
   for j,(a,b)in enumerate(zip(section,section[1:])):
    quad=[a[0],a[1],b[1],b[0]];poly=[xz(v)for v in quad]
    signs=[cross(poly[i],poly[(i+1)%4],poly[(i+2)%4])for i in range(4)]
    assert all(s>=-1e-9 for s in signs)or all(s<=1e-9 for s in signs),('Nonconvex side strip',o['id'],lo+j,k)
    for tt in fan(quad):
     tt=up(tt);bands.append(dict(owner=o['id'],side=k,section=lo+j,poly=[xz(v)for v in tt],triangle=tt,plane=plane(tt)))
   bound_sections.append(dict(owner=o['id'],side=k,first_section=lo,last_section=hi,shared_sections=section,source_outer_height_policy='The new grass setback follows the existing road section height exactly. True retained-source height differences are closed by explicit vertical bank faces; no steep interpolated earth slope is fabricated.'))
 idx=geo._SpatialIndex(4)
 for i,b in enumerate(bands):idx.add(i,b['poly'])
 new=[];changed=[];kept=[];changed_source=[];drop=[]
 for ti in range(len(old_grass)//3):
  tri=old_grass[ti*3:ti*3+3];poly=[xz(v)for v in tri];ids=sorted(idx.candidates(poly));parts=[tri];out=[]
  for i in ids:
   b=bands[i];next_parts=[]
   for part in parts:
    inside=clean(geo.convex_intersection([xz(v)for v in part],b['poly']))
    if not inside:next_parts.append(part);continue
    if geo.polygon_area(inside)<1e-12:next_parts.append(part);continue
    out.extend((up([[q[0],ph(b['plane'],q),q[1]]for q in tt]),i)for tt in fan(inside))
    next_parts.extend(cut3(part,b['poly']))
   parts=next_parts
  if out:
   changed_source.append(ti)
   for t,i in out:
    if valid(t):changed.append(dict(triangle=t,band=i,old_triangle=ti))
    else:drop.append(dict(triangle=t,old_triangle=ti,area_m2=area3(t),reason='Subquantization split fragment'))
   for part in parts:
    for t in fan(part):
     if valid(t):kept.extend(t)
     else:drop.append(dict(triangle=t,old_triangle=ti,area_m2=area3(t),reason='Subquantization retained split fragment'))
  else:kept.extend(tri)
 # Share exact float32 XZ height values only among the new shoulder top. The
 # analytic neighboring shared-section planes differ only by rounding here.
 byq=collections.defaultdict(list)
 for row in changed:
  for v in row['triangle']:byq[key(xz(v))].append(v)
 conflicts=[]
 for q,vs in byq.items():
  ys=[v[1]for v in vs];delta=max(ys)-min(ys)
  if delta>1e-4:conflicts.append(dict(xz=q,range_m=delta))
  y=float(np.float32(sum(ys)/len(ys)))
  for v in vs:v[1]=y
 assert not conflicts,('New side planes disagree',conflicts[:4])
 # A source edge can be T-split by the existing terrain tessellation. Find
 # exterior edges by bounded sided probes, not by naive exact edge cancellation.
 newidx=geo._SpatialIndex(2)
 for i,row in enumerate(changed):row['poly']=[xz(v)for v in row['triangle']];newidx.add(i,row['poly'])
 def in_new(q):return any(geo.point_in_convex_polygon(q,changed[i]['poly'],1e-9)for i in newidx.candidates([q]))
 edges=collections.defaultdict(list)
 for i,r in enumerate(changed):
  for a,b in zip(r['triangle'],r['triangle'][1:]+r['triangle'][:1]):edges[tuple(sorted((key(xz(a)),key(xz(b)))))].append((i,a,b))
 boundary=[];uncertain=[]
 for es in edges.values():
  if len(es)==2:continue
  for i,a,b in es:
   ll=math.dist(xz(a),xz(b))
   if ll<1e-5:continue
   n=[-(b[2]-a[2])/ll,(b[0]-a[0])/ll];m=[(a[0]+b[0])/2,(a[2]+b[2])/2];eps=min(.00015,ll*.02)
   plus=in_new([m[k]+n[k]*eps for k in range(2)]);minus=in_new([m[k]-n[k]*eps for k in range(2)])
   if plus and minus:continue
   if plus==minus:
    uncertain.append(dict(a=a,b=b,length_m=ll,plus=plus,minus=minus));continue
   # Corrected upper faces are upward, hence outside is normally left.
   if plus:n=[-v for v in n]
   boundary.append((i,a,b,n))
 # Resolved adjacent top surfaces: exact retained source fragments + r09 added
 # tops. These are sampled only just outside the repaired side footprint.
 edits={(e['material'],e['triangle_index']):e for e in p['surface_edits']};adj=[]
 for row in rows:
  for t in edits.get((row['material'],row['triangle_index']),{}).get('replacement_triangles_xyz_m',[row['triangle']]):
   if row['material']!='water' and geo.polygon_area([xz(v)for v in t])>1e-10:adj.append(dict(material=row['material'],triangle=t,source='retained_source'))
 for m,vs in p['appended_surfaces'].items():
  if m=='bank':continue
  adj.extend(dict(material=m,triangle=vs[i:i+3],source='r09_appended')for i in range(0,len(vs),3))
 ai=geo._SpatialIndex(4)
 for i,r in enumerate(adj):
  r['poly']=[xz(v)for v in r['triangle']];r['plane']=plane(r['triangle']);ai.add(i,r['poly'])
 def containing(q):return [adj[i]for i in ai.candidates([q])if geo.point_in_convex_polygon(q,adj[i]['poly'],1e-8)]
 walls=[];wall_ledger=[];missing=[];zero_walls=0
 for bi,(ri,a,b,n)in enumerate(boundary):
  aa,bb=xz(a),xz(b);dx,dz=bb[0]-aa[0],bb[1]-aa[1];ll=math.hypot(dx,dz);eps=.0002
  # Break at every adjacent triangle edge crossing; each resulting lower edge
  # then belongs to one exact unchanged affine source plane.
  cuts={0.,1.}
  candidates=ai.candidates([[aa[k]-eps for k in range(2)],[bb[k]+eps for k in range(2)]])
  for ci in candidates:
   pp=adj[ci]['poly']
   for u,v in zip(pp,pp[1:]+pp[:1]):
    ex,ez=v[0]-u[0],v[1]-u[1];den=dx*ez-dz*ex
    if abs(den)<1e-13:continue
    t=((u[0]-aa[0])*ez-(u[1]-aa[1])*ex)/den;s=((u[0]-aa[0])*dz-(u[1]-aa[1])*dx)/den
    if 1e-8<t<1-1e-8 and -1e-8<=s<=1+1e-8:cuts.add(t)
  cuts=sorted(cuts)
  for t0,t1 in zip(cuts,cuts[1:]):
   if (t1-t0)*ll<1e-6:continue
   t=(t0+t1)/2;q=[aa[0]+t*dx+n[0]*eps,aa[1]+t*dz+n[1]*eps];rs=containing(q)
   if not rs:
    missing.append(dict(boundary=bi,xz=q,length_m=(t1-t0)*ll));continue
   r=max(rs,key=lambda r:ph(r['plane'],q));top=[];bottom=[]
   for tt in [t0,t1]:
    xyz=[a[k]+tt*(b[k]-a[k])for k in range(3)];top.append(xyz);bottom.append([xyz[0],ph(r['plane'],xz(xyz)),xyz[2]])
   if max(abs(top[j][1]-bottom[j][1])for j in [0,1])<1e-4:zero_walls+=1;continue
   # If difference crosses zero, split there to avoid a bow-tie wall.
   da,db=top[0][1]-bottom[0][1],top[1][1]-bottom[1][1];segments=[(top,bottom)]
   if da*db<0:
    tt=da/(da-db);v=[top[0][k]+tt*(top[1][k]-top[0][k])for k in range(3)];segments=[([top[0],v],[bottom[0],v]),([v,top[1]],[v,bottom[1]])]
   emitted=[]
   for upv,dnv in segments:
    for tri in [[upv[0],dnv[1],upv[1]],[upv[0],dnv[0],dnv[1]]]:
     f=np.asarray(tri,dtype=np.float32);normal=np.cross(f[1]-f[0],f[2]-f[0])
     if float(np.dot(normal,normal))==0:continue
     sign=1 if sum(upv[j][1]-dnv[j][1]for j in [0,1])>0 else -1
     if (float(normal[0])*n[0]+float(normal[2])*n[1])*sign<0:tri=[tri[0],tri[2],tri[1]]
     emitted.append(len(walls)//3);walls.extend(tri)
   wall_ledger.append(dict(boundary=bi,upper=[top[0],top[1]],lower=[bottom[0],bottom[1]],outside_normal_xz=n,adjacent_material=r['material'],adjacent_kind=r['source'],bank_triangle_indices=emitted))
 p['appended_surfaces']['ground_grass']=kept+[v for r in changed for v in r['triangle']];p['appended_surfaces']['bank']=p['appended_surfaces'].get('bank',[])+walls
 p['id']='R10_LANDWARD_GATE_SHOULDER_CLOSURE';p['status']='SOURCE_CANDIDATE_VISUAL_AND_RUNTIME_REVALIDATION_PENDING'
 stage=H/'shoulder_repair_r10_staging';stage.mkdir(exist_ok=True)
 write(stage/'surface_patch.json',p);write(stage/'repair_report.json',dict(input=ref(src/'surface_patch.json'),output=ref(stage/'surface_patch.json'),changed_old_grass_triangles=changed_source,new_top_triangles=len(changed),kept_grass_triangles=len(kept)//3,bank_triangles=len(walls)//3,shared_sections=bound_sections,boundary_edge_count=len(boundary),unclassified_boundary_probe_edges=uncertain,zero_height_boundary_intervals=zero_walls,missing_adjacent_intervals=missing,discarded_subquantization=drop,road_array_digest=digest(p['appended_surfaces']['road']),source_edits_digest=digest(p['surface_edits']),unchanged_road=p['appended_surfaces']['road']==json.load(open(src/'surface_patch.json'))['appended_surfaces']['road'],unchanged_source_edits=p['surface_edits']==json.load(open(src/'surface_patch.json'))['surface_edits'],elapsed_seconds=time.monotonic()-start))
 write(stage/'wall_ledger.json',wall_ledger)
 print(json.dumps(dict(new_top_triangles=len(changed),bank_triangles=len(walls)//3,boundary_edges=len(boundary),missing_adjacent=len(missing),dropped=len(drop),seconds=time.monotonic()-start)),flush=True)
if __name__=='__main__':main()
