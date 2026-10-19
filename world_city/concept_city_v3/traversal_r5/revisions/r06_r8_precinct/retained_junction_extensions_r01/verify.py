"""Independent finite set/parity review of new outer-terminal handoff."""
import importlib.util,json,math,pathlib,sys,time
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('junction_build',H/'build.py');b=importlib.util.module_from_spec(sp);sp.loader.exec_module(b)
geo=b.geo;u=b.u

def area(ps):return sum(geo.polygon_area(p)for p in ps)
def difference(parts,cuts):
 idx=geo._SpatialIndex(8)
 for i,p in enumerate(cuts):idx.add(i,p)
 out=[]
 for poly in parts:
  rem=[poly]
  for i in idx.candidates(poly):rem=[p for q in rem for p in u.subtract(q,cuts[i])]
  out.extend(rem)
 return out

def main():
 start=time.monotonic();data=b.read(H/'junction_extensions.json');prior=b.read(b.B/'public_corridor_priorities_r01/priorities.json');inv=b.read(b.B/'primary_inventory/inventory.json');old=b.read(b.B/'fixed_interfaces_r18_r01/fixed_interfaces_complete.json');roads={r['id']:b.Road(r)for r in inv['roads']};repair=set(prior['minimum_public_ground_corridors']);repairparts=[p for rid in repair for p in roads[rid].polys];extensionparts=[p for r in data['extensions']for p in r['polygons_xz_m']];allparts=repairparts+extensionparts
 caps=[];spill=[];bad=[];coverage=[];errors=[]
 for r in data['endpoint_reconciliation_required']:
  road=roads[r['road_id']];p=road.ps[0 if r['endpoint']=='start'else-1];poly=b.ownership.circle(p,road.w/2);missing=difference([poly],repairparts);v=dict(r,original_end_cap_polygon_xz_m=poly,not_already_in_regeneration_polygons_xz_m=missing,not_already_in_regeneration_area_m2=area(missing),classification='ORIGINAL_FINITE_CAP_FULLY_INSIDE_EXISTING_REPAIR_UNION'if area(missing)<=1e-7 else'OUTER_CAP_HAS_RETAINED_BOUNDARY_REQUIRING_EXACT_PROFILE')
  caps.append(v)
 for r in data['extensions']:
  rem=difference(r['polygons_xz_m'],roads[r['road_id']].polys);v=dict(id=r['id'],canonical_footprint_spill_area_m2=area(rem));spill.append(v)
  if v['canonical_footprint_spill_area_m2']>1e-7:errors.append(v)
 for p in prior['full_width_shared_domains']:
  if not any(r['road_id']in p['roads']for r in data['extensions'])or p['a_is_regeneration_candidate']==p['b_is_regeneration_candidate']:continue
  rem=difference([q['polygon_xz_m']for q in p['raw_overlap_parts']],allparts);coverage.append(dict(roads=p['roads'],unowned_overlap_area_m2=area(rem)))
  if area(rem)>1e-7:errors.append(coverage[-1])
 passed=set(r['road_id']for r in data['extensions']);seen=set()
 for r in old['regions']:
  if r.get('kind')!='actual_retained_corridor_overlap'or math.hypot(*r['plane_y_xz_m'][:2])<=.12+1e-7:continue
  rid=next(k for k in r['roads']if k in passed);key=(rid,r['source']['material'],r['source']['triangle_index'])
  if key in seen:continue
  seen.add(key);tri=[[v[0],v[2]]for v in r['triangle_xyz_m']];inside=[p for q in roads[rid].polys if(p:=u.clean(geo.convex_intersection(tri,q)))];rem=difference(inside,allparts);bad.append(dict(road_id=rid,source=r['source'],source_grade=math.hypot(*r['plane_y_xz_m'][:2]),outside_expanded_repair_area_m2=area(rem)))
  if area(rem)>1e-7:errors.append(bad[-1])
 max_delta=0.
 for t in data['terminals']:
  pr=t['profile'];assert pr['valid']and not pr['uncovered_t_intervals']and not pr['incompatible_height_knots']
  for v in pr['knots_xyz_m']:
   point=[v[0],v[2]]
   for row in pr['pieces']:
    tri=[[q[0],q[2]]for q in row['source']['vertices_xyz_m']]
    # Source endpoint belongs to the exact cross-section interval.
    tval=((point[0]-pr['edge_xz_m'][0][0])*(pr['edge_xz_m'][1][0]-pr['edge_xz_m'][0][0])+(point[1]-pr['edge_xz_m'][0][1])*(pr['edge_xz_m'][1][1]-pr['edge_xz_m'][0][1]))/math.dist(*pr['edge_xz_m'])**2
    if row['t_interval'][0]-1e-9<=tval<=row['t_interval'][1]+1e-9:max_delta=max(max_delta,abs(v[1]-b.height(row['source'],point)))
 out=dict(status='PASS_BOUNDED_EXACT_TERMINALS_WITH_CAP_CLASSIFICATION'if not errors else'FAIL',input=b.ref(H/'junction_extensions.json'),source_scene_sha256=b.a.SCENE_SHA256,terminal_count=len(data['terminals']),exact_segment_count=len(data['segments']),max_fixed_knot_source_height_spread_m=max_delta,source_grade_max=max(t['profile']['max_source_triangle_grade']for t in data['terminals']),cap_classification=caps,canonical_footprint_checks=spill,shared_overlap_coverage=coverage,bad_source_face_extent_checks=bad,failures=errors,seconds=time.monotonic()-start)
 b.write('verification.json',out);print(json.dumps(dict(status=out['status'],report=b.ref(H/'verification.json'),terminals=len(data['terminals']),segments=len(data['segments']),cap_classes={c:sum(r['classification']==c for r in caps)for c in {r['classification']for r in caps}},max_delta=max_delta,errors=len(errors),seconds=out['seconds'])),flush=True)
if __name__=='__main__':main()
