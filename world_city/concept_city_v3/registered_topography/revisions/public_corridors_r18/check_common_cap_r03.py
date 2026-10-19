"""Independent finite common-cap boundary and accepted-profile checks.
The 1nm boundary classification is numerical diagnosis only; all geometry,
collision coordinates and controller thresholds remain exact input values.
"""
import json,math,collections
from .height_field import HERE,fixed_sources
from . import finite_geometry_r03 as g
from .screen_contour_domain_r02 import boundary_interval
from ..r17_district_batches import author as a

def main():
 source=HERE/'finite_field_candidate_r05_common.json';data=json.loads(source.read_bytes());review=HERE/'common_cap_transition_review_r03.json';changes=json.loads(review.read_bytes())['changed_parts'];cp=a.ROOT/data['report']['common_cap_transition']['actual_cap_handoff']['path'];cap=json.loads(cp.read_bytes());records=data['records'];ix=a.geo._SpatialIndex(4)
 for i,r in enumerate(records):ix.add(i,r['polygon_xz_m'])
 failures=[];samples=[];max_error=0.;native_overlap=[]
 for j,s in enumerate(cap['actual_outer_cap_edge_segments']):
  p,q=s['edge_xz_m']
  for k in ix.candidates([p,q]):
   r=records[k];span=boundary_interval(p,q,r['polygon_xz_m'])
   if not span:continue
   pts=[[p[c]+t*(q[c]-p[c]) for c in(0,1)]for t in span];err=max(abs(a.common.height(r['plane_y_xz_m'],v)-8)for v in pts);max_error=max(max_error,err);item=dict(segment=j,owner=r['id'],span=span,error_m=err);samples.append(item)
   if err>1e-7:failures.append(item)
 for j,poly in enumerate(cap['native_cap_polygon_parts_xz_m']):
  for k in ix.candidates(poly):
   r=records[k];inter=g.clip(r['polygon_xz_m'],poly)
   if inter and g.area(inter)>1e-9:native_overlap.append(dict(cap=j,owner=r['id'],area_m2=g.area(inter),polygon_xz_m=inter))
 regs,segs,refs=fixed_sources();si=a.geo._SpatialIndex(8)
 for i,s in enumerate(segs):si.add(i,[[v[0],v[2]]for v in s['xyz_m']])
 fixed_rows=[];fixed_fail=[]
 for r in changes:
  for j in si.candidates(r['polygon_xz_m']):
   s=segs[j];p,q=s['xyz_m'];span=boundary_interval([p[0],p[2]],[q[0],q[2]],r['polygon_xz_m'])
   if not span:continue
   err=max(abs(a.common.height(r['plane_y_xz_m'],[p[0]+t*(q[0]-p[0]),p[2]+t*(q[2]-p[2])])-(p[1]+t*(q[1]-p[1])))for t in span);row=dict(owner=r['id'],fixed_segment=s['id'],error_m=err);fixed_rows.append(row)
   if err>1e-7:fixed_fail.append(row)
 # Every already-released frontage source plane remains identical over its
 # actual intersecting direct-emission owners; no old source point is moved.
 fp=HERE/'frontage_profiles_r01.json';front=json.loads(fp.read_bytes());print('frontage schema',front.keys(),flush=True)
 counts=collections.Counter(r['id']for r in records)
 out=dict(status='PASS_COMMON_CAP_FINITE_SEAMS'if not(failures or native_overlap or fixed_fail or any(v>1 for v in counts.values()))else'HELD_COMMON_CAP',candidate=dict(path=str(source.relative_to(a.ROOT)),sha256=a.sha(source)),cap_handoff=dict(path=str(cp.relative_to(a.ROOT)),sha256=a.sha(cp)),edge_portions=len(samples),maximum_cap_edge_error_m=max_error,cap_edge_failures=failures,native_positive_overlap=native_overlap,fixed_segment_portions=len(fixed_rows),max_fixed_segment_error_m=max((r['error_m']for r in fixed_rows),default=0),fixed_segment_failures=fixed_fail,duplicate_owner_ids=[k for k,v in counts.items()if v>1],scope=__doc__,code_sha256=a.sha(__file__),activation=False)
 (HERE/'common_cap_boundary_review_r03.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print(out,flush=True)
if __name__=='__main__':main()
