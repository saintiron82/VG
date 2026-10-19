import json,math,collections
from .height_field import HERE
from . import finite_geometry_r03 as g
from ..r17_district_batches import author as a

def contact(p,q):
 for u,v in zip(p,p[1:]+p[:1]):
  L=math.dist(u,v)
  if L<1e-8:continue
  for x,y in zip(q,q[1:]+q[:1]):
   if max(abs(g.cross(u,v,t))/L for t in [x,y])>1e-7:continue
   t=[sum((k[i]-u[i])*(v[i]-u[i]) for i in(0,1))/L for k in[x,y]]
   if min(L,max(t))-max(0,min(t))>1e-8:return True
 return False

def main():
 p=HERE/'north_mask_restoration_r02_candidate.json';d=json.loads(p.read_bytes());np=HERE/'north_residual_native_projection_r01.json';n=json.loads(np.read_bytes());polys=g.subtract(d['retired_mask_residual_polygons_xz_m'],[r['polygon_xz_m']for r in n['rows']]);idx=a.geo._SpatialIndex(4)
 for i,q in enumerate(polys):idx.add(i,q)
 parent=list(range(len(polys)))
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for i,q in enumerate(polys):
  for j in idx.candidates(q):
   if j<=i:continue
   if contact(q,polys[j]):parent[root(i)]=root(j)
 groups=collections.defaultdict(list)
 for i,q in enumerate(polys):groups[root(i)].append(q)
 rows=[];ep=HERE/'boundary_closure_handoff_r05_native.json';edges=[r for r in json.loads(ep.read_bytes())['rows']if r['category']=='BOUNDED_OBSOLETE_BRIDGE_MASK_RESTORATION_REQUIRED']
 for k,qs in groups.items():
  pts=[v for q in qs for v in q];b=[min(v[0]for v in pts),min(v[1]for v in pts),max(v[0]for v in pts),max(v[1]for v in pts)];hits=[r for r in edges if any(contact(q,r['edge_xz_m'])for q in qs)];rows.append(dict(id=k,polygon_count=len(qs),area_m2=math.fsum(g.area(q)for q in qs),bounds_xz_m=b,polygons_xz_m=qs,matching_unknown_edges=hits))
 out={'status':'CONNECTED_RESIDUAL_DIAGNOSTIC_ONLY','component_contact_roundoff_m':1e-7,'components':rows};op=HERE/'north_residual_components_r01.json';op.write_text(json.dumps(out,separators=(',',':'))+'\n');print([{k:v for k,v in r.items()if k!='polygons_xz_m'and k!='matching_unknown_edges'}|{'edge_count':len(r['matching_unknown_edges'])}for r in rows])
if __name__=='__main__':main()
