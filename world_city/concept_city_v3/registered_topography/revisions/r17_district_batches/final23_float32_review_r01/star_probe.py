import json,collections,math
from scipy.spatial import Delaunay
from .audit import HERE,ny,f32
from .neighbor_probe import plane_difference,up,key
from .. import author as a

def ring_for(tris,ids,center):
 edges=[];lookup={}
 for i in ids:
  t=tris[i];others=[v for v in t if key(v)!=center]
  if len(others)!=2:return None
  u,v=map(key,others);edges.append((u,v));lookup[u]=others[0];lookup[v]=others[1]
 adjacent=collections.defaultdict(list)
 for u,v in edges:adjacent[u].append(v);adjacent[v].append(u)
 if any(len(v)!=2 for v in adjacent.values()):return None
 start=next(iter(adjacent));prev=None;cur=start;ring=[]
 for _ in range(len(adjacent)+1):
  ring.append(lookup[cur]);n=next((x for x in adjacent[cur]if x!=prev),None)
  if n==start:return ring if len(ring)==len(adjacent)else None
  prev,cur=cur,n
 return None

def options(tris,ids,center):
 ring=ring_for(tris,ids,center)
 if not ring:return[]
 old=[tris[i]for i in ids];before=sum(ny(t)for t in old)/2;opts=[]
 for root in range(len(ring)):
  r=ring[root:]+ring[:root];new=[up([r[0],r[i],r[i+1]])for i in range(1,len(r)-1)]
  if any(ny(t)<=0 for t in new):continue
  after=sum(ny(t)for t in new)/2
  if abs(after-before)>max(1e-12,before*1e-9):continue
  normals=[ny([[f32(c)for c in v]for v in t])for t in new]
  if min(normals)<=0:continue
  delta=plane_difference(old,new)
  opts.append(dict(source_indices=ids,removed_interior_vertex_xz_m=list(center),outer_vertices_xyz_m=ring,replacement_triangles_xyz_m=new,maximum_plane_difference_m=delta,source_area_delta_m2=after-before))
 return opts

def run():
 p=json.loads((HERE.parent/'coherent_final24_r02/top_scene_patch_r01.json').read_bytes());vs=p['appended_surfaces']['ground_stone'];tris=[vs[i:i+3]for i in range(0,len(vs),3)];idx=collections.defaultdict(list)
 for i,t in enumerate(tris):
  for k in {key(v)for v in t}:idx[k].append(i)
 bad=[r['appended_triangle_index']for r in json.loads((HERE/'report.json').read_bytes())['cases']if r['kind']=='appended'and r['float32_normal_y']<0];records=[]
 for i in bad:
  opts=[];stars=[]
  for v in tris[i]:
   k=key(v);ids=idx[k];ring=ring_for(tris,ids,k);stars.append((len(ids),None if ring is None else len(ring)));opts+=options(tris,ids,k)
  opts.sort(key=lambda r:r['maximum_plane_difference_m']);print(i,'stars',stars,'options',[(r['source_indices'],r['maximum_plane_difference_m'])for r in opts[:3]],flush=True);records.append(dict(index=i,options=opts))
 (HERE/'star_probe.json').write_text(json.dumps(dict(records=records),separators=(',',':'))+'\n')
if __name__=='__main__':run()
