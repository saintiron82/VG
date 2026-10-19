"""R17: exact frozen-R7 terrain bands and district-scale finite preflight.

This is a read-only source/query layer. It neither places assets nor writes a
scene. All outputs bind the corrected R7 byte hash. Native holes remain holes;
missing rendered top is never silently treated as level support.
"""
from __future__ import annotations
import hashlib,json,math,time,argparse
from pathlib import Path
from collections import defaultdict
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.registered_source.geometry import triangulate
from ..r16_working_ranges import author as common
from ..r16_working_ranges.frozen_r6 import normal_y,fan_upward

HERE=Path(__file__).resolve().parent;CITY=HERE.parents[2];ROOT=HERE.parents[4]
SCENE_PATH=CITY/'evidence/visual_registered_common_r7_palette_r01/scene.json'
SCENE_SHA256='1429ae51b7c72b12940dcf0dd7e12c2684cab95f81735d228bba64dc819317c1'
PLAN_PATH=CITY/'registered_source/plan.json'
PUBLIC_MATERIALS={'road','alley'}
BAND_TOLERANCE_M=1e-7
AREA_EPSILON_M2=1e-8
PRIORITY_BLOCKS=['BLOCK_015','BLOCK_007','BLOCK_013']

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical_sha(data):return hashlib.sha256(json.dumps(data,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def load_scene():
 b=SCENE_PATH.read_bytes()
 if hashlib.sha256(b).hexdigest()!=SCENE_SHA256:raise ValueError('Changed corrected R7 scene')
 return json.loads(b)
def bounds(poly):return [min(p[0]for p in poly),min(p[1]for p in poly),max(p[0]for p in poly),max(p[1]for p in poly)]
def intersects(a,b):return a[0]<=b[2]+1e-10 and a[2]>=b[0]-1e-10 and a[1]<=b[3]+1e-10 and a[3]>=b[1]-1e-10
def clip(a,b):return common.clean(geo.convex_intersection(a,b))
def source_rows(scene):
 for material,vs in scene['surfaces'].items():
  if material in ('water','bank'):continue
  for j in range(0,len(vs),3):
   t=vs[j:j+3]
   if normal_y(t)<=1e-10:continue
   p=[[v[0],v[2]]for v in t]
   yield material,j//3,t,p

class TriangleIndex:
 """Index only one district's actual rendered tops. Build once per batch."""
 def __init__(self,scene,windows):
  self.rows=[];self.index=geo._SpatialIndex(16);self.candidate_tests=0
  boxes=[bounds(p)for p in windows];wi=geo._SpatialIndex(32)
  for i,p in enumerate(windows):wi.add(i,p)
  for m,j,t,p in source_rows(scene):
   bb=bounds(p)
   if not any(intersects(bb,boxes[i])for i in wi.candidates(p)):continue
   row=dict(material=m,triangle_index=j,vertices_xyz_m=t,polygon_xz_m=p,plane_y_xz_m=common.plane(t),source_triangle_sha256=canonical_sha(t))
   self.index.add(len(self.rows),p);self.rows.append(row)
 def covering(self,poly):
  for i in self.index.candidates(poly):
   self.candidate_tests+=1;r=self.rows[i];p=clip(poly,r['polygon_xz_m'])
   if p and geo.polygon_area(p)>AREA_EPSILON_M2:yield dict(r,intersection_polygon_xz_m=p)

def audit_polygon(index,polygon,expected_floor_y_m=None,grade_limit=.12):
 """Exact plane extrema/full-triangle grade plus finite set coverage.

Existing native surfaces need a separate supplied cache mask. A ground hole is
reported as missing, never filled from an analytic height guess.
"""
 pieces=[]
 for part in triangulate(polygon):pieces.extend(index.covering(part))
 covers=[r['intersection_polygon_xz_m']for r in pieces]
 remaining=common.subtract(triangulate(polygon),covers)
 gap=sum(geo.polygon_area(p)for p in remaining)
 rows=[]
 for r in pieces:
  p=r['intersection_polygon_xz_m'];plane=r['plane_y_xz_m'];ys=[common.height(plane,q)for q in p]
  rows.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],polygon_xz_m=p,plane_y_xz_m=plane,area_m2=geo.polygon_area(p),min_y_m=min(ys),max_y_m=max(ys),actual_triangle_grade=math.hypot(*plane[:2])))
 area=geo.polygon_area(polygon);covered=sum(r['area_m2']for r in rows)
 max_delta=max((max(abs(r['min_y_m']-expected_floor_y_m),abs(r['max_y_m']-expected_floor_y_m))for r in rows),default=0)if expected_floor_y_m is not None else None
 max_grade=max((r['actual_triangle_grade']for r in rows),default=0)
 return dict(area_m2=area,covered_area_m2=covered,missing_area_m2=gap,excess_area_m2=max(0,covered-area+gap),max_floor_delta_m=max_delta,max_actual_triangle_grade=max_grade,passes_existing_surface=gap<=1e-7 and covered<=area+1e-7 and max_grade<=grade_limit+1e-9 and(max_delta is None or max_delta<=BAND_TOLERANCE_M),source_pieces=rows,uncovered_polygons_xz_m=remaining)

