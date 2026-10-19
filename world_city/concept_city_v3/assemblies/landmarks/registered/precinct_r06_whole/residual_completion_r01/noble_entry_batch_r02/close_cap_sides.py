"""Close only uncovered native-side/cap-remainder vertical intervals."""
from build_ground_patch import *
from world_city.concept_city_v3.registered_integration.r8 import compose_finite_patches as compose
from world_city.concept_city_v3.registered_integration.r6 import merge_patches as merger
from finite_collision_clip import area3
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.audit_retired_boundaries import interval

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--normalization',required=True);args=ap.parse_args();nd=Path(args.normalization).resolve();binding=load(nd/'binding.json');reviewpath=CITY/'registered_topography/revisions/public_corridors_r18/noble_r02_public_ownership_final_review.json';review=load(reviewpath);ground=load(OUT/'native_ground_candidate_audit.json');assert review['edge_count']==47 and not review['positive_area_owner_conflicts']
 down={r['id']:r for r in ground['new_native_undersides']};collars={r['id']:r for r in ground['private_sampling_collars']};tops=ground['new_native_upward_faces'];ti=geo._SpatialIndex(2)
 for i,r in enumerate(tops):ti.add(i,r['polygon_xz_m'])
 sides=[];si=geo._SpatialIndex(4)
 for pr in binding['patches']:
  p=load(ROOT/pr['path'])
  for mat,vs in p['appended_surfaces'].items():
   if mat!='bank':continue
   for i in range(len(vs)//3):
    tr=vs[3*i:3*i+3];q=[[v[0],v[2]]for v in tr]
    si.add(len(sides),q);sides.append(dict(patch=pr,material=mat,appended_triangle_index=i,triangle=tr))
 new=[];rows=[]
 for e in review['edges']:
  base=down.get(e['owner_id']);collar=collars.get(e['owner_id']);assert base or collar
  segments=[]
  for original in e['public_segments']:
   u,v=original['interval'];knots={u,v};a,z=e['edge_xz_m']
   if base:
    for j in ti.candidates(e['edge_xz_m']):
     r=tops[j]
     if r['native_id']!=base['native_id']:continue
     span=interval(a,z,r['polygon_xz_m'])
     if span:
      knots.update(x for x in span if u<x<v)
   ks=sorted(knots)
   segments +=[dict(original,interval=[l,h])for l,h in zip(ks,ks[1:])if (h-l)*math.dist(a,z)>1e-8]
  for s in segments:
   a,z=e['edge_xz_m'];u,v=s['interval'];edge=[[a[k]+t*(z[k]-a[k])for k in(0,1)]for t in(u,v)];mid=[sum(p[k]for p in edge)/2 for k in(0,1)];neighbor=[terrain.common.height(s['plane_y_xz_m'],x)for x in edge]
   if base:
    lo=base['plane_y_xz_m'][2];candidates=[tops[j]for j in ti.candidates([mid])if tops[j]['native_id']==base['native_id']and geo.point_in_convex_polygon(mid,tops[j]['polygon_xz_m'],1e-8)];assert candidates,(e['owner_id'],mid);top=max(r['plane_y_xz_m'][2]for r in candidates);native=[min(top,max(lo,y))for y in neighbor]
   else:
    native=[terrain.common.height(collar['plane_y_xz_m'],x)for x in edge];lo=min(native);top=max(native)
   q=[[edge[0][0],native[0],edge[0][1]],[edge[1][0],native[1],edge[1][1]],[edge[1][0],neighbor[1],edge[1][1]],[edge[0][0],neighbor[0],edge[0][1]]];desired=[t for t in([q[0],q[1],q[2]],[q[0],q[2],q[3]])if area3(t)>1e-10];remaining=[];coverage=[]
   for tr in desired:
    n,L,d,project,unproject=compose.project_frame(tr);poly=[project(x)for x in tr];masks=[]
    for j in si.candidates(edge):
     old=sides[j];t=old['triangle']
     if max(abs(compose.dot(n,x)-d)/L for x in t)>1e-8:continue
     pp=[project(x)for x in t];c=fg.clip(poly,pp)
     if fg.area(c)>1e-12:masks.append(pp);coverage.append(dict(patch=old['patch'],material=old['material'],appended_triangle_index=old['appended_triangle_index'],source_triangle_sha256=merger.canonical_sha(t)))
    for p in fg.subtract([poly],masks):
     vs=[unproject(x)for x in p]
     for k in range(1,len(vs)-1):
      t=[vs[0],vs[k],vs[k+1]]
      if area3(t)>1e-10:
       if compose.dot(n,compose.cross(compose.sub(t[1],t[0]),compose.sub(t[2],t[0])))<0:t=[t[0],t[2],t[1]]
       remaining.append(t)
   new+=remaining;rows.append(dict(native_owner_id=e['owner_id'],neighbor_owner_id=s['owner_id'],kind=s['kind'],edge_xz_m=edge,native_bottom_y_m=lo,native_top_y_m=top,neighbor_plane_y_xz_m=s['plane_y_xz_m'],desired_triangles_xyz_m=desired,existing_exact_side_coverage=coverage,new_nonwalking_triangles_xyz_m=remaining))
 assert len(review['edges'])==47 and all(not e['uncovered_intervals']for e in review['edges'])
 deps=[(r,load(ROOT/r['path']))for r in binding['patches']if load(ROOT/r['path'])['id']in('R8_NOBLE_SEVEN_FINE_ENTRY_R01','R8_JOINT_61_BOUNDARY_NORTH_EXACT_REBOUND_FINAL_R01')]
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R8_NOBLE_R02_EXACT_CAP_REMAINDER_SIDE_CLOSURE',status='SOURCE_READY_RUNTIME_PENDING',base_scene_sha256=terrain.SCENE_SHA256,source_surface_hashes={},surface_edits=[],appended_surfaces={'bank':[v for tr in new for v in tr]},removed_foundation_proxy_ids=[],requires_patch_ids=[p['id']for r,p in deps],requires_patch_canonical_sha256={p['id']:merger.canonical_sha(p)for r,p in deps},source_references=[ref(reviewpath),ref(OUT/'native_ground_candidate_audit.json')]+[r for r,p in deps])
 write('cap_remainder_side_patch.json',patch);write('cap_remainder_side_audit.json',dict(status='PASS_EXACT_NONWALKING_CAP_INTERVAL_CLOSURE',public_ownership=ref(reviewpath),normalization_binding=ref(nd/'binding.json'),source_native=ref(OUT/'resolved_native_candidate.json'),rows=rows,summary=dict(accepted_edges=47,intervals=len(rows),new_triangles=len(new),new_side_area_m2=sum(area3(t)for t in new),four_other_edges_retained_base_closed=True),retained_base_face_proof=ref(OUT/'native_edge_diagnosis.json'),runtime_ready=False));print('cap sides',len(rows),len(new),sum(area3(t)for t in new),flush=True)
if __name__=='__main__':main()
