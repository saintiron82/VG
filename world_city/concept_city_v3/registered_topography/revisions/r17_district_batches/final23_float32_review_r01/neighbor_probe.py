import json,math,collections
from .audit import HERE,ny,f32
from .. import author as a

def key(v):return (round(v[0],10),round(v[2],10))

def up(t):return[t[0],t[2],t[1]]if ny(t)<0 else t

def plane(t):
 u=[t[1][k]-t[0][k]for k in range(3)];v=[t[2][k]-t[0][k]for k in range(3)];n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
 if n[1]==0:return None
 x,z=-n[0]/n[1],-n[2]/n[1];return[x,z,t[0][1]-x*t[0][0]-z*t[0][2]]

def plane_difference(old,new):
 planes=[plane(t)for t in old];nplanes=[plane(t)for t in new];maximum=0
 if any(p is None for p in planes+nplanes):return float("inf")
 from ..final_profile_audit_r01 import exact_clip as e
 for t,p in zip(old,planes):
  for q,np in zip(new,nplanes):
   clip=e.clip([[v[0],v[2]]for v in t],[[v[0],v[2]]for v in q]);maximum=max([maximum]+[abs(a.common.height(p,v)-a.common.height(np,v))for v in clip])
 return maximum

def probe(tris,bad):
 edges=collections.defaultdict(list)
 for i,t in enumerate(tris):
  for k in range(3):edges[tuple(sorted((key(t[k]),key(t[(k+1)%3]))))].append((i,k))
 candidates=[]
 for i in bad:
  t=tris[i];opts=[]
  for k in range(3):
   for j,l in edges[tuple(sorted((key(t[k]),key(t[(k+1)%3]))))]:
    if j==i:continue
    q=tris[j];x=t[(k+2)%3];y=q[(l+2)%3];u=t[k];v=t[(k+1)%3];new=[up([x,y,u]),up([y,x,v])];before=(ny(t)+ny(q))/2;after=sum(ny(r)for r in new)/2
    if min(ny(r)for r in new)<=0 or abs(before-after)>max(1e-12,before*1e-9):continue
    ns=[ny([[f32(c)for c in v]for v in r])for r in new]
    if min(ns)<=0:continue
    opts.append(dict(neighbor=j,new=new,maximum_plane_difference_m=plane_difference([t,q],new),source_area_delta_m2=after-before,float32_normal_y=ns))
  opts.sort(key=lambda r:r['maximum_plane_difference_m']);candidates.append(dict(index=i,options=opts));print('Case',i,'options',[(r['neighbor'],r['maximum_plane_difference_m'])for r in opts],flush=True)
 return candidates

def run():
 p=json.loads((HERE.parent/'coherent_final24_r02/top_scene_patch_r01.json').read_bytes());report=json.loads((HERE/'report.json').read_bytes());vs=p['appended_surfaces']['ground_stone'];tris=[vs[i:i+3]for i in range(0,len(vs),3)];bad=[r['appended_triangle_index']for r in report['cases']if r['kind']=='appended'and r['float32_normal_y']<0];appended=probe(tris,bad)
 e=next(r for r in p['surface_edits']if r['material']=='land_D_NOBLE'and r['triangle_index']==22795);replacement=probe(e['replacement_triangles_xyz_m'],[1]);(HERE/'neighbor_probe.json').write_text(json.dumps(dict(appended=appended,replacement=replacement),separators=(',',':'))+'\n')
if __name__=='__main__':run()