def preflight_batch(scene,batch):
 """Input finite proposals, emit per-parcel findings without applying changes.

Required batch: base_scene_sha256, parcels[] each {id, floor_y_m,
 footing_polygons_xz_m, walk_polygons_xz_m, court_polygons_xz_m}; optional
 protected_regions[] {id,kind,polygon_xz_m}. Full ribbon polygons, including
 joins/caps, are mandatory; a centerline alone is insufficient.
"""
 if batch['base_scene_sha256']!=SCENE_SHA256:raise ValueError('Stale district batch')
 parcels=batch['parcels'];windows=[p for r in parcels for key in('footing_polygons_xz_m','walk_polygons_xz_m','court_polygons_xz_m')for p in r.get(key,[])]
 index=TriangleIndex(scene,windows);out=[]
 protected=batch.get('protected_regions',[])
 for r in parcels:
  checks=[];conflicts=[]
  for key in('footing_polygons_xz_m','walk_polygons_xz_m','court_polygons_xz_m'):
   for i,p in enumerate(r.get(key,[])):
    result=audit_polygon(index,p,r['floor_y_m']);result.update(kind=key,polygon_index=i);checks.append(result)
    for owner in protected:
     # Public walking overlap is a seam proposal, never automatic rejection;
     # footings/courts may not occupy water/native/traffic reservations.
     if key=='walk_polygons_xz_m'and owner['kind']=='public_lane':continue
     for a in triangulate(p):
      for b in triangulate(owner['polygon_xz_m']):
       q=clip(a,b)
       if q and geo.polygon_area(q)>AREA_EPSILON_M2:conflicts.append(dict(owner_id=owner['id'],kind=key,polygon_xz_m=q,area_m2=geo.polygon_area(q)))
  out.append(dict(parcel_id=r['id'],status='EXISTING_LEVEL_SURFACE_CANDIDATE'if checks and all(q['passes_existing_surface']for q in checks)and not conflicts else'REQUIRES_FINITE_REPLAN_OR_RESTORATION',checks=checks,protected_conflicts=conflicts))
 return dict(schema='riverstone.r17.batch_preflight.v1',base_scene_sha256=SCENE_SHA256,parcel_count=len(out),indexed_source_triangles=len(index.rows),triangle_candidate_tests=index.candidate_tests,parcels=out,activation=False,native_volume_and_capsule_checks='Still required before promotion')

