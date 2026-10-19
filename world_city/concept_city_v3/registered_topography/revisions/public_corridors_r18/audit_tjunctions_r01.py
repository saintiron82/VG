"""Detect finite active source edge/subdivision height discontinuities."""
import json,math,collections,time
from .height_field import HERE
from . import finite_geometry_r03 as g
from .revise_native_emission_r07 import ref
from ..r17_district_batches import author as a

def contains(p,poly):
 b=a.bounds(poly)
 if p[0]<b[0]-1e-9 or p[0]>b[2]+1e-9 or p[1]<b[1]-1e-9 or p[1]>b[3]+1e-9:return False
 s=1 if g.signed_area(poly)>0 else-1
 return all(s*g.cross(u,v,p)>=-1e-9*math.dist(u,v)for u,v in zip(poly,poly[1:]+poly[:1])if math.dist(u,v)>1e-12)
def main():
 start=time.monotonic();mp=HERE/'field_refinement_r01.json';fp=HERE/'finite_field_candidate_r07_native_bound.json';mesh=json.loads(mp.read_bytes())['triangles_xyz_m'];pub=json.loads(fp.read_bytes());by=collections.defaultdict(list)
 for r in pub['records']:by[r['source_triangle_index']].append(r)
 points={};idx=a.geo._SpatialIndex(4)
 for i in by:
  for v in mesh[i]:points.setdefault(tuple(v),set()).add(i)
 vertices=list(points)
 for i,v in enumerate(vertices):idx.add(i,[[v[0],v[2]]])
 rows=[];seen=set()
 for i in by:
  tri=mesh[i]
  for ei,(u,v)in enumerate(zip(tri,tri[1:]+tri[:1])):
   p,q=[u[0],u[2]],[v[0],v[2]];L=math.dist(p,q)
   if L<1e-8:continue
   for vi in idx.candidates([p,q]):
    w=vertices[vi];xz=[w[0],w[2]];t=sum((xz[k]-p[k])*(q[k]-p[k])for k in(0,1))/(L*L)
    if not 1e-9<t<1-1e-9:continue
    distance=abs(g.cross(p,q,xz))/L
    if distance>1e-9:continue
    y=u[1]+t*(v[1]-u[1]);delta=w[1]-y
    if abs(delta)<=1e-7:continue
    coarse=[r['id']for r in by[i]if contains(xz,r['polygon_xz_m'])];fine=[r['id']for si in points[w]if si!=i for r in by[si]if contains(xz,r['polygon_xz_m'])]
    if not coarse or not fine:continue
    key=(i,ei,tuple(xz),round(w[1],12))
    if key in seen:continue
    seen.add(key);rows.append(dict(coarse_source_triangle=i,source_edge=ei,edge_xyz_m=[u,v],point_xyz_m=list(w),coarse_interpolated_y_m=y,delta_y_m=delta,perpendicular_distance_m=distance,coarse_public_owner_ids=coarse,fine_source_triangles=sorted(points[w]-{i}),fine_public_owner_ids=fine))
 protected=[];refs=[ref(mp),ref(fp)]
 for sub in ['contour_bulk_r01','coherent_batch18_r01']:
  p=a.CITY/'registered_topography/revisions/r17_district_batches'/sub/'physical_owner_handoff_r02.json';d=json.loads(p.read_bytes());protected+=d['public_fixed_regions'];refs.append(ref(p))
 pi=a.geo._SpatialIndex(4)
 for i,p in enumerate(protected):pi.add(i,p['polygon_xz_m'])
 changed=sorted({r['coarse_source_triangle']for r in rows});conflicts=[]
 for i in changed:
  for r in by[i]:
   for j in pi.candidates(r['polygon_xz_m']):
    q=g.clip(r['polygon_xz_m'],protected[j]['polygon_xz_m']);ar=g.area(q)
    if ar>1e-9:conflicts.append(dict(source_triangle=i,public_owner_id=r['id'],protected_owner_id=protected[j].get('id',protected[j].get('owner_id')),polygon_xz_m=q,area_m2=ar))
 out=dict(schema='riverstone.r18.tjunction_height_audit.v1',status='FAIL_ACTIVE_SHARED_EDGE_HEIGHT_DISCONTINUITIES'if rows else'PASS',sources=refs,rows=rows,coarse_source_triangles=changed,active_coarse_area_m2=math.fsum(g.area(r['polygon_xz_m'])for i in changed for r in by[i]),maximum_abs_height_jump_m=max((abs(r['delta_y_m'])for r in rows),default=0),protected_first41_intersections=conflicts,seconds=time.monotonic()-start,policy='Detection uses1nm geometric coincidence only, preserving all source coordinates. Both faces must actually own the finite point; bbox and signed-distance rejection prevent far-away tiny-polygon matches. No height changes are authorized by this audit.')
 op=HERE/'active_tjunction_audit_r01.json';op.write_text(json.dumps(out,separators=(',',':'))+'\n');print({k:v for k,v in out.items()if k not in ['sources','rows','coarse_source_triangles','protected_first41_intersections']});print('rows',len(rows),'coarse',len(changed),'protected',len(conflicts),ref(op))
if __name__=='__main__':main()
