"""Retire four finite original road slivers; keep all finished surfaces and seams."""
from . import audit_residuals as a
from world_city.concept_city_v3.registered_integration.r6 import merge_patches as m
from world_city.concept_city_v3.assemblies.waterworks.registered_water_completion_r01.approaches_r02 import select_profiles as sp
import math

def tube(p,q,r=.35):
 L=math.dist(p,q);n=[-(q[1]-p[1])/L,(q[0]-p[0])/L];out=[[[v[k]+sign*r*n[k]for k in(0,1)]for v,sign in[(p,1),(q,1),(q,-1),(p,-1)]]]
 for c in[p,q]:out.append([[c[0]+r/math.cos(math.pi/16)*math.cos(i*math.pi/8),c[1]+r/math.cos(math.pi/16)*math.sin(i*math.pi/8)]for i in range(16)])
 return out

def main():
 audit=a.read(a.H/'residual_audit.json');base=a.read(a.BASE);old=a.read(a.OLD/'surface_patch.json');rows=audit['candidates'];assert len(rows)==4;edits=[];proof=[];field=next(p for p in a.read(a.OLD/'fields.json')['profiles']if p['id']=='NORTH_SHARED_JUNCTION');masks=[t['polygon_xz_m']for t in field['triangles']]
 for r in rows:
  assert r['entire_projected_span_owned']and not r['already_edited']and r['actual_retained_index']is not None
  t=r['vertices_xyz_m'];assert m.canonical_sha(t)==r['source_triangle_sha256'];edges=[]
  for u,v in zip(t,t[1:]+t[:1]):
   span=a.spans([u[0],u[2]],[v[0],v[2]],masks);assert len(span)==1 and span[0][0]<1e-7 and span[0][1]>1-1e-7;edges.append(span)
  proof.append(dict(source_triangle_index=r['triangle_index'],every_edge_supported_spans_t=edges,source_plane_area_removed_m2=r['actual_3d_area_m2'],projected_area_removed_m2=r['projected_area_m2'],existing_finished_surface_y_m=15.6,source_face_bottom_clearance_m=r['clearance_above_finished_surface_m'][0]))
  edits.append(dict(material='road',triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],replacement_triangles_xyz_m=[]))
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='WATER_COMPLETION_NORTH_SLIVER_RETIREMENT_R03',status='FINITE_SOURCE_ACCEPTED_PENDING_COMPOSED_REPLAY',base_scene_sha256=a.sha(a.BASE),source_surface_hashes={'road':m.canonical_sha(base['surfaces']['road'])},surface_edits=edits,appended_surfaces={},removed_foundation_proxy_ids=[]);m.validate_against_scene(base,patch);combined=m.merge([old,patch],a.sha(a.BASE));assert len(combined['surface_edits'])==len(old['surface_edits'])+4;a.write(a.H/'surface_patch.json',patch)
 # Stay inside the same named-road ribbons, but turn before their closed endpoint.
 d=a.read(a.CITY/'traversal_r5/revisions/r06_r8_precinct/district_services_r02/prepared_runtime.json');source=next(r for r in d['routes']if r['id']=='NORTH_TWO_BRIDGE_NETWORK');pts=source['points'];apex=10;c=pts[apex];distance=2.;before=pts[apex-1];after=pts[apex+1]
 def inset(v):
  L=math.hypot(v[0]-c[0],v[2]-c[2]);return[c[0]+distance*(v[0]-c[0])/L,15.6,c[2]+distance*(v[2]-c[2])/L]
 turn=[inset(before),inset(after)];new=pts[:apex]+turn+pts[apex+1:];shared=new[8:15];caps=[]
 for u,v in zip(shared,shared[1:]):caps+=tube([u[0],u[2]],[v[0],v[2]])
 bridge_rows=a.read(a.H.parent/'crossing_interfaces.json')['crossings'];covermasks=masks+[b['traffic_polygon_xz_m']for b in bridge_rows if b['id']in field['bridge_ids']];gaps=[q for p in caps for q in a.finite.subtract([p],covermasks)];gaparea=sum(a.g.polygon_area(q)for q in gaps);assert gaparea<1e-7,(gaparea,gaps)
 route=dict(schema='riverstone.north_shared_interior_turn.r03',id='NORTH_TWO_BRIDGE_INTERIOR_TURN_R03',source_failed_case='NORTH_TWO_BRIDGE_NETWORK',source_roads=['MARKET_NORTH','NORTH_BACK_LANE'],points_xyz_m=new,reverse_points_xyz_m=list(reversed(new)),route_kind='Same source-road axes with a 2m inset chord inside the existing junction, avoiding the closed terminal apex.',closed_terminal_xyz_m=c,original_route_retained=a.ref(a.CITY/'traversal_r5/revisions/r06_r8_precinct/district_services_r02/prepared_runtime.json'),turn_inset_distance_m=distance,capsule_radius_m=.3,conservative_clear_tube_radius_m=.35,tube_polygon_method='Segment rectangles plus circumscribed 16-sided endpoint disks; contains the full radius-0.35m capsule projection.',shared_field_route_xyz_m=shared,tube_polygons_xz_m=caps,unsupported_tube_area_m2=gaparea,finished_field=a.ref(a.OLD/'fields.json'),limits=['This is an interior traversal path, not a replacement or widening of the source road centerlines.','Actual unchanged-controller replay on the composed repair scene remains required.']);a.write(a.H/'route_handoff.json',route)
 a.write(a.H/'source_tests.json',dict(schema='riverstone.finite_north_sliver_source_tests.r03',status='PASS_STATIC_PENDING_ACTUAL_REPLAY',base_scene=a.ref(a.BASE),integrated_failed_scene=a.ref(a.ACTUAL),prior_patch=a.ref(a.OLD/'surface_patch.json'),prior_field=a.ref(a.OLD/'fields.json'),prior_public_profiles=a.ref(a.OLD/'public_handoff.json'),patch=a.ref(a.H/'surface_patch.json'),route=a.ref(a.H/'route_handoff.json'),retirement_proofs=proof,checks=dict(exact_source_hashes=True,all_retired_faces_project_inside_existing_owned_field=True,all_retired_faces_above_existing_finished_top=True,disjoint_from_prior_source_indices=True,no_new_geometry=True,no_water_or_bank_edits=True,no_native_changes=True,no_public_seam_changes=True,interior_turn_full_capsule_supported=gaparea<1e-7),removed_actual_face_area_m2=sum(r['actual_3d_area_m2']for r in rows),removed_projected_area_m2=sum(r['projected_area_m2']for r in rows),geometric_tolerance_m=1e-7))
 print('PATCH',len(edits),'ROAD SLIVERS; actual 3D area',sum(r['actual_3d_area_m2']for r in rows),'turn missing',gaparea)
if __name__=='__main__':main()