def terrain_bands(scene,plan):
 started=time.monotonic();blockparts=[];bi=geo._SpatialIndex(32);states={}; exact=[]
 for block in plan['blocks']:
  parts=triangulate(block['polygon_xz_m']);total=sum(geo.polygon_area(p)for p in parts)
  if abs(total-geo.polygon_area(block['polygon_xz_m']))>1e-5:raise ValueError('Incomplete block triangulation '+block['id'])
  states[block['id']]=dict(block_id=block['id'],gross_area_m2=total,bounds_xz_m=bounds(block['polygon_xz_m']),flat_ground_bands=defaultdict(float),flat_public_bands=defaultdict(float),sloped_ground_area_m2=0.,sloped_public_area_m2=0.,above_12_percent_area_m2=0.,rendered_top_area_m2=0.,source_piece_count=0)
  for p in parts:
   bi.add(len(blockparts),p);blockparts.append((block['id'],p,bounds(p)))
 tested=0;clips=0
 for material,j,t,p in source_rows(scene):
  bb=bounds(p);ids=bi.candidates(p)
  if not ids:continue
  ys=[v[1]for v in t];flat=max(ys)-min(ys)<=BAND_TOLERANCE_M;plane=None
  for i in ids:
   bid,bp,box=blockparts[i]
   if not intersects(bb,box):continue
   tested+=1;q=clip(p,bp)
   if not q:continue
   area=geo.polygon_area(q)
   if area<=AREA_EPSILON_M2:continue
   clips+=1;s=states[bid];s['rendered_top_area_m2']+=area;s['source_piece_count']+=1
   if flat:
    y=round(sum(ys)/3,7);kind='flat_public_bands'if material in PUBLIC_MATERIALS else'flat_ground_bands';s[kind][str(y)]+=area
    if bid in PRIORITY_BLOCKS and material not in PUBLIC_MATERIALS and y in (1.,2.2,2.5,4.):
     exact.append(dict(block_id=bid,floor_y_m=y,material=material,triangle_index=j,polygon_xz_m=q))
   else:
    if plane is None:plane=common.plane(t)
    grade=math.hypot(*plane[:2]);s['sloped_public_area_m2'if material in PUBLIC_MATERIALS else'sloped_ground_area_m2']+=area
    if grade>.12+1e-7:s['above_12_percent_area_m2']+=area
 for s in states.values():
  for key in('flat_ground_bands','flat_public_bands'):s[key]=[dict(floor_y_m=float(y),area_m2=area)for y,area in sorted(s[key].items(),key=lambda x:-x[1])]
  s['not_rendered_top_area_m2']=s['gross_area_m2']-s['rendered_top_area_m2']
  s['interpretation']='Measured actual terrain tops only. Native holes, wet domains and protected owners require separate subtraction; this is not developable land area.'
 return dict(schema='riverstone.r17.exact_terrain_bands.v1',base_scene_sha256=SCENE_SHA256,source_plan_sha256=sha(PLAN_PATH),blocks=list(states.values()),priority_exact_band_regions=exact,measurements=dict(elapsed_seconds=time.monotonic()-started,convex_clip_tests=tested,positive_pieces=clips),status='SOURCE_SCREENING_NOT_PLACEMENT_APPROVAL')

def build_contract(report):
 return dict(schema='riverstone.r17.district_batch_contract.v1',status='SOURCE_SCREENING_READY_PENDING_PLANNING_CELLS',base_scene=dict(path=str(SCENE_PATH.relative_to(ROOT)),sha256=SCENE_SHA256),source_plan=dict(path=str(PLAN_PATH.relative_to(ROOT)),sha256=sha(PLAN_PATH)),priority_blocks=PRIORITY_BLOCKS,terrain_report=dict(path=str((HERE/'terrain_bands.json').relative_to(ROOT)),sha256=sha(HERE/'terrain_bands.json')),workflow=['One actual scene index per district; shared cached range families grouped by finished-floor band.','Planner supplies exact disjoint parcels, usable courts, complete 2m walking /3.5m service ribbons and >=4m canal reservation.','Subtract current native footprints/water/traffic and accepted private reservations before filling parcels. Retire only explicit old IDs and restore their old finite holes/doors with the same district patch.','Validate exact native footing bottom/threshold datum and all full-width route pieces in batches. Level-band reuse requires zero source height excursion; nonlevel profiles remain separate bounded candidates.','Native holes replace terrain tops only at actual occupied sections. Roof/eave bounds are collision reservations, never floor masks. Courts/material regions repaint existing triangles once.','Compose interacting source-index edits geometrically once; conflicting index edits cannot be applied sequentially. Preserve all unaffected triangle values/order.','Every new top is +Y; coverage, overlap, side/retaining, full-triangle grade and fixed seams are producer gates. Actual controller/visual review follows integration.'],batch_limits=dict(default_block_ids_per_patch=3,default_parcel_count=80,preflight_chunk_parcels=25,max_public_grade=.12,compile_budget_current_cells=0),measurement=report['measurements'],activation=False)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--scan',action='store_true');args=parser.parse_args()
 if args.scan:
  out=HERE/'terrain_bands.json'
  if out.exists():raise SystemExit('Refusing to overwrite measured terrain bands')
  report=terrain_bands(load_scene(),json.loads(PLAN_PATH.read_bytes()));out.write_text(json.dumps(report,separators=(',',':'))+'\n')
  (HERE/'contract.json').write_text(json.dumps(build_contract(report),separators=(',',':'))+'\n')
  print(json.dumps(dict(report_sha256=sha(out),measurement=report['measurements'],blocks=[dict(id=s['block_id'],ground=s['flat_ground_bands'][:3],sloped=s['sloped_ground_area_m2'])for s in report['blocks']]),indent=2))
