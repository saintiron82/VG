"""R16 source-only finite ownership plan. Final R6 triangle binding is required.

No source or scene is mutated on import. Native footing masks are exact cached
geometry; courts repaint existing planes rather than add a second floor.
"""
from __future__ import annotations
import copy,hashlib,json,math
from pathlib import Path
from functools import lru_cache
from world_city.runtime_city.checks import placement as geo

HERE=Path(__file__).resolve().parent
CITY=HERE.parents[2];ROOT=HERE.parents[4]
SOURCE=CITY/'assemblies/ordinary/registered/working_ranges_r01'
EXPECTED={
 'resolved_placements.json':'57577354dd51455f49b836e5e65e628ec9d0988888647d3f5f42e034dd9aba07',
 'terrain_handoff.json':'ddf332fd05d588a75b8a0d55aa286725a1564b9b302c9b0e00559f5c39cdd848',
 'native_geometry.json':'90290ba6e3199086ca97918ee866175d99337fd2a1242ee45cf87f1e0d9b8c71',
 'selection.json':'a4906b631996483c2331bcbf1f866291c0e2321d795aa95f6d6bdf77da3707a4',
 'court_plan.json':'e72136ec74860225b21ed49afea5130c8ef8201bb92f2befe0acff7628efdb10',
 'access_handoff.json':'48edcd3b38508ac61fbe930a6f5e38d736ac585f352ce6aea0ad1b2867ad3077',
 'evidence/frozen_r5_local_triangles.json':'2aee3bf5be23985bb969019d7e0b9d096e6c90f1cadf887e48f2328eb9ff1dec'}
MIN_AREA=1e-10

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
@lru_cache(None)
def read(name):
 p=SOURCE/name
 if sha(p)!=EXPECTED[name]:raise ValueError('Changed sealed working-range input: '+str(p))
 return json.loads(p.read_bytes())

def clean(poly):
 out=[]
 for p in poly:
  if not out or math.dist(p,out[-1])>1e-9:out.append(list(p))
 while len(out)>1 and math.dist(out[0],out[-1])<=1e-9:out.pop()
 return out if len(out)>=3 and geo.polygon_area(out)>MIN_AREA else None

def subtract(polygons,masks):
 out=list(polygons)
 for m in masks:
  nxt=[]
  for p in out:
   if clean(geo.convex_intersection(p,m)):nxt.extend(q for x in geo.convex_difference(p,m) if(q:=clean(x)))
   else:nxt.append(p)
  out=nxt
  if not out:break
 return out

def disjoint_union(polygons):
 out=[];index=geo._SpatialIndex(8)
 for poly in polygons:
  p=clean(poly)
  if not p:continue
  cuts=[out[i] for i in sorted(index.candidates(p))]
  for q in subtract([p],cuts):index.add(len(out),q);out.append(q)
 return out

def plane(tri):
 a,b,c=tri;dx1=b[0]-a[0];dz1=b[2]-a[2];dx2=c[0]-a[0];dz2=c[2]-a[2];det=dx1*dz2-dx2*dz1
 if abs(det)<1e-14:raise ValueError('Vertical source triangle')
 gx=((b[1]-a[1])*dz2-(c[1]-a[1])*dz1)/det;gz=(dx1*(c[1]-a[1])-dx2*(b[1]-a[1]))/det
 return [gx,gz,a[1]-gx*a[0]-gz*a[2]]
def height(coeff,p):return coeff[0]*p[0]+coeff[1]*p[1]+coeff[2]

@lru_cache(None)
def native_holes():
 out=[]
 for owner in read('terrain_handoff.json')['native_foundation_owners']:
  for i,p in enumerate(owner['polygons_xz_m']):
   out.append(dict(id=owner['id']+':'+str(i),kind='exact_native_footing_hole',parcel_id=owner['parcel_id'],holding_id=owner['holding_id'],polygon_xz_m=p,render_land=False,native_bottom_y_m=owner['native_bottom_y_m'],finished_threshold_y_m=owner['native_entry_threshold_y_m'],existing_ground_y_m=owner['existing_ground_y_m'],native_render_sha256=owner['render_sha256'],native_mask_index=i,additional_support_required=False,activation=False))
 return out

