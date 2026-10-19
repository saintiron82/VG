"""Emit exact current traffic-minus-accepted-owners; preserve design exceptions."""
import json,math,time,collections
from .height_field import HERE
from . import public_domain as d,finite_geometry as g
from .grid_candidate import grade
from ..r17_district_batches import author as a

def main():
 start=time.monotonic();source=HERE/'field_refinement_r01.json';mesh=json.loads(source.read_bytes());mp=HERE/'boundary_ownership_inputs_r01.json';mdata=json.loads(mp.read_bytes());assert all(a.sha(a.ROOT/r['path'])==r['sha256']for r in mdata['source_refs']);traffic=d.polygons();masks=mdata['masks'];ti=a.geo._SpatialIndex(8);mi=a.geo._SpatialIndex(8)
 for i,p in enumerate(traffic):ti.add(i,p)
 for i,m in enumerate(masks):mi.add(i,m['polygon_xz_m'])
 records=[];exceptions=[];stats=collections.Counter();source_cells=collections.defaultdict(list)
 for n,t in enumerate(mesh['triangles_xyz_m']):
  p=[[v[0],v[2]]for v in t];source_cells[(math.floor(sum(v[0]for v in t)/12)*4,math.floor(sum(v[2]for v in t)/12)*4)].append(n)
  intersections=[q for i in sorted(ti.candidates(p))if(q:=g.clip(p,traffic[i]))];parts=g.union(intersections);parts=g.subtract(parts,[masks[i]['polygon_xz_m']for i in sorted(mi.candidates(p))]);pl=a.common.plane(t)
  for k,q in enumerate(parts):
   xyz=[[v[0],a.common.height(pl,v),v[1]]for v in q];ts=list(a.fan_upward(xyz));r=dict(id=f'R18_FINITE:{n}:{k}',source_triangle_index=n,polygon_xz_m=q,plane_y_xz_m=pl,triangles_xyz_m=ts,source_gradient=grade(t));records.append(r)
   if grade(t)>.12+1e-7:
    lengths=[math.dist(u,v)for u,v in zip(q,q[1:]+q[:1])];exceptions.append(dict(id=r['id'],source_triangle_index=n,polygon_xz_m=q,triangle_xyz_m=t,plane_y_xz_m=pl,gradient=grade(t),area_m2=g.area(q),bounds_xz_m=[min(v[0]for v in q),min(v[1]for v in q),max(v[0]for v in q),max(v[1]for v in q)],maximum_edge_length_m=max(lengths),source_triangle_min_altitude_m=2*g.area(p)/max(math.dist(u,v)for u,v in zip(p,p[1:]+p[:1])),height_range_m=max(v[1]for v in xyz)-min(v[1]for v in xyz)))
  if n%3000==0:print('finite',n,'records',len(records),'seconds',time.monotonic()-start,flush=True)
 report=dict(schema='riverstone.r18.finite_public_emission.v1',status='FINITE_CANDIDATE_WITH_EXPLICIT_DESIGN_GRADE_EXCEPTIONS',source_mesh=dict(path=str(source.relative_to(a.ROOT)),sha256=a.sha(source)),ownership_inputs=dict(path=str(mp.relative_to(a.ROOT)),sha256=a.sha(mp)),source_refs=mesh['source_refs']+mdata['source_refs'],geometry_code_sha256=a.sha(HERE/'finite_geometry.py'),source_triangles=len(mesh['triangles_xyz_m']),finite_records=len(records),finite_area_m2=math.fsum(g.area(r['polygon_xz_m'])for r in records),exceptions=exceptions,exception_area_m2=math.fsum(r['area_m2']for r in exceptions),exception_source_triangles=len(set(r['source_triangle_index']for r in exceptions)),max_source_grade=max((r['source_gradient']for r in records),default=0),seconds=time.monotonic()-start,activation=False,scope='Finite candidate only. Design grade exceptions retained explicitly; side closure, exact seam coverage, and actual unchanged-controller replay remain required.')
 (HERE/'finite_field_candidate_r01.json').write_text(json.dumps(dict(report=report,records=records),separators=(',',':'))+'\n');(HERE/'finite_emission_review_r01.json').write_text(json.dumps(report,separators=(',',':'))+'\n');print({k:v for k,v in report.items()if k not in('source_refs','exceptions')},flush=True)
if __name__=='__main__':main()
