"""Freeze bounded source-verified inputs without changing any producer/shared asset."""
from build_candidate import *
import shutil

def main():
 p=read(H/'surface_patch.json');s=read(BASE);owners=p['ownership'][0]['ownership_polygons_xz_m'];seen=set();errors=[]
 assert sha(BASE)==SHA
 for m,h in p['source_surface_hashes'].items():assert ch(s['surfaces'][m])==h
 for e in p['surface_edits']:
  key=(e['material'],e['triangle_index']);assert key not in seen;seen.add(key);t=s['surfaces'][key[0]][key[1]*3:key[1]*3+3];assert t==e['source_triangle_xyz_m']and ch(t)==e['source_triangle_sha256']
  a=np.asarray(t);normal=np.cross(a[1]-a[0],a[2]-a[0])
  for rr in e['replacement_triangles_xyz_m']:
   b=np.asarray(rr);assert np.dot(normal,np.cross(b[1]-b[0],b[2]-b[0]))>0
   assert max(abs(float(np.dot(normal,v-a[0])))for v in b)<1e-5
   assert all(geo.intersection_area([xz(v)for v in rr],o)<1e-6 for o in owners)
 for m,vs in p['appended_surfaces'].items():
  for k in range(0,len(vs),3):
   t=np.asarray(vs[k:k+3],dtype=np.float32);n=np.cross(t[1]-t[0],t[2]-t[0]);assert np.dot(n,n)>0 and (m=='bank'or n[1]>0)
   assert geo.uncovered_area_by_union([xz(v)for v in vs[k:k+3]],owners)<1e-6
 new_area=sum(geo.polygon_area([xz(v)for v in vs[k:k+3]])for vs in p['appended_surfaces'].values()for k in range(0,len(vs),3));owner_area=sum(geo.polygon_area(o)for o in owners);assert abs(new_area-owner_area)<1e-5
 pack=read(H/'pack.json');asset_checks=[]
 for key,a in pack['common_assets'].items():
  master=ROOT/(a.get('master_path')or a['source']['path']);render=ROOT/(a.get('render_path')or a['cache']['path']);assert sha(master)==(a.get('master_sha256')or a['source']['sha256']);assert sha(render)==(a.get('render_sha256')or a['cache']['sha256']);asset_checks.append(dict(id=key,master=ref(master),render=ref(render),unchanged=True))
 write('exact_patch_audit.json',dict(status='PASS_EXACT_FINITE_SOURCE_AND_NATIVE_REFERENCES',base_unchanged=True,source_face_edits=len(seen),source_surface_hashes_verified=True,outside_fragments_on_original_planes=True,appended_float32_valid=True,owned_area_m2=owner_area,appended_projected_area_m2=new_area,numeric_sliver_difference_m2=owner_area-new_area,numeric_total_area_tolerance_m2=1e-5,assets=asset_checks,limited_scope='Static geometry only; pending unchanged-controller replay and scene view.'))
 clergy=read(H/'context.json')['sites']['clergy'];proposals=[('HIGH_APPROACH_INNER',[[172.9278912093672,-198.19427223270506],[187.9,-174],[189.5,-168],[188.5,-157],[193,-146.5],[198,-137.5],[204.18127359,-129.88806654],[205.87179725,-130.95677125]]),('HIGH_APPROACH_WEST_SHIFT',[[172.9278912093672,-198.19427223270506],[187.9,-174],[189.5,-168],[187,-156.5],[192,-146],[198,-137.5],[204.18127359,-129.88806654],[205.87179725,-130.95677125]])];out=[]
 for iid,pts in proposals:
  hits=[]
  for n,(a,b)in enumerate(zip(pts,pts[1:])):
   q=geo.road_ribbon(a,b,2.)
   for r in clergy['bodies']:
    ar=geo.intersection_area(q,r['polygon_xz_m'])
    if ar>1e-8:hits.append(dict(segment_index=n,native_instance_id=r['id'],positive_area_contact_m2=ar))
  out.append(dict(id=iid,width_m=2,polyline_xz_m=pts,length_horizontal_m=sum(math.dist(a,b)for a,b in zip(pts,pts[1:])),contacts=hits,status='REJECT_THIS_POLYLINE_PENDING_BOUNDED_RELOCATION_OR_NEW_ALIGNMENT'))
 write('clergy_options.json',dict(status='NOT_IMPLEMENTED',options=out,low_alley_option=dict(horizontal_gap_m=22.6517,height_gap_m=8.45624,status='Requires actual stairs/landings or staffed lower frontage with separate institution supply; no flat-path claim'),high_approach_option='The high forecourt is a real near-level public origin. Two exact 2m candidate alignments contact existing precinct walls/crop beds. This rejects only these lines, not all possible high approaches.',next_bounded_decision='Investigate one short boundary/crop-bed relocation or a narrower actual clear route before any further construction. No institution scale increase is needed.'))
 out=H/'candidate_r01';out.mkdir(exist_ok=False)
 files=['pack.json','surface_patch.json','ground_ownership.json','source_tests.json','float32_filter_report.json','exact_patch_audit.json','clergy_options.json']
 for n in files:shutil.copy2(H/n,out/n)
 idx=read(H/'index.json');idx['packs'][-1]=ref(out/'pack.json');(out/'index.json').write_text(json.dumps(idx,indent=2)+'\n')
 r=read(H/'routes.json');r['finite_patch']=ref(out/'surface_patch.json');r['visual_index']=ref(out/'index.json');r['gate_native_id']='R06_ABBEY_GATE_R05:herb';r['gate_source_id']='ABBEY_NORTH_WORK:main_gate';r['gate_center_xyz_m']=[-259,8,-7.823607];r['gate_clear_width_m']=4;r['ward_source_id']='ABBEY_NORTH_WORK:infirmary:actual_entry';r['ward_door_center_xyz_m']=[-324,8,-16];r['source_plan']=ref(C/'registered_source/plan.json');(out/'routes.json').write_text(json.dumps(r,indent=2)+'\n')
 snaps=out/'source_snapshot';snaps.mkdir()
 for n in ['build_candidate.py','validate_candidate.py','filter_float32.py','inspect_context.py','probe_routes.py','audit_and_freeze.py']:shutil.copy2(H/n,snaps/n)
 deps=[C/'review_geometry.py',ROOT/'world_city/runtime_city/checks/placement.py',C/'registered_integration/r9/landward_gates/build_corridors.py',C/'validation/check_landmark_access_candidate.py',H/'context.json']
 manifest=dict(status='FROZEN_SOURCE_PASS_RUNTIME_AND_SCENE_VIEW_PENDING',base_scene=ref(BASE),files={str(x.relative_to(out)):sha(x)for x in out.rglob('*')if x.is_file()},source_dependencies=[ref(q)for q in deps],scope='One public arrival, one admission-only ward path. No unrestricted inner-court through-route, cart, medical capacity or interior gameplay claim.')
 (out/'FROZEN.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(candidate=str(out.relative_to(ROOT)),routes=ref(out/'routes.json'),patch=ref(out/'surface_patch.json'),index=ref(out/'index.json')),indent=2))
if __name__=='__main__':main()