@lru_cache(None)
def court_regions():
 out=[]
 for court in read('terrain_handoff.json')['source_courts']:
  # Native floors take precedence, though the source screening expects no overlap.
  for i,p in enumerate(subtract([court['polygon_xz_m']],[r['polygon_xz_m'] for r in native_holes()])):
   out.append(dict(id=court['id']+':MATERIAL:'+str(i),kind='existing_plane_court_material',holding_id=court['holding_id'],polygon_xz_m=p,material='ground_stone',expected_existing_y_m=2.5,height_policy='Barycentrically retain each actual R6 source triangle plane; no added floor or holding-wide leveling.',native_paving_status='Unimplemented; terrain material preview only.',activation=False))
 return out

@lru_cache(None)
def walk_reservations():
 h=read('terrain_handoff.json');out=[]
 sources=[(r['id'],r['holding_id'],r['width_m'],r['ribbon_and_join_polygons_xz_m'],'actual_native_door_route') for r in h['internal_walkspaces']]
 sources += [(r['id']+':COURT_LINK',r['holding_id'],r['access_link']['width_m'],r['access_link']['ribbon_and_join_polygons_xz_m'],'court_route') for r in h['source_courts']]
 for rid,holding,width,polys,kind in sources:
  for i,p in enumerate(disjoint_union(polys)):
   out.append(dict(id=rid+':RESERVE:'+str(i),route_id=rid,holding_id=holding,kind=kind,width_m=width,polygon_xz_m=p,finished_y_m=2.5,policy='Protect existing actual ground and cached threshold surfaces; do not add a duplicate ribbon.',activation=False))
 return out

@lru_cache(None)
def terminal_domains():
 out=[]
 for hold in read('terrain_handoff.json')['terminal_grade_holds']:
  for i,p in enumerate(disjoint_union(hold['bounded_review_polygons_xz_m'])):
   out.append(dict(id=hold['id']+':'+str(i),route_id=hold['route_id'],holding_id=hold['holding_id'],kind='pending_public_transition',width_m=hold['review_width_m'],polygon_xz_m=p,grade_limit=.12,profile_status='Held until one continuous finite field passes actual R6 boundary and triangle checks.',activation=False))
 return out

def all_candidate_ledger():
 rows=copy.deepcopy(read('selection.json')['all_candidate_status']);selected=set(read('selection.json')['selected_parcel_ids'])
 for r in rows:
  r['r16_stage']='native_footing_and_access_source_candidate' if r['parcel_id'] in selected else 'deferred_unimplemented_preserved'
  r['r16_active']=False
 if len(rows)!=26 or len({r['parcel_id'] for r in rows})!=26:raise ValueError('All26 candidate ledger changed')
 return rows

class FrozenLocal:
 def __init__(self):
  self.data=read('evidence/frozen_r5_local_triangles.json');self.rows=[];self.index=geo._SpatialIndex(8)
  for i,r in enumerate(self.data['records']):
   tri=r['vertices_m'];poly=[[p[0],p[2]] for p in tri];row=dict(r,polygon_xz_m=poly,plane_y_xz_m=plane(tri));self.index.add(i,poly);self.rows.append(row)
 def cover(self,poly):
  parts=[]
  for i in sorted(self.index.candidates(poly)):
   r=self.rows[i];q=clean(geo.convex_intersection(poly,r['polygon_xz_m']))
   if q:parts.append(dict(material=r['material'],source_triangle_index=r['source_triangle_index'],polygon_xz_m=q,source_vertices_xyz_m=r['vertices_m'],min_y_m=min(height(r['plane_y_xz_m'],p) for p in q),max_y_m=max(height(r['plane_y_xz_m'],p) for p in q),plane_y_xz_m=r['plane_y_xz_m']))
  return parts

