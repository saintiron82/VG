"""Independent per-grid finite area/winding proof for emitted owner records."""
import json,math,time,collections,sys
from .height_field import HERE
from . import public_domain as d,finite_geometry as g
from .grid_candidate import grade
from ..r17_district_batches import author as a

def main():
 start=time.monotonic();source=HERE/(sys.argv[1]if len(sys.argv)>1 else'finite_field_candidate_r01.json');outname=sys.argv[2]if len(sys.argv)>2 else'finite_ownership_review_r01.json';data=json.loads(source.read_bytes());records=data['records'];mask_path=a.ROOT/data['report']['ownership_inputs']['path'];assert a.sha(mask_path)==data['report']['ownership_inputs']['sha256'];mdata=json.loads(mask_path.read_bytes());masks=mdata['masks'];traffic=d.polygons();ti=a.geo._SpatialIndex(8);mi=a.geo._SpatialIndex(8);cells=collections.defaultdict(list)
 for n,p in enumerate(traffic):ti.add(n,p)
 for n,r in enumerate(masks):mi.add(n,r['polygon_xz_m'])
 for r in records:
  p=r['polygon_xz_m'];key=tuple(math.floor(math.fsum(v[k]for v in p)/len(p)/4)*4 for k in(0,1));cells[key].append(r)
 grid=json.loads((HERE/'grid_screen.json').read_bytes());rows=[];winding=[];plane_err=0.;tri_area_err=0.;clip_spill=0.;actual_grades=[]
 for n,c in enumerate(grid['cells']):
  x,z=c['origin_xz_m'];p=[[x,z],[x+4,z],[x+4,z+4],[x,z+4]];parts=g.union([q for i in sorted(ti.candidates(p))if(q:=g.clip(p,traffic[i]))]);parts=g.subtract(parts,[masks[i]['polygon_xz_m']for i in sorted(mi.candidates(p))]);expected=math.fsum(g.area(q)for q in parts);rs=cells.get((x,z),[]);actual=math.fsum(g.area(r['polygon_xz_m'])for r in rs);diff=actual-expected
  if abs(diff)>1e-7:rows.append(dict(origin_xz_m=[x,z],expected_area_m2=expected,emitted_area_m2=actual,error_m2=diff))
  for r in rs:
   pl=r['plane_y_xz_m'];poly=r['polygon_xz_m'];ts=r['triangles_xyz_m'];tri_area_err=max(tri_area_err,abs(math.fsum(abs(a.normal_y(t))/2 for t in ts)-g.area(poly)))
   for t in ts:
    ny=a.normal_y(t)
    if ny<=0:winding.append(dict(id=r['id'],triangle_xyz_m=t,normal_y=ny))
    if abs(ny)>1e-14:actual_grades.append(grade(t))
    plane_err=max(plane_err,max(abs(v[1]-a.common.height(pl,[v[0],v[2]]))for v in t))
  if n%1000==0:print('audited cells',n,'failures',len(rows),'seconds',time.monotonic()-start,flush=True)
 report=dict(status='PASS_FINITE_AREA_WINDING_WITH_EXPLICIT_DESIGN_EXCEPTIONS'if not(rows or winding)else'HELD_FINITE_OWNERSHIP_AUDIT',candidate=dict(path=str(source.relative_to(a.ROOT)),sha256=a.sha(source)),ownership_inputs=data['report']['ownership_inputs'],code_sha256=a.sha(__file__),geometry_code_sha256=a.sha(HERE/'finite_geometry.py'),source_grid_proof_sha256=a.sha(HERE/'candidate_geometry_review_r01.json'),cells=len(grid['cells']),owner_records=len(records),cell_area_budget_m2=1e-7,area_failures=rows,winding_failures=winding,max_polygon_to_triangle_area_error_m2=tri_area_err,max_plane_lift_error_m=plane_err,maximum_emitted_triangle_gradient=max(actual_grades,default=0),source_exception_triangles=data['report']['exception_source_triangles'],source_exception_area_m2=data['report']['exception_area_m2'],seconds=time.monotonic()-start,activation=False,scope='Independent per-cell traffic-minus-current-owner area agreement plus source nonoverlap proof; tiny floating-area residuals remain explicit. Design exceptions, side closure and actual unchanged-controller replay remain open.')
 (HERE/outname).write_text(json.dumps(report,separators=(',',':'))+'\n');print({k:v for k,v in report.items()if k not in('area_failures','winding_failures')},flush=True)
if __name__=='__main__':main()
