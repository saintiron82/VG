"""Compose two moved full-width routes on unchanged exact corrected-R6 planes.

Shared convex clipping and the registered upward-fan rule only. No terrain
export, native compile, scene mutation, interpolated blend, or implicit steps.
"""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[6];sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT))
from find_level_approaches import s,ribbons,audit
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import frozen_r6 as f
import json,math,hashlib,collections

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return dict(path=str(Path(p).relative_to(ROOT)),sha256=sha(p))
def read(p):return json.loads(Path(p).read_text())
def write(n,d):(HERE/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def area(ps):return sum(s.a.geo.polygon_area(p)for p in ps)
def prefix_to_cut(line,cut):
 out=[]
 for p,q in zip(line,line[1:]):
  out.append(p)
  if abs(math.dist(p,cut)+math.dist(cut,q)-math.dist(p,q))<1e-7:return out+[cut]
 raise ValueError('Cut outside original route')
def source_ref(r):return {k:r[k]for k in('material','triangle_index','source_triangle_sha256','vertices_xyz_m','plane_y_xz_m')}
def intersections(ps,qs):
 return [p for x in ps for y in qs if(p:=s.a.polygon(s.a.geo.convex_intersection(x,y)))]
def clip_side_xyz(tri,mask):
 """Clip XYZ to convex XZ halfplanes, retaining zero-projection vertical faces."""
 out=[list(v)for v in tri];sign=1 if s.a.geo.signed_polygon_area(mask)>0 else -1
 for a,b in zip(mask,mask[1:]+mask[:1]):
  def distance(p):return sign*((b[0]-a[0])*(p[2]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
  src=out;out=[]
  if not src:break
  for p,q in zip(src,src[1:]+src[:1]):
   dp,dq=distance(p),distance(q);ip,iq=dp>=-1e-9,dq>=-1e-9
   if ip:out.append(p)
   if ip!=iq:
    t=dp/(dp-dq);out.append([p[k]+t*(q[k]-p[k])for k in range(3)])
 return out
def side_audit(scene,ps):
 box=s.bounds(ps);hits=[];blocked=[];examined=0
 for material,vs in scene['surfaces'].items():
  for j in range(0,len(vs),3):
   t=vs[j:j+3]
   if material!='bank' and f.normal_y(t)>1e-10:continue
   xx=[p[0]for p in t];zz=[p[2]for p in t]
   if max(xx)<box[0] or min(xx)>box[2]or max(zz)<box[1]or min(zz)>box[3]:continue
   examined+=1
   clipped=[q for p in ps if(q:=clip_side_xyz(t,p))]
   if not clipped:continue
   maxy=max(p[1]for q in clipped for p in q);row=dict(material=material,triangle_index=j//3,source_triangle_sha256=f.canonical_sha(t),source_vertices_xyz_m=t,clipped_vertices_xyz_m=clipped,maximum_intersection_y_m=maxy,above_floor_m=max(0.,maxy-2.5),zero_projected_area=abs(f.normal_y(t))<=1e-10)
   hits.append(row)
   if maxy>2.5000001:blocked.append(row)
 return dict(examined_nearby_side_triangles=examined,intersections=hits,above_floor_obstructions=blocked,old_side_removals_required=bool(blocked),method='XYZ halfplane clipping against every convex walking region, preserving zero-area XZ side projections. Any clipped point above +2.5 m is an obstruction.')
def main():
 scene=f.load_scene();c0=read(HERE/'level_approach_candidates.json')[0]['best_candidates'][0];c1=read(HERE/'gate_preserving_level_candidates.json')['best_candidates'][0];cs=[c0,c1]
 routes=[];masks=[]
 for i,(h,c)in enumerate(zip(s.H['terminal_grade_holds'],cs)):
  old=next(r for r in s.A['external_routes']if r['id']==h['route_id']);tail=c['line_xz_m'];pfx=prefix_to_cut(old['polyline_xz_m'],tail[0]);full=pfx[:-1]+tail;ps=s.disjoint(ribbons(tail,old['width_m']));masks.append(ps)
  inner=s.end_edge(tail,old['width_m'],True);terminal=s.end_edge(tail,old['width_m']);road_owner=s.a.base.owner_at(*tail[-1]);assert road_owner.get('road_id')=='LOWER_CONTOUR',(i,road_owner)
  if i==1:assert old['gate']['position_xz_m'] in tail
  routes.append(dict(id=old['id'],replaces_source_route_id=old['id'],width_m=old['width_m'],polyline_xz_m=full,revised_terminal_polyline_xz_m=tail,unchanged_prefix_polyline_xz_m=pfx,original_held_tail_length_m=12.,revised_tail_length_m=c['length_m'],tail_length_change_m=c['length_m']-12.,terminal_moved_from_xz_m=h['polyline_xz_m'][-1],terminal_moved_to_xz_m=tail[-1],gate=old['gate'],gate_preserved=True,inner_full_width_edge_xz_m=inner,terminal_full_width_edge_xz_m=terminal,source_public_owner_id=road_owner['owner_id'],source_public_road_id=road_owner['road_id'],candidate_union_area_m2=area(ps),original_terminal_union_area_m2=area(s.disjoint(h['bounded_review_polygons_xz_m'])),unimplemented_gate_status=old['gate_status']))
 shared=intersections(masks[0],masks[1]);only0=s.a.subtract(masks[0],masks[1]);only1=s.a.subtract(masks[1],masks[0]);regions=[]
 for group,ids in [(only0,[routes[0]['id']]),(only1,[routes[1]['id']]),(shared,[r['id']for r in routes])]:
  for p in group:regions.append(dict(id=f'R16_MOVED_LANES:REGION:{len(regions)}',owner_id='R16_MOVED_LANES:SHARED_LEVEL_FIELD',route_ids=ids,polygon_xz_m=p,plane_policy='Preserve actual source plane; all accepted pieces are already at +2.5 m.'))
 ps=[r['polygon_xz_m']for r in regions];bb=s.bounds(ps);idx=f.SurfaceIndex(scene,windows=[bb],margin=.01)
 print('regions',len(regions),'union area',area(ps),'shared',area(shared),'bounds',bb,flush=True)
 protected=s.a.base.surface_domains(bb,False);protected=[r for r in protected if r['kind']not in('ground','terrace','road','road_shoulder')]+s.EXPLICIT_PROTECTED
 protected += [dict(owner_id=r['id'],kind='new_native_hole',polygon_xz_m=p)for r in s.H['native_foundation_owners']for p in r['polygons_xz_m']]
 protected += [dict(owner_id=r['id'],kind='new_native_walking_obstacle',polygon_xz_m=p)for r in s.N['placements']for p in r['native_walking_obstacles_xz_m']]
 pi=s.a.geo._SpatialIndex(8)
 for k,r in enumerate(protected):pi.add(k,r['polygon_xz_m'])
 conflicts=[]
 for region in regions:
  p=region['polygon_xz_m']
  for k in pi.candidates(p):
   r=protected[k];q=s.a.polygon(s.a.geo.convex_intersection(p,r['polygon_xz_m']))
   if q:conflicts.append(dict(region_id=region['id'],owner_id=r['owner_id'],kind=r['kind'],polygon_xz_m=q,area_m2=s.a.geo.polygon_area(q)))
 assert not conflicts,conflicts[:5]
 sides=side_audit(scene,ps);write('retained_side_obstruction_audit.json',sides)
 assert not sides['above_floor_obstructions'],sides['above_floor_obstructions'][:3]
 clips=[];cover_rows=[]
 for region in regions:
  p=region['polygon_xz_m'];parts=idx.cover(p);cover=sum(s.a.geo.polygon_area(r['intersection_polygon_xz_m'])for r in parts);err=cover-s.a.geo.polygon_area(p);assert abs(err)<1e-7,(region['id'],err)
  for r in parts:
   q=r['intersection_polygon_xz_m'];values=[f.a.height(r['plane_y_xz_m'],v)for v in q];assert max(abs(y-2.5)for y in values)<1e-7
   assert math.hypot(*r['plane_y_xz_m'][:2])<=.12000001
   clips.append(dict(region=region,polygon_xz_m=q,source=r))
  cover_rows.append(dict(region_id=region['id'],area_m2=s.a.geo.polygon_area(p),covered_m2=cover,error_m2=err))
 # Conforming centroid fans: insert every collinear seam knot before fanning.
 # This is the same R15 exact-clipping profile construction, with no new mesher.
 verts=[];buckets=collections.defaultdict(list)
 def weld(p):
  key=tuple(math.floor(v/1e-8)for v in p)
  for dx in(-1,0,1):
   for dz in(-1,0,1):
    for k in buckets[(key[0]+dx,key[1]+dz)]:
     if math.dist(p,verts[k])<1e-8:return k
  k=len(verts);verts.append(list(p));buckets[key].append(k);return k
 rows=[]
 for c in clips:rows.append((c,[weld(p)for p in c['polygon_xz_m']]))
 vi=s.a.geo._SpatialIndex(2)
 for k,p in enumerate(verts):vi.add(k,[p])
 triangles=[];emitted=0.
 for c,ids in rows:
  knots=[]
  for i,j in zip(ids,ids[1:]+ids[:1]):
   p,q=verts[i],verts[j];den=math.dist(p,q)**2;edge=[(0.,i)]
   for k in vi.candidates([p,q]):
    if k in(i,j):continue
    t=sum((verts[k][z]-p[z])*(q[z]-p[z])for z in(0,1))/den
    if 1e-10<t<1-1e-10 and math.dist(verts[k],s.point(p,q,t))<1e-8:edge.append((t,k))
   knots.extend(k for t,k in sorted(edge))
  poly=[verts[k]for k in knots];center=[sum(v[z]for v in poly)/len(poly)for z in(0,1)];plane=c['source']['plane_y_xz_m']
  for p,q in zip(poly,poly[1:]+poly[:1]):
   xyz=f.lift([center,p,q],plane);xyz=f.upward(xyz)
   if f.normal_y(xyz)<=1e-10:continue
   emitted+=f.normal_y(xyz)/2
   material='road'if c['source']['material']=='road'else'ground_stone'
   triangles.append(dict(id=f'R16_MOVED_LANES:TOP:{len(triangles)}',region_id=c['region']['id'],owner_id=c['region']['owner_id'],route_ids=c['region']['route_ids'],material=material,vertices_xyz_m=xyz,polygon_xz_m=[[v[0],v[2]]for v in xyz],plane_y_xz_m=list(plane),actual_triangle_gradient=math.hypot(*f.a.plane(xyz)[:2]),source_r6=source_ref(c['source'])))
 assert abs(emitted-area(ps))<1e-6,(emitted,area(ps))
 # Exact outer boundary ledger. Each segment is evaluated on its own actual
 # R6 source triangle. Height disagreement is reported, never averaged.
 ledger=[];source_incompatible=[]
 for ei,e in enumerate(s.perimeter(ps)):
  pp=s.profile(*e)
  source_incompatible += [dict(edge_index=ei,**k)for k in pp['incompatible_height_knots']]
  for part in pp['pieces']:
   mid=[sum(v[z]for v in e)/2 for z in(0,1)];kind='unchanged_frozen_lateral_plane'
   for route in routes:
    if s.on_edge(mid,route['inner_full_width_edge_xz_m']):kind='fixed_inner_full_width_2_5'
    if s.on_edge(mid,route['terminal_full_width_edge_xz_m']):kind='fixed_public_road_full_width_join'
   src=part['source'];source_triangle=s.TRIS[src['local_snapshot_triangle_index']]
   xyz=part['vertices_xyz_m'];assert max(abs(v[1]-2.5)for v in xyz)<1e-7
   ledger.append(dict(id=f'R16_MOVED_LANES:SEAM:{len(ledger)}',kind=kind,inside_vertices_xyz_m=xyz,outside_vertices_xyz_m=xyz,maximum_height_error_m=0.,retaining=False,source_r6=dict(material=src['material'],triangle_index=src['source_triangle_index'],source_triangle_sha256=f.canonical_sha(src['vertices_m']),vertices_xyz_m=src['vertices_m'],plane_y_xz_m=src['plane_y_xz_m'])))
 assert not source_incompatible,source_incompatible
 end_profiles=[]
 for r in routes:
  end=s.profile(*r['terminal_full_width_edge_xz_m']);inner=s.profile(*r['inner_full_width_edge_xz_m']);assert not end['grade_violations']and not end['incompatible_height_knots']
  assert abs(sum(p['length_m']for p in end['pieces']if p['source']['material']=='road')-r['width_m'])<1e-7
  end_profiles.append(dict(route_id=r['id'],inner=inner,public_road_terminal=end))
 old_domains=s.disjoint([p for h in s.H['terminal_grade_holds']for p in h['bounded_review_polygons_xz_m']]);added=s.a.subtract(ps,old_domains);released=s.a.subtract(old_domains,ps)
 inputs=[ref(f.SCENE_PATH),ref(Path(__file__)),ref(Path(f.__file__)),ref(Path(f.a.__file__)),ref(Path(s.__file__)),ref(HERE/'r6_local_source.json'),ref(HERE/'level_approach_candidates.json'),ref(HERE/'gate_preserving_level_candidates.json')]+[ref(s.PACK/n)for n in s.EXPECTED]
 for p in sorted(s.READ_INPUTS):
  if p.exists() and p.is_relative_to(ROOT) and p.suffix in('.py','.json','.npz')and not p.is_relative_to(HERE):
   r=ref(p)
   if r not in inputs:inputs.append(r)
 body=dict(schema='riverstone.r16_moved_lane_profiles.v1',status='EXACT_R6_LEVEL_SOURCE_PROFILES_PENDING_PARENT_COMPOSITION_AND_INDEPENDENT_AUDIT',accepted=False,scene_activated=False,base_scene_sha256=f.SCENE_SHA256,source_scene=ref(f.SCENE_PATH),input_bindings=inputs,
  solution_method='Move only the finite held tails to level LOWER_CONTOUR joins, preserve original source gate reservations, retain each exact corrected-R6 triangle plane, and compose both lanes into a single shared owner. No height solve or public-road height edits are needed.',
  replaced_source_route_ids=[r['id']for r in routes],routes=routes,regions=regions,triangles=triangles,boundary_seam_ledger=ledger,full_width_profiles=end_profiles,affected_old_side_masks=[],retaining_sides=[],retained_side_obstruction_audit=ref(HERE/'retained_side_obstruction_audit.json'),protected_owner_conflicts=conflicts,source_height_conflicts=source_incompatible,
  changed_route_footprint=dict(added_area_m2=area(added),released_old_terminal_area_m2=area(released),added_polygons_xz_m=added,released_polygons_xz_m=released,released_policy='Original R6 source remains unchanged; these released reservation pieces are not new walking surface.'),
  proof=dict(union_area_m2=area(ps),emitted_triangle_area_m2=emitted,coverage_error_m2=emitted-area(ps),per_region_coverage=cover_rows,shared_route_overlap_m2=area(shared),shared_field_single_ownership=True,all_tops_positive_y=all(f.normal_y(t['vertices_xyz_m'])>0 for t in triangles),maximum_actual_triangle_gradient=max(t['actual_triangle_gradient']for t in triangles),grade_limit=.12,maximum_source_plane_change_m=0.,maximum_frozen_boundary_height_error_m=0.,protected_overlap_m2=0.,output_triangle_count=len(triangles),source_triangle_count=len({(t['source_r6']['material'],t['source_r6']['triangle_index'])for t in triangles})),
  scope_limits=['No full scene export or native compilation.','Source gates retain their positions and widths, but native jamb/leaf authoring remains a separate hold.','Final independent patch composition, actual scene review and exterior capsule validation remain parent gates.','Both old original fixed-seam failures remain preserved in prior evidence.'])
 write('level_profile_handoff.json',body)
 write('level_profile_summary.json',{k:body[k]for k in('status','base_scene_sha256','solution_method','replaced_source_route_ids','routes','proof','scope_limits')})
 print(json.dumps({k:body['proof'][k]for k in('union_area_m2','emitted_triangle_area_m2','coverage_error_m2','shared_route_overlap_m2','maximum_actual_triangle_gradient','output_triangle_count','source_triangle_count')}),flush=True)
if __name__=='__main__':main()
