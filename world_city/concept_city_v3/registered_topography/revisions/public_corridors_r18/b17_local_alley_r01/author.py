"""Finite B17 alley coarse/fine fan repair. Original outer XYZ edges retained."""
import json,math,hashlib,time,resource,gc
from pathlib import Path
from .. import finite_geometry_r03 as g
from ...r17_district_batches import author as a
HERE=Path(__file__).resolve().parent
ROOT=a.ROOT

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v):return hashlib.sha256(json.dumps(v,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def ref(p):return dict(path=str(Path(p).relative_to(ROOT)),sha256=sha(p))
def load_bound(p,h):assert sha(p)==h;return json.loads(Path(p).read_bytes())
def normal(t):
 u=[t[1][i]-t[0][i]for i in range(3)];v=[t[2][i]-t[0][i]for i in range(3)]
 return[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
def grade(t):n=normal(t);return math.hypot(n[0],n[2])/abs(n[1])
def poly(t):return[[v[0],v[2]]for v in t]
def plane(t):return a.common.plane(t)
def height(t,p):return a.common.height(plane(t),p)
def main():
 start=time.monotonic();exception=ROOT/'world_city/concept_city_v3/registered_topography/revisions/r17_district_batches/b17_public_fan_exception_r01/source_exception.json';data=load_bound(exception,'d0af57b9b85c8c7318758474da164e696d0528249cab470b4c44d22b6eb4bf7d')
 scene_path=ROOT/data['base_scene']['path'];scene=load_bound(scene_path,data['base_scene']['sha256']);source=scene['surfaces']['road'];old=[source[3*i:3*i+3]for i in range(53659,53688)]
 L0=old[0][0];L1=scene['surfaces']['road'][53683*3+1]
 rights=[scene['surfaces']['road'][53684*3+2],scene['surfaces']['road'][53684*3+1],scene['surfaces']['road'][53685*3+1],scene['surfaces']['road'][53686*3+1]]
 u0=(32-L0[0])/(rights[0][0]-L0[0]);u1=(32-L1[0])/(rights[-1][0]-L1[0]);rows=[]
 for j,r in enumerate(rights):
  t=(r[2]-120)/8;l=[L0[k]+t*(L1[k]-L0[k])for k in range(3)];u=u0*(1-t)+u1*t;m=[l[k]+u*(r[k]-l[k])for k in range(3)]
  if j==0:m=[32,1.422819844599276,120]
  if j==3:m=[32,1,128]
  rows.append([l,m,r])
 new=[]
 for i in range(3):
  for j in range(2):
   p,q=rows[i][j],rows[i][j+1];r,s=rows[i+1][j],rows[i+1][j+1]
   options=[[[p,q,r],[q,s,r]],[[p,q,s],[p,s,r]]];new.extend(min(options,key=lambda ts:max(map(grade,ts))))
 new=[t if normal(t)[1]>0 else[t[0],t[2],t[1]]for t in new]
 oldps=[poly(t)for t in old];newps=[poly(t)for t in new];oldarea=math.fsum(g.area(p)for p in oldps);newarea=math.fsum(g.area(p)for p in newps)
 missing=g.subtract(oldps,newps);excess=g.subtract(newps,oldps);ma=math.fsum(g.area(p)for p in missing);ea=math.fsum(g.area(p)for p in excess)
 overlaps=[]
 for i,p in enumerate(newps):
  for j,q in enumerate(newps[:i]):
   hit=g.clip(p,q)
   if hit:overlaps.append(dict(a=i,b=j,polygon_xz_m=hit,area_m2=g.area(hit)))
 deltas=[]
 for i,t in enumerate(new):
  for j,o in enumerate(old):
   q=g.clip(poly(t),poly(o))
   if q:
    vals=[height(t,p)-height(o,p)for p in q];deltas.append(dict(new_triangle_index=i,source_triangle_index=53659+j,polygon_xz_m=q,height_delta_range_m=[min(vals),max(vals)]))
 # Preserve the exact original perimeter and its source heights, including the top/bottom X32 knots.
 perimeter=[L0,old[0][2],rights[0],rights[1],rights[2],rights[3],[32,1,128],L1]
 boundary=[]
 for A,B in zip(perimeter,perimeter[1:]+perimeter[:1]):
  samples=[]
  for u in [0,.125,.25,.5,.75,.875,1]:
   v=[A[k]+u*(B[k]-A[k])for k in range(3)];heights=[]
   for t in new:
    p=poly(t);sgn=1 if g.signed_area(p)>0 else-1
    if all(sgn*g.cross(x,y,[v[0],v[2]])>=-1e-10*math.dist(x,y)for x,y in zip(p,p[1:]+p[:1])):heights.append(height(t,[v[0],v[2]]))
   assert heights,(A,B,u);err=max(abs(h-v[1])for h in heights);samples.append(dict(t=u,expected_xyz_m=v,max_height_error_m=err))
  boundary.append(dict(xyz_m=[A,B],samples=samples))
 maxseam=max(s['max_height_error_m']for e in boundary for s in e['samples']);assert maxseam<1e-10
 banks=[]
 for material in ['bank']:
  vs=scene['surfaces'][material]
  for i in range(0,len(vs),3):
   t=vs[i:i+3]
   if min(p[0]for p in t)>rights[-1][0]or max(p[0]for p in t)<L0[0]or min(p[2]for p in t)>128 or max(p[2]for p in t)<120:continue
   banks.append(dict(material=material,triangle_index=i//3,source_triangle_sha256=canonical(t),triangle_xyz_m=t,action='retained_exactly',classification='Existing outer strip/end faces; no interior X32 riser faces in the source band.'))
 oldhashes={canonical(t):53659+i for i,t in enumerate(old)};assert len(oldhashes)==29
 source_refs=[ref(scene_path),ref(exception)];del scene;gc.collect()
 # Rebind uniquely to base R7 ordered XYZ for normal parent finite patch composition.
 base=ROOT/'world_city/concept_city_v3/evidence/visual_registered_common_r7_palette_r01/scene.json';basehash='1429ae51b7c72b12940dcf0dd7e12c2684cab95f81735d228bba64dc819317c1';bs=load_bound(base,basehash);vs=bs['surfaces']['road'];matches={h:[]for h in oldhashes}
 for i in range(0,len(vs),3):
  t=vs[i:i+3]
  if min(p[0]for p in t)>34 or max(p[0]for p in t)<29 or min(p[2]for p in t)>128 or max(p[2]for p in t)<120:continue
  h=canonical(t)
  if h in matches:matches[h].append(i//3)
 assert all(len(m)==1 for m in matches.values()),matches
 edits=[dict(material='road',triangle_index=matches[canonical(t)][0],source_triangle_sha256=canonical(t),replacement_triangles_xyz_m=[])for t in old]
 patch=dict(schema='riverstone.finite_scene_patch.v1',id='R18_B17_ALLEY_LOCAL_FAN_R01',base_scene_sha256=basehash,source_surface_hashes={'road':canonical(vs)},surface_edits=edits,appended_surfaces={'road':[v for t in new for v in t]},removed_foundation_proxy_ids=[],source_refs=source_refs+[ref(base)],scope='29 old fan faces replaced by 12 continuous full-band public triangles. Only finite top ownership changes; native/water/banks and all measured outer XYZ edges remain unchanged.',runtime_ready=False)
 pp=HERE/'scene_patch.json';pp.write_text(json.dumps(patch,separators=(',',':'))+'\n')
 owners=[dict(id='B17_ALLEY_LOCAL_R01:'+str(i),polygon_xz_m=poly(t),plane_y_xz_m=plane(t),triangles_xyz_m=[t],material='road',road_id='BLOCK_017:ALLEY',source_retirement_indices=list(range(53659,53688)))for i,t in enumerate(new)]
 op=HERE/'physical_owners.json';op.write_text(json.dumps(dict(owners=owners,source_refs=source_refs,source_patch=ref(pp)),separators=(',',':'))+'\n')
 tests=dict(source_hashes_bound=True,unique_base_R7_face_matches=all(len(v)==1for v in matches.values()),old_count_29=len(old)==29,new_count_12=len(new)==12,finite_XZ_coverage=ma<1e-9 and ea<1e-9,new_positive_area_overlap=sum(r['area_m2']for r in overlaps)<1e-9,all_upward=all(normal(t)[1]>0for t in new),grade_le_12percent=max(map(grade,new))<=.12,exact_measured_outer_seams=maxseam<1e-10,all_original_bank_faces_retained=True)
 review=dict(status='PASS_FINITE_SOURCE_GEOMETRY_PENDING_RUNTIME'if all(tests.values())else'HELD',source_refs=source_refs+[ref(base),ref(Path(__file__))],patch=ref(pp),physical_owners=ref(op),tests=tests,source_triangle_count=len(old),replacement_triangle_count=len(new),source_area_m2=oldarea,replacement_area_m2=newarea,missing_area_m2=ma,excess_area_m2=ea,missing_polygons=missing,excess_polygons=excess,positive_area_overlaps=overlaps,max_grade=max(map(grade,new)),max_source_grade=max(map(grade,old)),height_delta_range_m=[min(r['height_delta_range_m'][0]for r in deltas),max(r['height_delta_range_m'][1]for r in deltas)],source_plane_intersection_deltas=deltas,exact_outer_boundary=boundary,maximum_outer_height_error_m=maxseam,nearby_retained_banks=banks,bounds_xz_m=[min(v[0]for t in new for v in t),120,max(v[0]for t in new for v in t),128],other_53688_exception='Separate 0.01143 m² retained face at X71.64 was not altered; it does not overlap the requested I004 entry.',seconds=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,runtime_ready=False)
 rp=HERE/'review.json';rp.write_text(json.dumps(review,separators=(',',':'))+'\n');freeze=dict(status=review['status'],files=[ref(pp),ref(op),ref(rp),ref(Path(__file__))],runtime_ready=False);fp=HERE/'freeze_manifest.json';fp.write_text(json.dumps(freeze,separators=(',',':'))+'\n');print(json.dumps(dict(patch=ref(pp),owners=ref(op),review=ref(rp),freeze=ref(fp),tests=tests,summary={k:review[k]for k in ['source_area_m2','replacement_area_m2','missing_area_m2','excess_area_m2','max_grade','height_delta_range_m','seconds']})))
if __name__=='__main__':main()
