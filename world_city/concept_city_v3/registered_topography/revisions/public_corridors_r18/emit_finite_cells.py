"""Normalized finite owner emission, preserving source planes and all positive fans."""
import json,math,time,collections
from .height_field import HERE
from . import public_domain as d,finite_geometry_r03 as g
from .grid_candidate import grade
from ..r17_district_batches import author as a

def positive_fan(poly,plane):
 xyz=[[v[0],a.common.height(plane,v),v[1]]for v in poly];out=[]
 for i in range(1,len(xyz)-1):
  t=[xyz[0],xyz[i],xyz[i+1]];ny=a.normal_y(t)
  if ny<0:t=[t[0],t[2],t[1]];ny=-ny
  if ny>0:out.append(t)
 return out

def main():
 start=time.monotonic();source=HERE/'field_refinement_r01.json';mesh=json.loads(source.read_bytes());mp=HERE/'boundary_ownership_inputs_r03.json';assert a.sha(mp)=='f40e534df8491c1ab40453f923c51c61ae9e0b7ee48aea76f27e83354ed452e2';mdata=json.loads(mp.read_bytes());assert all(a.sha(a.ROOT/r['path'])==r['sha256']for r in mdata['source_refs']);traffic=d.polygons();masks=mdata['masks'];ti=a.geo._SpatialIndex(8);mi=a.geo._SpatialIndex(8)
 for i,p in enumerate(traffic):ti.add(i,p)
 for i,m in enumerate(masks):mi.add(i,m['polygon_xz_m'])
 normalization=[]
 for kind,rows in [('traffic',traffic),('accepted_owner',[r['polygon_xz_m']for r in masks])]:
  for i,p in enumerate(rows):
   q=g.normalize_mask(p)
   if q!=p:normalization.append(dict(kind=kind,index=i,owner_id=masks[i].get('id')if kind=='accepted_owner'else None,before_polygon_xz_m=p,after_polygon_xz_m=q,absolute_area_change_m2=abs(g.area(p)-g.area(q))))
 records=[];exceptions=[];cells=collections.defaultdict(list)
 for n,t in enumerate(mesh['triangles_xyz_m']):cells[(math.floor(sum(v[0]for v in t)/12)*4,math.floor(sum(v[2]for v in t)/12)*4)].append(n)
 rows=[]
 for ci,(key,indices)in enumerate(cells.items()):
  x,z=key;cell=[[x,z],[x+4,z],[x+4,z+4],[x,z+4]];parts=g.union([q for i in sorted(ti.candidates(cell))if(q:=g.clip(cell,traffic[i]))]);parts=g.subtract(parts,[masks[i]['polygon_xz_m']for i in sorted(mi.candidates(cell))]);expected=math.fsum(g.area(p)for p in parts);actual=0.
  for n in indices:
   t=mesh['triangles_xyz_m'][n];poly=[[v[0],v[2]]for v in t];pl=a.common.plane(t)
   for k,p in enumerate(parts):
    q=g.clip(poly,p)
    if not q:continue
    ts=positive_fan(q,pl);r=dict(id=f'R18_FINITE:{n}:{k}',source_triangle_index=n,polygon_xz_m=q,plane_y_xz_m=pl,triangles_xyz_m=ts,source_gradient=grade(t));records.append(r);actual+=g.area(q)
    if grade(t)>.12+1e-7:exceptions.append(dict(id=r['id'],source_triangle_index=n,polygon_xz_m=q,triangle_xyz_m=t,plane_y_xz_m=pl,gradient=grade(t),area_m2=g.area(q),bounds_xz_m=[min(v[0]for v in q),min(v[1]for v in q),max(v[0]for v in q),max(v[1]for v in q)],source_triangle_min_altitude_m=2*g.area(poly)/max(math.dist(u,v)for u,v in zip(poly,poly[1:]+poly[:1])),height_range_m=max(a.common.height(pl,v)for v in q)-min(a.common.height(pl,v)for v in q)))
  rows.append(dict(origin_xz_m=list(key),target_area_m2=expected,emitted_owner_area_m2=actual,error_m2=actual-expected))
  if ci%1000==0:print('cells',ci,'records',len(records),'seconds',time.monotonic()-start,flush=True)
 area=math.fsum(g.area(r['polygon_xz_m'])for r in records);renderarea=math.fsum(abs(a.normal_y(t))/2 for r in records for t in r['triangles_xyz_m']);failures=[r for r in rows if abs(r['error_m2'])>1e-7];report=dict(schema='riverstone.r18.finite_public_emission.v2',status='FINITE_CANDIDATE_WITH_EXPLICIT_DESIGN_GRADE_EXCEPTIONS'if not failures else'HELD_FINITE_AREA_FAILURES',source_mesh=dict(path=str(source.relative_to(a.ROOT)),sha256=a.sha(source)),ownership_inputs=dict(path=str(mp.relative_to(a.ROOT)),sha256=a.sha(mp)),source_refs=mesh['source_refs']+mdata['source_refs'],geometry_code_sha256=a.sha(HERE/'finite_geometry_r03.py'),source_triangles=len(mesh['triangles_xyz_m']),finite_records=len(records),finite_area_m2=area,rendered_triangles=sum(len(r['triangles_xyz_m'])for r in records),rendered_area_m2=renderarea,owner_minus_rendered_area_m2=area-renderarea,empty_fan_records=[dict(id=r['id'],area_m2=g.area(r['polygon_xz_m']))for r in records if not r['triangles_xyz_m']],exceptions=exceptions,exception_area_m2=math.fsum(r['area_m2']for r in exceptions),exception_source_triangles=len(set(r['source_triangle_index']for r in exceptions)),max_source_grade=max((r['source_gradient']for r in records),default=0),normalization_count=len(normalization),normalization_total_absolute_area_delta_m2=math.fsum(r['absolute_area_change_m2']for r in normalization),normalization_bound_m=1e-9,max_cell_area_error_m2=max(abs(r['error_m2'])for r in rows),cell_area_failures=failures,seconds=time.monotonic()-start,activation=False,scope='Exact finite owner candidate with positive-winding fans. The 1nm consecutive mask duplicate normalization and design-grade exceptions are explicit. Side closure and unchanged-controller replay remain required.')
 (HERE/'finite_field_candidate_r02.json').write_text(json.dumps(dict(report=report,records=records),separators=(',',':'))+'\n');(HERE/'finite_emission_review_r02.json').write_text(json.dumps(report,separators=(',',':'))+'\n');(HERE/'finite_mask_normalization_r02.json').write_text(json.dumps(dict(report=report['normalization_count'],records=normalization,cell_area_ledger=rows),separators=(',',':'))+'\n');print({k:v for k,v in report.items()if k not in('source_refs','exceptions','empty_fan_records','cell_area_failures')},flush=True)
if __name__=='__main__':main()
