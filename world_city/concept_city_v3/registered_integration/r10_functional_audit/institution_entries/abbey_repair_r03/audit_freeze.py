"""Exact source, continuous-top and side-closure checks, then freeze r03."""
from build_repair import *
import shutil

def main():
 p=read(H/'surface_patch.json');s=read(BASE);owners=p['ownership'][0]['ownership_polygons_xz_m'];seen=set();assert sha(BASE)==SHA
 for m,h in p['source_surface_hashes'].items():assert ch(s['surfaces'][m])==h
 for e in p['surface_edits']:
  key=(e['material'],e['triangle_index']);assert key not in seen;seen.add(key);t=s['surfaces'][key[0]][key[1]*3:key[1]*3+3];assert t==e['source_triangle_xyz_m']and ch(t)==e['source_triangle_sha256'];a=np.asarray(t);normal=np.cross(a[1]-a[0],a[2]-a[0])
  for rr in e['replacement_triangles_xyz_m']:
   b=np.asarray(rr);assert np.dot(normal,np.cross(b[1]-b[0],b[2]-b[0]))>0;assert max(abs(float(np.dot(normal,v-a[0])))for v in b)<1e-5;assert all(g.intersection_area([xz(v)for v in rr],o)<1e-6 for o in owners)
 for m,vs in p['appended_surfaces'].items():
  for k in range(0,len(vs),3):
   t=np.asarray(vs[k:k+3],dtype=np.float32);n=np.cross(t[1]-t[0],t[2]-t[0]);assert np.dot(n,n)>0 and (m=='bank'or n[1]>0);assert g.uncovered_area_by_union([xz(v)for v in vs[k:k+3]],owners)<1e-6
 newarea=sum(g.polygon_area([xz(v)for v in vs[k:k+3]])for m,vs in p['appended_surfaces'].items()if m!='bank'for k in range(0,len(vs),3));ownerarea=sum(g.polygon_area(o)for o in owners);assert abs(newarea-ownerarea)<1e-8
 # Every original source face wholly inside the finite owner must be edited,
 # including microscopic faces that are significant to capsule contact.
 unedited_inside=[];retained_intrusions=[]
 for rr in source_rows():
  tt=rr['triangle'];pp=[xz(v)for v in tt];key=(rr['material'],rr['triangle_index'])
  if rr['material']=='water':continue
  full=all(g.point_in_convex_polygon(v,owners[0],0)for v in pp)
  if full and key not in seen:unedited_inside.append(key)
 edits={(e['material'],e['triangle_index']):e for e in p['surface_edits']}
 for rr in source_rows():
  if rr['material']=='water':continue
  key=(rr['material'],rr['triangle_index']);ee=edits.get(key);triangles=ee['replacement_triangles_xyz_m']if ee else[rr['triangle']]
  for tt in triangles:
   cur=tt
   for aa,bb in zip(owners[0],owners[0][1:]+owners[0][:1]):
    if not cur:break
    cur,_=split3(cur,aa,bb,1)
   ar=sum(area3(t)for t in fan(cur))if len(cur)>=3 else 0.
   if ar>1e-12:retained_intrusions.append(dict(source=key,area3_inside_m2=ar))
 assert not unedited_inside,unedited_inside
 assert not retained_intrusions,retained_intrusions
 old=Ground(source_rows());top=Ground([dict(material=m,triangle_index=k//3,triangle=vs[k:k+3])for m,vs in p['appended_surfaces'].items()if m!='bank'for k in range(0,len(vs),3)]);cl=read(H/'closure_ledger.json');closure=cl['perimeter_closure'];sample_count=0;covered=0;maxdiff=0;missing=[]
 owner=owners[0]
 for side,(a,b)in enumerate(zip(owner,owner[1:]+owner[:1])):
  length=math.dist(a,b);n=math.ceil(length/.1);outward=[(b[1]-a[1])/length,-(b[0]-a[0])/length]
  for j in range(n):
   t=(j+.5)/n;q=[a[k]+t*(b[k]-a[k])for k in [0,1]];probe=[q[k]+outward[k]*1e-6 for k in [0,1]];sample_count+=1
   try:oldy=old.at(probe)
   except ValueError:oldy=8.
   newy=top.at(q);delta=abs(newy-oldy);maxdiff=max(maxdiff,delta)
   if delta<2e-5:continue
   matches=[r for r in closure if r['side']==side and g.point_segment_distance(q,r['from_xz_m'],r['to_xz_m'])<1e-7]
   if matches:covered+=1
   else:missing.append(dict(side=side,point=q,old_y_m=oldy,new_y_m=newy))
 assert not missing,missing
 pack=read(H/'pack.json');refs=[]
 for k,a in pack['common_assets'].items():
  m=ROOT/(a.get('master_path')or a['source']['path']);r=ROOT/(a.get('render_path')or a['cache']['path']);assert sha(m)==(a.get('master_sha256')or a['source']['sha256']);assert sha(r)==(a.get('render_sha256')or a['cache']['sha256']);refs.append(dict(id=k,master=ref(m),render=ref(r)))
 audit=dict(status='SOURCE_CONTINUOUS_TOP_CLOSED_PERIMETER_PASS_RUNTIME_VISUAL_PENDING',base_unchanged=True,exact_source_face_checks=len(seen),outside_source_plane_preserved=True,new_top_projected_area_m2=newarea,owned_area_m2=ownerarea,projected_area_error_m2=ownerarea-newarea,top_internal_height_jump_count=cl['internal_height_jump_count'],outer_boundary_samples=sample_count,samples_needing_and_having_side_closure=covered,maximum_outer_retained_level_difference_m=maxdiff,unclosed_sample_count=0,unedited_source_faces_wholly_inside_owner=len(unedited_inside),retained_source_intrusions=len(retained_intrusions),common_assets=refs,view_requirement='Repeat the same eye view that failed r01. A source pass is not acceptance.');write('exact_patch_audit.json',audit)
 out=H/'candidate_r03';out.mkdir(exist_ok=False)
 for n in ['pack.json','surface_patch.json','ground_ownership.json','source_tests.json','closure_ledger.json','exact_patch_audit.json']:shutil.copy2(H/n,out/n)
 idx=read(H/'index.json');idx['packs'][-1]=ref(out/'pack.json');(out/'index.json').write_text(json.dumps(idx,indent=2)+'\n');r=read(H/'routes.json');r['finite_patch']=ref(out/'surface_patch.json');r['visual_index']=ref(out/'index.json');r['gate_native_id']='R06_ABBEY_GATE_R05:herb';r['gate_source_id']='ABBEY_NORTH_WORK:main_gate';r['gate_center_xyz_m']=[-259,8,-7.823607];r['gate_clear_width_m']=4;r['ward_source_id']='ABBEY_NORTH_WORK:infirmary:actual_entry';r['ward_door_center_xyz_m']=[-324,8,-16];r['source_plan']=ref(C/'registered_source/plan.json');r['supersedes_failed_candidate']=ref(H.parent/'candidate_r01/FROZEN.json');(out/'routes.json').write_text(json.dumps(r,indent=2)+'\n')
 snap=out/'source_snapshot';snap.mkdir()
 for n in ['build_repair.py','validate_repair.py','audit_freeze.py','finite_helpers_frozen.py','build_corridors_r07_preserved.py']:shutil.copy2(H/n,snap/n)
 deps=[C/'review_geometry.py',ROOT/'world_city/runtime_city/checks/placement.py',H/'finite_helpers_frozen.py',H/'build_corridors_r07_preserved.py',C/'validation/check_landmark_access_candidate.py',H.parent/'context.json'];manifest=dict(status='FROZEN_SOURCE_REPAIR_PASS_RUNTIME_AND_SCENE_VIEW_PENDING',base_scene=ref(BASE),files={str(q.relative_to(out)):sha(q)for q in out.rglob('*')if q.is_file()},source_dependencies=[ref(q)for q in deps],prior_failed_view=ref(C/'evidence/r10_functional_r01/R10_ABBEY_PUBLIC_GATE_EYE.png'));(out/'FROZEN.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps(dict(candidate=str(out.relative_to(ROOT)),routes=ref(out/'routes.json'),patch=ref(out/'surface_patch.json'),index=ref(out/'index.json'),audit=audit),indent=2))
if __name__=='__main__':main()
