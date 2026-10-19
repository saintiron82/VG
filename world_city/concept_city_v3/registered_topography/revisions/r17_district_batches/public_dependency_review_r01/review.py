"""Review actual private-boundary constraints without redesigning retained roads.

Historical internal public seams are recorded, not erased or equated. A solve
may proceed only with complete source-backed public coverage; every incident
private vertex still uses the exact public plane and every emitted triangle is
measured. No scene activation is performed here.
"""
import json, math, time, collections
from pathlib import Path
from .. import author as a
from ..contour_bulk_r01 import profile_mesh
from ..coherent_batch18_r01.route_interval import interval
from ...public_corridors_r18 import public_domain
HERE=Path(__file__).resolve().parent; OLD=HERE.parent/'contour_bulk_r01'
R18=HERE.parent.parent/'public_corridors_r18/finite_field_candidate_r04_common.json'
R04=a.CITY/'evidence/r8_district_r04/scene.json'
R04_SHA='3c63a21f4490e1dada6be34428dc2d1ffacd326d8f34b2deee81e378ab6680d7'

def write(path,data):
 if path.exists():raise ValueError('Refusing to replace '+str(path))
 path.write_text(json.dumps(data,separators=(',',':'),allow_nan=False)+'\n')
def area(ps):return sum(a.geo.polygon_area(p)for p in ps)
def indexed(rows):
 idx=a.geo._SpatialIndex(8)
 for i,r in enumerate(rows):idx.add(i,r['polygon_xz_m'])
 return idx

def seams(regions):
 idx=indexed(regions);out=[]
 for i,r in enumerate(regions):
  poly=r['polygon_xz_m']
  for p,q in zip(poly,poly[1:]+poly[:1]):
   if math.dist(p,q)<1e-8:continue
   for j in sorted(idx.candidates([p,q])):
    if j<=i:continue
    s=regions[j];sp=interval(p,q,s['polygon_xz_m'])
    if not sp or (sp[1]-sp[0])*math.dist(p,q)<1e-7:continue
    edge=[[p[k]+t*(q[k]-p[k])for k in(0,1)]for t in sp]
    delta=max(abs(a.common.height(r['plane_y_xz_m'],x)-a.common.height(s['plane_y_xz_m'],x))for x in edge)
    if delta>1e-7:out.append(dict(left=r['id'],right=s['id'],edge_xz_m=edge,maximum_height_error_m=delta))
 return out

def source_review():
 start=time.monotonic();assert a.sha(R04)==R04_SHA
 summary=json.loads((OLD/'private_profiles_summary_r02.json').read_bytes())
 selected={h for r in summary['groups']if r['status']=='HELD_PUBLIC_DEPENDENCY'for h in r['holding_ids']}
 req=[r for r in json.loads((OLD/'exact_public_reservations.json').read_bytes())['entries']if r['holding_id']in selected]
 # The B005 dry-side addendum is already included in exact_public_reservations.
 assert len(req)==17
 source=json.loads(R18.read_bytes())['records'];si=indexed(source)
 traffic=public_domain.records();ti=indexed(traffic)
 scene=json.loads(R04.read_bytes());ix=a.TriangleIndex(scene,[p for r in req for p in r['public_union_parts_xz_m']]);entries=[]
 for entry in req:
  requested=entry['public_union_parts_xz_m'];active=[]
  for p in requested:
   active.extend(q for i in ti.candidates(p)if(q:=a.clip(p,traffic[i]['polygon_xz_m'])))
  active=a.common.disjoint_union(active);outside=a.common.subtract(requested,active)
  regions=[]
  for p in active:
   for i in sorted(si.candidates(p)):
    s=source[i];q=a.clip(p,s['polygon_xz_m'])
    if q:regions.append(dict(id=entry['holding_id']+':CURRENT_R18:'+str(len(regions)),source_kind='sealed_r18_finite_plane',source_record_id=s['id'],source_triangle_index=s['source_triangle_index'],polygon_xz_m=q,plane_y_xz_m=s['plane_y_xz_m'],gradient=math.hypot(*s['plane_y_xz_m'][:2])))
  r18_gap=a.common.subtract(active,[r['polygon_xz_m']for r in regions]);retained_regions=[];retained_gap=[]
  for p in outside:
   parts=list(ix.covering(p));retained_gap.extend(a.common.subtract([p],[r['intersection_polygon_xz_m']for r in parts]))
   for s in parts:
    retained_regions.append(dict(id=entry['holding_id']+':CURRENT_R04:'+str(len(retained_regions)),source_kind='actual_retained_r04_top',source_material=s['material'],source_triangle_index=s['triangle_index'],source_triangle_sha256=s['source_triangle_sha256'],polygon_xz_m=s['intersection_polygon_xz_m'],plane_y_xz_m=s['plane_y_xz_m'],gradient=math.hypot(*s['plane_y_xz_m'][:2])))
  regions+=retained_regions
  inherited=seams(regions);steep=[r for r in regions if r['gradient']>.12+1e-7]
  gaps=area(r18_gap)+area(retained_gap)
  row=dict(holding_id=entry['holding_id'],public_road_id=entry['named_public_road_id'],profile_regions=regions,r18_uncovered_polygons_xz_m=r18_gap,retained_uncovered_polygons_xz_m=retained_gap,uncovered_area_m2=gaps,inherited_public_height_seams=inherited,inherited_public_steep_regions=steep,maximum_inherited_public_gradient=max((r['gradient']for r in regions),default=0),status='SOURCE_COVERAGE_READY_FOR_PRIVATE_BOUNDARY_SOLVE'if gaps<=1e-7 else'HELD_UNCOVERED_PUBLIC_OWNER',activation=False)
  entries.append(row);print(entry['holding_id'],row['status'],'gaps',gaps,'internal seams',len(inherited),'max grade',row['maximum_inherited_public_gradient'],flush=True)
 out=dict(base_scene=dict(path=str(R04.relative_to(a.ROOT)),sha256=R04_SHA),public_source=dict(path=str(R18.relative_to(a.ROOT)),sha256=a.sha(R18)),request_source=dict(path=str((OLD/'exact_public_reservations.json').relative_to(a.ROOT)),sha256=a.sha(OLD/'exact_public_reservations.json')),entries=entries,summary=dict(entries=len(entries),coverage_ready=sum(r['uncovered_area_m2']<=1e-7 for r in entries),seconds=time.monotonic()-start),policy='Historical public interior seams and grades remain recorded. Actual incident private-boundary constraints must pass separately. No public coordinate or existing road is modified.',activation=False)
 write(HERE/'actual_public_inputs_r01.json',out);print(out['summary'],flush=True)

