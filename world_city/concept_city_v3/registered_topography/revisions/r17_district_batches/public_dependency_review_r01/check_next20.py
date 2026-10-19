"""Source mesh, upward winding, finite coverage, and shared private field checks."""
import json,math,time
from .review import HERE,OLD,write
from .. import author as a

def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def run():
 t=time.monotonic();rp=HERE/'next20_atomic_rebind_request_r01.json';req=json.loads(rp.read_bytes());selected=[];checks=[];seen=set();fixed=[];entries=[]
 for hid,b in req['profile_bindings'].items():
  p=a.ROOT/b['path'];assert a.sha(p)==b['sha256'];d=json.loads(p.read_bytes());res=d['result'];faces=res['triangles'];domains=d['private_domain_polygons_xz_m'];public=d['public_fixed_regions']
  expected=sum(a.geo.polygon_area(p)for p in domains);actual=sum(a.geo.polygon_area(r['polygon_xz_m'])for r in faces);normal_bad=sum(a.normal_y(r['vertices_xyz_m'])<=0 for r in faces);g=max(math.hypot(*a.common.plane(r['vertices_xyz_m'])[:2])for r in faces)
  assert abs(expected-actual)<1e-6 and not normal_bad and g<=.12+1e-7
  checks.append(dict(holding_id=hid,profile=b,domain_area_m2=expected,actual_triangle_area_m2=actual,area_error_m2=actual-expected,triangles=len(faces),downward_triangles=normal_bad,maximum_actual_gradient=g))
  entries.append(dict(holding_ids=[hid],profile=b,public_fixed_regions=public));fixed.extend(public)
  if b['path']not in seen:seen.add(b['path']);selected.append(d)
 comparisons=[]
 # New selected field pairs are measured exactly. No sequential override of
 # one independently solved private profile is allowed.
 for i,d in enumerate(selected):
  for e in selected[i+1:]:
   hits=[]
   for p in d['private_domain_polygons_xz_m']:
    for q in e['private_domain_polygons_xz_m']:
     hit=a.clip(p,q)
     if hit:hits.append(hit)
   if not hits:continue
   ar=sum(a.geo.polygon_area(p)for p in a.common.disjoint_union(hits))
   if ar<1e-8:continue
   idx=a.geo._SpatialIndex(4);tri=e['result']['triangles'];errors=[]
   for j,r in enumerate(tri):idx.add(j,r['polygon_xz_m'])
   for r in d['result']['triangles']:
    for j in idx.candidates(r['polygon_xz_m']):
     s=tri[j];p=a.clip(r['polygon_xz_m'],s['polygon_xz_m'])
     if p:errors.append(max(abs(a.common.height(r['plane_y_xz_m'],q)-a.common.height(s['plane_y_xz_m'],q))for q in p))
   comparisons.append(dict(left=d.get('holding_id',d.get('holding_ids')),right=e.get('holding_id',e.get('holding_ids')),area_m2=ar,max_error_m=max(errors,default=0)))
 assert all(r['max_error_m']<1e-7 for r in comparisons)
 write(HERE/'next20_fixed_public_regions_r01.json',dict(schema='riverstone.r17.pending_batch.fixed_public_regions.v1',source_request=ref(rp),selected_holding_ids=req['matched_next_batch_holding_ids'],entries=entries,public_fixed_regions=fixed,policy='Exact R18 and unchanged current-R04 public planes. Frozen accepted batches remain unchanged.',activation=False))
 out=dict(status='PASSED_SOURCE_TRIANGLE_WINDING_COVERAGE_AND_SELECTED_PRIVATE_COMPATIBILITY',source_request=ref(rp),checks=checks,private_pair_intersections=comparisons,triangle_count=sum(r['triangles']for r in checks),maximum_gradient=max(r['maximum_actual_gradient']for r in checks),maximum_area_error_m2=max(abs(r['area_error_m2'])for r in checks),seconds=time.monotonic()-t,scope='Native source rebind, final side ownership and actual controller replay remain required.',activation=False);write(HERE/'next20_source_mesh_review_r01.json',out);print({k:v for k,v in out.items()if k not in('checks','private_pair_intersections')},flush=True)
if __name__=='__main__':run()
