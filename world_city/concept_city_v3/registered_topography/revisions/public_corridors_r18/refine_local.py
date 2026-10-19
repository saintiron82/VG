"""Bounded edge-projection refinement of genuinely violating field triangles.
Original fixed profiles and field are unchanged; only touched triangles and
neighbors sharing a split edge are subdivided. No blanket density increase.
"""
import collections,json,math,time
from .height_field import HERE,HeightField,fixed_sources
from .grid_candidate import grade
from .tessellate import triangulate_best
from ..r17_district_batches import author as a

MAX_ROUNDS=4;MAX_TRIANGLES=40000

def edgekey(p,q):return tuple(sorted((tuple(round(v,12)for v in p),tuple(round(v,12)for v in q))))
def badrows(tris):return[(i,grade(t))for i,t in enumerate(tris)if grade(t)>.12+1e-7]
def main():
 start=time.monotonic();path=HERE/'field_tessellation.json';source=json.loads(path.read_bytes());regions,segments,refs=fixed_sources();assert refs==source['report']['source_refs'];field=HeightField(regions,segments);tris=source['triangles_xyz_m'];rounds=[]
 for n in range(MAX_ROUNDS):
  bad=badrows(tris);specs=collections.defaultdict(list);unrefinable=[]
  for i,g in bad:
   t=tris[i];ps=[[p[0],p[2]]for p in t];choices=[]
   for j in range(3):
    p,q,r=ps[j],ps[(j+1)%3],ps[(j+2)%3];L2=math.dist(p,q)**2
    foot=sum((r[k]-p[k])*(q[k]-p[k])for k in(0,1))/L2
    for f in (foot,.5):
     if not 1e-7<f<1-1e-7:continue
     xz=[p[k]+f*(q[k]-p[k])for k in(0,1)];v=[xz[0],field.value(*xz),xz[1]];new=[ [t[j],v,t[(j+2)%3]],[v,t[(j+1)%3],t[(j+2)%3]] ]
     if min(abs(a.normal_y(x))for x in new)<=1e-12:continue
     score=max(grade(x)for x in new);choices.append((score,j,f,xz))
   if not choices:unrefinable.append(i);continue
   score,j,f,xz=min(choices)
   if score>=g*.999 and g>.13:unrefinable.append(i);continue
   specs[edgekey(ps[j],ps[(j+1)%3])].append(xz)
  refined=[];touched=0
  for t in tris:
   ps=[[p[0],p[2]]for p in t];ring=[];changed=False
   for p,q in zip(ps,ps[1:]+ps[:1]):
    mids=specs.get(edgekey(p,q),[]);ring.append(p)
    if not mids:continue
    L2=math.dist(p,q)**2;coords=[]
    for m in mids:
     f=sum((m[k]-p[k])*(q[k]-p[k])for k in(0,1))/L2
     if 1e-9<f<1-1e-9:coords.append((f,m))
    last=None
    for _,m in sorted(coords):
     if last is None or math.dist(last,m)>1e-10:ring.append(m);last=m;changed=True
   if changed:refined+=triangulate_best(ring,field);touched+=1
   else:refined.append(t)
  now=badrows(refined);row=dict(round=n,input_triangles=len(tris),violating_before=len(bad),split_edges=len(specs),unrefinable_triangles=unrefinable,touched_triangles=touched,output_triangles=len(refined),violating_after=len(now),maximum_gradient=max((g for _,g in now),default=0),violating_area_m2=sum(abs(a.normal_y(refined[i]))/2 for i,g in now),seconds=time.monotonic()-start);rounds.append(row);print({k:v for k,v in row.items()if k!='unrefinable_triangles'},flush=True);tris=refined
  if not now or len(tris)>MAX_TRIANGLES or not specs:break
 out=dict(schema='riverstone.r18.local_edge_refinement.v1',source_mesh_sha256=a.sha(path),source_refs=refs,rounds=rounds,status='READY_FOR_FINITE_OWNER_REVIEW'if not badrows(tris)else'HELD_REMAINING_TRIANGLE_GRADES',triangles_xyz_m=tris,limits=['Finite original source masks and water/native exclusions still required.','No source fixed profile, controller or existing scene has changed.'])
 (HERE/'field_refinement_r01.json').write_text(json.dumps(out,separators=(',',':'))+'\n');(HERE/'refinement_review_r01.json').write_text(json.dumps({k:v for k,v in out.items()if k!='triangles_xyz_m'},separators=(',',':'))+'\n')
if __name__=='__main__':main()