def bounded_source_audit():
 frozen=FrozenLocal();ledger=[]
 for owner in native_holes()+court_regions():
  poly=owner['polygon_xz_m'];parts=frozen.cover(poly);area=geo.polygon_area(poly);actual=sum(geo.polygon_area(r['polygon_xz_m']) for r in parts)
  remaining=subtract([poly],[r['polygon_xz_m'] for r in parts]);gap=sum(geo.polygon_area(p) for p in remaining)
  overlap=0.
  for i,p in enumerate(parts):
   for q in parts[i+1:]:overlap+=geo.polygon_area(geo.convex_intersection(p['polygon_xz_m'],q['polygon_xz_m']))
  values=[v for r in parts for v in (r['min_y_m'],r['max_y_m'])]
  ledger.append(dict(owner_id=owner['id'],area_m2=area,covered_area_m2=actual,missing_area_m2=gap,overlap_area_m2=overlap,min_y_m=min(values),max_y_m=max(values),height_delta_from_2_5_m=max(abs(v-2.5) for v in values),source_parts=parts))
 overlap=[];td=terminal_domains()
 for i,r in enumerate(td):
  for q in td[i+1:]:
   if r['route_id']==q['route_id']:continue
   p=clean(geo.convex_intersection(r['polygon_xz_m'],q['polygon_xz_m']))
   if p:overlap.append(dict(route_ids=[r['route_id'],q['route_id']],polygon_xz_m=p,area_m2=geo.polygon_area(p),policy='One shared height owner required; never independently append both route surfaces.'))
 return dict(status='PROVISIONAL_R5_SOURCE_PROOF_ONLY',source_scene=frozen.data['scene'],owner_checks=ledger,terminal_intersections=overlap,terminal_overlap_m2=sum(x['area_m2'] for x in overlap),r6_scene_binding=None)

def build_contract():
 h=read('terrain_handoff.json');return dict(schema='riverstone.r16_working_ranges.source_plan.v1',status='INACTIVE_SOURCE_MATH_PENDING_R6_SCENE_HASH',active=False,r6_scene_binding=None,input_refs=[dict(path=str((SOURCE/k).relative_to(ROOT)),sha256=v) for k,v in EXPECTED.items()],all26_candidate_ledger=all_candidate_ledger(),native_footing_holes=native_holes(),court_material_regions=court_regions(),retained_walk_reservations=walk_reservations(),terminal_grade_review_domains=terminal_domains(),terminal_grade_holds=copy.deepcopy(h['terminal_grade_holds']),source_thresholds=copy.deepcopy(h['exact_native_door_leaves']),retired_native_ids=[],retired_path_ids=[],whole_holding_pad_domains=[],additional_support_compile_budget_cells=0,scene_patch_policy=dict(base='Exact upcoming R6 scene bytes, not stale R5 indices.',old_triangles='Clip only finite accepted native holes/court paint/public profiles; preserve every unaffected triangle value and order.',court_height='Same original triangle plane, no duplicate top.',native_bearing='Existing +2.5 terrain remains solid below exact +2.0 native underside.',public_profiles='Actual clipped triangle gradients <=12%; full-width fixed seams; no hidden steps in cart lane.',water='Finite wet domains and underlying beds retained.'),limits=['R5 evidence is provisional and cannot activate R6.','No native court paving, gate leaves, interiors or capsule validation is claimed.','All22 other candidate ranges stay unimplemented.'])

if __name__=='__main__':
 for name,data in [('source_plan.json',build_contract()),('source_ground_audit.json',bounded_source_audit())]:
  p=HERE/name
  if p.exists():raise SystemExit('Refusing to overwrite source candidate '+name)
  p.write_text(json.dumps(data,separators=(',',':'))+'\n');print(name,sha(p),flush=True)
