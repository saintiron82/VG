"""Independent artifact audit; no route authoring or scene mutation."""
import sys
sys.dont_write_bytecode=True
import collections,hashlib,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[6];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as geo

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def canonical(v):return hashlib.sha256(json.dumps(v,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def projected(t):return [[v[0],v[2]]for v in t]
def normal_y(t):
 a,b,c=t;return (b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2])
def plane(t):
 a,b,c=t;dx,dz=b[0]-a[0],b[2]-a[2];ex,ez=c[0]-a[0],c[2]-a[2];det=dx*ez-dz*ex;gx=((b[1]-a[1])*ez-dz*(c[1]-a[1]))/det;gz=(dx*(c[1]-a[1])-(b[1]-a[1])*ex)/det;return gx,gz,a[1]-gx*a[0]-gz*a[2]
def main():
 d=read(HERE/'level_profile_handoff.json');checks=[]
 def check(name,value,detail=None):
  checks.append(dict(name=name,passed=bool(value),detail=detail));assert value,(name,detail)
 check('all_bound_input_hashes_match',all(sha(ROOT/r['path'])==r['sha256']for r in d['input_bindings']),len(d['input_bindings']))
 checkpoint=read(HERE/'r6_prior_checkpoint_record.json');check('all_eight_prior_checkpoint_files_unchanged',all(sha(ROOT/r['path'])==r['sha256']for r in checkpoint['files']))
 scene=read(ROOT/d['source_scene']['path']);check('corrected_r6_scene_exact',sha(ROOT/d['source_scene']['path'])=='6e441b9ca417db63dccbb0bbccd48aa59e6a2a62079cdeeb3e5440d78f654844')
 regions={r['id']:r for r in d['regions']};by_region=collections.defaultdict(list);max_grade=0.;min_normal=math.inf;source_ids=set();max_plane_error=0.
 for t in d['triangles']:
  xyz=t['vertices_xyz_m'];n=normal_y(xyz);min_normal=min(min_normal,n);check_value=n>1e-10
  assert check_value,t['id'];p=plane(xyz);max_grade=max(max_grade,math.hypot(*p[:2]));r=t['source_r6'];source=scene['surfaces'][r['material']][r['triangle_index']*3:r['triangle_index']*3+3]
  assert canonical(source)==r['source_triangle_sha256'] and source==r['vertices_xyz_m'],t['id']
  sp=plane(source);max_plane_error=max(max_plane_error,max(abs(v[1]-(sp[0]*v[0]+sp[1]*v[2]+sp[2]))for v in xyz));by_region[t['region_id']].append(t)
  assert all(geo.point_in_convex_polygon(v,regions[t['region_id']]['polygon_xz_m'],1e-7)for v in projected(xyz)),t['id']
  source_ids.add((r['material'],r['triangle_index']))
 check('every_emitted_top_is_positive_Y',min_normal>1e-10,min_normal)
 check('actual_emitted_gradients_at_most_12_percent',max_grade<=.12000001,max_grade)
 check('every_triangle_retains_exact_actual_r6_source_plane',max_plane_error<1e-8,max_plane_error)
 overlap=0.;regions_list=list(regions.values())
 for i,r in enumerate(regions_list):
  for q in regions_list[i+1:]:overlap+=geo.polygon_area(geo.convex_intersection(r['polygon_xz_m'],q['polygon_xz_m']))
 check('region_pairwise_overlap_is_zero',overlap<1e-7,overlap)
 triangle_overlap=0.;max_error=0.
 for rid,region in regions.items():
  ts=by_region[rid];ar=sum(normal_y(t['vertices_xyz_m'])/2 for t in ts);max_error=max(max_error,abs(ar-geo.polygon_area(region['polygon_xz_m'])))
  for i,t in enumerate(ts):
   for q in ts[i+1:]:triangle_overlap+=geo.polygon_area(geo.convex_intersection(t['polygon_xz_m'],q['polygon_xz_m']))
 check('triangle_pairwise_overlap_is_zero',triangle_overlap<1e-7,triangle_overlap)
 check('each_full_region_is_covered_without_holes',max_error<1e-7,max_error)
 water=[]
 vs=scene['surfaces'].get('water',[])
 for i in range(0,len(vs),3):
  p=projected(vs[i:i+3])
  for r in regions_list:
   q=geo.convex_intersection(p,r['polygon_xz_m']);a=geo.polygon_area(q)
   if a>1e-8:water.append(dict(source_water_triangle_index=i//3,region_id=r['id'],overlap_m2=a))
 check('no_water_overlap',not water,water)
 check('no_protected_or_native_owner_conflicts',not d['protected_owner_conflicts'])
 sides=read(ROOT/d['retained_side_obstruction_audit']['path']);check('side_audit_has_no_above_floor_obstruction',not sides['above_floor_obstructions'],dict(examined=sides['examined_nearby_side_triangles'],intersecting=len(sides['intersections'])))
 check('no_old_side_removals_required',not sides['old_side_removals_required']and not d['affected_old_side_masks'])
 for r,p in zip(d['routes'],d['full_width_profiles']):
  w=r['width_m'];check(r['id']+':same_actual_width',w in(2.,3.5));edge=r['terminal_full_width_edge_xz_m'];check(r['id']+':exact_full_width_terminal',abs(math.dist(*edge)-w)<1e-8)
  profile=p['public_road_terminal'];check(r['id']+':complete_public_road_terminal_coverage',abs(sum(x['length_m']for x in profile['pieces']if x['source']['material']=='road')-w)<1e-7)
  check(r['id']+':single_valued_frozen_walking_join',not profile['incompatible_height_knots']and not profile['grade_violations'])
  gate=r['gate']['position_xz_m'];line=r['polyline_xz_m']
  check(r['id']+':unchanged_source_gate',any(abs(math.dist(a,gate)+math.dist(gate,b)-math.dist(a,b))<1e-8 for a,b in zip(line,line[1:])))
  cut=r['unchanged_prefix_polyline_xz_m'][-1];check(r['id']+':unchanged_inner_cut',cut==r['revised_terminal_polyline_xz_m'][0])
 check('every_boundary_seam_is_exact_source_and_same_height',all(r['inside_vertices_xyz_m']==r['outside_vertices_xyz_m']and max(abs(v[1]-2.5)for v in r['inside_vertices_xyz_m'])<1e-8 for r in d['boundary_seam_ledger']))
 out=dict(schema='riverstone.r16_level_lane_independent_artifact_audit.v1',status='PASS_SOURCE_ARTIFACT_ONLY_PENDING_PARENT_SCENE_AND_CAPSULE_AUDIT',artifact_sha256=sha(HERE/'level_profile_handoff.json'),test_code_sha256=sha(Path(__file__)),check_count=len(checks),checks=checks,source_r6_triangle_count=len(source_ids),emitted_triangle_count=len(d['triangles']),source_scene_sha256=d['base_scene_sha256'],scene_activated=False)
 (HERE/'independent_artifact_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'],len(checks),'checks',flush=True)
if __name__=='__main__':main()
