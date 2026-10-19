"""Independent robust triangle, ownership, cut/fill, and retaining-side checks."""
from inspect_extents import *
from solve_interfaces import distance, retired_at

def strict(p,poly,eps=1e-7):
 sign=1 if a.geo.signed_polygon_area(poly)>0 else -1
 return all(sign*a.geo._cross(u,v,p)>eps*math.dist(u,v) for u,v in zip(poly,poly[1:]+poly[:1]))
def cut_positive(poly,plane):
 A,B,C=plane;den=A*A+B*B
 if den<1e-24:return poly if C>=0 else None
 q=[-C*A/den,-C*B/den];r=[q[0]+B,q[1]-A]
 return a.polygon(a.geo._clip_halfplane(poly,q,r,1.,0.,True))
def volume(poly,plane):
 return sum(a.geo.polygon_area(t)*sum(a.plane_height(plane,*v) for v in t)/3 for t in fan(poly)) if poly else 0.

def audit(path):
 r=json.loads(path.read_text());source={s['material']+':'+str(s['triangle_index']):s for s in r['source_triangles']};tris=r['triangles'];idx=a.geo._SpatialIndex(2);areas=[];overlap=0.;protected_overlap=0.;cut=fill=0.;maximum=0.;slender=[]
 for k,t in enumerate(tris):
  poly=t['polygon_xz_m'];area=a.geo.polygon_area(poly);areas.append(area);plane=a.affine_plane(t['vertices_xyz_m']);grade=math.hypot(*plane[:2]);maximum=max(maximum,grade);edgelengths=[math.dist(p,q) for p,q in zip(poly,poly[1:]+poly[:1])];height=2*area/max(edgelengths);slender.append(height/max(edgelengths))
  for j in idx.candidates(poly):
   q=a.polygon(a.geo.convex_intersection(poly,tris[j]['polygon_xz_m']))
   if q:overlap+=a.geo.polygon_area(q)
  idx.add(k,poly)
  for pr in r['protected_owners']:
   q=a.polygon(a.geo.convex_intersection(poly,pr['polygon_xz_m']))
   if q:protected_overlap+=a.geo.polygon_area(q)
  if t['source_key']:
   old=source[t['source_key']]['plane_y_xz_m'];delta=[plane[j]-old[j] for j in range(3)];pos=cut_positive(poly,delta);neg=cut_positive(poly,[-v for v in delta]);fill+=volume(pos,delta);cut-=volume(neg,delta)
 retaining_conflicts=[];retaining_ranges=[]
 for side in r.get('retaining_sides',[]):
  pp=[[v[0],v[2]] for v in side['inside_vertices_xyz_m']];mid=[sum(v[j] for v in pp)/2 for j in(0,1)];owner=a.effective_record_after_retirement(*mid);gate_inside=any(strict(mid,g['polygon_xz_m']) for g in C['gate_profiles']);public_inside=owner.get('kind') in('road','replacement_road','port_tie','external_triangular_surface','reservoir_service_public_landing','door_landing','door_approach','b015_entry','density_entry') and owner.get('polygon_xz_m') and strict(mid,owner['polygon_xz_m'])
  if gate_inside or public_inside:retaining_conflicts.append(dict(side_id=side['id'],midpoint_xz_m=mid,owner_id=owner.get('owner_id'),owner_kind=owner.get('kind'),inside_gate=gate_inside,inside_public=bool(public_inside)))
  retaining_ranges.append(dict(id=side['id'],maximum_height_difference_m=max(abs(p[1]-q[1]) for p,q in zip(side['inside_vertices_xyz_m'],side['outside_frozen_vertices_xyz_m'])),inherited_owner_kind=owner.get('kind'),inherited_owner_id=owner.get('owner_id')))
 frozen_errors=[abs(p[1]-q[1]) for b in r['boundary'] if b['kind'] in('frozen_outer_seam','protected_entrance_frozen_seam') for p,q in zip(b['vertices_xyz_m'],b['frozen_vertices_xyz_m'])]
 report=dict(index=r['index'],property_id=r['property_id'],path=path.name,profile_sha256=a.sha(path),maximum_actual_clipped_triangle_gradient=maximum,minimum_triangle_area_m2=min(areas),minimum_triangle_altitude_to_longest_edge_ratio=min(slender),triangle_pair_positive_overlap_area_m2=overlap,protected_owner_overlap_area_m2=protected_overlap,triangle_area_minus_masks_m2=sum(areas)-r['mask_area_m2'],gate_coverage_error_m2=r['proof']['gate_area_error_m2'],full_inner_width_m=r['gate_width_m'],inner_datum_error_m=r['proof']['gate_inner_datum_error_m'],fixed_frozen_seam_error_m=max(frozen_errors,default=0.),cut_volume_against_removed_frozen_faces_m3=cut,fill_volume_against_removed_frozen_faces_m3=fill,net_volume_m3=fill-cut,maximum_cut_m=r['proof']['maximum_cut_m'],maximum_fill_m=r['proof']['maximum_fill_m'],retaining_side_count=len(r.get('retaining_sides',[])),retaining_side_walking_conflicts=retaining_conflicts,retaining_sides=retaining_ranges,regression_guard='Every actual final clipped triangle measured; the historical 0.483 skinny-triangle failure is not waived by an analytic grade.',status='PASS' if maximum<=.12000001 and overlap<1e-7 and protected_overlap<1e-7 and abs(sum(areas)-r['mask_area_m2'])<1e-7 and abs(r['proof']['gate_area_error_m2'])<1e-7 and max(frozen_errors,default=0.)<1e-8 and not retaining_conflicts else 'FAIL')
 print(report['index'],report['status'],'grade',maximum,'protected',protected_overlap,'overlap',overlap,'retaining conflicts',retaining_conflicts,flush=True);return report

def run():
 reports=[]
 for path in sorted(HERE.glob('retaining_bound_interface_*.json')):
  r=json.loads(path.read_text())
  if 'triangles' in r:reports.append(audit(path))
 out=dict(schema='riverstone.r15_public_profile_independent_audit.v1',source_contract_sha256=a.sha(HERE.parent/'source_contract.json'),source_scene_sha256=a.sha(SCENE),reports=reports,pass_count=sum(r['status']=='PASS' for r in reports),limitations=['This finite geometry audit does not activate a scene or certify capsule traversal.','Exact frozen matching applies to public/door exterior seams. Separately declared inherited backland retaining sides preserve both heights.'])
 (HERE/'solved_profiles_audit.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':run()