def solve():
 inputs=json.loads((HERE/'actual_public_inputs_r01.json').read_bytes());entries={r['holding_id']:r for r in inputs['entries']};groups=json.loads((OLD/'shared_private_groups_r03.json').read_bytes())['groups'];outdir=HERE/'private_profiles';outdir.mkdir(exist_ok=True);rows=[]
 for group in groups:
  if not set(group['holding_ids'])&set(entries):continue
  assert all(h in entries for h in group['holding_ids'])
  path=outdir/(group['id'].replace(':','_')+'.json')
  if path.exists():row=json.loads(path.read_bytes())
  elif any(entries[h]['uncovered_area_m2']>1e-7 for h in group['holding_ids']):
   row=dict(id=group['id'],holding_ids=group['holding_ids'],status='HELD_UNCOVERED_PUBLIC_OWNER',uncovered_by_holding={h:entries[h]['uncovered_area_m2']for h in group['holding_ids']},activation=False);write(path,row)
  else:
   t=time.monotonic();regions=[];seen=set()
   for h in group['holding_ids']:
    for r in entries[h]['profile_regions']:
     k=a.canonical_sha([r['polygon_xz_m'],r['plane_y_xz_m']])
     if k not in seen:seen.add(k);regions.append(r)
   full=a.common.disjoint_union([p for h in group['source_holding_records']for p in h['external_route_polygons_xz_m']]);domains=a.common.subtract(full,[r['polygon_xz_m']for r in regions]);fixed=group['gate_fixed_regions']+regions;targets=group['gate_targets']
   target=lambda p:min(targets,key=lambda r:math.dist(p,r['point_xz_m']))['floor_y_m']
   try:res=profile_mesh.solve(domains,fixed,target,pitch=1.,seam_points=[p for r in regions for p in r['polygon_xz_m']])
   except Exception as e:res=dict(status='SOLVER_EXCEPTION_HOLD',type=type(e).__name__,message=str(e))
   row=dict(id=group['id'],holding_ids=group['holding_ids'],status=res['status'],result=res,private_domain_polygons_xz_m=domains,public_fixed_regions=regions,elapsed_s=time.monotonic()-t,activation=False);write(path,row)
  brief=dict(id=row['id'],holding_ids=row['holding_ids'],status=row['status'],maximum_gradient=row.get('result',{}).get('maximum_gradient'),conflict_count=len(row.get('result',{}).get('conflicts',[])),path=str(path.relative_to(a.ROOT)),sha256=a.sha(path));rows.append(brief);print(brief,flush=True)
 write(HERE/'private_boundary_summary_r01.json',dict(rows=rows,counts=dict(collections.Counter(r['status']for r in rows for _ in r['holding_ids'])),activation=False))
if __name__=='__main__':
 import sys
 {'sources':source_review,'solve':solve}[sys.argv[1]]()
