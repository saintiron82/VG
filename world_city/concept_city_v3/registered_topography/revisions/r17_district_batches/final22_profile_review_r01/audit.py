"""Independent exact finite coverage, winding and grade checks on final refits."""
import json,math,collections
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write,index
from ..final_profile_audit_r01.exact_clip import clip,difference
from ..public_owner_completion_r04.solve import grid
HERE=Path(__file__).resolve().parent
from ..final24_atomic_rebind_r01.prepare_request import FILES as SELECTED
FILES=list(SELECTED.values())
def subtract(ps,masks):
 for p in masks:ps=[v for q in ps for v in difference(q,p)]
 return ps
def audit(path):
 d=json.loads(path.read_bytes());res=d['result'];res=res['result']if 'triangles'not in res and 'result'in res else res;tris=res['triangles'];domains=d['private_domain_polygons_xz_m'];ti=index(tris);di=a.geo._SpatialIndex(4)
 for j,p in enumerate(domains):di.add(j,p)
 overlap=0.;outside=0.;missing=0.;badw=[];maxgrade=0.;badheight=[]
 for i,t in enumerate(tris):
  xyz=t['vertices_xyz_m'];p=t['polygon_xz_m'];assert all(math.isfinite(v)for x in xyz for v in x)
  if a.normal_y(xyz)<=0:badw.append(i)
  plane=a.common.plane(xyz);maxgrade=max(maxgrade,math.hypot(*plane[:2]));badheight.append(max(abs(a.common.height(t.get('plane_y_xz_m',t.get('plane',plane)),[x,z])-y)for x,y,z in xyz))
  for j in ti.candidates(p):
   if j>i:overlap+=a.geo.polygon_area(clip(p,tris[j]['polygon_xz_m']))
  outside+=sum(a.geo.polygon_area(q)for q in subtract([p],[domains[j]for j in di.candidates(p)]))
 _, union_cells=grid(domains,[],pitch=2.)
 raw_domain_area=sum(a.geo.polygon_area(p)for p in domains);expected=sum(c['area_m2']for c in union_cells);got=sum(a.geo.polygon_area(t['polygon_xz_m'])for t in tris);missing=max(0.,expected-(got-outside-overlap));limit=d.get('grade_limit',res.get('grade_limit',.12));source=d.get('source');source_ok=not source or a.sha(a.ROOT/source['path'])==source['sha256']
 row=dict(holding_ids=d.get('holding_ids',[d.get('holding_id')]),source=dict(path=str(path.relative_to(a.ROOT)),sha256=a.sha(path)),source_binding_verified=source_ok,triangle_count=len(tris),source_sum_area_m2=raw_domain_area,expected_union_area_m2=expected,triangle_area_m2=got,positive_overlap_m2=overlap,outside_domain_m2=outside,missing_domain_m2=missing,downward_triangles=badw,maximum_gradient=maxgrade,grade_limit=limit,maximum_plane_error_m=max(badheight,default=0),maximum_fixed_error_m=res.get('maximum_fixed_error_m'),passed=source_ok and not badw and overlap<1e-7 and outside<1e-7 and missing<1e-7 and abs(got-expected)<1e-7 and maxgrade<=limit+1e-7 and max(badheight,default=0)<1e-7)
 return row
def run():
 rows=[]
 for f in FILES:
  row=audit(a.HERE/f);rows.append(row);print(row,flush=True)
 write(HERE/'geometry_review.json',dict(rows=rows,passed=all(r['passed']for r in rows),policy='Exact signed halfplanes. Source domains are a union, so duplicated source pieces are not counted twice. Complete coverage follows measured union area, zero outside area, and pairwise disjoint emitted interiors. Capsule/runtime approval remains separate.'))
if __name__=='__main__':run()
